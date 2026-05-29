"""Dissertation writer for full dissertation generation."""

import logging
from pathlib import Path
from typing import Optional

from research_rag.retrieval import Retriever
from research_rag.synthesis.client import SynthesisClient
from research_rag.writing.chapter_writer import ChapterWriter
from research_rag.writing.mla_formatter import MLAFormatter
from research_rag.writing.outline import ChapterOutline
from research_rag.writing.state import DissertationState

logger = logging.getLogger(__name__)


class DissertationWriter:
    """Orchestrates full dissertation writing from chapter_plan.md.

    Pipeline:
    1. Parse chapter_plan.md into ChapterOutline objects
    2. Write each chapter via ChapterWriter
    3. Accumulate citations in DissertationState
    4. Generate Works Cited page
    """

    def __init__(
        self,
        retriever: Retriever,
        synthesis_client: Optional[SynthesisClient] = None,
        state: Optional[DissertationState] = None,
        formatter: Optional[MLAFormatter] = None,
        top_k: int = 10,
    ):
        self.retriever = retriever
        self.synthesis_client = synthesis_client or SynthesisClient(
            api_key=retriever.embedding_service.api_key,
        )
        self.formatter = formatter or MLAFormatter()
        self.state = state or DissertationState()
        self.chapter_writer = ChapterWriter(
            retriever=retriever,
            synthesis_client=self.synthesis_client,
            state=self.state,
            formatter=self.formatter,
            top_k=top_k,
        )

    def parse_chapter_plan(self, plan_text: str) -> list[ChapterOutline]:
        """Parse full chapter_plan.md into list of ChapterOutline objects.

        Handles format:
            ### Chapter I — Title (Pages)
            #### 1.1 Section Title
            - Key point

        Returns:
            List of ChapterOutline objects, one per chapter.
        """
        chapters = []
        current_chapter = None
        current_section = None

        for line in plan_text.split("\n"):
            stripped = line.strip()

            # Skip empty lines and non-heading lines
            if not stripped:
                continue

            # Chapter heading: ### Chapter I — Title (8–10 Pages)
            if stripped.startswith("###") and "Chapter" in stripped:
                if current_chapter:
                    chapters.append(current_chapter)

                # Parse chapter number and title
                parts = stripped.replace("###", "").strip().split("—")
                title = parts[1].strip().split("(")[0].strip() if len(parts) >= 2 else "Untitled"

                chapter_num = 0
                for word in stripped.split():
                    if word.isdigit():
                        chapter_num = int(word)
                        break
                    # Handle Roman numerals
                    roman_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}
                    if word in roman_map:
                        chapter_num = roman_map[word]
                        break

                current_chapter = ChapterOutline(chapter_num, title)
                current_section = None
                continue

            # Section heading: #### 1.1 Section Title
            if stripped.startswith("####") and current_chapter:
                sec_title = stripped.replace("####", "").strip()
                # Remove leading number like "1.1"
                if sec_title and sec_title[0].isdigit():
                    sec_title = sec_title.split(" ", 1)[-1] if " " in sec_title else sec_title
                current_section = current_chapter.add_section(sec_title, "")
                continue

            # Key point: - Point text
            if stripped.startswith("-") and current_section:
                point = stripped.lstrip("- ").strip()
                current_section.key_points.append(point)
                continue

        # Don't forget last chapter
        if current_chapter:
            chapters.append(current_chapter)

        return chapters

    def write_dissertation(
        self,
        plan_text: str,
        title: str = "",
        thesis: str = "",
        chapter_callback=None,
    ) -> dict:
        """Write complete dissertation from chapter_plan.md text.

        Args:
            plan_text: Full content of chapter_plan.md
            title: Dissertation title
            thesis: Thesis statement
            chapter_callback: Optional callback(chapter_num, total, result) after each chapter

        Returns:
            Dict with chapters, full_text, word_count, citations, works_cited
        """
        if title:
            self.state.title = title
        if thesis:
            self.state.thesis = thesis

        chapters = self.parse_chapter_plan(plan_text)
        logger.info("Parsed %d chapters from plan", len(chapters))

        chapters_text = []
        all_citations = []

        for i, outline in enumerate(chapters):
            logger.info(
                "Writing chapter %d/%d: %s",
                i + 1,
                len(chapters),
                outline.title,
            )

            result = self.chapter_writer.write_chapter(outline)

            chapters_text.append(result["chapter_text"])
            all_citations.extend(result["citations"])

            if chapter_callback:
                chapter_callback(i + 1, len(chapters), result)

        full_text = "\n\n---\n\n".join(chapters_text)
        word_count = len(full_text.split())
        works_cited = self.formatter.build_works_cited()

        return {
            "chapters": chapters_text,
            "full_text": full_text,
            "word_count": word_count,
            "citations": all_citations,
            "works_cited": works_cited,
            "chapter_count": len(chapters),
            "stats": self.chapter_writer.get_stats(),
        }

    def write_single_chapter(
        self,
        chapter_number: int,
        title: str = "",
        context: str = "",
        sections_data: Optional[list[dict]] = None,
    ) -> dict:
        """Write a single chapter by number.

        Args:
            chapter_number: Chapter number (e.g., 3 for Chapter III)
            title: Chapter title
            context: Context about the chapter's argument
            sections_data: Optional list of section dicts with 'title' and 'description'

        Returns:
            Dict with chapter_text, citations, word_count
        """
        if not title:
            title = f"Chapter {chapter_number}"

        outline = ChapterOutline(chapter_number, title)

        if sections_data:
            for sec in sections_data:
                outline.add_section(sec["title"], sec.get("description", ""))
        else:
            # Default sections
            outline.add_section(f"{chapter_number}.1 Introduction", "Introduce the chapter topic.")
            outline.add_section(f"{chapter_number}.2 Main Analysis", "Core analysis with evidence.")
            outline.add_section(f"{chapter_number}.3 Conclusion", "Summarize and transition.")

        return self.chapter_writer.write_chapter(outline, chapter_context=context)

    def get_works_cited(self) -> str:
        """Generate Works Cited page from all accumulated citations."""
        return self.formatter.build_works_cited()

    def get_full_dissertation(self) -> str:
        """Get complete dissertation text with Works Cited."""
        chapters = []
        for num in sorted(self.state.chapters.keys()):
            chapter = self.state.chapters[num]
            sections_text = []
            for sec in chapter.get("sections", []):
                sections_text.append(sec.get("text", ""))
            chapter_text = "\n\n".join(sections_text)
            chapters.append(f"# Chapter {num}: {chapter['title']}\n\n{chapter_text}")

        full_text = "\n\n---\n\n".join(chapters)
        works_cited = self.get_works_cited()

        if works_cited:
            full_text += f"\n\n---\n\n# Works Cited\n\n{works_cited}"

        return full_text

    def save(self, path: Path) -> None:
        """Save dissertation state to file."""
        self.state.save(path)

    def load(self, path: Path) -> None:
        """Load dissertation state from file."""
        self.state = DissertationState.load(path)
        self.chapter_writer.state = self.state

    def get_stats(self) -> dict:
        """Get dissertation writing statistics."""
        return {
            "title": self.state.title,
            "chapters_written": len(self.state.chapters),
            "total_word_count": self.state.get_word_count(),
            "total_citations": len(self.state.get_all_citations()),
            "current_chapter": self.state.current_chapter,
        }
