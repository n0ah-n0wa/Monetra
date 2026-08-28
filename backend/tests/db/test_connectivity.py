"""Database connectivity diagnostic tests."""

from unittest.mock import AsyncMock, MagicMock

from app.db.session import check_database_connectivity
from sqlalchemy.exc import OperationalError


async def test_check_database_connectivity_returns_latency_on_success() -> None:
    connection = AsyncMock()
    connection.execute = AsyncMock()
    connect_cm = AsyncMock()
    connect_cm.__aenter__.return_value = connection
    connect_cm.__aexit__.return_value = None

    engine = MagicMock()
    engine.connect.return_value = connect_cm

    result = await check_database_connectivity(engine=engine)

    assert result.ok is True
    assert result.latency_ms is not None
    assert result.error is None


async def test_check_database_connectivity_returns_safe_error_category() -> None:
    engine = MagicMock()
    engine.connect.side_effect = OperationalError("statement", {}, Exception("boom"))

    result = await check_database_connectivity(engine=engine)

    assert result.ok is False
    assert result.error == "database_connection_failed"
    assert "boom" not in (result.error or "")
    assert "statement" not in (result.error or "")
