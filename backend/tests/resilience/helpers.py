"""Shared helpers for production failure regression tests."""

from __future__ import annotations

import uuid
from decimal import Decimal
from io import BytesIO

from httpx import AsyncClient

VALID_PASSWORD = "SecurePass1"
CSV_HEADER = (
    "transaction_date,transaction_type,amount,description,category,"
    "external_reference,notes\n"
)


async def register_token(client: AsyncClient, *, prefix: str = "resilience") -> str:
    email = f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def create_account(
    client: AsyncClient,
    token: str,
    *,
    opening_balance: str = "1000.0000",
) -> str:
    response = await client.post(
        "/api/v1/accounts",
        json={
            "name": f"Acct-{uuid.uuid4().hex[:6]}",
            "account_type": "bank",
            "currency": "USD",
            "opening_balance": opening_balance,
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def account_balance(
    client: AsyncClient,
    token: str,
    account_id: str,
) -> Decimal:
    response = await client.get(
        f"/api/v1/accounts/{account_id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    return Decimal(response.json()["current_balance"])


async def upload_csv(
    client: AsyncClient,
    token: str,
    *,
    account_id: str,
    content: str,
    filename: str = "import.csv",
) -> object:
    return await client.post(
        "/api/v1/imports",
        data={"account_id": account_id},
        files={
            "file": (filename, BytesIO(content.encode("utf-8")), "text/csv"),
        },
        headers=auth_headers(token),
    )
