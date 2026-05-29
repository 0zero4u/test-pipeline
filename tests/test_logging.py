"""Tests for logging module."""

import json
import logging
from pathlib import Path

from research_rag.logging import JSONFormatter, get_logger, setup_logging


def test_setup_logging():
    """Test logging setup."""
    logger = setup_logging(level="DEBUG")

    assert logger.name == "research_rag"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1  # Console handler


def test_get_logger():
    """Test child logger creation."""
    setup_logging(level="INFO")
    logger = get_logger("ingestion")

    assert logger.name == "research_rag.ingestion"


def test_json_formatter():
    """Test JSON log formatter."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test message"
    assert "timestamp" in parsed


def test_logging_to_file(tmp_path):
    """Test logging to file."""
    log_file = tmp_path / "test.log"
    logger = setup_logging(level="INFO", log_file=log_file)

    logger.info("Test log message")

    assert log_file.exists()
    content = log_file.read_text()
    assert "Test log message" in content
