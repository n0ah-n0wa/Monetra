"""Database session infrastructure tests."""

import pytest
from app.db.session import get_engine, ping_database
from sqlalchemy import text


@pytest.mark.asyncio
async def test_ping_database_returns_bool() -> None:
    result = await ping_database()
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_engine_executes_when_database_up() -> None:
    ok = await ping_database()
    if not ok:
        pytest.skip("PostgreSQL is not available")
    engine = get_engine()
    async with engine.connect() as connection:
        value = await connection.scalar(text("SELECT 1"))
    assert value == 1
