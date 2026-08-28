"""Regression tests for proxy-aware auth rate limiting."""

from __future__ import annotations

import uuid

import pytest
from app.core.config import Settings
from app.core.rate_limit import InMemoryRateLimiter
from app.db.session import get_engine, ping_database
from app.main import create_app
from httpx import ASGITransport, AsyncClient

API = "/api/v1"
VALID_PASSWORD = "SecurePass1"


def _unique_email(prefix: str = "proxy") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
async def proxy_rate_limited_client():
    settings = Settings(
        app_env="test",
        auth_rate_limit_max_requests=2,
        trusted_proxy_count=1,
    )
    application = create_app(settings=settings)

    async with application.router.lifespan_context(application):
        if not await ping_database(get_engine()):
            pytest.skip("PostgreSQL is not available")

        limiter = application.state.rate_limiter
        if isinstance(limiter, InMemoryRateLimiter):
            limiter.reset()

        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        if isinstance(limiter, InMemoryRateLimiter):
            limiter.reset()


async def test_auth_rate_limit_honors_x_forwarded_for_behind_proxy(
    proxy_rate_limited_client: AsyncClient,
) -> None:
    """Each distinct forwarded client IP gets its own rate-limit bucket."""
    email = _unique_email()
    headers = {"X-Forwarded-For": "203.0.113.10"}

    for _ in range(2):
        response = await proxy_rate_limited_client.post(
            f"{API}/auth/login",
            json={"email": email, "password": "wrong-password"},
            headers=headers,
        )
        assert response.status_code == 401

    blocked = await proxy_rate_limited_client.post(
        f"{API}/auth/login",
        json={"email": email, "password": "wrong-password"},
        headers=headers,
    )
    assert blocked.status_code == 429

    other_client = await proxy_rate_limited_client.post(
        f"{API}/auth/login",
        json={"email": email, "password": "wrong-password"},
        headers={"X-Forwarded-For": "203.0.113.11"},
    )
    assert other_client.status_code == 401
