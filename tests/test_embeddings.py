"""Tests for the embedding service."""

import os

import numpy as np
import pytest

from research_rag.embeddings.api import EmbeddingService


class TestEmbeddingService:
    """Test EmbeddingService initialization and fallback behavior."""

    def test_init_defaults_to_local_when_no_api_key(self):
        service = EmbeddingService(api_key=None)
        assert service._using_local is True
        assert "bge-small" in service.model

    def test_init_uses_api_when_key_provided(self):
        service = EmbeddingService(api_key="sk-test-key")
        assert service._using_local is False
        assert service.model == "thenlper/gte-large"

    def test_init_uses_env_var_key(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-env-key")
        service = EmbeddingService()
        assert service._using_local is False

    def test_init_prefers_explicit_key_over_env(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-env-key")
        service = EmbeddingService(api_key="sk-explicit")
        assert service.api_key == "sk-explicit"

    def test_dimension_local(self):
        service = EmbeddingService(api_key=None)
        dim = service.dimension
        assert dim == 384  # BGE-small-en-v1.5

    def test_dimension_api(self):
        service = EmbeddingService(api_key="sk-test")
        assert service.dimension == 1024  # GTE-Large

    def test_embed_empty(self):
        service = EmbeddingService(api_key=None)
        result = service.embed([])
        assert isinstance(result, np.ndarray)
        assert result.shape == (0, 384)

    def test_embed_local_returns_float32(self):
        service = EmbeddingService(api_key=None)
        texts = ["hello world", "test sentence"]
        result = service.embed(texts)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert result.shape == (2, 384)
        assert not np.all(result[0] == result[1])  # different texts = different embeddings

    def test_embed_local_single_text(self):
        service = EmbeddingService(api_key=None)
        result = service.embed(["single text"])
        assert result.shape == (1, 384)

    def test_embed_query_local_adds_prefix(self, monkeypatch):
        """BGE models add query instruction prefix."""
        service = EmbeddingService(api_key=None)
        # Verify prefix is added by checking it's not the same as plain embed
        plain = service.embed(["test query"])[0]
        query_vec = service.embed_query("test query")
        assert not np.array_equal(plain, query_vec)

    def test_batch_embedding(self):
        service = EmbeddingService(api_key=None, batch_size=2)
        texts = ["a", "b", "c", "d", "e"]
        result = service.embed(texts)
        assert result.shape == (5, 384)

    def test_repr_local(self):
        service = EmbeddingService(api_key=None)
        rep = repr(service)
        assert "bge-small" in rep
        assert "384" in rep
        assert "local=True" in rep

    def test_repr_api(self):
        service = EmbeddingService(api_key="sk-test")
        rep = repr(service)
        assert "gte-large" in rep
        assert "1024" in rep
        assert "local=False" in rep
