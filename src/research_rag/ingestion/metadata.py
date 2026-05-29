"""Metadata extraction from parsed PDF text using regex/heuristics."""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from research_rag.logging import get_logger
from research_rag.models import DocumentMetadata

logger = get_logger("ingestion.metadata")

# Patterns for metadata extraction
TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
YEAR_PATTERN = re.compile(r"\b(1[89]\d{2}|20[0-2]\d)\b")
JOURNAL_KEYWORDS = [
    "journal", "review", "studies", "quarterly", "transactions",
    "proceedings", "annals", "bulletin", "review", "magazine",
]
JOURNAL_PATTERN = re.compile(
    r"([A-Z][a-zA-Z]*(?:\s+(?:of|and|the|in|for)\s+)?[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*"
    r"(?:\s+(?:Journal|Review|Studies|Quarterly|Transactions|Proceedings|Annals|Bulletin))?)",
)
VOLUME_ISSUE_PATTERN = re.compile(
    r"(?:Vol\.?|Volume)\s*(\d+)\s*(?:,\s*(?:No\.?|Number|Issue)\s*(\d+))?",
    re.IGNORECASE,
)
DOI_PATTERN = re.compile(r"\b(10\.\d{4,}/[\w\-._;()/:]+)\b")
AUTHOR_LINE_PATTERN = re.compile(
    r"^(?:by\s+)?([A-Z][a-zA-Z]*\s+[A-Z][a-zA-Z]*"
    r"(?:\s+(?:and|&)\s+[A-Z][a-zA-Z]*\s+[A-Z][a-zA-Z]*)*)",
    re.MULTILINE,
)


def _extract_title(text: str) -> Optional[str]:
    """Extract the document title from first page text."""
    # Try first H1 heading
    match = TITLE_PATTERN.search(text)
    if match:
        title = match.group(1).strip()
        if len(title) > 10 and len(title) < 500:
            return title

    # Fallback: first line that looks like a title (capitalized, reasonable length)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:20]:
        cleaned = line.strip("#* \t")
        if (
            cleaned
            and cleaned[0].isupper()
            and 15 < len(cleaned) < 300
            and not cleaned.startswith("http")
        ):
            return cleaned

    return None


def _extract_authors(text: str) -> list[str]:
    """Extract author names from first page text."""
    # Try "by Author Name" pattern
    match = AUTHOR_LINE_PATTERN.search(text)
    if match:
        authors_str = match.group(1)
        if authors_str.lower().startswith("by "):
            authors_str = authors_str[3:]
        authors = re.split(r"\s+(?:and|&)\s+|\s*,\s*", authors_str)
        return [a.strip() for a in authors if a.strip()]

    # Fallback: look for common author patterns (Name Surname)
    # Usually authors appear on lines after the title
    lines = text.split("\n")
    for i, line in enumerate(lines[:15]):
        cleaned = line.strip()
        # Look for comma-separated names with initials
        if re.match(
            r"^[A-Z][a-z]*\s+[A-Z][a-z]*"
            r"(?:\s*,\s*[A-Z][a-z]*\s+[A-Z][a-z]*)+$",
            cleaned,
        ):
            return [n.strip() for n in cleaned.split(",")]
        # Look for "Name Surname and Name Surname"
        name_match = re.findall(
            r"([A-Z][a-z]+\s+[A-Z]\.?\s*[A-Z]?[a-z]*)", cleaned
        )
        if len(name_match) >= 1 and i > 0:
            # Only if previous line looks like a title
            prev = lines[i - 1].strip()
            if prev and len(prev) > 15 and not prev.startswith("#"):
                pass
            if len(name_match) <= 4:
                return [n.strip() for n in name_match]

    return []


def _extract_year(text: str) -> Optional[int]:
    """Extract publication year from text."""
    years = YEAR_PATTERN.findall(text)
    if years:
        # Filter to reasonable range
        valid_years = [int(y) for y in years if 1900 <= int(y) <= 2026]
        if valid_years:
            # Return the most common year (usually the publication year)
            from collections import Counter
            return Counter(valid_years).most_common(1)[0][0]
    return None


def _extract_journal(text: str) -> str:
    """Extract journal name from text."""
    lines = text.split("\n")
    for line in lines[:30]:
        cleaned = line.strip().lower()
        for keyword in JOURNAL_KEYWORDS:
            if keyword in cleaned:
                # Return original case version
                match = re.search(
                    r"[A-Z][A-Za-z\s&,]+(?:Journal|Review|Studies|Quarterly|"
                    r"Transactions|Proceedings|Annals|Bulletin)[A-Za-z\s,&]*",
                    line,
                )
                if match:
                    return match.group(0).strip().strip(",")
    return ""


def _extract_volume_issue(text: str) -> tuple[str, str]:
    """Extract volume and issue numbers."""
    match = VOLUME_ISSUE_PATTERN.search(text)
    if match:
        volume = match.group(1) or ""
        issue = match.group(2) or ""
        return volume, issue
    return "", ""


def _extract_doi(text: str) -> Optional[str]:
    """Extract DOI from text."""
    match = DOI_PATTERN.search(text)
    if match:
        return match.group(1).rstrip(".,;:")
    return None


def _compute_confidence(
    title: Optional[str],
    authors: list[str],
    year: Optional[int],
    journal: str,
    doi: Optional[str],
) -> float:
    """Compute metadata extraction confidence score."""
    score = 0.0
    fields = 0

    if title and len(title) > 10:
        score += 0.35
        fields += 1
    if authors:
        score += 0.25
        fields += 1
    if year is not None:
        score += 0.15
        fields += 1
    if journal:
        score += 0.15
        fields += 1
    if doi:
        score += 0.10
        fields += 1

    if fields >= 4:
        return min(score, 1.0)
    elif fields >= 2:
        return min(score * 0.9, 0.8)
    elif fields >= 1:
        return min(score * 0.8, 0.5)
    return 0.3


def extract_metadata(text: str, filename: str) -> DocumentMetadata:
    """Extract document metadata from first-page text using heuristics.

    Args:
        text: First page text from parsed PDF.
        filename: Original PDF filename (used for ID fallback).

    Returns:
        DocumentMetadata with extracted fields and confidence score.
    """
    if not text:
        logger.warning("Empty text provided for metadata extraction: %s", filename)
        return DocumentMetadata(
            document_id=Path(filename).stem,
            title=Path(filename).stem,
            source_file=filename,
            metadata_confidence=0.3,
        )

    title = _extract_title(text)
    authors = _extract_authors(text)
    year = _extract_year(text)
    journal = _extract_journal(text)
    volume, issue = _extract_volume_issue(text)
    doi = _extract_doi(text)

    confidence = _compute_confidence(title, authors, year, journal, doi)
    document_id = Path(filename).stem

    return DocumentMetadata(
        document_id=document_id,
        title=title or Path(filename).stem,
        authors=authors,
        year=year,
        journal=journal,
        volume=volume,
        issue=issue,
        doi=doi,
        source_file=filename,
        metadata_confidence=confidence,
        ingestion_date=datetime.utcnow(),
    )
