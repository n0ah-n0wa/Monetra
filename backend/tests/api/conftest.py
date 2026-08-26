"""API integration test fixtures."""

from collections.abc import AsyncIterator

import pytest
from app.core.rate_limit import InMemoryRateLimiter
from app.db.session import get_engine, ping_database
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def auth_client(application) -> AsyncIterator[AsyncClient]:
    """HTTP client for auth flows; skips when PostgreSQL is unavailable."""
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
    from app.services.notification_providers import InMemoryNotificationProvider

    provider = getattr(application.state, "notification_provider", None)
    if not isinstance(provider, InMemoryNotificationProvider):
        pytest.skip("In-memory notification provider is not configured")
    provider.clear()
    return provider


@pytest.fixture
def rate_limited_application(app_settings):
    from app.main import create_app

    return create_app(
        settings=app_settings.model_copy(
            update={"auth_rate_limit_max_requests": 2},
        ),
    )


@pytest.fixture
async def rate_limited_auth_client(
    rate_limited_application,
) -> AsyncIterator[AsyncClient]:
    """Auth client with a low rate limit for rate-limiting tests."""
    async with rate_limited_application.router.lifespan_context(
        rate_limited_application,
    ):
        if not await ping_database(get_engine()):
            pytest.skip("PostgreSQL is not available")

        limiter = getattr(rate_limited_application.state, "rate_limiter", None)
        if isinstance(limiter, InMemoryRateLimiter):
            limiter.reset()

        transport = ASGITransport(app=rate_limited_application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        if isinstance(limiter, InMemoryRateLimiter):
            limiter.reset()
