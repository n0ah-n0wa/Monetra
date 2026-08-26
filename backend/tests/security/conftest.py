"""Security test fixtures."""

from collections.abc import AsyncIterator

import pytest
from app.services.notification_providers import InMemoryNotificationProvider
from httpx import AsyncClient


@pytest.fixture
async def auth_client(application) -> AsyncIterator[AsyncClient]:
    """HTTP client for auth flows; skips when PostgreSQL is unavailable."""
    from app.core.rate_limit import InMemoryRateLimiter
    from app.db.session import get_engine, ping_database
    from httpx import ASGITransport

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


@pytest.fixture
def notification_provider(application, auth_client):
    provider = getattr(application.state, "notification_provider", None)
    if not isinstance(provider, InMemoryNotificationProvider):
        pytest.skip("In-memory notification provider is not configured")
    provider.clear()
    return provider
