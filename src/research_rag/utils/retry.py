"""Retry decorator with exponential backoff and jitter (powered by tenacity)."""

from typing import Any, Callable, Optional, ParamSpec, TypeVar

from tenacity import (
    retry as tenacity_retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from research_rag.utils.errors import APIError, RateLimitError, ServerError

P = ParamSpec("P")
T = TypeVar("T")

DEFAULT_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    APIError,
    RateLimitError,
    ServerError,
    ConnectionError,
    TimeoutError,
)


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple[type[Exception], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that retries a function with exponential backoff and jitter.

    Args:
        max_retries: Maximum number of retry attempts (default 3).
        base_delay: Initial delay between retries in seconds (default 1.0).
        retryable_exceptions: Tuple of exception types that trigger a retry.
        on_retry: Optional callback invoked before each retry. Receives the
            exception, the current attempt number (0-based), and the sleep delay.

    Returns:
        A decorator that wraps the target function with retry logic.
    """
    max_attempts = max_retries + 1

    # Exponential backoff: base_delay * 2^n, same as original formula
    wait = wait_exponential(
        multiplier=base_delay,
        min=base_delay,
        max=base_delay * (2**max_retries),
    ) + wait_random(0, base_delay * 0.25)

    # Map on_retry callback to tenacity's before_sleep
    before_sleep_fn = None
    if on_retry is not None:

        def _before_sleep(retry_state):
            exc = retry_state.outcome.exception()
            attempt = retry_state.attempt_number - 1  # tenacity is 1-based
            delay = retry_state.idle_for
            on_retry(exc, attempt, delay)

        before_sleep_fn = _before_sleep

    return tenacity_retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait,
        retry=retry_if_exception_type(retryable_exceptions),
        before_sleep=before_sleep_fn,
        reraise=True,
    )
