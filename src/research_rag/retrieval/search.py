"""Semantic search and retrieval for Research RAG."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from research_rag.embeddings import EmbeddingService
from research_rag.storage.chroma import ChromaStore


@dataclass
class SearchResult:
    """A single search result with context."""

    chunk_id: str
    document_id: str
    title: str
    section_title: str
    page_start: int
    page_end: int
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class Retriever:
    """Semantic retriever that searches stored chunks.

    Combines ChromaStore with embedding service for query processing.
    Supports metadata filtering and result formatting.
    """

    def __init__(
        self,
        store: Optional[ChromaStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ):
        self.store = store or ChromaStore(
            embedding_service=embedding_service,
        )
        self.embedding_service = embedding_service or self.store.embedding_service
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        where: Optional[dict[str, Any]] = None,
        min_score: Optional[float] = None,
    ) -> list[SearchResult]:
        """Execute a semantic search.

        Args:
            query: Natural language query string.
            top_k: Number of results (defaults to self.top_k).
            where: Optional metadata filter dict.
                Example: {"year": 2024} or {"authors": {"$contains": "Singh"}}
            min_score: Minimum similarity score threshold (cosine distance).
                Lower values = more similar. Defaults to self.similarity_threshold.

        Returns:
            List of SearchResult objects sorted by relevance (best first).
        """
        k = top_k or self.top_k
        threshold = min_score if min_score is not None else self.similarity_threshold

        raw_results = self.store.query(
            query_text=query,
            n_results=k,
            where=where,
        )

        results = []
        for r in raw_results:
            distance = r["distance"]
            if threshold > 0.0 and distance > threshold:
                continue

            meta = r.get("metadata", {})
            results.append(
                SearchResult(
                    chunk_id=r["id"],
                    document_id=meta.get("document_id", ""),
                    title=meta.get("title", ""),
                    section_title=meta.get("section_title", ""),
                    page_start=meta.get("page_start", 0),
                    page_end=meta.get("page_end", 0),
                    text=r.get("document", ""),
                    score=1.0 - distance,  # Convert distance to similarity score
                    metadata=meta,
                )
            )

        # Sort by score descending (best first)
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def search_by_document(
        self,
        document_id: str,
        query: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> list[SearchResult]:
        """Search within a specific document.

        Args:
            document_id: Document to restrict search to.
            query: Optional query (if None, returns all chunks for doc).
            top_k: Number of results.

        Returns:
            List of SearchResult objects.
        """
        where = {"document_id": document_id}
        if query:
            return self.search(query=query, top_k=top_k, where=where)

        # If no query, just get all chunks for the document
        raw_results = self.store.query(
            query_text="",
            n_results=top_k or 100,
            where=where,
        )
        results = []
        for r in raw_results:
            meta = r.get("metadata", {})
            results.append(
                SearchResult(
                    chunk_id=r["id"],
                    document_id=meta.get("document_id", ""),
                    title=meta.get("title", ""),
                    section_title=meta.get("section_title", ""),
                    page_start=meta.get("page_start", 0),
                    page_end=meta.get("page_end", 0),
                    text=r.get("document", ""),
                    score=1.0,
                    metadata=meta,
                )
            )
        return results

    def format_results(
        self,
        results: list[SearchResult],
        include_text: bool = True,
        max_text_length: int = 300,
    ) -> str:
        """Format search results as a readable string.

        Args:
            results: List of SearchResult objects.
            include_text: Whether to include text excerpts.
            max_text_length: Max characters for text excerpts.

        Returns:
            Formatted string representation.
        """
        if not results:
            return "No results found."

        lines = [f"Found {len(results)} result(s):\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.title}" if r.title else f"[{i}] {r.document_id}")
            lines.append(f"    Section: {r.section_title}" if r.section_title else "")
            lines.append(f"    Pages: {r.page_start}-{r.page_end}")
            lines.append(f"    Relevance: {r.score:.3f}")
            if include_text and r.text:
                excerpt = r.text[:max_text_length].replace("\n", " ")
                if len(r.text) > max_text_length:
                    excerpt += "..."
                lines.append(f"    Text: {excerpt}")
            lines.append("")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"Retriever(store={self.store.persist_directory.name}, "
            f"top_k={self.top_k}, embedding={self.embedding_service.model})"
        )
