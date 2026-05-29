"""Tests for the semantic retriever."""

import tempfile
from pathlib import Path

import pytest

from research_rag.embeddings import EmbeddingService
from research_rag.models import Chunk, DocumentMetadata, ChunkFlags
from research_rag.retrieval import Retriever
from research_rag.storage.chroma import ChromaStore


@pytest.fixture
def store():
    """Provide a populated ChromaStore for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        chroma_path = Path(tmp)
        embed = EmbeddingService(api_key=None)
        store = ChromaStore(
            persist_directory=chroma_path,
            embedding_service=embed,
            collection_name="test_retrieval",
        )

        meta1 = DocumentMetadata(
            document_id="doc1",
            title="Quantum Physics Introduction",
            authors=["Einstein"],
            year=2024,
            source_file="quantum.pdf",
            metadata_confidence=0.9,
        )
        meta2 = DocumentMetadata(
            document_id="doc2",
            title="Literary Analysis of Modern Poetry",
            authors=["Sharma"],
            year=2023,
            source_file="poetry.pdf",
            metadata_confidence=0.85,
        )

        chunks = [
            Chunk(
                chunk_id="doc1_chunk_0000", document_id="doc1",
                section_title="Wave Functions", page_start=1, page_end=2,
                text="Quantum wave functions describe the probability amplitude of particles. The Schrodinger equation governs their evolution.",
                token_count=60, metadata=meta1, flags=ChunkFlags(has_citations=True),
            ),
            Chunk(
                chunk_id="doc1_chunk_0001", document_id="doc1",
                section_title="Particle Physics", page_start=3, page_end=4,
                text="Subatomic particles exhibit wave-particle duality. The uncertainty principle limits simultaneous measurement of certain properties.",
                token_count=65, metadata=meta1,
            ),
            Chunk(
                chunk_id="doc2_chunk_0000", document_id="doc2",
                section_title="Symbolism in Poetry", page_start=1, page_end=1,
                text="Modernist poetry often uses fragmented imagery and stream of consciousness to convey emotional truth.",
                token_count=50, metadata=meta2,
            ),
            Chunk(
                chunk_id="doc2_chunk_0001", document_id="doc2",
                section_title="Postcolonial Themes", page_start=2, page_end=3,
                text="Postcolonial literature examines identity formation and cultural hybridity in the aftermath of colonial rule.",
                token_count=55, metadata=meta2, flags=ChunkFlags(has_citations=True),
            ),
        ]
        store.upsert_chunks(chunks)
        yield store


@pytest.fixture
def retriever(store):
    return Retriever(store=store, top_k=5, embedding_service=store.embedding_service)


class TestRetriever:
    """Test Retriever search functionality."""

    def test_search_returns_results(self, retriever):
        results = retriever.search("quantum mechanics wave particles")
        assert len(results) > 0
        # Most relevant should be from doc1 (quantum physics)
        assert results[0].document_id == "doc1"

    def test_search_top_k(self, retriever):
        results = retriever.search("quantum", top_k=1)
        assert len(results) == 1

    def test_search_respects_default_top_k(self, retriever):
        retriever.top_k = 2
        results = retriever.search("literature")
        assert len(results) <= 2

    def test_search_returns_ordered_by_relevance(self, retriever):
        results = retriever.search("quantum")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_contains_correct_fields(self, retriever):
        results = retriever.search("quantum")
        r = results[0]
        assert r.chunk_id
        assert r.document_id
        assert r.text
        assert isinstance(r.score, float)
        assert r.page_start >= 1
        assert r.page_end >= r.page_start

    def test_search_no_match(self, retriever):
        results = retriever.search("xyznonexistenttopic2024")
        for r in results:
            assert 0.0 <= r.score <= 1.0

    def test_search_empty_query(self, retriever):
        results = retriever.search("")
        assert len(results) > 0  # Should still return nearest neighbors

    def test_search_by_document(self, retriever):
        results = retriever.search_by_document("doc1")
        assert len(results) == 2
        for r in results:
            assert r.document_id == "doc1"

    def test_search_by_document_with_query(self, retriever):
        results = retriever.search_by_document("doc1", query="wave")
        assert len(results) > 0
        for r in results:
            assert r.document_id == "doc1"

    def test_search_by_document_nonexistent(self, retriever):
        results = retriever.search_by_document("nonexistent")
        assert len(results) == 0

    def test_format_results(self, retriever):
        results = retriever.search("quantum")
        formatted = retriever.format_results(results, include_text=True)
        assert "Found" in formatted
        assert "Quantum" in formatted
        assert "Relevance:" in formatted

    def test_format_results_no_text(self, retriever):
        results = retriever.search("quantum")
        formatted = retriever.format_results(results, include_text=False)
        assert "Quantum" in formatted

    def test_format_results_no_results(self, retriever):
        formatted = retriever.format_results([])
        assert "No results" in formatted

    def test_cross_domain_relevance(self, retriever):
        """Literature query should rank poetry doc higher."""
        results = retriever.search("poetry symbolism literature")
        assert len(results) > 0
        assert results[0].document_id == "doc2"

    def test_score_range(self, retriever):
        results = retriever.search("quantum")
        for r in results:
            assert 0.0 <= r.score <= 1.0
