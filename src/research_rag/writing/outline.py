"""Chapter outline generator for dissertation writing."""

import logging
from typing import Optional

from research_rag.synthesis.client import SynthesisClient
from research_rag.writing.prompts import build_chapter_outline_prompt

logger = logging.getLogger(__name__)


class ChapterSection:
    """A single section within a chapter."""

    def __init__(
        self,
        title: str,
        description: str,
        target_words: int = 1500,
    ):
        self.title = title
        self.description = description
        self.target_words = target_words
        self.key_points: list[str] = []
        self.generated_text: str = ""
        self.citations: list[dict] = []

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "target_words": self.target_words,
            "key_points": self.key_points,
            "generated_text": self.generated_text,
            "citations": self.citations,
        }


class ChapterOutline:
    """Represents a chapter outline with sections.

    Parses chapter_plan.md style outlines into structured objects
    that ChapterWriter can process.
    """

    def __init__(
        self,
        chapter_number: int,
        title: str,
        description: str = "",
    ):
        self.chapter_number = chapter_number
        self.title = title
        self.description = description
        self.sections: list[ChapterSection] = []
        self.introduction: str = ""
        self.conclusion: str = ""

    def add_section(
        self,
        title: str,
        description: str,
        target_words: int = 1500,
    ) -> ChapterSection:
        """Add a section to the chapter outline."""
        section = ChapterSection(title, description, target_words)
        self.sections.append(section)
        return section

    @property
    def total_target_words(self) -> int:
        return sum(s.target_words for s in self.sections)

    @property
    def section_count(self) -> int:
        return len(self.sections)

    def to_dict(self) -> dict:
        return {
            "chapter_number": self.chapter_number,
            "title": self.title,
            "description": self.description,
            "sections": [s.to_dict() for s in self.sections],
            "introduction": self.introduction,
            "conclusion": self.conclusion,
        }

    @classmethod
    def from_chapter_plan(
        cls,
        chapter_number: int,
        title: str,
        sections_data: list[dict],
        description: str = "",
    ) -> "ChapterOutline":
        """Create outline from chapter_plan.md style data.

        Args:
            chapter_number: Chapter number (e.g., 3 for Chapter III)
            title: Chapter title
            sections_data: List of dicts with 'title' and 'description' keys
            description: Optional chapter description

        Returns:
            ChapterOutline instance
        """
        outline = cls(chapter_number, title, description)
        for sec in sections_data:
            outline.add_section(sec["title"], sec["description"])
        return outline

    @classmethod
    def from_text(cls, text: str) -> "ChapterOutline":
        """Parse a chapter outline from text (e.g., chapter_plan.md format).

        Expects format like:
        ### Chapter III — Partition and Violence in Train to Pakistan (14–16 Pages)

        #### 3.1 Historical Violence in the Novel
        - Representation of Partition riots and brutality
        """
        lines = text.strip().split("\n")
        if not lines:
            return cls(0, "Untitled")

        # Parse chapter title
        first_line = lines[0].strip()
        chapter_num = 0
        title = "Untitled"

        if "Chapter" in first_line:
            parts = first_line.split("—")
            if len(parts) >= 2:
                title = parts[1].strip().split("(")[0].strip()
            # Extract chapter number
            for word in first_line.split():
                if word.isdigit():
                    chapter_num = int(word)
                    break

        outline = cls(chapter_num, title)

        # Parse sections
        current_section = None
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("####"):
                sec_title = stripped.replace("####", "").strip()
                current_section = outline.add_section(sec_title, "")
            elif stripped.startswith("-") and current_section:
                point = stripped.lstrip("- ").strip()
                current_section.key_points.append(point)

        return outline
