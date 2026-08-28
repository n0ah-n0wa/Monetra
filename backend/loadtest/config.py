"""Load test configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True, slots=True)
class LoadTestConfig:
    """Runtime settings for local load tests (non-production only)."""

    base_url: str
    email: str
    password: str
    concurrency: int
    iterations: int
    transaction_seed_count: int
    budget_seed_count: int
    request_timeout_seconds: float

    @classmethod
    def from_env(cls) -> LoadTestConfig:
        return cls(
            base_url=_env_str("LOADTEST_BASE_URL", "http://127.0.0.1:8000").rstrip(
                "/",
            ),
            email=_env_str("LOADTEST_EMAIL", "loadtest-user@example.com"),
            password=_env_str("LOADTEST_PASSWORD", "LoadTest1!"),
            concurrency=_env_int("LOADTEST_CONCURRENCY", 8),
            iterations=_env_int("LOADTEST_ITERATIONS", 40),
            transaction_seed_count=_env_int("LOADTEST_TRANSACTION_COUNT", 1200),
            budget_seed_count=_env_int("LOADTEST_BUDGET_COUNT", 5),
            request_timeout_seconds=float(
                _env_str("LOADTEST_REQUEST_TIMEOUT_SECONDS", "30"),
            ),
        )
