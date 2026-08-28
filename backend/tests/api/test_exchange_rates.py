"""Exchange rate API integration tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

API = "/api/v1/exchange-rates"
VALID_PASSWORD = "SecurePass1"


async def _register_token(client: AsyncClient, prefix: str = "fx") -> str:
    email = f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_store_and_lookup_historical_rate(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client, "store-rate")
    create = await auth_client.post(
        API,
        json={
            "base_currency": "CHF",
            "quote_currency": "USD",
            "rate": "1.25000000",
            "rate_date": "2026-03-01",
            "source": "manual",
            "overwrite_existing": True,
        },
        headers=_auth(token),
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["rate"] == "1.25000000"
    assert body["rate_date"] == "2026-03-01"
    assert "retrieved_at" in body

    lookup = await auth_client.get(
        f"{API}/lookup?base_currency=CHF&quote_currency=USD&rate_date=2026-03-15",
        headers=_auth(token),
    )
    assert lookup.status_code == 200
    assert lookup.json()["rate"] == "1.25000000"
    assert lookup.json()["rate_date"] == "2026-03-01"


@pytest.mark.asyncio
async def test_historical_rate_not_overwritten_by_default(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "immutable-rate")
    first = await auth_client.post(
        API,
        json={
            "base_currency": "AUD",
            "quote_currency": "USD",
            "rate": "1.30000000",
            "rate_date": "2026-04-01",
            "overwrite_existing": True,
        },
        headers=_auth(token),
    )
    assert first.status_code == 201

    conflict = await auth_client.post(
        API,
        json={
            "base_currency": "AUD",
            "quote_currency": "USD",
            "rate": "9.99900000",
            "rate_date": "2026-04-01",
        },
        headers=_auth(token),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "EXCHANGE_RATE_EXISTS"

    overwrite = await auth_client.post(
        API,
        json={
            "base_currency": "AUD",
            "quote_currency": "USD",
            "rate": "1.31000000",
            "rate_date": "2026-04-01",
            "overwrite_existing": True,
        },
        headers=_auth(token),
    )
    assert overwrite.status_code == 201
    assert overwrite.json()["rate"] == "1.31000000"


@pytest.mark.asyncio
async def test_convert_uses_stored_historical_rate(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client, "convert-rate")
    await auth_client.post(
        API,
        json={
            "base_currency": "EUR",
            "quote_currency": "USD",
            "rate": "1.10000000",
            "rate_date": "2026-05-01",
            "overwrite_existing": True,
        },
        headers=_auth(token),
    )
    await auth_client.post(
        API,
        json={
            "base_currency": "EUR",
            "quote_currency": "USD",
            "rate": "2.00000000",
            "rate_date": "2026-05-20",
            "overwrite_existing": True,
        },
        headers=_auth(token),
    )

    older = await auth_client.post(
        f"{API}/convert",
        json={
            "amount": "100.0000",
            "from_currency": "EUR",
            "to_currency": "USD",
            "as_of_date": "2026-05-10",
        },
        headers=_auth(token),
    )
    assert older.status_code == 200
    assert older.json()["converted_amount"] == "110.0000"
    assert older.json()["rate_used"] == "1.10000000"

    newer = await auth_client.post(
        f"{API}/convert",
        json={
            "amount": "100.0000",
            "from_currency": "EUR",
            "to_currency": "USD",
            "as_of_date": "2026-05-25",
        },
        headers=_auth(token),
    )
    assert newer.status_code == 200
    assert newer.json()["converted_amount"] == "200.0000"


@pytest.mark.asyncio
async def test_convert_same_currency(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client, "same-fx")
    response = await auth_client.post(
        f"{API}/convert",
        json={
            "amount": "12.3400",
            "from_currency": "USD",
            "to_currency": "USD",
            "as_of_date": "2026-01-01",
        },
        headers=_auth(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["converted_amount"] == "12.3400"
    assert body["rate_used"] is None


@pytest.mark.asyncio
async def test_convert_missing_rate(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client, "missing-fx")
    response = await auth_client.post(
        f"{API}/convert",
        json={
            "amount": "10.0000",
            "from_currency": "NOK",
            "to_currency": "SEK",
            "as_of_date": "2026-01-01",
        },
        headers=_auth(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MISSING_EXCHANGE_RATE"


@pytest.mark.asyncio
async def test_fetch_provider_unavailable_by_default(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "provider-none")
    response = await auth_client.post(
        f"{API}/fetch",
        json={
            "base_currency": "EUR",
            "quote_currency": "USD",
            "rate_date": "2026-06-01",
        },
        headers=_auth(token),
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "EXCHANGE_RATE_PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_exchange_rate_write_forbidden_outside_test_env(
    auth_client: AsyncClient,
    app_settings,
) -> None:
    from app.main import create_app

    dev_app = create_app(
        settings=app_settings.model_copy(update={"app_env": "development"}),
    )
    transport = ASGITransport(app=dev_app)
    async with (
        dev_app.router.lifespan_context(dev_app),
        AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client,
    ):
        token = await _register_token(client, "dev-fx-blocked")
        response = await client.post(
            API,
            json={
                "base_currency": "EUR",
                "quote_currency": "USD",
                "rate": "1.10000000",
                "rate_date": "2026-06-01",
                "overwrite_existing": True,
            },
            headers=_auth(token),
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
