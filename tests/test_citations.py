"""Tests for the citation parser."""

from research_rag.citations.parser import CitationParser

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
