"""Citation validator for verifying citations against metadata."""

import logging
from typing import Optional

from research_rag.citations.parser import Citation

logger = logging.getLogger(__name__)


class CitationValidator:
    """Validates citations against ground truth metadata from Chroma.

    Enriches citations with author names and publication year.
    Catches hallucinations by detecting mismatches.
    """

    def validate(
        self,
        citations: list[Citation],
        metadata_map: dict[str, dict],
    ) -> list[Citation]:
        """Validate and enrich citations with metadata.

        Args:
            citations: List of Citation objects from parser.
            metadata_map: Dict mapping document_id -> metadata dict.
                Each metadata dict has: title, authors (list), year (int|None).

        Returns:
            List of Citation objects with authors and year enriched.
        """
        validated = []

        for citation in citations:
            # Look up metadata by document_id
            meta = metadata_map.get(citation.document_id)

            if meta:
                # Enrich with metadata
                citation.authors = meta.get("authors", [])
                citation.year = meta.get("year")
                citation.is_validated = True

                logger.debug(
                    "Validated citation [%d]: %s by %s (%s)",
                    citation.citation_number,
                    citation.title[:50],
                    ", ".join(citation.authors) if citation.authors else "unknown",
                    citation.year or "n.d.",
                )
            else:
                # No metadata found - flag as unvalidated
                citation.is_validated = False
                logger.warning(
                    "Citation [%d] document_id '%s' not found in metadata",
                    citation.citation_number,
                    citation.document_id,
                )

            validated.append(citation)

        return validated

    def format_citation(self, citation: Citation) -> str:
        """Format a single citation for display.

        Args:
            citation: Citation object to format.

        Returns:
            Formatted string like "Dr Urmila Devi (2021) — Title, p. 45"
        """
        parts = []

        # Author + year prefix
        if citation.authors:
            author_str = self._format_authors(citation.authors)
            if citation.year:
                parts.append(f"{author_str} ({citation.year})")
            else:
                parts.append(f"{author_str} (n.d.)")
        elif citation.year:
            parts.append(f"({citation.year})")

        # Title
        if citation.title:
            parts.append(citation.title)

        # Page
        if citation.page:
            parts.append(f"p. {citation.page}")

        return " — ".join(parts) if parts else f"[{citation.citation_number}]"

    def _format_authors(self, authors: list[str]) -> str:
        """Format author list for display.

        Args:
            authors: List of author names.

        Returns:
            Formatted string like "Dr Urmila Devi" or "Naved Alam et al."
        """
        if not authors:
            return "Unknown"
        elif len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return f"{authors[0]} & {authors[1]}"
        else:
            return f"{authors[0]} et al."
