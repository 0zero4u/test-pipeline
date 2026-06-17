"""Tests for the chunker module."""

from datetime import datetime

from research_rag.config import IngestionConfig
from research_rag.ingestion.chunker import chunk_document, estimate_tokens
from research_rag.models import DocumentMetadata


SAMPLE_DOC_META = DocumentMetadata(
    document_id="test_doc",
    title="Test Document",
    authors=["Author One"],
    year=2024,
    source_file="test.pdf",
    metadata_confidence=0.85,
    ingestion_date=datetime.utcnow(),
)


def test_estimate_tokens():
    """Test token estimation."""
    assert estimate_tokens("") == 0
    assert estimate_tokens("Hello world") == 2
    assert estimate_tokens("A" * 100) == 13


def test_chunk_small_document():
    """Test chunking a small document (single chunk)."""
    markdown = "# Introduction\n\nThis is a small test document with minimal content."
    chunks = chunk_document(markdown, [], SAMPLE_DOC_META)
    assert len(chunks) >= 1
    assert chunks[0].document_id == "test_doc"


def test_chunk_with_sections():
    """Test chunking with section headings."""
    markdown = (
        "# Section 1\n\n"
        + "A" * 2500
        + "B" * 2500
    )
    sections = [
        {"title": "Section 1", "level": 1, "page_no": 1},
        {"title": "Section 2", "level": 1, "page_no": 1},
    ]
    chunks = chunk_document(markdown, sections, SAMPLE_DOC_META)
    assert len(chunks) >= 2
    assert "Section 1" in chunks[0].section_title or "Section 2" in chunks[0].section_title


def test_chunk_id_format():
    """Test chunk ID format."""
    markdown = "Some content"
    chunks = chunk_document(markdown, [], SAMPLE_DOC_META)
    assert chunks[0].chunk_id.startswith("test_doc_chunk_")
    assert chunks[0].chunk_id.endswith("_0000")


def test_chunk_metadata_attached():
    """Test that document metadata is attached to chunks."""
    markdown = "Document content here"
    chunks = chunk_document(markdown, [], SAMPLE_DOC_META)
    assert chunks[0].metadata is not None
    assert chunks[0].metadata.document_id == "test_doc"


def test_chunk_page_numbers():
    """Test page number assignment."""
    markdown = "Page 1 content\n<!-- page break -->\nPage 2 content"
    chunks = chunk_document(markdown, [], SAMPLE_DOC_META)
    assert all(c.page_start >= 1 for c in chunks)
    assert all(c.page_end >= c.page_start for c in chunks)


def test_chunk_token_count():
    """Test token count estimation on chunks."""
    markdown = "Word " * 200
    chunks = chunk_document(markdown, [], SAMPLE_DOC_META)
    assert all(c.token_count > 0 for c in chunks)


def test_custom_config():
    """Test chunking with custom config."""
    config = IngestionConfig(chunk_size_min=100, chunk_size_max=300, chunk_overlap=0.1)
    markdown = "# Big Section\n\n" + "Paragraph content. " * 500
    chunks = chunk_document(markdown, [], SAMPLE_DOC_META, config)
    assert len(chunks) > 0


def test_empty_document():
    """Test chunking empty document."""
    chunks = chunk_document("", [], SAMPLE_DOC_META)
    assert len(chunks) == 0
