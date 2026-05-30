"""Tests for MLA 9th Edition formatter."""

from research_rag.writing.mla_formatter import MLAFormatter, MLACitation


class TestMLACitation:
    """Test MLACitation formatting for different source types."""

    def test_format_author_two_names(self):
        cit = MLACitation(author="Priyanka Gupta")
        assert cit.format_author() == "Gupta, Priyanka"

    def test_format_author_single_name(self):
        cit = MLACitation(author="Chaucer")
        assert cit.format_author() == "Chaucer"

    def test_format_author_empty(self):
        cit = MLACitation(author="")
        assert cit.format_author() == "Unknown Author"

    def test_format_inline_with_page(self):
        cit = MLACitation(author="Khushwant Singh", page="45")
        assert cit.format_inline() == "(Singh 45)"

    def test_format_inline_without_page(self):
        cit = MLACitation(author="Khushwant Singh")
        assert cit.format_inline() == "(Singh)"

    def test_format_journal_article(self):
        cit = MLACitation(
            author="Priyanka Gupta",
            title="Women and Violence in Partition Narratives",
            year=2018,
            journal="Research Scholar",
            volume="7",
            issue="2",
            page="45-60",
            source_type="journal",
        )
        result = cit.format_works_cited()
        assert "Gupta, Priyanka." in result
        assert '"Women and Violence in Partition Narratives."' in result
        assert "*Research Scholar*" in result
        assert "vol. 7" in result
        assert "no. 2" in result
        assert ", 2018" in result
        assert "pp. 45-60" in result

    def test_format_book(self):
        cit = MLACitation(
            author="Khushwant Singh",
            title="Train to Pakistan",
            year=1956,
            publisher="Chatto & Windus",
            source_type="book",
        )
        result = cit.format_works_cited()
        assert "Singh, Khushwant." in result
        assert "*Train to Pakistan*." in result
        assert "Chatto & Windus," in result
        assert "1956." in result

    def test_format_book_with_edition(self):
        cit = MLACitation(
            author="Henry Louis Gates",
            title="The Norton Anthology of African American Literature",
            year=2014,
            publisher="W. W. Norton",
            edition="3rd ed.",
            source_type="book",
        )
        result = cit.format_works_cited()
        assert "3rd ed.," in result
        assert "W. W. Norton," in result

    def test_format_film(self):
        cit = MLACitation(
            title="Train to Pakistan",
            director="Pramod Chakravorty",
            production_co="Shemaroo Entertainment",
            year=1998,
            source_type="film",
        )
        result = cit.format_works_cited()
        assert "*Train to Pakistan*." in result
        assert "Directed by Pramod Chakravorty," in result
        assert "Shemaroo Entertainment," in result
        assert "1998." in result

    def test_format_edited_volume_chapter(self):
        cit = MLACitation(
            title="Partition and the Genre of the Novel",
            journal="The Partition of India: Literary Responses",
            editor="Alok Bhalla",
            publisher="Macmillan",
            year=2002,
            page="112-130",
            source_type="edited_volume",
        )
        result = cit.format_works_cited()
        assert '"Partition and the Genre of the Novel."' in result
        assert "*The Partition of India: Literary Responses*," in result
        assert "edited by Alok Bhalla," in result
        assert "Macmillan," in result
        assert "pp. 112-130" in result

    def test_format_chapter_in_book(self):
        cit = MLACitation(
            author="Gyanendra Pandey",
            title="Remembering Partition",
            journal="Remembering Partition: Violence, Nationalism and History in India",
            publisher="Cambridge University Press",
            year=2001,
            page="1-50",
            source_type="chapter",
        )
        result = cit.format_works_cited()
        assert "Pandey, Gyanendra." in result
        assert '"Remembering Partition."' in result
        assert "Cambridge University Press," in result
        assert "pp. 1-50" in result

    def test_format_no_year(self):
        cit = MLACitation(
            author="Unknown Author",
            title="Some Paper",
            source_type="journal",
        )
        result = cit.format_works_cited()
        assert ", n.d." in result

    def test_format_no_title(self):
        cit = MLACitation(
            author="Test Author",
            source_type="book",
        )
        result = cit.format_works_cited()
        assert "*Untitled*." in result


class TestMLAFormatter:
    """Test MLAFormatter integration."""

    def setup_method(self):
        self.formatter = MLAFormatter()

    def test_add_citation(self):
        cit = self.formatter.add_citation(
            citation_number=1,
            author="Priyanka Gupta",
            title="Test Article",
            year=2020,
            source_type="journal",
        )
        assert isinstance(cit, MLACitation)
        assert cit.author == "Priyanka Gupta"

    def test_get_inline_citation(self):
        self.formatter.add_citation(
            citation_number=1,
            author="Khushwant Singh",
            page="45",
        )
        assert self.formatter.get_inline_citation(1) == "(Singh 45)"

    def test_get_inline_citation_unknown(self):
        assert self.formatter.get_inline_citation(99) == "[99]"

    def test_format_answer(self):
        self.formatter.add_citation(
            citation_number=1,
            author="Khushwant Singh",
            page="45",
        )
        answer = "According to [1], the novel portrays violence."
        result = self.formatter.format_answer(answer)
        assert "(Singh 45)" in result
        assert "[1]" not in result

    def test_format_answer_multiple(self):
        self.formatter.add_citation(1, author="Khushwant Singh", page="45")
        self.formatter.add_citation(2, author="Priyanka Gupta", page="30")
        answer = "Sources [1] and [2] agree."
        result = self.formatter.format_answer(answer)
        assert "(Singh 45)" in result
        assert "(Gupta 30)" in result

    def test_build_works_cited_empty(self):
        assert self.formatter.build_works_cited() == ""

    def test_build_works_cited_with_header(self):
        self.formatter.add_citation(
            citation_number=1,
            author="Priyanka Gupta",
            title="Test Article",
            year=2020,
            source_type="journal",
        )
        result = self.formatter.build_works_cited()
        assert result.startswith("Works Cited\n")

    def test_build_works_cited_alphabetical(self):
        self.formatter.add_citation(1, author="Zoe Smith", title="Z Article", source_type="journal")
        self.formatter.add_citation(2, author="Alice Brown", title="A Article", source_type="journal")
        result = self.formatter.build_works_cited()
        lines = result.split("\n\n")
        # Alice should come before Zoe (after header)
        alice_pos = result.find("Brown, Alice")
        zoe_pos = result.find("Smith, Zoe")
        assert alice_pos < zoe_pos

    def test_get_citation_details(self):
        self.formatter.add_citation(
            citation_number=1,
            author="Test",
            title="Title",
            year=2020,
            source_type="book",
            publisher="Publisher",
        )
        details = self.formatter.get_citation_details(1)
        assert details["source_type"] == "book"
        assert details["publisher"] == "Publisher"

    def test_get_citation_details_unknown(self):
        assert self.formatter.get_citation_details(99) is None

    def test_reset(self):
        self.formatter.add_citation(1, author="Test")
        self.formatter.reset()
        assert self.formatter.build_works_cited() == ""

    def test_mixed_source_types(self):
        self.formatter.add_citation(1, author="Author One", title="Journal Article", source_type="journal", journal="Journal X")
        self.formatter.add_citation(2, author="Author Two", title="Book Title", source_type="book", publisher="Publisher")
        self.formatter.add_citation(3, title="Film Title", director="Director Name", source_type="film", year=2000)
        result = self.formatter.build_works_cited()
        assert "*Journal X*" in result
        assert "*Book Title*" in result
        assert "*Film Title*" in result
        assert "Directed by Director Name" in result
