"""Citation formatter for converting [1] markers to MLA/APA formatted citations."""

import logging
import re

logger = logging.getLogger(__name__)


class CitationFormatter:
    """Converts raw [1] citation markers in LLM answer text to proper
    MLA/APA formatted inline citations.

    Also generates a "Works Cited" / References section.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_last_name(self, name: str) -> str:
        """Extract the surname from a full author name.

        Args:
            name: Full author name, e.g. "John Smith" or "Smith, John".

        Returns:
            Surname string, or "Unknown" if *name* is empty.
        """
        if not name or not name.strip():
            return "Unknown"

        name = name.strip()

        # "Smith, John" -> "Smith"
        if "," in name:
            return name.split(",")[0].strip()

        # "John Smith" -> "Smith"
        parts = name.split()
        return parts[-1]

    # ------------------------------------------------------------------
    def format_inline(self, citation: dict, style: str = "mla") -> str:
        """Format a single citation dict as an inline parenthetical reference.

        Args:
            citation: Dict with keys ``citation_number``, ``authors`` (list[str]),
                ``year`` (str|None), ``page`` (int|None), ``title`` (str),
                ``document_id`` (str).
            style: ``"mla"`` (default) or ``"apa"``.

        Returns:
            Formatted inline citation string, e.g. ``(Smith 2021, p. 45)``.
        """
        authors: list[str] = citation.get("authors") or []
        year: str | None = citation.get("year")
        page: int | None = citation.get("page")
        title: str = citation.get("title") or ""
        document_id: str = citation.get("document_id") or ""
        style = style.lower()

        # --- Author part ---------------------------------------------------
        surnames = [self.extract_last_name(a) for a in authors if a.strip()]
        author_part = self._format_author_part(surnames, title, document_id, style)

        # --- Year part -----------------------------------------------------
        year_part = "n.d." if not year else str(year)

        # --- Page part -----------------------------------------------------
        page_part = f"p. {page}" if page is not None else None

        # --- Assemble ------------------------------------------------------
        if style == "apa":
            # (LastName, Year, p. #)
            parts = [author_part, year_part]
            if page_part:
                parts.append(page_part)
            return "(" + ", ".join(parts) + ")"
        else:
            # MLA: (LastName Year, p. #)  – no comma between author and year
            body = f"{author_part} {year_part}"
            if page_part:
                body += f", {page_part}"
            return f"({body})"

    # ------------------------------------------------------------------
    def replace_citations(
        self, answer: str, citations: list[dict], style: str = "mla"
    ) -> str:
        """Replace all ``[N]`` markers in *answer* with formatted inline citations.

        Args:
            answer: Raw answer text containing ``[1]``, ``[2]`` etc.
            citations: List of citation dicts (as accepted by ``format_inline``).
            style: ``"mla"`` or ``"apa"``.

        Returns:
            Answer text with ``[N]`` markers replaced.
        """
        lookup = {
            str(c["citation_number"]): self.format_inline(c, style)
            for c in citations
        }
        return re.sub(
            r"\[(\d+)[^\]]*\]",
            lambda m: lookup.get(m.group(1), m.group(0)),
            answer,
        )

    # ------------------------------------------------------------------
    def generate_works_cited(
        self, citations: list[dict], style: str = "mla"
    ) -> str:
        """Generate a "Works Cited" (MLA) or "References" (APA) section.

        Args:
            citations: List of citation dicts.
            style: ``"mla"`` (default) or ``"apa"``.

        Returns:
            Markdown section string, or ``""`` when there are no citations.
        """
        if not citations:
            return ""

        # Deduplicate by document_id (first occurrence wins)
        seen: set[str] = set()
        unique: list[dict] = []
        for c in citations:
            doc_id = c.get("document_id", "")
            if doc_id not in seen:
                seen.add(doc_id)
                unique.append(c)

        # Sort by last name of first author; "Unknown" entries go to end.
        def _sort_key(c: dict) -> tuple:
            authors = c.get("authors") or []
            surname = (
                self.extract_last_name(authors[0])
                if authors
                else "Unknown"
            )
            # Push "Unknown" to the end
            return (1 if surname == "Unknown" else 0, surname.lower())

        unique.sort(key=_sort_key)

        entries: list[str] = []
        for c in unique:
            entries.append(self._format_entry(c, style))

        heading = "\n\n## References\n\n" if style == "apa" else "\n\n## Works Cited\n\n"
        return heading + "\n\n".join(entries) + "\n\n"

    # ------------------------------------------------------------------
    def format(
        self,
        answer: str,
        citations: list[dict],
        style: str = "mla",
        include_works_cited: bool = True,
    ) -> dict:
        """Full formatting pipeline: replace inline citations + optional Works Cited.

        Args:
            answer: Raw answer text.
            citations: List of citation dicts.
            style: ``"mla"`` or ``"apa"``.
            include_works_cited: Whether to append a works-cited section.

        Returns:
            Dict with keys ``"answer"`` (str) and ``"works_cited"`` (str).
        """
        formatted_answer = self.replace_citations(answer, citations, style)
        works_cited = (
            self.generate_works_cited(citations, style)
            if include_works_cited
            else ""
        )
        if works_cited:
            formatted_answer += works_cited
        return {"answer": formatted_answer, "works_cited": works_cited}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _format_author_part(
        self,
        surnames: list[str],
        title: str,
        document_id: str,
        style: str,
    ) -> str:
        """Build the author portion of an inline citation.

        Falls back to *title* (in double quotes) and then to *document_id*
        when there are no known authors.
        """
        if surnames:
            if len(surnames) == 1:
                return surnames[0]
            elif len(surnames) == 2:
                joiner = " & " if style == "apa" else " and "
                return joiner.join(surnames)
            else:
                # 3+ authors → "Last1 et al."  (MLA) / "Last1 et al." (APA)
                return f"{surnames[0]} et al."
        elif title:
            return f'"{title}"'
        else:
            return document_id or "Unknown"

    def _format_entry(self, citation: dict, style: str) -> str:
        """Format one entry for the Works Cited / References section."""
        authors: list[str] = citation.get("authors") or []
        year: str | None = citation.get("year")
        title: str = citation.get("title") or ""
        page: int | None = citation.get("page")

        # Author line: "Last, First."
        if authors:
            author_entries = []
            for a in authors:
                parts = a.rsplit(",", 1)
                if len(parts) == 2:
                    # Already "Last, First"
                    author_entries.append(a.strip())
                else:
                    # "First Last" → "Last, First"
                    name_parts = a.strip().split()
                    if len(name_parts) >= 2:
                        author_entries.append(
                            f"{name_parts[-1]}, {' '.join(name_parts[:-1])}"
                        )
                    else:
                        author_entries.append(a.strip())
            author_line = ", ".join(author_entries) + "."
        else:
            author_line = ""

        if style == "apa":
            return self._apa_entry(author_line, year, title, page)
        return self._mla_entry(author_line, year, title, page)

    def _mla_entry(
        self,
        author_line: str,
        year: str | None,
        title: str,
        page: int | None,
    ) -> str:
        """MLA entry: Author. "Title." Year. p. Page."""
        parts = []
        if author_line:
            parts.append(author_line)
        if title:
            parts.append(f'"{title}."')
        if year:
            parts.append(f"{year}.")
        if page is not None:
            parts.append(f"p. {page}.")
        return " ".join(parts)

    def _apa_entry(
        self,
        author_line: str,
        year: str | None,
        title: str,
        page: int | None,
    ) -> str:
        """APA entry: Author (Year). Title. p. Page."""
        parts = []
        if author_line:
            parts.append(author_line)
        if year:
            parts.append(f"({year}).")
        else:
            parts.append("(n.d.).")
        if title:
            parts.append(f"{title}.")
        if page is not None:
            parts.append(f"p. {page}.")
        return " ".join(parts)
