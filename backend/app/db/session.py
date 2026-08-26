"""Async SQLAlchemy engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_async_engine_from_settings(settings: Settings | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine from settings."""
    cfg = settings or get_settings()
    return create_async_engine(
        cfg.async_database_url,
        pool_size=cfg.database_pool_size,
        max_overflow=cfg.database_max_overflow,
        pool_pre_ping=True,
        echo=cfg.database_echo,
    )


def _dispose_engine_sync(engine: AsyncEngine) -> None:
    """Dispose an async engine from synchronous code (import/re-init paths)."""
    engine.sync_engine.dispose()


def init_db(settings: Settings | None = None) -> AsyncEngine:
    """Initialize (or replace) the module-level engine and session factory.

    Any previous engine is disposed first to avoid connection pool leaks.
    Prefer calling this from the application lifespan with explicit settings.
    """
    global _engine, _session_factory

    if _engine is not None:
        _dispose_engine_sync(_engine)
        _engine = None
        _session_factory = None

    cfg = settings or get_settings()
    _engine = create_async_engine_from_settings(cfg)
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return _engine


def get_engine() -> AsyncEngine:
    """Return the shared engine, creating it lazily if needed."""
    if _engine is None:
        return init_db()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        init_db()
    assert _session_factory is not None
    return _session_factory


async def dispose_db() -> None:
    """Dispose the engine and clear module state."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield a request-scoped database session.

    Callers are responsible for committing. The session is rolled back on
    unhandled exceptions and always closed when the request ends.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def ping_database(engine: AsyncEngine | None = None) -> bool:
    """Return True when PostgreSQL accepts a simple query."""
    target = engine or get_engine()
    try:
        async with target.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
