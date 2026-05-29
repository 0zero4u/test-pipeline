"""Tests for configuration module."""

import os
from pathlib import Path

import pytest

from research_rag.config import Settings, load_settings


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings()

    assert settings.log_level == "INFO"
    assert settings.debug is False
    assert settings.ingestion.chunk_size_min == 500
    assert settings.ingestion.chunk_size_max == 900
    assert settings.retrieval.top_k == 5
    assert settings.synthesis.model == "deepseek/deepseek-v4-flash"


def test_settings_from_env(monkeypatch):
    """Test settings from environment variables."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-embedding-key")

    settings = Settings()

    assert settings.openrouter_api_key == "test-key-123"
    assert settings.embedding_api_key == "test-embedding-key"


def test_load_settings_with_config(tmp_path):
    """Test loading settings from config file."""
    config_content = """
log_level: DEBUG
debug: true
ingestion:
  chunk_size_min: 300
  chunk_size_max: 600
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    settings = load_settings(config_file)

    assert settings.log_level == "DEBUG"
    assert settings.debug is True
    assert settings.ingestion.chunk_size_min == 300
    assert settings.ingestion.chunk_size_max == 600


def test_settings_validation():
    """Test settings validation."""
    # Invalid chunk overlap (should be between 0 and 1)
    with pytest.raises(Exception):
        Settings(ingestion={"chunk_overlap": 1.5})

    # Invalid top_k (should be >= 1)
    with pytest.raises(Exception):
        Settings(retrieval={"top_k": 0})
