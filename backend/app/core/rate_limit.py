"""Rate limiting primitives with a Redis-ready interface."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from typing import Protocol


class RateLimiter(Protocol):
    """Check whether a request key is within configured limits."""

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Return True when the request is allowed."""

    def reset(self) -> None:
        """Clear counters (used in tests)."""


class InMemoryRateLimiter:
    """Process-local sliding-window rate limiter.

    Suitable for development and single-instance deployments. The interface is
    intentionally narrow so a Redis-backed implementation can replace it later.
    """

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        now = self._clock()
        window_start = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


def get_rate_limiter(application: object) -> RateLimiter:
    """Return the shared rate limiter stored on the FastAPI app."""
    state = getattr(application, "state", None)
    limiter = getattr(state, "rate_limiter", None) if state is not None else None
    if isinstance(limiter, InMemoryRateLimiter):
        return limiter
    return InMemoryRateLimiter()
