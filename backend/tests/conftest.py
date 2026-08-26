"""Shared pytest fixtures."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure test settings are applied before the app imports settings.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://monetra:monetra@localhost:5432/monetra_test",
)
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-secret-key-must-be-at-least-32-chars",
)
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")


@pytest.fixture
async def client() -> AsyncClient:
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    application = create_app()

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
