"""Section-aware chunking for parsed documents."""

import math
import re
import tiktoken
from typing import Any, Optional

from research_rag.config import IngestionConfig
from research_rag.logging import get_logger
from research_rag.models import Chunk, DocumentMetadata

logger = get_logger("ingestion.chunker")

# Rough token estimation (~5.5 chars per token for English prose)
CHARS_PER_TOKEN = 5

_encoding = None


def _get_encoding():
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.get_encoding("cl100k_base")
    return _encoding


def estimate_tokens(text: str) -> int:
    """Estimate token count using tiktoken (cl100k_base)."""
    if not text:
        return 0
    return len(_get_encoding().encode(text))


def _find_section_boundaries(
    markdown: str, sections: list[dict[str, Any]]
) -> list[tuple[int, int, Optional[str], int]]:
    """Find character boundaries for each section in the markdown.

    Returns list of (char_start, char_end, heading_text, heading_level).
    If no sections found, treats the whole document as one section.
    """
    boundaries: list[tuple[int, int, Optional[str], int]] = []

    if not sections:
        # No sections found — treat whole document as one section
        return [(0, len(markdown), None, 0)]

    for i, section in enumerate(sections):
        heading_text = section["title"]
        level = section["level"]

        # Search for the heading marker + text in markdown
        # Use a flexible pattern to handle formatting differences
        pattern = re.escape(heading_text)
        match = re.search(pattern, markdown)

        if match:
            start = match.start()
            # End is the start of the next section, or end of document
            if i + 1 < len(sections):
                next_pattern = re.escape(sections[i + 1]["title"])
                next_match = re.search(next_pattern, markdown)
                end = next_match.start() if next_match else len(markdown)
            else:
                end = len(markdown)
            boundaries.append((start, end, heading_text, level))
        else:
            # If heading not found in markdown, add at approximate position
            if boundaries:
                # Place after previous section
                prev_end = boundaries[-1][1]
                boundaries.append((prev_end, prev_end + 1, heading_text, level))
            else:
                boundaries.append((0, 1, heading_text, level))

    # Sort and fix overlapping/empty boundaries
    boundaries.sort(key=lambda b: b[0])
    fixed: list[tuple[int, int, Optional[str], int]] = []
    for start, end, heading, level in boundaries:
        if not fixed:
            fixed.append((max(0, start), min(len(markdown), end), heading, level))
        else:
            prev = fixed[-1]
            new_start = max(prev[1], start)
            new_end = min(len(markdown), max(new_start + 1, end))
            if new_start < new_end:
                fixed.append((new_start, new_end, heading, level))

    if not fixed:
        fixed = [(0, len(markdown), None, 0)]

    return fixed


