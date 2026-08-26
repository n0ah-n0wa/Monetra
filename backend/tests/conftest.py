"""Shared pytest fixtures."""

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure test settings are applied before the app imports settings.
os.environ["APP_ENV"] = "test"
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://monetra:monetra@localhost:5432/monetra_test",
)
os.environ["JWT_SECRET_KEY"] = "test-secret-key-must-be-at-least-32-chars"
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("DEBUG", "false")


@pytest.fixture
def app_settings():
    from app.core.config import Settings, get_settings

    get_settings.cache_clear()
    return Settings()


@pytest.fixture
def application(app_settings):
    from app.main import create_app

    return create_app(settings=app_settings)


@pytest.fixture
async def client(application) -> AsyncIterator[AsyncClient]:
    """HTTP client with application lifespan (DB init/dispose) active."""
    async with application.router.lifespan_context(application):
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
