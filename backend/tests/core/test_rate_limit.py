"""Rate limiter unit tests."""

from app.core.rate_limit import InMemoryRateLimiter


def test_in_memory_rate_limiter_allows_within_window() -> None:
    clock = {"now": 100.0}
    limiter = InMemoryRateLimiter(clock=lambda: clock["now"])
    assert limiter.allow("key", limit=2, window_seconds=60) is True
    assert limiter.allow("key", limit=2, window_seconds=60) is True
    assert limiter.allow("key", limit=2, window_seconds=60) is False


def test_in_memory_rate_limiter_resets_after_window() -> None:
    clock = {"now": 100.0}
    limiter = InMemoryRateLimiter(clock=lambda: clock["now"])
    assert limiter.allow("key", limit=1, window_seconds=60) is True
    assert limiter.allow("key", limit=1, window_seconds=60) is False
    clock["now"] = 161.0
    assert limiter.allow("key", limit=1, window_seconds=60) is True


def test_in_memory_rate_limiter_reset_clears_counters() -> None:
    limiter = InMemoryRateLimiter()
    assert limiter.allow("key", limit=1, window_seconds=60) is True
    assert limiter.allow("key", limit=1, window_seconds=60) is False
    limiter.reset()
    assert limiter.allow("key", limit=1, window_seconds=60) is True
