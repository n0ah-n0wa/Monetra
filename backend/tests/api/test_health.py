"""Health and readiness endpoint tests."""

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
    assert isinstance(payload["database"], bool)
    if response.status_code == 200:
        assert payload == {"status": "ready", "database": True}
    else:
        assert payload == {"status": "unavailable", "database": False}
