"""Cross-chapter state management for dissertation writing."""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DissertationState:
    """Manages state across chapters for coherent dissertation writing.

    Tracks thesis statement, previous chapter summaries,
    accumulated citations, and writing progress.
    """

    def __init__(self, title: str = "", thesis: str = ""):
        self.title = title
        self.thesis = thesis
        self.chapters: dict[int, dict] = {}
        self.all_citations: list[dict] = []
        self.current_chapter: Optional[int] = None

    def start_chapter(self, chapter_number: int, title: str) -> None:
        """Mark a chapter as started."""
        self.current_chapter = chapter_number
        self.chapters[chapter_number] = {
            "title": title,
            "sections": [],
            "summary": "",
            "citations": [],
        }
        logger.info("Started Chapter %d: %s", chapter_number, title)

    def add_section(
        self,
        chapter_number: int,
        section_title: str,
        text: str,
        citations: list[dict],
    ) -> None:
        """Record a completed section."""
        if chapter_number not in self.chapters:
            self.start_chapter(chapter_number, "")

        chapter = self.chapters[chapter_number]
        chapter["sections"].append({
            "title": section_title,
            "text": text,
            "word_count": len(text.split()),
        })
        chapter["citations"].extend(citations)
        self.all_citations.extend(citations)

    def finish_chapter(self, chapter_number: int, summary: str) -> None:
        """Mark a chapter as completed with a summary."""
        if chapter_number in self.chapters:
            self.chapters[chapter_number]["summary"] = summary
        self.current_chapter = None

    def get_previous_summaries(self, up_to_chapter: int) -> str:
        """Get summaries of all chapters before the given number."""
        summaries = []
        for num in sorted(self.chapters.keys()):
            if num < up_to_chapter:
                ch = self.chapters[num]
                if ch.get("summary"):
                    summaries.append(f"Chapter {num}: {ch['summary']}")
        return "\n".join(summaries) if summaries else ""

    def get_current_chapter_summary(self) -> str:
        """Get summary of sections written in current chapter."""
        if self.current_chapter is None:
            return ""
        chapter = self.chapters.get(self.current_chapter)
        if not chapter:
            return ""
        section_summaries = []
        for sec in chapter["sections"]:
            words = sec.get("word_count", 0)
            section_summaries.append(f"{sec['title']} ({words} words)")
        return "; ".join(section_summaries)

    def get_all_citations(self) -> list[dict]:
        """Get all citations across all chapters."""
        return self.all_citations

    def get_chapter_citations(self, chapter_number: int) -> list[dict]:
        """Get citations for a specific chapter."""
        chapter = self.chapters.get(chapter_number)
        return chapter["citations"] if chapter else []

    def get_word_count(self, chapter_number: Optional[int] = None) -> int:
        """Get word count for a chapter or total."""
        if chapter_number:
            chapter = self.chapters.get(chapter_number)
            if not chapter:
                return 0
            return sum(s.get("word_count", 0) for s in chapter["sections"])

        total = 0
        for chapter in self.chapters.values():
            total += sum(s.get("word_count", 0) for s in chapter["sections"])
        return total

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "thesis": self.thesis,
            "chapters": self.chapters,
            "all_citations": self.all_citations,
            "current_chapter": self.current_chapter,
        }

    def save(self, path: Path) -> None:
        """Save state to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.info("Saved dissertation state to %s", path)

    @classmethod
    def load(cls, path: Path) -> "DissertationState":
        """Load state from JSON file."""
        if not path.exists():
            return cls()
        try:
            with open(path) as f:
                data = json.load(f)
            state = cls(title=data.get("title", ""), thesis=data.get("thesis", ""))
            state.chapters = data.get("chapters", {})
            state.all_citations = data.get("all_citations", [])
            state.current_chapter = data.get("current_chapter")
            return state
        except Exception as exc:
            logger.warning("Failed to load state: %s", exc)
            return cls()
