"""Health and readiness endpoint tests."""

from unittest.mock import AsyncMock, patch

from app.db.session import DatabaseConnectivityResult
from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


async def test_health_propagates_request_id(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "test-corr-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-corr-123"


async def test_ready_when_database_available(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code in {200, 503}
    payload = response.json()
    assert "status" in payload
    assert "database" in payload
    assert "checks" in payload
    assert isinstance(payload["database"], bool)
    assert payload["checks"]["database"]["status"] in {"ok", "unavailable"}
    if response.status_code == 200:
        assert payload["status"] == "ready"
        assert payload["database"] is True
        assert payload["checks"]["database"]["status"] == "ok"
        assert payload["checks"]["database"]["latency_ms"] is not None
    else:
        assert payload["status"] == "unavailable"
        assert payload["database"] is False
        assert payload["checks"]["database"]["status"] == "unavailable"


async def test_ready_returns_503_when_database_unavailable(
    client: AsyncClient,
) -> None:
    unavailable = DatabaseConnectivityResult(
        ok=False,
        latency_ms=12.5,
        error="database_connection_failed",
    )
    with patch(
        "app.api.v1.health.check_database_connectivity",
        new=AsyncMock(return_value=unavailable),
    ):
        response = await client.get("/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload == {
        "status": "unavailable",
        "database": False,
        "checks": {
            "database": {
                "status": "unavailable",
                "latency_ms": 12.5,
                "error": "database_connection_failed",
            },
        },
    }


async def test_ready_includes_database_latency_when_available(
    client: AsyncClient,
) -> None:
    available = DatabaseConnectivityResult(ok=True, latency_ms=3.21)
    with patch(
        "app.api.v1.health.check_database_connectivity",
        new=AsyncMock(return_value=available),
    ):
        response = await client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["checks"]["database"]["latency_ms"] == 3.21
    assert payload["checks"]["database"]["error"] is None
