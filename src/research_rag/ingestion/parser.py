"""PDF parser using Docling."""

import logging
import re
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter
from docling_core.types.doc import DocItemLabel, TextItem

from research_rag.logging import get_logger

logger = get_logger("ingestion.parser")

PAGE_BREAK_MARKER = "<!-- page break -->"


class ParsedDocument:
    """Result of parsing a PDF with Docling."""

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


def _extract_sections(doc: Any) -> list[dict[str, Any]]:
    """Extract section headings from a DoclingDocument."""
    sections: list[dict[str, Any]] = []
    for item, level in doc.iterate_items():
        if isinstance(item, TextItem) and item.label == DocItemLabel.SECTION_HEADER:
            page_no = item.prov[0].page_no if item.prov else 1
            sections.append({
                "title": item.text,
                "level": item.level if hasattr(item, "level") else level,
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
    """Parse a PDF file using Docling.

    Args:
        file_path: Path to the PDF file.

    Returns:
        ParsedDocument containing markdown, sections, and page info.

    Raises:
        FileNotFoundError: If the PDF does not exist.
        RuntimeError: If Docling fails to parse the PDF.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    document_id = _make_document_id(file_path)

    logger.info("Parsing PDF: %s", file_path.name)

    try:
        converter = DocumentConverter()
        result = converter.convert(str(file_path))
        doc = result.document
    except Exception as exc:
        raise RuntimeError(
            f"Docling failed to parse {file_path.name}: {exc}"
        ) from exc

    # Export markdown with page break placeholders
    markdown = doc.export_to_markdown(
        page_break_placeholder=PAGE_BREAK_MARKER,
    )

    # Extract sections
    sections = _extract_sections(doc)

    # Get page boundaries from markdown
    page_boundaries = _get_page_boundaries(markdown)

    # Determine page count
    page_count = max(doc.page_count, len(page_boundaries))

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
