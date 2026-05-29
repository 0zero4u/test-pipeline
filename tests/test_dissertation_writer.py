"""Tests for DissertationWriter and chapter plan parsing."""

from research_rag.writing.dissertation_writer import DissertationWriter
from research_rag.writing.outline import ChapterOutline


SAMPLE_CHAPTER_PLAN = """### Chapter I — Introduction (8–10 Pages)

#### 1.1 Historical Background: The Partition of India
- Political and socio-historical context of the 1947 Partition
- Causes and consequences of communal division

#### 1.2 About Khushwant Singh
- Life and literary background
- Contribution to Partition literature

#### 1.3 Thesis Statement
- Central argument of the dissertation

---

### Chapter II — Review of Literature (8–10 Pages)

#### 2.1 Overview of Partition Literature
- Development and major themes of Partition writing

#### 2.2 Critical Studies on Train to Pakistan
- Scholarly interpretations of the novel

---

### Chapter III — Partition and Violence (14–16 Pages)

#### 3.1 Historical Violence in the Novel
- Representation of Partition riots and brutality

#### 3.2 Communal Breakdown in Mano Majra
- Collapse of communal harmony

#### 3.3 Comparative Analysis
- Similarities and differences in representation
"""

SAMPLE_CHAPTER_PLAN_ROMAN = """### Chapter IV — Humanism and Moral Conflict (14–16 Pages)

#### 4.1 Jugga as the Humanist Figure
- Jugga's transformation and sacrifice

#### 4.2 Compassion Amid Violence
- Human relationships during crisis
"""


class TestDissertationWriterParsing:
    """Test chapter plan parsing."""

    def test_parse_single_chapter(self):
        plan = """### Chapter I — Introduction (8–10 Pages)

#### 1.1 Background
- Point one
- Point two
"""
        writer = DissertationWriter.__new__(DissertationWriter)
        chapters = writer.parse_chapter_plan(plan)
        assert len(chapters) == 1
        assert chapters[0].chapter_number == 1
        assert "Introduction" in chapters[0].title

    def test_parse_multiple_chapters(self):
        writer = DissertationWriter.__new__(DissertationWriter)
        chapters = writer.parse_chapter_plan(SAMPLE_CHAPTER_PLAN)
        assert len(chapters) == 3
        assert chapters[0].chapter_number == 1
        assert chapters[1].chapter_number == 2
        assert chapters[2].chapter_number == 3

    def test_parse_chapter_titles(self):
        writer = DissertationWriter.__new__(DissertationWriter)
        chapters = writer.parse_chapter_plan(SAMPLE_CHAPTER_PLAN)
        assert "Introduction" in chapters[0].title
        assert "Review of Literature" in chapters[1].title
        assert "Partition and Violence" in chapters[2].title

    def test_parse_sections(self):
        writer = DissertationWriter.__new__(DissertationWriter)
        chapters = writer.parse_chapter_plan(SAMPLE_CHAPTER_PLAN)
        assert len(chapters[0].sections) == 3
        assert len(chapters[1].sections) == 2
        assert len(chapters[2].sections) == 3

    def test_parse_section_titles(self):
        writer = DissertationWriter.__new__(DissertationWriter)
        chapters = writer.parse_chapter_plan(SAMPLE_CHAPTER_PLAN)
        section_titles = [s.title for s in chapters[0].sections]
        assert "Background" in section_titles[0]
        assert "Khushwant Singh" in section_titles[1]
        assert "Thesis Statement" in section_titles[2]

    def test_parse_key_points(self):
        writer = DissertationWriter.__new__(DissertationWriter)
        chapters = writer.parse_chapter_plan(SAMPLE_CHAPTER_PLAN)
        first_section = chapters[0].sections[0]
        assert len(first_section.key_points) == 2
        assert "1947 Partition" in first_section.key_points[0]

    def test_parse_roman_numerals(self):
        writer = DissertationWriter.__new__(DissertationWriter)
        chapters = writer.parse_chapter_plan(SAMPLE_CHAPTER_PLAN_ROMAN)
        assert len(chapters) == 1
        assert chapters[0].chapter_number == 4

    def test_parse_empty_plan(self):
        writer = DissertationWriter.__new__(DissertationWriter)
        chapters = writer.parse_chapter_plan("")
        assert len(chapters) == 0

    def test_parse_no_sections(self):
        plan = """### Chapter I — Introduction

Some text without sections.
"""
        writer = DissertationWriter.__new__(DissertationWriter)
        chapters = writer.parse_chapter_plan(plan)
        assert len(chapters) == 1
        assert len(chapters[0].sections) == 0


class TestChapterOutlineFromPlan:
    """Test ChapterOutline.from_chapter_plan method."""

    def test_from_chapter_plan(self):
        sections_data = [
            {"title": "1.1 Background", "description": "Historical context"},
            {"title": "1.2 Analysis", "description": "Main analysis"},
        ]
        outline = ChapterOutline.from_chapter_plan(
            chapter_number=1,
            title="Introduction",
            sections_data=sections_data,
        )
        assert outline.chapter_number == 1
        assert outline.title == "Introduction"
        assert len(outline.sections) == 2

    def test_from_chapter_plan_with_description(self):
        sections_data = [{"title": "Section 1", "description": "Desc"}]
        outline = ChapterOutline.from_chapter_plan(
            chapter_number=2,
            title="Review",
            sections_data=sections_data,
            description="Chapter description",
        )
        assert outline.description == "Chapter description"
