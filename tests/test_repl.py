"""Tests for the REPL CLI module."""

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from research_rag.cli.repl import _parse_command, repl


class TestReplImport:
    """Verify the repl module can be imported as documented."""

    def test_import_repl_function(self):
        """Import the repl function from the documented path."""
        from research_rag.cli.repl import repl as repl_func

        assert callable(repl_func)


class TestParseCommand:
    """Test command-line parsing for the REPL."""

    def test_ask_with_quoted_question_and_flag(self):
        """Parse: ask \"question\" -k 5"""
        command, args, kwargs = _parse_command('ask "What is partition violence?" -k 5')
        assert command == "ask"
        assert args == ["What is partition violence?"]
        assert kwargs == {"k": "5"}

    def test_help_command(self):
        """Parse: help"""
        command, args, kwargs = _parse_command("help")
        assert command == "help"
        assert args == []
        assert kwargs == {}

    def test_exit_command(self):
        """Parse: exit"""
        command, args, kwargs = _parse_command("exit")
        assert command == "exit"
        assert args == []
        assert kwargs == {}

    def test_status_command(self):
        """Parse: status"""
        command, args, kwargs = _parse_command("status")
        assert command == "status"
        assert args == []
        assert kwargs == {}

    def test_empty_line(self):
        """Parse empty input."""
        command, args, kwargs = _parse_command("")
        assert command == ""
        assert args == []
        assert kwargs == {}

    def test_multiple_args(self):
        """Parse command with multiple positional args."""
        command, args, kwargs = _parse_command('ingest ./pdfs/ --verbose')
        assert command == "ingest"
        assert args == ["./pdfs/"]
        assert kwargs == {"verbose": True}

    def test_boolean_flag(self):
        """Parse a flag with no value as True."""
        command, args, kwargs = _parse_command("ask \"hello\" --reasoning")
        assert command == "ask"
        assert kwargs["reasoning"] is True

    def test_multiple_flags(self):
        """Parse multiple flags mixed with positional args."""
        command, args, kwargs = _parse_command('query "machine learning" -k 5 --verbose')
        assert command == "query"
        assert args == ["machine learning"]
        assert kwargs == {"k": "5", "verbose": True}

    def test_case_insensitive_command(self):
        """Commands are lower-cased."""
        command, _, _ = _parse_command("EXIT")
        assert command == "exit"


class TestReplLifecycle:
    """Test REPL startup and shutdown behaviour."""

    def test_repl_exit_breaks_loop(self):
        """Typing 'exit' prints goodbye and breaks the loop."""
        mock_settings = MagicMock()
        mock_settings.openrouter_api_key = None
        mock_settings.storage.chroma_path = "./data/chroma"
        mock_settings.retrieval.top_k = 5

        with patch("research_rag.cli.repl._setup_readline"):
            with patch("research_rag.cli.repl.EmbeddingService"):
                with patch("research_rag.cli.repl.ChromaStore"):
                    with patch("research_rag.cli.repl.Retriever"):
                        with patch("research_rag.cli.repl.AnswerGenerator"):
                            with patch("research_rag.cli.repl._print_welcome"):
                                with patch("builtins.input", side_effect=["exit"]):
                                    with patch("research_rag.cli.repl.console.print") as mock_print:
                                        repl(mock_settings)

        # Verify "Goodbye!" was printed
        goodbye_calls = [call for call in mock_print.call_args_list if "Goodbye" in str(call)]
        assert len(goodbye_calls) >= 1

    def test_repl_quit_breaks_loop(self):
        """Typing 'quit' also exits gracefully."""
        mock_settings = MagicMock()
        mock_settings.openrouter_api_key = None
        mock_settings.storage.chroma_path = "./data/chroma"
        mock_settings.retrieval.top_k = 5

        with patch("research_rag.cli.repl._setup_readline"):
            with patch("research_rag.cli.repl.EmbeddingService"):
                with patch("research_rag.cli.repl.ChromaStore"):
                    with patch("research_rag.cli.repl.Retriever"):
                        with patch("research_rag.cli.repl.AnswerGenerator"):
                            with patch("research_rag.cli.repl._print_welcome"):
                                with patch("builtins.input", side_effect=["quit"]):
                                    with patch("research_rag.cli.repl.console.print") as mock_print:
                                        repl(mock_settings)

        goodbye_calls = [call for call in mock_print.call_args_list if "Goodbye" in str(call)]
        assert len(goodbye_calls) >= 1

    def test_repl_eof_breaks_loop(self):
        """EOFError (Ctrl+D) breaks the loop gracefully."""
        mock_settings = MagicMock()
        mock_settings.openrouter_api_key = None
        mock_settings.storage.chroma_path = "./data/chroma"
        mock_settings.retrieval.top_k = 5

        with patch("research_rag.cli.repl._setup_readline"):
            with patch("research_rag.cli.repl.EmbeddingService"):
                with patch("research_rag.cli.repl.ChromaStore"):
                    with patch("research_rag.cli.repl.Retriever"):
                        with patch("research_rag.cli.repl.AnswerGenerator"):
                            with patch("research_rag.cli.repl._print_welcome"):
                                with patch("builtins.input", side_effect=EOFError):
                                    with patch("research_rag.cli.repl.console.print") as mock_print:
                                        repl(mock_settings)

        goodbye_calls = [call for call in mock_print.call_args_list if "Goodbye" in str(call)]
        assert len(goodbye_calls) >= 1

    def test_repl_keyboard_interrupt_breaks_loop(self):
        """KeyboardInterrupt (Ctrl+C) breaks the loop gracefully."""
        mock_settings = MagicMock()
        mock_settings.openrouter_api_key = None
        mock_settings.storage.chroma_path = "./data/chroma"
        mock_settings.retrieval.top_k = 5

        with patch("research_rag.cli.repl._setup_readline"):
            with patch("research_rag.cli.repl.EmbeddingService"):
                with patch("research_rag.cli.repl.ChromaStore"):
                    with patch("research_rag.cli.repl.Retriever"):
                        with patch("research_rag.cli.repl.AnswerGenerator"):
                            with patch("research_rag.cli.repl._print_welcome"):
                                with patch("builtins.input", side_effect=KeyboardInterrupt):
                                    with patch("research_rag.cli.repl.console.print") as mock_print:
                                        repl(mock_settings)

        goodbye_calls = [call for call in mock_print.call_args_list if "Goodbye" in str(call)]
        assert len(goodbye_calls) >= 1


class TestReplSubprocess:
    """Lightweight integration tests using subprocess."""

    def test_repl_subprocess_exit(self):
        """Run REPL via subprocess with piped 'exit' input."""
        proc = subprocess.run(
            [sys.executable, "-c", "from research_rag.cli.repl import repl; from research_rag.config import Settings; repl(Settings())"],
            input="exit\n",
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should exit cleanly (code 0) and print goodbye
        assert proc.returncode == 0
        assert "Goodbye" in proc.stdout or "Goodbye" in proc.stderr

    def test_repl_subprocess_help_then_exit(self):
        """Run REPL with help then exit."""
        proc = subprocess.run(
            [sys.executable, "-c", "from research_rag.cli.repl import repl; from research_rag.config import Settings; repl(Settings())"],
            input="help\nexit\n",
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0
        combined = proc.stdout + proc.stderr
        assert "Available Commands" in combined or "ask" in combined
