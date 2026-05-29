"""Tests for the citation parser and validator."""

from research_rag.citations.parser import CitationParser, Citation
from research_rag.citations.validator import CitationValidator

# Helper to create a mock search result
def make_result(chunk_id, doc_id, title, page, score):
    return type("MockResult", (), {
        "chunk_id": chunk_id,
        "document_id": doc_id,
        "title": title,
        "page_start": page,
        "score": score,
    })()


class TestCitationParser:
    """Test parsing inline citations from LLM output."""

    def setup_method(self):
        self.parser = CitationParser()
        self.results = [
            make_result("doc1_c0", "doc1", "Paper One", 3, 0.95),
            make_result("doc1_c1", "doc1", "Paper One", 5, 0.88),
            make_result("doc2_c0", "doc2", "Paper Two", 10, 0.75),
        ]

    def test_parse_single_citation(self):
        answer = "According to [1], the answer is clear."
        citations = self.parser.parse(answer, self.results)
        assert len(citations) == 1
        assert citations[0].chunk_id == "doc1_c0"
        assert citations[0].citation_number == 1

    def test_parse_multiple_citations(self):
        answer = "Some claim X [1], while others argue Y [2][3]."
        citations = self.parser.parse(answer, self.results)
        assert len(citations) == 3

    def test_parse_comma_separated(self):
        answer = "Multiple sources agree [1,2,3]."
        citations = self.parser.parse(answer, self.results)
        assert len(citations) == 3
        ids = {c.chunk_id for c in citations}
        assert ids == {"doc1_c0", "doc1_c1", "doc2_c0"}

    def test_parse_range(self):
        answer = "As shown in recent work [1-3]."
        citations = self.parser.parse(answer, self.results)
        assert len(citations) == 3

    def test_parse_range_with_dash(self):
        answer = "Studies [1–3] confirm this."  # en-dash
        citations = self.parser.parse(answer, self.results)
        assert len(citations) == 3

    def test_no_citations(self):
        answer = "The answer is clear without any sources."
        citations = self.parser.parse(answer, self.results)
        assert len(citations) == 0

    def test_empty_answer(self):
        citations = self.parser.parse("", self.results)
        assert len(citations) == 0

    def test_no_evidence_results(self):
        answer = "According to [1]."
        citations = self.parser.parse(answer, [])
        assert len(citations) == 0

    def test_out_of_range_number(self):
        answer = "According to [99]."
        citations = self.parser.parse(answer, self.results)
        assert len(citations) == 0

    def test_skip_duplicates(self):
        """Same chunk cited twice should only appear once."""
        answer = "First [1] and then [1] again."
        citations = self.parser.parse(answer, self.results)
        assert len(citations) == 1

    def test_to_dict(self):
        answer = "See [1]."
        citations = self.parser.parse(answer, self.results[:1])
        d = citations[0].to_dict()
        assert d["chunk_id"] == "doc1_c0"
        assert d["page"] == 3
        assert "relevance_score" in d


class TestCitationValidator:
    """Test citation validation and enrichment."""

    def setup_method(self):
        self.validator = CitationValidator()
        self.metadata_map = {
            "doc1": {"title": "Paper One", "authors": ["Alice Smith"], "year": 2021},
            "doc2": {"title": "Paper Two", "authors": ["Bob Jones", "Carol White"], "year": None},
        }

    def test_validate_enriches_citation(self):
        citation = Citation(
            chunk_id="doc1_c0", document_id="doc1", title="Paper One",
            page=3, relevance_score=0.95, citation_number=1,
        )
        validated = self.validator.validate([citation], self.metadata_map)
        assert validated[0].authors == ["Alice Smith"]
        assert validated[0].year == 2021
        assert validated[0].is_validated is True

    def test_validate_multiple_authors(self):
        citation = Citation(
            chunk_id="doc2_c0", document_id="doc2", title="Paper Two",
            page=10, relevance_score=0.75, citation_number=1,
        )
        validated = self.validator.validate([citation], self.metadata_map)
        assert validated[0].authors == ["Bob Jones", "Carol White"]
        assert validated[0].year is None

    def test_validate_unknown_document(self):
        citation = Citation(
            chunk_id="unknown_c0", document_id="unknown", title="Unknown",
            page=1, relevance_score=0.5, citation_number=1,
        )
        validated = self.validator.validate([citation], self.metadata_map)
        assert validated[0].authors == []
        assert validated[0].year is None
        assert validated[0].is_validated is False

    def test_format_citation_with_authors_and_year(self):
        citation = Citation(
            chunk_id="doc1_c0", document_id="doc1", title="Paper One",
            page=3, relevance_score=0.95, citation_number=1,
            authors=["Alice Smith"], year=2021, is_validated=True,
        )
        formatted = self.validator.format_citation(citation)
        assert "Alice Smith" in formatted
        assert "2021" in formatted
        assert "Paper One" in formatted
        assert "p. 3" in formatted

    def test_format_citation_no_year(self):
        citation = Citation(
            chunk_id="doc2_c0", document_id="doc2", title="Paper Two",
            page=10, relevance_score=0.75, citation_number=1,
            authors=["Bob Jones", "Carol White"], year=None, is_validated=True,
        )
        formatted = self.validator.format_citation(citation)
        assert "Bob Jones & Carol White" in formatted
        assert "n.d." in formatted

    def test_format_citation_three_plus_authors(self):
        citation = Citation(
            chunk_id="doc3_c0", document_id="doc3", title="Paper Three",
            page=5, relevance_score=0.8, citation_number=1,
            authors=["A", "B", "C"], year=2023, is_validated=True,
        )
        formatted = self.validator.format_citation(citation)
        assert "A et al." in formatted

    def test_format_citation_two_authors(self):
        citation = Citation(
            chunk_id="doc4_c0", document_id="doc4", title="Paper Four",
            page=1, relevance_score=0.7, citation_number=1,
            authors=["X", "Y"], year=2020, is_validated=True,
        )
        formatted = self.validator.format_citation(citation)
        assert "X & Y" in formatted

    def test_to_dict_includes_new_fields(self):
        citation = Citation(
            chunk_id="doc1_c0", document_id="doc1", title="Paper One",
            page=3, relevance_score=0.95, citation_number=1,
            authors=["Alice Smith"], year=2021, is_validated=True,
        )
        d = citation.to_dict()
        assert d["authors"] == ["Alice Smith"]
        assert d["year"] == 2021
        assert d["is_validated"] is True
