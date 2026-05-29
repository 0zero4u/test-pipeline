"""Citation parser for extracting inline citations from LLM output."""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from research_rag.retrieval.search import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A single citation extracted from an LLM response."""

    chunk_id: str
    document_id: str
    title: str
    page: int
    relevance_score: float
    citation_number: int

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "title": self.title,
            "page": self.page,
            "relevance_score": round(self.relevance_score, 3),
            "citation_number": self.citation_number,
        }


class CitationParser:
    """Extracts inline citations [1], [2], etc. from LLM responses.

    Matches citation markers to the evidence chunks that were provided.
    """

    # Pattern matches [1], [2,3], [1-3], etc.
    CITATION_PATTERN = re.compile(r"\[(\d+(?:\s*[,–\-]\s*\d+)*)\]")

    def parse(
        self,
        answer: str,
        evidence_results: list[SearchResult],
    ) -> list[Citation]:
        """Parse citations from an LLM-generated answer.

        Args:
            answer: The raw answer text containing [1], [2] markers.
            evidence_results: The list of SearchResult objects that were
                provided as evidence (indexed 1-based).

        Returns:
            List of Citation objects.
        """
        citations: list[Citation] = []
        seen_ids: set[str] = set()

        matches = self.CITATION_PATTERN.findall(answer)

        for match in matches:
            numbers = self._expand_numbers(match)
            for num in numbers:
                idx = num - 1  # Convert to 0-based
                if 0 <= idx < len(evidence_results):
                    result = evidence_results[idx]
                    if result.chunk_id not in seen_ids:
                        seen_ids.add(result.chunk_id)
                        citations.append(
                            Citation(
                                chunk_id=result.chunk_id,
                                document_id=result.document_id,
                                title=result.title,
                                page=result.page_start,
                                relevance_score=result.score,
                                citation_number=num,
                            )
                        )

        logger.debug("Parsed %d unique citations from answer", len(citations))
        return citations

    def _expand_numbers(self, group: str) -> list[int]:
        """Expand citation groups like '1,2,3' or '1-3' into list of ints."""
        numbers: list[int] = []
        # Split on commas first to get individual items (numbers or ranges)
        items = re.split(r"\s*,\s*", group)
        for item in items:
            item = item.strip()
            # Check for range pattern: 1-3 or 1–3
            range_match = re.match(r"(\d+)\s*[–\-]\s*(\d+)", item)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2))
                if start <= end:
                    numbers.extend(range(start, end + 1))
            elif item.isdigit():
                numbers.append(int(item))
        return sorted(set(numbers))
