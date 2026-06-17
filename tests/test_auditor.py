"""Tests for CitationAuditor — claim extraction and verification against source chunks."""

from research_rag.citations.auditor import CitationAuditor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockResult:
    """Minimal stand-in for a search result with a .text attribute."""
    def __init__(self, text):
        self.text = text


# ---------------------------------------------------------------------------
# extract_claims
# ---------------------------------------------------------------------------

def test_extract_claims_finds_sentence():
    """Simple sentence with [1] → extracts the sentence text."""
    auditor = CitationAuditor()
    text = "This is the key finding [1]."
    claims = auditor.extract_claims(text, 1)
    assert len(claims) >= 1
    assert "This is the key finding" in claims[0]


def test_extract_claims_multiple_granularities():
    """A long sentence ending with [1] returns at least 2 granularities."""
    auditor = CitationAuditor()
    text = (
        "The partition of British India in 1947 led to one of the largest "
        "mass migrations in human history, with an estimated 15 million people "
        "crossing borders amid widespread communal violence and the collapse "
        "of established administrative structures on both sides [1]."
    )
    claims = auditor.extract_claims(text, 1)
    assert len(claims) >= 2


# ---------------------------------------------------------------------------
# verify_claim
# ---------------------------------------------------------------------------

def test_verify_claim_exact_match():
    """Exact substring match → True."""
    auditor = CitationAuditor()
    assert auditor.verify_claim("key finding", "This is the key finding") is True


def test_verify_claim_case_insensitive():
    """Case mismatch should still match → True."""
    auditor = CitationAuditor()
    assert auditor.verify_claim("Key Finding", "this is the KEY FINDING") is True


def test_verify_claim_no_match():
    """Completely unrelated strings → False."""
    auditor = CitationAuditor()
    assert auditor.verify_claim("unrelated text", "completely different content") is False


# ---------------------------------------------------------------------------
# audit — full pipeline
# ---------------------------------------------------------------------------

ANSWER_EXAMPLE = (
    "The partition violence was a key finding in the research [1]. "
    "Communal harmony remained an important theme throughout [2]."
)


def test_audit_all_verified():
    """Both citations have claims present in their chunks → 2 verified, 0 flagged."""
    auditor = CitationAuditor()
    citations = [
        {"citation_number": 1, "chunk_id": "doc1_c0", "document_id": "doc1"},
        {"citation_number": 2, "chunk_id": "doc1_c1", "document_id": "doc1"},
    ]
    results = [
        MockResult(
            "The partition violence was a key finding in the research"
        ),
        MockResult(
            "Communal harmony remained an important theme throughout"
        ),
    ]
    report = auditor.audit(ANSWER_EXAMPLE, citations, results)
    assert report["total_citations"] == 2
    assert report["verified_count"] == 2
    assert report["flagged_count"] == 0


def test_audit_one_flagged():
    """Second citation's claim not present in its chunk → 1 verified, 1 flagged."""
    auditor = CitationAuditor()
    citations = [
        {"citation_number": 1, "chunk_id": "doc1_c0", "document_id": "doc1"},
        {"citation_number": 2, "chunk_id": "doc1_c1", "document_id": "doc1"},
    ]
    results = [
        MockResult(
            "The partition violence was a key finding in the research"
        ),
        MockResult("completely unrelated content"),
    ]
    report = auditor.audit(ANSWER_EXAMPLE, citations, results)
    assert report["total_citations"] == 2
    assert report["verified_count"] == 1
    assert report["flagged_count"] == 1


def test_audit_no_results():
    """results=None → all citations skip-verified."""
    auditor = CitationAuditor()
    citations = [
        {"citation_number": 1, "chunk_id": "doc1_c0", "document_id": "doc1"},
        {"citation_number": 2, "chunk_id": "doc1_c1", "document_id": "doc1"},
    ]
    report = auditor.audit(ANSWER_EXAMPLE, citations, results=None)
    assert report["total_citations"] == 2
    assert report["verified_count"] == 2
    assert report["flagged_count"] == 0


def test_audit_empty_citations():
    """Empty citation list → total=0, verified=0, flagged=0."""
    auditor = CitationAuditor()
    results = [
        MockResult(
            "The partition violence was a key finding in the research"
        ),
        MockResult(
            "Communal harmony remained an important theme throughout"
        ),
    ]
    report = auditor.audit(ANSWER_EXAMPLE, [], results)
    assert report["total_citations"] == 0
    assert report["verified_count"] == 0
    assert report["flagged_count"] == 0


def test_audit_returns_report_dict():
    """audit() returns a dict with all 4 expected keys."""
    auditor = CitationAuditor()
    citations = [
        {"citation_number": 1, "chunk_id": "doc1_c0", "document_id": "doc1"},
        {"citation_number": 2, "chunk_id": "doc1_c1", "document_id": "doc1"},
    ]
    results = [
        MockResult(
            "The partition violence was a key finding in the research"
        ),
        MockResult(
            "Communal harmony remained an important theme throughout"
        ),
    ]
    report = auditor.audit(ANSWER_EXAMPLE, citations, results)
    assert isinstance(report, dict)
    assert set(report.keys()) == {"total_citations", "verified_count", "flagged_count", "details"}
