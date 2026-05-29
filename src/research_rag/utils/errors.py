"""Custom exception hierarchy for Research RAG."""

from typing import Any


class ResearchRAGError(Exception):
    """Base exception for all Research RAG errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class ConfigError(ResearchRAGError):
    """Raised for configuration or setup issues."""


class APIError(ResearchRAGError):
    """Raised for API call failures."""


class AuthenticationError(APIError):
    """Raised for 401 authentication failures."""


class RateLimitError(APIError):
    """Raised for 429 rate limit failures."""


class ServerError(APIError):
    """Raised for 5xx server errors."""


class IngestionError(ResearchRAGError):
    """Raised for PDF ingestion failures."""


class RetrievalError(ResearchRAGError):
    """Raised for search/retrieval failures."""
