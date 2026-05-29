"""Tests for chapter writing assistance."""

from research_rag.writing.chapter_writer import ChapterWriter
from research_rag.writing.mla_formatter import MLAFormatter, MLACitation
from research_rag.writing.outline import ChapterOutline, ChapterSection
from research_rag.writing.state import DissertationState
from research_rag.writing.prompts import build_section_prompt, build_works_cited_prompt


class TestChapterOutline:
    """Test chapter outline generation."""

    def test_create_outline(self):
        outline = ChapterOutline(3, "Partition and Violence")
        assert outline.chapter_number == 3
        assert outline.title == "Partition and Violence"

    def test_add_section(self):
        outline = ChapterOutline(1, "Introduction")
        sec = outline.add_section("1.1 Background", "Historical context")
        assert sec.title == "1.1 Background"
        assert outline.section_count == 1

    def test_total_target_words(self):
        outline = ChapterOutline(1, "Intro")
        outline.add_section("1.1", "desc", target_words=1000)
        outline.add_section("1.2", "desc", target_words=1500)
        assert outline.total_target_words == 2500

    def test_to_dict(self):
        outline = ChapterOutline(2, "Literature Review")
        outline.add_section("2.1 Overview", "Key studies")
        d = outline.to_dict()
        assert d["chapter_number"] == 2
        assert len(d["sections"]) == 1

    def test_from_chapter_plan(self):
        sections = [
            {"title": "3.1 Violence", "description": "Analyze violence"},
            {"title": "3.2 Community", "description": "Communal breakdown"},
        ]
        outline = ChapterOutline.from_chapter_plan(3, "Partition", sections)
        assert outline.chapter_number == 3
        assert outline.section_count == 2


class TestMLAFormatter:
    """Test MLA citation formatting."""

    def setup_method(self):
        self.formatter = MLAFormatter()

    def test_add_citation(self):
        cit = self.formatter.add_citation(1, author="Singh", title="Train to Pakistan", year=1956)
        assert cit.author == "Singh"

    def test_inline_citation(self):
        self.formatter.add_citation(1, author="Khushwant Singh", page="45")
        inline = self.formatter.get_inline_citation(1)
        assert "Singh" in inline
        assert "45" in inline

    def test_format_answer(self):
        self.formatter.add_citation(1, author="Singh", page="10")
        result = self.formatter.format_answer("As shown in [1], violence erupts.")
        assert "[1]" not in result
        assert "Singh" in result

    def test_works_cited(self):
        self.formatter.add_citation(1, author="Khushwant Singh", title="Train to Pakistan", year=1956)
        self.formatter.add_citation(2, author="Urvashi Butalia", title="The Other Side of Silence", year=2001)
        wc = self.formatter.build_works_cited()
        assert "Butalia" in wc
        assert "Singh" in wc

    def test_format_author(self):
        cit = MLACitation(author="Khushwant Singh")
        assert cit.format_author() == "Singh, Khushwant"

    def test_format_works_cited_entry(self):
        cit = MLACitation(
            author="Khushwant Singh",
            title="Train to Pakistan",
            year=1956,
            journal="Novel Review",
            page="10-20",
        )
        entry = cit.format_works_cited()
        assert "Singh" in entry
        assert "1956" in entry

    def test_reset(self):
        self.formatter.add_citation(1, author="Test")
        self.formatter.reset()
        assert self.formatter.get_inline_citation(1) == "[1]"


class TestDissertationState:
    """Test cross-chapter state management."""

    def setup_method(self):
        self.state = DissertationState(title="My Dissertation", thesis="Partition violence")

    def test_start_chapter(self):
        self.state.start_chapter(1, "Introduction")
        assert self.state.current_chapter == 1

    def test_add_section(self):
        self.state.start_chapter(1, "Intro")
        self.state.add_section(1, "1.1 Background", "Some text about...", [{"author": "Singh"}])
        assert len(self.state.chapters[1]["sections"]) == 1

    def test_finish_chapter(self):
        self.state.start_chapter(1, "Intro")
        self.state.add_section(1, "1.1", "text", [])
        self.state.finish_chapter(1, "Intro covers background")
        assert self.state.current_chapter is None
        assert self.state.chapters[1]["summary"] == "Intro covers background"

    def test_get_previous_summaries(self):
        self.state.start_chapter(1, "Intro")
        self.state.finish_chapter(1, "Intro summary")
        self.state.start_chapter(2, "Lit Review")
        prev = self.state.get_previous_summaries(2)
        assert "Intro summary" in prev

    def test_word_count(self):
        self.state.start_chapter(1, "Intro")
        self.state.add_section(1, "1.1", "word " * 100, [])
        assert self.state.get_word_count(1) == 100

    def test_to_dict(self):
        self.state.start_chapter(1, "Intro")
        d = self.state.to_dict()
        assert d["title"] == "My Dissertation"
        assert 1 in d["chapters"]


class TestPrompts:
    """Test prompt building functions."""

    def test_build_section_prompt(self):
        chunks = [{"text": "Evidence text", "title": "Paper", "page": 10, "author": "Singh", "year": 2020}]
        msgs = build_section_prompt("3.1 Violence", "Analyze violence", chunks)
        assert len(msgs) == 2
        assert "3.1 Violence" in msgs[1]["content"]

    def test_build_works_cited_prompt(self):
        citations = [{"author": "Singh", "title": "Novel", "year": 1956}]
        msgs = build_works_cited_prompt(citations)
        assert len(msgs) == 2
        assert "Singh" in msgs[1]["content"]
