"""User profile API tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

VALID_PASSWORD = "SecurePass1"


async def _register(client: AsyncClient) -> tuple[str, dict]:
    email = f"profile-{uuid.uuid4().hex[:12]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_update_reporting_currency(auth_client: AsyncClient) -> None:
    _, headers = await _register(auth_client)

    me = await auth_client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["reporting_currency"] == "USD"

    updated = await auth_client.patch(
        "/api/v1/users/me",
        json={"reporting_currency": "eur"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["reporting_currency"] == "EUR"

    again = await auth_client.get("/api/v1/users/me", headers=headers)
    assert again.json()["reporting_currency"] == "EUR"


@pytest.mark.asyncio
async def test_update_reporting_currency_rejects_invalid(
    auth_client: AsyncClient,
) -> None:
    _, headers = await _register(auth_client)
    response = await auth_client.patch(
        "/api/v1/users/me",
        json={"reporting_currency": "EURO"},
        headers=headers,
    )
    assert response.status_code == 422