def _split_large_section(
    text: str, max_chars: int, overlap_chars: int
) -> list[str]:
    """Split a large section at paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len <= max_chars:
            current.append(para)
            current_len += para_len + 2  # +2 for paragraph separator
        else:
            if current:
                chunk = "\n\n".join(current)
                chunks.append(chunk)

                # Apply overlap: include last paragraph(s) from previous chunk
                overlap_text = ""
                overlap_paras: list[str] = []
                overlap_len = 0
                for p in reversed(current):
                    p_len = len(p) + 2
                    if overlap_len + p_len <= overlap_chars:
                        overlap_paras.insert(0, p)
                        overlap_len += p_len
                    else:
                        break
                if overlap_paras:
                    overlap_text = "\n\n".join(overlap_paras) + "\n\n"

                current = [overlap_text + para] if overlap_text else [para]
                current_len = len(current[0])
            else:
                # Single paragraph exceeds max — hard split
                chunks.append(para[:max_chars])
                remaining = para[max_chars:]
                if remaining:
                    current = [remaining]
                    current_len = len(remaining)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def chunk_document(
    markdown: str,
    sections: list[dict[str, Any]],
    doc_metadata: DocumentMetadata,
    config: Optional[IngestionConfig] = None,
) -> list[Chunk]:
    """Split a parsed document into chunks using section-aware algorithm.

    Args:
        markdown: Full document markdown with page markers.
        sections: List of section heading info from parser.
        doc_metadata: Document-level metadata to attach to each chunk.
        config: Ingestion config (chunk size, overlap). Uses defaults if None.

    Returns:
        List of Chunk objects.
    """
    if config is None:
        config = IngestionConfig()

    min_chars = config.chunk_size_min * CHARS_PER_TOKEN
    max_chars = config.chunk_size_max * CHARS_PER_TOKEN
    overlap_chars = int(max_chars * config.chunk_overlap)

    # Find section boundaries in markdown
    boundaries = _find_section_boundaries(markdown, sections)

    # Parse page markers for page tracking
    page_markers = list(re.finditer(r"<!-- page break -->", markdown))
    page_positions = [m.end() for m in page_markers]

    def _get_page_for_position(pos: int) -> int:
        """Determine page number for a character position."""
        for i, pp in enumerate(page_positions):
            if pos < pp:
                return i + 1
        return len(page_positions) + 1

    raw_chunks: list[tuple[str, str, int, int]] = []
    # (text, section_title, page_start, page_end)

    for start, end, heading, level in boundaries:
        section_text = markdown[start:end].strip()
        if not section_text:
            continue

        section_title = heading or ""

        section_chars = len(section_text)

        if section_chars <= max_chars and section_chars >= min_chars:
            # Ideal size — keep as single chunk
            page_start = _get_page_for_position(start)
            page_end = _get_page_for_position(end)
            raw_chunks.append((section_text, section_title, page_start, page_end))

        elif section_chars < min_chars:
            # Too small — merge with next section (handled by reducing boundaries)
            # For now, keep as-is but it'll merge with the next on append
            page_start = _get_page_for_position(start)
            page_end = _get_page_for_position(end)
            raw_chunks.append((section_text, section_title, page_start, page_end))

        else:
            # Too large — split at paragraph boundaries
            sub_chunks = _split_large_section(section_text, max_chars, overlap_chars)
            for sub_text in sub_chunks:
                # Find approximate position in original markdown
                sub_start = markdown.find(sub_text[:50], start)
                if sub_start == -1:
                    sub_start = start
                sub_end = sub_start + len(sub_text)
                page_start = _get_page_for_position(sub_start)
                page_end = _get_page_for_position(sub_end)
                raw_chunks.append((
                    sub_text.strip(),
                    section_title,
                    page_start,
                    page_end,
                ))

    # Merge small chunks with next chunk
    merged_chunks: list[tuple[str, str, int, int]] = []
    for chunk in raw_chunks:
        text, title, p_start, p_end = chunk
        char_count = len(text)

        if (
            merged_chunks
            and char_count < min_chars
            and estimate_tokens(merged_chunks[-1][0]) < config.chunk_size_max
        ):
            # Merge with previous chunk
            prev_text, prev_title, prev_p_start, prev_p_end = merged_chunks[-1]
            merged_text = prev_text + "\n\n" + text
            merged_chunks[-1] = (
                merged_text,
                prev_title or title,
                prev_p_start,
                p_end,
            )
        else:
            merged_chunks.append(chunk)

    # Build final Chunk objects
    chunks: list[Chunk] = []
    for i, (text, title, p_start, p_end) in enumerate(merged_chunks):
        token_count = estimate_tokens(text)
        chunk_id = f"{doc_metadata.document_id}_chunk_{i:04d}"

        # Detect flags
        has_quoted = bool(re.search(r'["""''\u2018\u2019]', text))
        has_citations = bool(
            re.search(r"\[\d+\]|\(\w+,\s*\d{4}\)", text)
        )

        chunk = Chunk(
            chunk_id=chunk_id,
            document_id=doc_metadata.document_id,
            section_title=title,
            page_start=p_start,
            page_end=p_end,
            text=text,
            token_count=token_count,
            metadata=doc_metadata,
            flags={
                "quoted_text": has_quoted,
                "has_citations": has_citations,
            },
        )
        chunks.append(chunk)

    logger.info(
        "Created %d chunks from document %s",
        len(chunks),
        doc_metadata.document_id,
    )

    return chunks
