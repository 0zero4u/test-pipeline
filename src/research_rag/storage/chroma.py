"""Chroma vector store for chunk storage and retrieval."""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from research_rag.embeddings import EmbeddingService
from research_rag.models import Chunk, DocumentMetadata

logger = logging.getLogger(__name__)

COLLECTION_NAME = "research_chunks"
DEFAULT_CHROMA_PATH = Path("./data/chroma")


@dataclass
class ChromaConfig:
    """Configuration for Chroma index tuning."""

    hnsw_space: str = "cosine"
    hnsw_m: int = 16
    hnsw_construction_ef: int = 100
    hnsw_search_ef: int = 50
    upsert_batch_size: int = 100


class ChromaStore:
    """Wrapper around ChromaDB for storing and retrieving chunk vectors.

    Handles collection lifecycle, upsert with deduplication,
    metadata filtering, and semantic search.
    """

    def __init__(
        self,
        persist_directory: Path = DEFAULT_CHROMA_PATH,
        embedding_service: Optional[EmbeddingService] = None,
        collection_name: str = COLLECTION_NAME,
        config: Optional[ChromaConfig] = None,
    ):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.config = config or ChromaConfig()
        self._embedding_service = embedding_service
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection: Optional[chromadb.Collection] = None

    @property
    def embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _ensure_client(self) -> chromadb.PersistentClient:
        if self._client is None:
            os.makedirs(self.persist_directory, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    def _ensure_collection(self) -> chromadb.Collection:
        if self._collection is not None:
            return self._collection

        client = self._ensure_client()

        # Try to get existing collection first
        try:
            self._collection = client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_service._get_local_ef()
                if self.embedding_service._using_local
                else None,
            )
            logger.info(
                "Loaded existing collection '%s' (%d entries)",
                self.collection_name,
                self._collection.count(),
            )
        except (ValueError, chromadb.errors.NotFoundError):
            # Collection doesn't exist, create it
            self._collection = client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_service._get_local_ef()
                if self.embedding_service._using_local
                else None,
                metadata={
                    "hnsw:space": self.config.hnsw_space,
                    "hnsw:M": self.config.hnsw_m,
                    "hnsw:construction_ef": self.config.hnsw_construction_ef,
                    "hnsw:search_ef": self.config.hnsw_search_ef,
                },
            )
            logger.info(
                "Created new collection '%s'", self.collection_name
            )

        return self._collection

    def _chunk_to_metadata(self, chunk: Chunk) -> dict[str, Any]:
        """Convert a Chunk model to Chroma metadata dict."""
        meta = {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "section_title": chunk.section_title,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "token_count": chunk.token_count,
            "has_citations": chunk.flags.has_citations,
            "quoted_text": chunk.flags.quoted_text,
        }
        if chunk.metadata:
            meta["title"] = chunk.metadata.title or ""
            meta["authors"] = ", ".join(chunk.metadata.authors)
            meta["year"] = chunk.metadata.year or 0
            meta["journal"] = chunk.metadata.journal or ""
            meta["source_file"] = chunk.metadata.source_file
            meta["metadata_confidence"] = chunk.metadata.metadata_confidence
        return meta

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        """Add or update chunks in the collection.

        Deduplicates by chunk_id: if a chunk with the same ID already
        exists, it will be overwritten.

        Args:
            chunks: List of Chunk objects to store.

        Returns:
            Number of chunks upserted.
        """
        if not chunks:
            return 0

        collection = self._ensure_collection()
        total_upserted = 0

        for i in range(0, len(chunks), self.config.upsert_batch_size):
            batch = chunks[i : i + self.config.upsert_batch_size]
            ids = [c.chunk_id for c in batch]
            documents = [c.text for c in batch]
            metadatas = [self._chunk_to_metadata(c) for c in batch]

            if self.embedding_service._using_local:
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
            else:
                embeddings = self.embedding_service.embed(documents)
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings.tolist(),
                    metadatas=metadatas,
                    documents=documents,
                )

            total_upserted += len(batch)

        logger.info("Upserted %d chunks into '%s'", total_upserted, self.collection_name)
        return total_upserted

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        """Delete specific chunks by ID.

        Args:
            chunk_ids: List of chunk IDs to delete.

        Returns:
            Number of chunks deleted.
        """
        if not chunk_ids:
            return 0

        collection = self._ensure_collection()
        collection.delete(ids=chunk_ids)
        logger.info("Deleted %d chunks", len(chunk_ids))
        return len(chunk_ids)

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document.

        Args:
            document_id: Document identifier.

        Returns:
            Number of chunks deleted.
        """
        collection = self._ensure_collection()
        results = collection.get(
            where={"document_id": document_id},
            include=[],
        )
        if not results["ids"]:
            return 0

        collection.delete(ids=results["ids"])
        logger.info(
            "Deleted %d chunks for document '%s'",
            len(results["ids"]),
            document_id,
        )
        return len(results["ids"])

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[dict[str, Any]] = None,
        where_document: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Search for chunks similar to query text.

        Args:
            query_text: Natural language query.
            n_results: Number of results to return (top-k).
            where: Metadata filter dict (e.g. {"year": 2024}).
            where_document: Document content filter.

        Returns:
            List of result dicts with keys: id, document, metadata, distance.
        """
        collection = self._ensure_collection()

        # For API-based embedding, pre-compute query embedding
        query_kwargs: dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }

        if where:
            query_kwargs["where"] = where
        if where_document:
            query_kwargs["where_document"] = where_document

        if not self.embedding_service._using_local:
            query_embedding = self.embedding_service.embed_query(query_text)
            query_kwargs["query_embeddings"] = [query_embedding.tolist()]
            del query_kwargs["query_texts"]

        results = collection.query(**query_kwargs)

        formatted = []
        if results["ids"]:
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })

        return formatted

    def count(self) -> int:
        """Return total number of chunks in the collection."""
        collection = self._ensure_collection()
        return collection.count()

    def reset(self) -> None:
        """Reset the entire collection (for testing)."""
        try:
            client = self._ensure_client()
            client.delete_collection(self.collection_name)
            self._collection = None
            logger.info("Reset collection '%s'", self.collection_name)
        except (ValueError, chromadb.errors.NotFoundError):
            pass

    def list_documents(self) -> list[str]:
        """Return list of unique document IDs in the store."""
        collection = self._ensure_collection()
        all_meta = collection.get(include=["metadatas"])
        doc_ids = set()
        for meta in all_meta["metadatas"]:
            if meta and "document_id" in meta:
                doc_ids.add(meta["document_id"])
        return sorted(doc_ids)

    @property
    def collection(self):
        """Access the underlying Chroma collection."""
        return self._ensure_collection()
