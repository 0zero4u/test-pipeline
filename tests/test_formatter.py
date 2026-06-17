"""Tests for CitationFormatter — inline citations, MLA/APA, Works Cited."""
from research_rag.citations.formatter import CitationFormatter


# ---------------------------------------------------------------------------
# extract_last_name
# ---------------------------------------------------------------------------

def test_extract_last_name_simple():
    """'John Smith' → 'Smith'."""
    f = CitationFormatter()
    assert f.extract_last_name("John Smith") == "Smith"


def test_extract_last_name_comma():
    """'Smith, John' → 'Smith'."""
    f = CitationFormatter()
    assert f.extract_last_name("Smith, John") == "Smith"


# ---------------------------------------------------------------------------
# format_inline — MLA
# ---------------------------------------------------------------------------

def test_format_mla_single_author():
    """Single author with year and page → (Smith 2021, p. 45)."""
    f = CitationFormatter()
    citation = {
        "citation_number": 1,
        "authors": ["John Smith"],
        "year": "2021",
        "page": 45,
        "title": "Paper",
        "document_id": "d1",
    }
    result = f.format_inline(citation, "mla")
    assert result == "(Smith 2021, p. 45)"


def test_format_mla_two_authors():
    """Two authors → (Smith and Jones 2021, p. 45)."""
    f = CitationFormatter()
    citation = {
        "citation_number": 1,
        "authors": ["John Smith", "Jane Jones"],
        "year": "2021",
        "page": 45,
        "title": "Paper",
        "document_id": "d1",
    }
    result = f.format_inline(citation, "mla")
    assert result == "(Smith and Jones 2021, p. 45)"


def test_format_mla_three_plus_authors():
    """Three or more authors → (Smith et al. 2021, p. 45)."""
    f = CitationFormatter()
    citation = {
        "citation_number": 1,
        "authors": ["Smith", "Jones", "Brown", "Lee"],
        "year": "2021",
        "page": 45,
        "title": "Paper",
        "document_id": "d1",
    }
    result = f.format_inline(citation, "mla")
    assert result == "(Smith et al. 2021, p. 45)"


def test_format_mla_no_year():
    """Missing year → (Smith n.d., p. 45)."""
    f = CitationFormatter()
    citation = {
        "citation_number": 1,
        "authors": ["John Smith"],
        "year": None,
        "page": 45,
        "title": "Paper",
        "document_id": "d1",
    }
    result = f.format_inline(citation, "mla")
    assert result == "(Smith n.d., p. 45)"


def test_format_mla_no_page():
    """Missing page → (Smith 2021)."""
    f = CitationFormatter()
    citation = {
        "citation_number": 1,
        "authors": ["John Smith"],
        "year": "2021",
        "page": None,
        "title": "Paper",
        "document_id": "d1",
    }
    result = f.format_inline(citation, "mla")
    assert result == "(Smith 2021)"


# ---------------------------------------------------------------------------
# format_inline — APA
# ---------------------------------------------------------------------------

def test_format_apa_single_author():
    """APA single author → (Smith, 2021, p. 45)."""
    f = CitationFormatter()
    citation = {
        "citation_number": 1,
        "authors": ["John Smith"],
        "year": "2021",
        "page": 45,
        "title": "Paper",
        "document_id": "d1",
    }
    result = f.format_inline(citation, "apa")
    assert result == "(Smith, 2021, p. 45)"


# ---------------------------------------------------------------------------
# replace_citations
# ---------------------------------------------------------------------------

def test_replace_inline_citations():
    """Replace [1] and [2] markers with formatted citations."""
    f = CitationFormatter()
    answer = "Answer [1] and [2]"
    citations = [
        {
            "citation_number": 1,
            "authors": ["John Smith"],
            "year": "2021",
            "page": 45,
            "title": "Paper",
            "document_id": "doc1",
        },
        {
            "citation_number": 2,
            "authors": ["Jane Jones"],
            "year": "2020",
            "page": 10,
            "title": "Another Paper",
            "document_id": "doc2",
        },
    ]
    result = f.replace_citations(answer, citations, "mla")
    assert result == "Answer (Smith 2021, p. 45) and (Jones 2020, p. 10)"


# ---------------------------------------------------------------------------
# generate_works_cited
# ---------------------------------------------------------------------------

def test_works_cited_deduplicates():
    """Two citations from same document_id → only one Works Cited entry."""
    f = CitationFormatter()
    citations = [
        {
            "citation_number": 1,
            "authors": ["John Smith"],
            "year": "2021",
            "page": 45,
            "title": "Paper",
            "document_id": "doc1",
        },
        {
            "citation_number": 2,
            "authors": ["John Smith"],
            "year": "2021",
            "page": 50,
            "title": "Paper",
            "document_id": "doc1",
        },
    ]
    result = f.generate_works_cited(citations, "mla")
    # Only one entry should appear
    assert result.count("Smith, John.") == 1


def test_works_cited_sorted():
    """Entries sorted alphabetically by last name (case-insensitive)."""
    f = CitationFormatter()
    citations = [
        {
            "citation_number": 1,
            "authors": ["Charlie Brown"],
            "year": "2020",
            "page": 10,
            "title": "Alpha",
            "document_id": "doc_c",
        },
        {
            "citation_number": 2,
            "authors": ["Alice Smith"],
            "year": "2021",
            "page": 5,
            "title": "Beta",
            "document_id": "doc_a",
        },
        {
            "citation_number": 3,
            "authors": ["Bob Jones"],
            "year": "2019",
            "page": 20,
            "title": "Gamma",
            "document_id": "doc_b",
        },
    ]
    result = f.generate_works_cited(citations, "mla")
    # Sort order by last name: Brown → Jones → Smith
    brown_pos = result.index("Brown, Charlie.")
    jones_pos = result.index("Jones, Bob.")
    smith_pos = result.index("Smith, Alice.")
    assert brown_pos < jones_pos < smith_pos


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_no_citations_unchanged():
    """Text without [N] markers passes through unchanged."""
    f = CitationFormatter()
    text = "This is a plain text with no citation markers."
    result = f.replace_citations(text, [], "mla")
    assert result == text


def test_missing_author_fallback():
    """No authors → falls back to title in quotes."""
    f = CitationFormatter()
    citation = {
        "citation_number": 1,
        "authors": [],
        "year": "2021",
        "page": 45,
        "title": "Mystery Paper",
        "document_id": "doc1",
    }
    result = f.format_inline(citation, "mla")
    # _format_author_part([], "Mystery Paper", "doc1", "mla") → '"Mystery Paper"'
    assert result == '("Mystery Paper" 2021, p. 45)'


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

def test_formatter_integration():
    """Full format() pipeline: no raw [N] markers survive."""
    f = CitationFormatter()
    answer = "According to [1], the answer is clear."
    citations = [
        {
            "citation_number": 1,
            "authors": ["John Smith"],
            "year": "2021",
            "page": 45,
            "title": "Paper",
            "document_id": "doc1",
        },
    ]
    result = f.format(answer, citations, "mla")
    # All [N] markers should be replaced
    assert "[1]" not in result["answer"]
    # Works Cited section should exist
    assert "## Works Cited" in result["answer"]
    assert result["works_cited"] != ""
