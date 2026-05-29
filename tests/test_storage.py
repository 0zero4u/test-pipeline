"""Tests for the Chroma vector store."""

import json
import tempfile
from pathlib import Path

import pytest

from research_rag.embeddings import EmbeddingService
from research_rag.models import Chunk, DocumentMetadata, ChunkFlags
from research_rag.storage.chroma import ChromaStore


@pytest.fixture
def temp_chroma_path():
    """Provide a temporary directory for Chroma persistence."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def store(temp_chroma_path):
    """Provide a ChromaStore with temporary persistence."""
    return ChromaStore(
        persist_directory=temp_chroma_path,
        embedding_service=EmbeddingService(api_key=None),
        collection_name="test_collection",
    )


@pytest.fixture
def sample_chunks():
    """Provide sample chunks for testing."""
    meta = DocumentMetadata(
        document_id="doc1",
        title="Test Document",
        authors=["Author A"],
        year=2024,
        journal="Test Journal",
        source_file="test.pdf",
        metadata_confidence=0.85,
    )
    return [
        Chunk(
            chunk_id="doc1_chunk_0000",
            document_id="doc1",
            section_title="Introduction",
            page_start=1,
            page_end=1,
            text="This is the introduction section of the test document. It discusses quantum physics and fundamental particles.",
            token_count=50,
            metadata=meta,
            flags=ChunkFlags(has_citations=False),
        ),
        Chunk(
            chunk_id="doc1_chunk_0001",
            document_id="doc1",
            section_title="Methodology",
            page_start=2,
            page_end=3,
            text="The methodology section describes the experimental setup used to measure particle decay rates. Results were collected over several months.",
            token_count=60,
            metadata=meta,
            flags=ChunkFlags(has_citations=True),
        ),
        Chunk(
            chunk_id="doc1_chunk_0002",
            document_id="doc1",
            section_title="Results",
            page_start=4,
            page_end=5,
            text="The results show significant correlation between temperature and reaction rate. This confirms the theoretical predictions.",
            token_count=55,
            metadata=meta,
            flags=ChunkFlags(has_citations=True),
        ),
    ]


class TestChromaStore:
    """Test ChromaStore CRUD operations."""

    def test_init_creates_directory_on_access(self, temp_chroma_path):
        """Directory is created lazily when client is first accessed."""
        store = ChromaStore(
            persist_directory=temp_chroma_path / "nested",
            embedding_service=EmbeddingService(api_key=None),
        )
        # Trigger client creation (the temp dir doesn't exist yet)
        store.count()
        assert (temp_chroma_path / "nested").exists()

    def test_count_empty(self, store):
        assert store.count() == 0

    def test_upsert_chunks(self, store, sample_chunks):
        n = store.upsert_chunks(sample_chunks)
        assert n == 3
        assert store.count() == 3

    def test_upsert_empty(self, store):
        n = store.upsert_chunks([])
        assert n == 0

    def test_upsert_dedup(self, store, sample_chunks):
        """Upserting same chunks again should not duplicate."""
        store.upsert_chunks(sample_chunks)
        assert store.count() == 3
        # Upsert again with same IDs
        store.upsert_chunks(sample_chunks)
        assert store.count() == 3  # Still 3, not 6

    def test_query_returns_results(self, store, sample_chunks):
        store.upsert_chunks(sample_chunks)
        results = store.query("quantum physics", n_results=5)
        assert len(results) == 3
        assert results[0]["id"].startswith("doc1_chunk")
        assert "distance" in results[0]

    def test_query_top_k(self, store, sample_chunks):
        store.upsert_chunks(sample_chunks)
        results = store.query("quantum physics", n_results=2)
        assert len(results) == 2

    def test_query_returns_metadata(self, store, sample_chunks):
        store.upsert_chunks(sample_chunks)
        results = store.query("quantum physics", n_results=1)
        meta = results[0]["metadata"]
        assert meta["document_id"] == "doc1"
        assert meta["title"] == "Test Document"
        assert meta["section_title"] == "Introduction"

    def test_delete_chunks(self, store, sample_chunks):
        store.upsert_chunks(sample_chunks)
        deleted = store.delete_chunks(["doc1_chunk_0000"])
        assert deleted == 1
        assert store.count() == 2

    def test_delete_document(self, store, sample_chunks):
        store.upsert_chunks(sample_chunks)
        deleted = store.delete_document("doc1")
        assert deleted == 3
        assert store.count() == 0

    def test_delete_document_nonexistent(self, store):
        deleted = store.delete_document("nonexistent")
        assert deleted == 0

    def test_list_documents(self, store, sample_chunks):
        store.upsert_chunks(sample_chunks)
        docs = store.list_documents()
        assert docs == ["doc1"]

    def test_list_documents_empty(self, store):
        docs = store.list_documents()
        assert docs == []

    def test_reset(self, store, sample_chunks):
        store.upsert_chunks(sample_chunks)
        store.reset()
        assert store.count() == 0

    def test_multiple_documents(self, store, sample_chunks):
        store.upsert_chunks(sample_chunks)

        meta2 = DocumentMetadata(
            document_id="doc2",
            title="Second Paper",
            authors=["Author B"],
            year=2023,
            source_file="paper2.pdf",
            metadata_confidence=0.75,
        )
        more_chunks = [
            Chunk(
                chunk_id="doc2_chunk_0000",
                document_id="doc2",
                section_title="Abstract",
                page_start=1, page_end=1,
                text="This paper explores neural networks.",
                token_count=30,
                metadata=meta2,
            )
        ]
        store.upsert_chunks(more_chunks)
        assert store.count() == 4
        assert len(store.list_documents()) == 2


class TestChromaStoreQuery:
    """Test ChromaStore metadata filtering in queries."""

    def test_query_with_where(self, store, sample_chunks):
        store.upsert_chunks(sample_chunks)

        # Filter by section_title
        results = store.query(
            "experiment",
            n_results=5,
            where={"section_title": "Results"},
        )
        assert len(results) == 1
        assert results[0]["metadata"]["section_title"] == "Results"

    def test_query_with_where_no_match(self, store, sample_chunks):
        store.upsert_chunks(sample_chunks)

        results = store.query(
            "quantum",
            n_results=5,
            where={"year": 1999},
        )
        assert len(results) == 0
