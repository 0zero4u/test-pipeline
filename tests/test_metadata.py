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
    assert metadata.metadata_confidence <= 0.5


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


# Regression tests for known metadata extraction issues


def test_keywords_line_not_matched_as_author():
    """rag_pdf2: 'Key Words: ...' should NOT be returned as author."""
    text_with_keywords = """# Partition and Communal Violence in Train to Pakistan

Key Words: Affective politics; Bhisham Sahni; Partition violence; Train to Pakistan

Research Scholar, Vol. 7, Issue 2, 2018

DOI: 10.1234/example
"""
    metadata = extract_metadata(text_with_keywords, "rag_pdf2.pdf")
    # "Key Words" should NOT appear in authors
    assert not any("key words" in a.lower() for a in metadata.authors)
    # Should return empty list or actual author name, not "Key Words"
    assert metadata.authors == [] or all(
        "key words" not in a.lower() for a in metadata.authors
    )


def test_keywords_with_name_not_matched_as_author():
    """rag_pdf1: 'Key Words: Khushwant Singh' should NOT return ['Khushwant Singh']."""
    text_with_keywords_name = """# Women and Violence in Partition Narratives

Key Words: Khushwant Singh, Partition violence, Gender studies

Journal of South Asian Studies, Vol. 12, No. 1, 2020

DOI: 10.5678/abc.123
"""
    metadata = extract_metadata(text_with_keywords_name, "rag_pdf1.pdf")
    # "Khushwant Singh" is the novel's author mentioned in keywords, NOT the paper author
    # The paper author is not listed, so authors should be empty
    assert not any("khushwant" in a.lower() for a in metadata.authors)


def test_abstract_line_not_matched_as_author():
    """Lines starting with 'Abstract' should not be matched as authors."""
    text_with_abstract = """# Violence and Memory in Partition Literature

Abstract: This paper examines...

Some Author Name

Journal of Literary Studies, 2022
"""
    metadata = extract_metadata(text_with_abstract, "test.pdf")
    # "Abstract" should not be in authors
    assert not any("abstract" in a.lower() for a in metadata.authors)


def test_doi_line_not_matched_as_author():
    """Lines containing DOI should not be matched as authors."""
    text_with_doi = """# Partition Studies

DOI: 10.1234/example

Jane Smith

Published 2021
"""
    metadata = extract_metadata(text_with_doi, "test.pdf")
    assert not any("doi" in a.lower() for a in metadata.authors)


def test_authors_between_title_and_abstract():
    """Authors should only be extracted between title and abstract."""
    text_with_abstract_after = """# Test Title

Abstract: Some abstract here

Actual Author Name

More text below.
"""
    metadata = extract_metadata(text_with_abstract_after, "test.pdf")
    # "Actual Author Name" is AFTER abstract, should not be extracted
    assert not any("actual" in a.lower() for a in metadata.authors)
