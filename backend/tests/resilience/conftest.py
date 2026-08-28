"""Fixtures for production failure regression tests."""

from collections.abc import AsyncIterator

import pytest
from app.core.rate_limit import InMemoryRateLimiter
from app.db.session import get_engine, ping_database
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def auth_client(application) -> AsyncIterator[AsyncClient]:
    """HTTP client for authenticated API flows."""
    async with application.router.lifespan_context(application):
        if not await ping_database(get_engine()):
            pytest.skip("PostgreSQL is not available")

        limiter = getattr(application.state, "rate_limiter", None)
        if isinstance(limiter, InMemoryRateLimiter):
            limiter.reset()

        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        if isinstance(limiter, InMemoryRateLimiter):
            limiter.reset()
