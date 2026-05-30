"""MLA 9th Edition formatter for citations and Works Cited."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

SOURCE_TYPES = ("journal", "book", "film", "edited_volume", "chapter")


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
        source_type: str = "journal",
        editor: str = "",
        publisher: str = "",
        edition: str = "",
        director: str = "",
        production_co: str = "",
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
        self.source_type = source_type
        self.editor = editor
        self.publisher = publisher
        self.edition = edition
        self.director = director
        self.production_co = production_co

    def format_author(self) -> str:
        """Format author name as 'Last, First' in title case."""
        if not self.author:
            return "Unknown Author"
        
        author = self.author.strip()
        
        # Filter out non-author entries
        non_authors = {"key words", "keywords", "unknown", "untitled", "abstract"}
        if author.lower() in non_authors:
            return "Unknown Author"
        
        # Convert all-caps to title case
        if author.isupper():
            author = author.title()
        
        # If already in "Last, First" format, return as-is
        if "," in author:
            return author
        
        parts = author.split()
        if len(parts) >= 2:
            return f"{parts[-1]}, {' '.join(parts[:-1])}"
        return author

    def format_inline(self) -> str:
        """Format for inline citation: (Author Page)."""
        author = self.format_author().split(",")[0]
        if self.page:
            return f"({author} {self.page})"
        return f"({author})"

    def format_works_cited(self) -> str:
        """Format full Works Cited entry based on source_type."""
        if self.source_type == "film":
            return self._format_film()
        elif self.source_type == "edited_volume":
            return self._format_edited_volume_chapter()
        elif self.source_type == "book":
            return self._format_book()
        elif self.source_type == "chapter":
            return self._format_chapter_in_book()
        return self._format_journal()

    def _format_journal(self) -> str:
        """Format journal article: Author. 'Title.' Journal, vol. X, no. Y (Year), pp. X-Y."""
        author = self.format_author()
        title = f'"{self.title}."' if self.title else '"Untitled."'
        journal_part = f" *{self.journal}*" if self.journal else ""
        if self.volume:
            journal_part += f", vol. {self.volume}"
        if self.issue:
            journal_part += f", no. {self.issue}"
        year_part = f" ({self.year})" if self.year else " (n.d.)"
        page_part = f", pp. {self.page}" if self.page else ""
        doi_part = f". DOI: {self.doi}" if self.doi else ""
        return f"{author}. {title}{journal_part}{year_part}{page_part}{doi_part}."

    def _format_book(self) -> str:
        """Format book: Author. *Title*. Edition, Publisher, Year."""
        author = self.format_author()
        title = f"*{self.title}*." if self.title else "*Untitled*."
        edition_part = f" {self.edition}," if self.edition else ""
        publisher_part = f" {self.publisher}," if self.publisher else ""
        year_part = f" {self.year}." if self.year else " n.d."
        return f"{author}. {title}{edition_part}{publisher_part}{year_part}"

    def _format_film(self) -> str:
        """Format film: *Title*. Directed by Director, Production Co., Year."""
        title = f"*{self.title}*." if self.title else "*Untitled*."
        director_part = f" Directed by {self.director}," if self.director else ""
        production_part = f" {self.production_co}," if self.production_co else ""
        year_part = f" {self.year}." if self.year else " n.d."
        return f"{title}{director_part}{production_part}{year_part}"

    def _format_edited_volume_chapter(self) -> str:
        """Format chapter in edited volume: 'Chapter.' *Book*, edited by Editor, Publisher, Year, pp. X-Y."""
        title = f'"{self.title}."' if self.title else '"Untitled."'
        book_title = f" *{self.journal}*," if self.journal else ""
        editor_part = f" edited by {self.editor}," if self.editor else ""
        publisher_part = f" {self.publisher}," if self.publisher else ""
        year_part = f" {self.year}," if self.year else " n.d.,"
        page_part = f" pp. {self.page}" if self.page else ""
        return f"{title}{book_title}{editor_part}{publisher_part}{year_part}{page_part}."

    def _format_chapter_in_book(self) -> str:
        """Format chapter in book: Author. 'Chapter.' *Book*, edited by Editor, Publisher, Year, pp. X-Y."""
        author = self.format_author()
        title = f'"{self.title}."' if self.title else '"Untitled."'
        book_title = f" *{self.journal}*," if self.journal else ""
        editor_part = f" edited by {self.editor}," if self.editor else ""
        publisher_part = f" {self.publisher}," if self.publisher else ""
        year_part = f" {self.year}," if self.year else " n.d.,"
        page_part = f" pp. {self.page}" if self.page else ""
        return f"{author}. {title}{book_title}{editor_part}{publisher_part}{year_part}{page_part}."


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
        source_type: str = "journal",
        editor: str = "",
        publisher: str = "",
        edition: str = "",
        director: str = "",
        production_co: str = "",
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
            source_type=source_type,
            editor=editor,
            publisher=publisher,
            edition=edition,
            director=director,
            production_co=production_co,
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

        # Deduplicate by author+title combination
        seen = set()
        unique_citations = []
        for cit in self._citation_map.values():
            key = f"{cit.format_author()}|{cit.title}"
            if key not in seen:
                seen.add(key)
                unique_citations.append(cit)

        # Sort alphabetically by author last name
        sorted_citations = sorted(
            unique_citations,
            key=lambda c: c.format_author().lower(),
        )

        header = "Works Cited\n" + "=" * 13 + "\n\n"
        entries = [cit.format_works_cited() for cit in sorted_citations]
        return header + "\n\n".join(entries)

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
            "source_type": citation.source_type,
            "editor": citation.editor,
            "publisher": citation.publisher,
            "edition": citation.edition,
            "director": citation.director,
            "production_co": citation.production_co,
        }

    def reset(self) -> None:
        """Clear all citations."""
        self._citation_map.clear()
        self._next_number = 1
