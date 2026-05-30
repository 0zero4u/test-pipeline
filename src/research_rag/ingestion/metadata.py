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
TITLE_PATTERN = re.compile(r"^##?\s+(.+)$", re.MULTILINE)
YEAR_PATTERN = re.compile(r"\b(1[89]\d{2}|20[0-2]\d)\b")
JOURNAL_KEYWORDS = [
    "journal", "review", "studies", "quarterly", "transactions",
    "proceedings", "annals", "bulletin", "review", "magazine",
]
VOLUME_ISSUE_PATTERN = re.compile(
    r"(?:Vol\.?|Volume)\s*(\d+)\s*(?:,\s*(?:No\.?|Number|Issue)\s*(\d+))?",
    re.IGNORECASE,
)
DOI_PATTERN = re.compile(r"\b(10\.\d{4,}/[\w\-._;()/:]+)\b")

# Blacklist: phrases that indicate NOT an author line
METADATA_KEYWORDS = {
    "keywords", "key words", "abstract", "doi", "volume", "issue",
    "journal", "proceedings", "received", "accepted", "published",
    "copyright", "issn", "isbn", "correspondence", "author",
    "affiliation", "university", "department", "email", "university",
    "college", "school", "institute", "centre", "center",
}

# Phrases that indicate body text (not author lines)
BODY_TEXT_INDICATORS = [
    "the ", "this ", "that ", "these ", "those ",
    "in ", "on ", "at ", "for ", "with ", "from ",
    "has ", "have ", "had ", "was ", "were ", "are ",
    "is ", "been ", "being ", "will ", "would ",
    "can ", "could ", "may ", "might ", "shall ",
    "according", "however", "moreover", "furthermore",
    "therefore", "consequently", "thus", "hence",
    "but ", "or ", "and ", "nor ", "yet ",
    "i ", "we ", "you ", "they ", "it ",
]

# Two-word phrases that are NOT author names
NON_AUTHOR_PHRASES = {
    "modern india", "british raj", "before partition", "after partition",
    "mano majra", "train to pakistan", "partition violence",
    "communal violence", "human spirit", "realistic picture",
    "study material", "research paper", "journal article",
    "vol. ", "issue ", "pp. ", "pages ",
}


def _is_metadata_line(line: str) -> bool:
    """Check if a line contains metadata keywords."""
    lower = line.strip().lower()
    return any(kw in lower for kw in METADATA_KEYWORDS)


def _is_body_text(line: str) -> bool:
    """Check if a line looks like body text (not author/title)."""
    lower = line.strip().lower()
    # Lines with periods are likely body text
    if "." in line and len(line) > 50:
        return True
    # Lines starting with common body text words
    if any(lower.startswith(word) for word in BODY_TEXT_INDICATORS):
        return True
    return False


def _is_non_author_phrase(line: str) -> bool:
    """Check if line contains known non-author phrases."""
    lower = line.strip().lower()
    return any(phrase in lower for phrase in NON_AUTHOR_PHRASES)


def _looks_like_author_name(name: str) -> bool:
    """Validate if a string looks like a real author name."""
    name = name.strip()
    
    # Too short or too long
    if len(name) < 3 or len(name) > 50:
        return False
    
    # Must have at least 2 words
    parts = name.split()
    if len(parts) < 2:
        return False
    
    # Each word should start with capital letter
    if not all(part[0].isupper() for part in parts if len(part) > 1):
        return False
    
    # Should not contain common non-name words
    lower = name.lower()
    non_name_words = {"the", "and", "for", "with", "from", "into", "about", "vol", "issue", "pp"}
    if any(word in lower.split() for word in non_name_words):
        return False
    
    # Should not be a known non-author phrase
    if _is_non_author_phrase(name):
        return False
    
    return True


def _find_title_line_index(lines: list[str]) -> int:
    """Find the line index where the title appears."""
    # Strategy 1: H1/H2 heading that looks like a title
    for i, line in enumerate(lines[:20]):
        match = TITLE_PATTERN.search(line)
        if match:
            candidate = match.group(1).strip()
            if _looks_like_author_name(candidate) and len(candidate) < 30:
                continue
            if len(candidate) >= 10 and len(candidate) < 500:
                return i

    # Strategy 2: First line that looks like a paper title (no # prefix)
    for i, line in enumerate(lines[:20]):
        cleaned = line.strip()
        if not cleaned or len(cleaned) < 15 or len(cleaned) > 300:
            continue
        if cleaned.startswith("#"):
            continue
        if _looks_like_author_name(cleaned) and len(cleaned) < 30:
            continue
        if _is_body_text(cleaned):
            continue
        if cleaned[0].isupper():
            return i

    return -1


def _extract_title(text: str) -> Optional[str]:
    """Extract the document title from first page text."""
    lines = text.split("\n")
    non_empty = [(i, l.strip()) for i, l in enumerate(lines) if l.strip()]

    if not non_empty:
        return None

    # Strategy 1: Find H1/H2 heading that looks like a title (not author name)
    for i, line in enumerate(lines[:20]):
        match = TITLE_PATTERN.search(line)
        if match:
            candidate = match.group(1).strip()
            # Skip if it looks like an author name (2 words, both capitalized, short)
            if _looks_like_author_name(candidate) and len(candidate) < 30:
                continue
            # Skip if too short
            if len(candidate) < 10:
                continue
            # Good title candidate
            if len(candidate) < 500:
                return candidate

    # Strategy 2: First line that looks like a paper title
    for i, (line_idx, line) in enumerate(non_empty[:10]):
        cleaned = line.strip("#* \t")
        if not cleaned or len(cleaned) < 15 or len(cleaned) > 300:
            continue
        if cleaned.startswith("http"):
            continue
        # Skip if looks like author name
        if _looks_like_author_name(cleaned) and len(cleaned) < 30:
            continue
        # Skip body text
        if _is_body_text(cleaned):
            continue
        # Title should have first letter capitalized
        if cleaned[0].isupper():
            return cleaned

    return None


