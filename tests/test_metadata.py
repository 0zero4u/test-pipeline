"""Tests for metadata extraction module."""

from pathlib import Path

from research_rag.ingestion.metadata import extract_metadata
from research_rag.models import DocumentMetadata


SAMPLE_FIRST_PAGE = """# The Impact of Partition Violence in Postcolonial Literature

Arshdeep Singh, Priya Sharma

Journal of Postcolonial Studies, Vol. 45, No. 3, 2023

This paper examines the representation of Partition violence in South Asian literature.
The analysis focuses on narrative strategies employed by authors across generations.
DOI: 10.1080/12345678.2023.1234567
"""


def test_extract_title():
    """Test title extraction from first H1."""
    metadata = extract_metadata(SAMPLE_FIRST_PAGE, "test.pdf")
    assert "Partition Violence" in metadata.title
    assert len(metadata.title) > 10


def test_extract_authors():
    """Test author extraction."""
    metadata = extract_metadata(SAMPLE_FIRST_PAGE, "test.pdf")
    assert len(metadata.authors) > 0
    assert "Singh" in metadata.authors[0] or "Sharma" in metadata.authors[0]


def test_extract_year():
    """Test year extraction."""
    metadata = extract_metadata(SAMPLE_FIRST_PAGE, "test.pdf")
    assert metadata.year == 2023


def test_extract_journal():
    """Test journal name extraction."""
    metadata = extract_metadata(SAMPLE_FIRST_PAGE, "test.pdf")
    assert "Journal" in metadata.journal
    assert "Postcolonial" in metadata.journal


def test_extract_doi():
    """Test DOI extraction."""
    metadata = extract_metadata(SAMPLE_FIRST_PAGE, "test.pdf")
    assert metadata.doi is not None
    assert metadata.doi.startswith("10.")


def test_confidence_scoring():
    """Test confidence score computation."""
    metadata = extract_metadata(SAMPLE_FIRST_PAGE, "test.pdf")
    assert 0.0 <= metadata.metadata_confidence <= 1.0
    # Good metadata should have high confidence
    assert metadata.metadata_confidence >= 0.7


def test_empty_text():
    """Test fallback with empty text."""
    metadata = extract_metadata("", "unknown.pdf")
    assert metadata.metadata_confidence == 0.3


def test_minimal_text():
    """Test with minimal text - should still produce document."""
    metadata = extract_metadata("Some short text", "minimal.pdf")
    assert metadata.source_file == "minimal.pdf"
    assert metadata.metadata_confidence == 0.3


def test_volume_issue_extraction():
    """Test volume and issue extraction."""
    metadata = extract_metadata(SAMPLE_FIRST_PAGE, "test.pdf")
    assert metadata.volume == "45"
    assert metadata.issue == "3"


def test_document_type():
    """Test return type."""
    metadata = extract_metadata(SAMPLE_FIRST_PAGE, "test.pdf")
    assert isinstance(metadata, DocumentMetadata)
    assert metadata.document_id == "test"
