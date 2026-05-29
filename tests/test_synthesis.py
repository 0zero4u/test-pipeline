"""Tests for answer synthesis."""

from unittest.mock import MagicMock, patch

import pytest

from research_rag.citations.parser import Citation
from research_rag.retrieval import Retriever, SearchResult
from research_rag.synthesis import AnswerGenerator
from research_rag.synthesis.generator import build_synthesis_messages
from research_rag.synthesis.prompts import SYNTHESIS_SYSTEM_PROMPT


class TestSynthesisPrompts:
    """Test prompt building."""

    def test_build_messages_structure(self):
        messages = build_synthesis_messages(
            "What is the main argument?",
            [("Text here.", "Paper Title", 5, "doc1")],
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert SYNTHESIS_SYSTEM_PROMPT in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "What is the main argument?" in messages[1]["content"]

    def test_build_messages_includes_evidence(self):
        messages = build_synthesis_messages(
            "test",
            [("Evidence text.", "Paper", 1, "doc1")],
        )
        user = messages[1]["content"]
        assert "[1]" in user
        assert "Evidence text." in user
        assert "Paper, Page 1" in user

    def test_build_messages_multiple_evidence(self):
        messages = build_synthesis_messages(
            "test",
            [
                ("First text.", "Paper A", 1, "doc1"),
                ("Second text.", "Paper B", 3, "doc2"),
            ],
        )
        user = messages[1]["content"]
        assert "[1]" in user
        assert "[2]" in user
        assert "Paper A" in user
        assert "Paper B" in user

    def test_build_messages_no_page(self):
        messages = build_synthesis_messages(
            "test",
            [("Text.", "Paper", 0, "doc1")],
        )
        user = messages[1]["content"]
        assert "Page" not in user.split("[1]")[1] if "[1]" in user else True


class MockRetriever:
    """Mock retriever that returns predictable results."""

    def __init__(self, results=None):
        self.results = results or []
        self.embedding_service = type("obj", (), {"api_key": None})()

    def search(self, query, top_k=5, where=None):
        return self.results


class TestAnswerGenerator:
    """Test answer generation pipeline."""

    def make_result(self, chunk_id, doc_id, title, page, text, score=0.9):
        return SearchResult(
            chunk_id=chunk_id,
            document_id=doc_id,
            title=title,
            section_title="Section",
            page_start=page,
            page_end=page + 1,
            text=text,
            score=score,
        )

    def test_empty_results_returns_early(self):
        gen = AnswerGenerator(retriever=MockRetriever([]))
        response = gen.answer("test query")
        assert "No relevant evidence" in response["answer"]
        assert response["confidence"] == 0.0
        assert len(response["citations"]) == 0

    def test_generation_failure_returns_error(self):
        result = self.make_result("c1", "d1", "Paper", 1, "Some text.")
        mock_retriever = MockRetriever([result])
        gen = AnswerGenerator(retriever=mock_retriever)

        # Mock synthesis client to fail
        gen.synthesis_client = type("obj", (), {
            "generate": MagicMock(side_effect=Exception("API down"))
        })()

        response = gen.answer("test")
        assert "Failed to generate" in response["answer"]
        assert response["confidence"] == 0.0

    def test_no_openrouter_key_fallback(self):
        result = self.make_result("c1", "d1", "Paper", 1, "Evidence text.")
        mock_retriever = MockRetriever([result])
        gen = AnswerGenerator(retriever=mock_retriever)

        # Mock synthesis client
        gen.synthesis_client = type("obj", (), {
            "generate": MagicMock(return_value="Answer based on [1].")
        })()

        response = gen.answer("test")
        assert response["answer"] == "Answer based on [1]."
        assert len(response["citations"]) >= 1

    def test_confidence_no_citations(self):
        gen = AnswerGenerator(retriever=MockRetriever([]))
        results = [self.make_result("c1", "d1", "Paper", 1, "Text")]
        confidence = gen._estimate_confidence([], results)
        assert confidence == 0.3

    def test_confidence_with_citations(self):
        gen = AnswerGenerator(retriever=MockRetriever([]))
        results = [self.make_result("c1", "d1", "Paper", 1, "Text", score=0.8)]
        citations = [Citation("c1", "d1", "Paper", 1, 0.8, 1)]
        confidence = gen._estimate_confidence(citations, results)
        assert 0.0 < confidence <= 1.0

    def test_confidence_no_results(self):
        gen = AnswerGenerator(retriever=MockRetriever([]))
        confidence = gen._estimate_confidence([], [])
        assert confidence == 0.0

    def test_reasoning_trace(self):
        result = self.make_result("c1", "d1", "Paper", 1, "Text", score=0.85)
        mock_retriever = MockRetriever([result])
        gen = AnswerGenerator(retriever=mock_retriever)
        gen.synthesis_client = type("obj", (), {
            "generate": MagicMock(return_value="Answer.")
        })()

        response = gen.answer("test", include_reasoning=True)
        assert "reasoning_trace" in response
        assert response["reasoning_trace"]["evidence_count"] > 0
        assert "evidence_scores" in response["reasoning_trace"]
