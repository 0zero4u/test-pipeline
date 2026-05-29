"""MLA 9th Edition formatter for citations and Works Cited."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MLACitation:
    """A single MLA-formatted citation."""

    def __init__(
        self,
        author: str = "",
        title: str = "",
        year: Optional[int] = None,
        journal: str = "",
        volume: str = "",
        issue: str = "",
        page: str = "",
        doi: str = "",
        source_file: str = "",
    ):
        self.author = author
        self.title = title
        self.year = year
        self.journal = journal
        self.volume = volume
        self.issue = issue
        self.page = page
        self.doi = doi
        self.source_file = source_file

    def format_author(self) -> str:
        """Format author name as 'Last, First'."""
        if not self.author:
            return "Unknown Author"
        parts = self.author.strip().split()
        if len(parts) >= 2:
            return f"{parts[-1]}, {' '.join(parts[:-1])}"
        return self.author

    def format_inline(self) -> str:
        """Format for inline citation: (Author Page)."""
        author = self.format_author().split(",")[0]
        if self.page:
            return f"({author} {self.page})"
        return f"({author})"

    def format_works_cited(self) -> str:
        """Format full Works Cited entry."""
        author = self.format_author()

        if self.title:
            if self.journal:
                title_fmt = f'"{self.title}."'
            else:
                title_fmt = f"*{self.title}*."
        else:
            title_fmt = "Untitled."

        journal_part = ""
        if self.journal:
            journal_part = f" *{self.journal}*"
            if self.volume:
                journal_part += f", vol. {self.volume}"
            if self.issue:
                journal_part += f", no. {self.issue}"

        year_part = f" ({self.year})" if self.year else " (n.d.)"
        page_part = f", pp. {self.page}" if self.page else ""
        doi_part = f". DOI: {self.doi}" if self.doi else ""

        return f"{author}. {title_fmt}{journal_part}{year_part}{page_part}{doi_part}."


class MLAFormatter:
    """Formats citations in MLA 9th Edition style."""

    def __init__(self):
        self._citation_map: dict[str, MLACitation] = {}
        self._next_number = 1

    def add_citation(
        self,
        citation_number: int,
        author: str = "",
        title: str = "",
        year: Optional[int] = None,
        journal: str = "",
        volume: str = "",
        issue: str = "",
        page: str = "",
        doi: str = "",
        source_file: str = "",
    ) -> MLACitation:
        """Add a citation to the formatter."""
        citation = MLACitation(
            author=author,
            title=title,
            year=year,
            journal=journal,
            volume=volume,
            issue=issue,
            page=page,
            doi=doi,
            source_file=source_file,
        )
        self._citation_map[str(citation_number)] = citation
        return citation

    def get_inline_citation(self, number: int) -> str:
        """Get inline citation format for a number."""
        citation = self._citation_map.get(str(number))
        if citation:
            return citation.format_inline()
        return f"[{number}]"

    def format_answer(self, answer: str) -> str:
        """Replace [N] markers with MLA inline citations."""
        import re
        def replace_marker(match):
            num = int(match.group(1))
            return self.get_inline_citation(num)
        return re.sub(r"\[(\d+)\]", replace_marker, answer)

    def build_works_cited(self) -> str:
        """Build Works Cited page from all added citations."""
        if not self._citation_map:
            return ""

        sorted_citations = sorted(
            self._citation_map.values(),
            key=lambda c: c.format_author(),
        )

        entries = [cit.format_works_cited() for cit in sorted_citations]
        return "\n\n".join(entries)

    def get_citation_details(self, number: int) -> Optional[dict]:
        """Get citation details for bibliography building."""
        citation = self._citation_map.get(str(number))
        if not citation:
            return None
        return {
            "author": citation.author,
            "title": citation.title,
            "year": citation.year,
            "journal": citation.journal,
            "volume": citation.volume,
            "issue": citation.issue,
            "page": citation.page,
            "doi": citation.doi,
            "source_file": citation.source_file,
        }

    def reset(self) -> None:
        """Clear all citations."""
        self._citation_map.clear()
        self._next_number = 1
