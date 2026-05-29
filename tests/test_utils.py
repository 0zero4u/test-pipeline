"""Tests for utils module: errors and retry decorator."""

import pytest

from research_rag.utils.errors import (
    APIError,
    AuthenticationError,
    ConfigError,
    IngestionError,
    RateLimitError,
    ResearchRAGError,
    RetrievalError,
    ServerError,
)
from research_rag.utils.retry import retry


class TestResearchRAGError:
    """Test the base exception and all subclasses."""

    @pytest.mark.parametrize(
        "exc_class",
        [
            ResearchRAGError,
            ConfigError,
            APIError,
            AuthenticationError,
            RateLimitError,
            ServerError,
            IngestionError,
            RetrievalError,
        ],
    )
    def test_exception_can_be_instantiated(self, exc_class):
        """Each exception class can be created with a message."""
        exc = exc_class("something went wrong")
        assert isinstance(exc, ResearchRAGError)
        assert exc.message == "something went wrong"

    def test_message_only_str(self):
        """__str__ returns just the message when no details are given."""
        exc = ResearchRAGError("simple error")
        assert str(exc) == "simple error"

    def test_message_with_details_str(self):
        """__str__ includes details dict when present."""
        exc = ResearchRAGError("request failed", details={"status": 500, "retry_after": 3})
        text = str(exc)
        assert "request failed" in text
        assert "status" in text
        assert "500" in text

    def test_details_defaults_to_empty_dict(self):
        """When details is omitted, it defaults to an empty dict."""
        exc = ResearchRAGError("no details")
        assert exc.details == {}

    def test_subclass_inheritance(self):
        """All subclasses are instances of ResearchRAGError and Exception."""
        exc = AuthenticationError("bad creds")
        assert isinstance(exc, APIError)
        assert isinstance(exc, ResearchRAGError)
        assert isinstance(exc, Exception)


class TestRetryDecorator:
    """Test the retry decorator behaviour."""

    def test_success_on_first_call(self):
        """A function that succeeds immediately returns correctly."""

        @retry(max_retries=3, base_delay=0.01)
        def always_ok():
            return 42

        assert always_ok() == 42

    def test_always_fails_raises_after_max_retries(self):
        """A function that always fails raises after exhausting retries."""
        call_count = 0

        @retry(max_retries=2, base_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise APIError("boom")

        with pytest.raises(APIError, match="boom"):
            always_fail()

        # initial + 2 retries = 3 total calls
        assert call_count == 3

    def test_fails_then_succeeds(self):
        """A function that fails N times then succeeds returns correctly."""
        call_count = 0

        @retry(max_retries=3, base_delay=0.01)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("throttled")
            return "ok"

        assert flaky() == "ok"
        assert call_count == 3

    def test_non_retryable_exception_not_caught(self):
        """Exceptions outside retryable_exceptions propagate immediately."""
        call_count = 0

        @retry(max_retries=3, base_delay=0.01)
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError, match="not retryable"):
            raises_value_error()

        assert call_count == 1

    def test_on_retry_callback_invoked(self):
        """The on_retry callback is called on each retry attempt."""
        retries_log = []

        def on_retry(exc, attempt, delay):
            retries_log.append((type(exc).__name__, attempt, delay))

        call_count = 0

        @retry(max_retries=2, base_delay=0.01, on_retry=on_retry)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ServerError("down")
            return "up"

        assert flaky() == "up"
        assert len(retries_log) == 2
        assert retries_log[0][0] == "ServerError"
        assert retries_log[0][1] == 0
        assert retries_log[1][1] == 1

    def test_retryable_exceptions_parameter(self):
        """Only the specified exception types trigger a retry."""
        call_count = 0

        @retry(
            max_retries=2,
            base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )
        def picky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("retry me")
            return "done"

        assert picky() == "done"
        assert call_count == 2

    def test_retryable_exceptions_ignores_others(self):
        """Exceptions not in retryable_exceptions propagate immediately."""
        call_count = 0

        @retry(
            max_retries=2,
            base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with pytest.raises(TypeError, match="wrong type"):
            raises_type_error()

        assert call_count == 1

    def test_zero_max_retries_raises_immediately(self):
        """With max_retries=0, the first failure is raised immediately."""
        call_count = 0

        @retry(max_retries=0, base_delay=0.01)
        def no_retries():
            nonlocal call_count
            call_count += 1
            raise APIError("fail")

        with pytest.raises(APIError, match="fail"):
            no_retries()

        assert call_count == 1

    def test_delay_is_non_negative(self):
        """Jittered delay should never be negative."""
        delays = []

        def on_retry(exc, attempt, delay):
            delays.append(delay)

        @retry(max_retries=5, base_delay=0.01, on_retry=on_retry)
        def always_fail():
            raise APIError("boom")

        with pytest.raises(APIError):
            always_fail()

        assert all(d >= 0.0 for d in delays)
