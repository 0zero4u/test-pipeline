"""Tests for data models."""

import pytest

from research_rag.models import (
    Chunk,
    ChunkFlags,
    Citation,
    DocumentMetadata,
    EntityExtraction,
    QueryResponse,
)


def test_document_metadata():
    """Test DocumentMetadata model."""
    metadata = DocumentMetadata(
        document_id="test-001",
        title="Test Document",
        authors=["Author One", "Author Two"],
        year=2024,
        source_file="test.pdf",
        metadata_confidence=0.85,
    )

    assert metadata.document_id == "test-001"
    assert metadata.title == "Test Document"
    assert len(metadata.authors) == 2
    assert metadata.year == 2024
    assert metadata.metadata_confidence == 0.85


def test_entity_extraction():
    """Test EntityExtraction model."""
    entities = EntityExtraction(
        people=["Khushwant Singh", "Urvashi Butalia"],
        works=["Train to Pakistan", "The Other Side of Silence"],
        themes=["Partition", "violence", "gender"],
        historical_events=["Partition of India"],
    )

    assert len(entities.people) == 2
    assert len(entities.works) == 2
    assert "Partition" in entities.themes
    assert len(entities.historical_events) == 1


def test_chunk():
    """Test Chunk model."""
    chunk = Chunk(
        chunk_id="chunk-001",
        document_id="doc-001",
        section_title="Introduction",
        page_start=1,
        page_end=2,
        text="This is a test chunk of text.",
        token_count=50,
    )

    assert chunk.chunk_id == "chunk-001"
    assert chunk.page_start == 1
    assert chunk.page_end == 2
    assert chunk.flags.quoted_text is False


def test_citation():
    """Test Citation model."""
    citation = Citation(
        chunk_id="chunk-001",
        document_id="doc-001",
        title="Test Document",
        page=15,
        relevance_score=0.89,
    )

    assert citation.relevance_score == 0.89
    assert citation.page == 15


def test_query_response():
    """Test QueryResponse model."""
    response = QueryResponse(
        query="How does Singh portray violence?",
        answer="Singh portrays violence through...",
        citations=[
            Citation(
                chunk_id="chunk-001",
                document_id="doc-001",
                title="Test",
                page=10,
                relevance_score=0.85,
            )
        ],
        confidence=0.82,
    )

    assert response.query == "How does Singh portray violence?"
    assert len(response.citations) == 1
    assert response.confidence == 0.82