def _extract_authors(text: str) -> list[str]:
    """Extract author names from first page text."""
    lines = text.split("\n")
    title_idx = _find_title_line_index(lines)

    # Strategy 1: Check lines BEFORE title (author might come first)
    if title_idx > 0:
        for i in range(title_idx - 1, max(-1, title_idx - 4), -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if not line:
                continue
            # Strip markdown heading prefix
            cleaned = line.lstrip("#").strip()
            if not cleaned:
                continue
            if _is_metadata_line(cleaned) or _is_body_text(cleaned) or _is_non_author_phrase(cleaned):
                continue
            if _looks_like_author_name(cleaned):
                authors = re.split(r"\s*(?:,|and|&)\s*", cleaned)
                authors = [a.strip() for a in authors if _looks_like_author_name(a)]
                if authors:
                    return authors

    # Strategy 2: Check lines AFTER title (within 3 lines)
    if title_idx >= 0:
        for i in range(title_idx + 1, min(title_idx + 4, len(lines))):
            line = lines[i].strip()
            if not line:
                continue
            cleaned = line.lstrip("#").strip()
            if not cleaned:
                continue
            if _is_metadata_line(cleaned) or _is_body_text(cleaned) or _is_non_author_phrase(cleaned):
                continue
            if _looks_like_author_name(cleaned):
                authors = re.split(r"\s*(?:,|and|&)\s*", cleaned)
                authors = [a.strip() for a in authors if _looks_like_author_name(a)]
                if authors:
                    return authors

    # Strategy 3: Search first 5 non-empty lines
    non_empty = [(i, l.strip()) for i, l in enumerate(lines) if l.strip()]
    for i, (line_idx, line) in enumerate(non_empty[:5]):
        cleaned = line.lstrip("#").strip()
        if not cleaned:
            continue
        if _is_metadata_line(cleaned) or _is_body_text(cleaned) or _is_non_author_phrase(cleaned):
            continue
        if _looks_like_author_name(cleaned):
            authors = re.split(r"\s*(?:,|and|&)\s*", cleaned)
            authors = [a.strip() for a in authors if _looks_like_author_name(a)]
            if authors:
                return authors

    return []

    # Find title position
    title_idx = _find_title_line_index(lines)

    # Strategy 1: Check lines BEFORE title (author might come first)
    if title_idx > 0:
        for i in range(title_idx - 1, max(-1, title_idx - 4), -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if not line or line.startswith("#"):
                continue
            if _is_metadata_line(line) or _is_body_text(line) or _is_non_author_phrase(line):
                continue
            if _looks_like_author_name(line):
                authors = re.split(r"\s*(?:,|and|&)\s*", line)
                authors = [a.strip() for a in authors if _looks_like_author_name(a)]
                if authors:
                    return authors

    # Strategy 2: Check lines AFTER title (within 3 lines)
    if title_idx >= 0:
        for i in range(title_idx + 1, min(title_idx + 4, len(lines))):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                continue
            if _is_metadata_line(line) or _is_body_text(line) or _is_non_author_phrase(line):
                continue
            if _looks_like_author_name(line):
                authors = re.split(r"\s*(?:,|and|&)\s*", line)
                authors = [a.strip() for a in authors if _looks_like_author_name(a)]
                if authors:
                    return authors

    # Strategy 3: Search first 5 non-empty lines for author pattern
    for i, (line_idx, line) in enumerate(non_empty[:5]):
        if line.startswith("#"):
            continue
        if _is_metadata_line(line) or _is_body_text(line) or _is_non_author_phrase(line):
            continue
        if _looks_like_author_name(line):
            authors = re.split(r"\s*(?:,|and|&)\s*", line)
            authors = [a.strip() for a in authors if _looks_like_author_name(a)]
            if authors:
                return authors

    return []


def _extract_year(text: str) -> Optional[int]:
    """Extract publication year from text.

    Strategy:
    1. Look for year near journal/publisher keywords (highest confidence)
    2. Look for year in copyright/publication patterns
    3. Look for year attached to month names (e.g., "June2023")
    4. Fall back to most common year in reasonable range
    """
    lines = text.split("\n")
    
    # Strategy 1: Year near journal/publisher keywords (first 10 lines)
    journal_patterns = [
        r"(?:journal|vol\.|volume|issue|published|copyright|©|ISSN)\s*.*?\b(1[89]\d{2}|20[0-2]\d)\b",
        r"\b(1[89]\d{2}|20[0-2]\d)\b\s*(?:journal|vol\.|volume|issue|published)",
    ]
    for line in lines[:10]:
        for pattern in journal_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                year = int(match.group(1))
                if 1900 <= year <= 2026:
                    return year
    
    # Strategy 2: Year attached to month (e.g., "June2023", "Jan 2023")
    month_year_pattern = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(\d{4})"
    match = re.search(month_year_pattern, text[:2000], re.IGNORECASE)
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2026:
            return year
    
    # Strategy 3: Year in parentheses after title-like text
    title_year_pattern = r"[\"'].*?[\"'].*?\((\d{4})\)"
    match = re.search(title_year_pattern, text[:1000])
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2026:
            return year
    
    # Strategy 4: Most common year in reasonable range (fallback)
    years = re.findall(r"\b(1[89]\d{2}|20[0-2]\d)\b", text)
    if years:
        valid_years = [int(y) for y in years if 1900 <= int(y) <= 2026]
        if valid_years:
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
    """Extract document metadata from first-page text using heuristics."""
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
