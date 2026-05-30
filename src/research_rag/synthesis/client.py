"""OpenRouter client for synthesis LLM calls."""

import logging
import os
from typing import Optional

from openai import OpenAI

from research_rag.utils import APIError, RateLimitError, ServerError, retry

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"

# Reasoning effort levels (for models that support it)
REASONING_LEVELS = ["low", "medium", "high", "xlow", "xhigh"]


class SynthesisClient:
    """Client for calling LLMs via OpenRouter for answer synthesis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        reasoning_effort: Optional[str] = None,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self._client: Optional[OpenAI] = None

        if not self.api_key:
            logger.warning("No OPENROUTER_API_KEY set. Synthesis calls will fail.")
        
        if self.reasoning_effort:
            logger.info("Reasoning effort set to: %s", self.reasoning_effort)

    def _get_client(self) -> OpenAI:
        """Lazily initialize the OpenAI client."""
        if self._client is None:
            self._client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=self.api_key or "",
            )
        return self._client

    @retry(retryable_exceptions=(APIError, RateLimitError, ServerError, ConnectionError, TimeoutError))
    def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            max_tokens: Override max tokens for this call.
            temperature: Override temperature for this call.
            reasoning_effort: Override reasoning effort (low/medium/high/xhigh).

        Returns:
            Generated text content.
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature if temperature is not None else self.temperature,
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/0zero4u/test-pipeline",
                    "X-Title": "Research RAG",
                },
            }
            
            effort = reasoning_effort or self.reasoning_effort
            if effort and effort in REASONING_LEVELS:
                kwargs["reasoning_effort"] = effort
                logger.debug("Using reasoning effort: %s", effort)
            
            response = self._get_client().chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            logger.debug(
                "Generation: %d input → %d output tokens (model=%s)",
                response.usage.prompt_tokens if response.usage else 0,
                response.usage.completion_tokens if response.usage else 0,
                self.model,
            )
            return content
        except Exception as exc:
            logger.error("OpenRouter synthesis call failed: %s", exc)
            raise

    def __repr__(self) -> str:
        return f"SynthesisClient(model={self.model}, max_tokens={self.max_tokens})"
