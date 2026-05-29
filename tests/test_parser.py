"""Tests for the PDF parser module."""

from pathlib import Path

from research_rag.ingestion.parser import (
    ParsedDocument,
    _make_document_id,
    _get_page_boundaries,
)


def test_parsed_document_creation():
    """Test ParsedDocument data class."""
    doc = ParsedDocument(
        document_id="test_001",
        file_path=Path("test.pdf"),
        markdown="# Title\n\nContent here.",
        sections=[{"title": "Title", "level": 1, "page_no": 1}],
        page_boundaries=[(1, 0, 20)],
        page_count=1,
        first_page_text="# Title\n\nContent here.",
    )
    assert doc.document_id == "test_001"
    assert doc.page_count == 1
    assert len(doc.sections) == 1


def test_make_document_id():
    """Test document ID generation from filename."""
    assert _make_document_id(Path("My_Paper.pdf")) == "my_paper"
    assert _make_document_id(Path("article v2 final.pdf")) == "article_v2_final"
    assert _make_document_id(Path("UPLOAD_001.PDF")) == "upload_001"


def test_make_document_id_truncates():
    """Test document ID truncation for long names."""
    long_name = "a" * 100 + ".pdf"
    doc_id = _make_document_id(Path(long_name))
    assert len(doc_id) <= 64


def test_page_boundaries_single():
    """Test page boundary parsing without markers."""
    boundaries = _get_page_boundaries("No markers here")
    assert len(boundaries) == 1
    assert boundaries[0][0] == 1


def test_page_boundaries_with_markers():
    """Test page boundary parsing with page break markers."""
    text = "Page1<!-- page break -->Page2<!-- page break -->Page3"
    boundaries = _get_page_boundaries(text)
    assert len(boundaries) == 3
    assert boundaries[0][0] == 1
    assert boundaries[1][0] == 2
    assert boundaries[2][0] == 3


def test_page_boundaries_positions():
    """Test page boundary character positions."""
    text = "AAA<!-- page break -->BBB"
    boundaries = _get_page_boundaries(text)
    assert len(boundaries) == 2
    # Page 1: "AAA" starting at 0
    assert boundaries[0][1] == 0  # start
    assert text[boundaries[0][1]:boundaries[0][2]] == "AAA"
    # Page 2: "BBB"
    assert text[boundaries[1][1]:boundaries[1][2]] == "BBB"


def test_page_boundaries_empty():
    """Test page boundaries with empty string."""
    boundaries = _get_page_boundaries("")
    assert len(boundaries) == 1
    assert boundaries[0][0] == 1
