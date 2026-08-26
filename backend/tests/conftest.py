"""Shared pytest fixtures."""

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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
async def db_engine(app_settings):

    from app.db.session import create_async_engine_from_settings, ping_database

    engine = create_async_engine_from_settings(app_settings)
    if not await ping_database(engine):
        await engine.dispose()
        pytest.skip("PostgreSQL is not available")
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):

    from sqlalchemy.ext.asyncio import AsyncSession

    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()


@pytest.fixture
async def user(db_session):
    from app.models.user import User

    entity = User(
        email="user@example.com",
        password_hash="hashed-password",
        password_changed_at=datetime.now(UTC),
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def other_user(db_session):
    from app.models.user import User

    entity = User(
        email="other@example.com",
        password_hash="hashed-password",
        password_changed_at=datetime.now(UTC),
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.fixture
async def system_category(db_session):
    from app.models.category import Category
    from app.models.enums import CategoryType

    entity = Category(
        user_id=None,
        name="Uncategorized",
        category_type=CategoryType.UNIVERSAL,
        is_system=True,
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


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
