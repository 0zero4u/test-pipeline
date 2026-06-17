"""PDF parser using pymupdf4llm."""

import logging
import re
from pathlib import Path
from typing import Any

import pymupdf4llm

from research_rag.logging import get_logger

logger = get_logger("ingestion.parser")

PAGE_BREAK_MARKER = "<!-- page break -->"


class ParsedDocument:
    """Result of parsing a PDF with pymupdf4llm."""

    def __init__(
        self,
        document_id: str,
        file_path: Path,
        markdown: str,
        sections: list[dict[str, Any]],
        page_boundaries: list[tuple[int, int, int]],
        page_count: int,
        first_page_text: str,
    ) -> None:
        self.document_id = document_id
        self.file_path = file_path
        self.markdown = markdown
        self.sections = sections
        self.page_boundaries = page_boundaries
        self.page_count = page_count
        self.first_page_text = first_page_text

    def __repr__(self) -> str:
        return (
            f"ParsedDocument(id={self.document_id}, "
            f"pages={self.page_count}, "
            f"sections={len(self.sections)})"
        )


def _make_document_id(file_path: Path) -> str:
    """Create a clean document ID from filename."""
    stem = file_path.stem
    # Lowercase, replace non-alphanumeric with underscores
    stem = re.sub(r"[^a-zA-Z0-9]+", "_", stem).strip("_").lower()
    # Truncate to reasonable length
    return stem[:64]


def _extract_sections(pages: list[str]) -> list[dict[str, Any]]:
    """Extract section headings from markdown pages.

    Parses markdown headings (h1/h2/h3) from each page and returns
    section metadata with title, level, and page number.

    Args:
        pages: List of markdown strings, one per page.

    Returns:
        List of dicts with 'title', 'level', and 'page_no' keys.
    """
    sections: list[dict[str, Any]] = []
    seen_headings: set[tuple[str, int]] = set()

    heading_pattern = re.compile(r"^ {0,3}(#{1,3})\s+(.+)$", re.MULTILINE)

    for page_no, page_text in enumerate(pages, 1):
        for match in heading_pattern.finditer(page_text):
            level = len(match.group(1))
            title = match.group(2).strip()
            # Deduplicate identical headings on the same level
            key = (title, level)
            if key not in seen_headings:
                seen_headings.add(key)
                sections.append({
                    "title": title,
                    "level": level,
                    "page_no": page_no,
                })

    return sections


def _get_page_boundaries(markdown: str) -> list[tuple[int, int, int]]:
    """Parse page boundaries from markdown with page break markers.

    Returns list of (page_number, char_start, char_end) tuples.
    """
    boundaries: list[tuple[int, int, int]] = []
    pattern = re.compile(re.escape(PAGE_BREAK_MARKER))
    parts = pattern.split(markdown)

    if not parts:
        return [(1, 0, len(markdown))]

    for i, part in enumerate(parts):
        page_no = i + 1
        char_start = sum(len(p) + len(PAGE_BREAK_MARKER) for p in parts[:i])
        char_end = char_start + len(part)
        boundaries.append((page_no, char_start, char_end))

    if not boundaries:
        boundaries = [(1, 0, len(markdown))]

    return boundaries


def parse_pdf(file_path: Path) -> ParsedDocument:
    """Parse a PDF file using pymupdf4llm.

    Args:
        file_path: Path to the PDF file.

    Returns:
        ParsedDocument containing markdown, sections, and page info.

    Raises:
        FileNotFoundError: If the PDF does not exist.
        RuntimeError: If pymupdf4llm fails to parse the PDF.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    document_id = _make_document_id(file_path)

    logger.info("Parsing PDF: %s", file_path.name)

    try:
        chunks = pymupdf4llm.to_markdown(str(file_path), page_chunks=True)
    except Exception as exc:
        raise RuntimeError(
            f"pymupdf4llm failed to parse {file_path.name}: {exc}"
        ) from exc

    # pymupdf4llm returns list of dicts with 'text' key when page_chunks=True
    pages = [chunk["text"] for chunk in chunks] if chunks else [""]

    # Reconstruct markdown with page break markers
    markdown = PAGE_BREAK_MARKER.join(pages)

    # Extract sections from page markdown
    sections = _extract_sections(pages)

    # Get page boundaries from markdown
    page_boundaries = _get_page_boundaries(markdown)

    # Determine page count
    page_count = max(len(pages), len(page_boundaries))

    # Extract first page text (for metadata extraction)
    first_page_text = markdown
    if page_boundaries:
        _, start, end = page_boundaries[0]
        first_page_text = markdown[start:end].strip()

    return ParsedDocument(
        document_id=document_id,
        file_path=file_path,
        markdown=markdown,
        sections=sections,
        page_boundaries=page_boundaries,
        page_count=page_count,
        first_page_text=first_page_text,
    )
