"""Retry decorator with exponential backoff and jitter."""

import functools
import random
import time
from typing import Any, Callable, Optional, ParamSpec, TypeVar

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

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    if attempt >= max_retries:
                        raise
                    delay = base_delay * (2 ** attempt)
                    jitter = delay * 0.25
                    delay = delay + random.uniform(-jitter, jitter)
                    delay = max(0.0, delay)
                    if on_retry is not None:
                        on_retry(exc, attempt, delay)
                    time.sleep(delay)
            # Defensive fallback — should never be reached.
            if last_exception is not None:
                raise last_exception
            raise RuntimeError("Retry loop exited without result or exception")

        return wrapper

    return decorator
