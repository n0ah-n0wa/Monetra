"""Financial goal API integration tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

API = "/api/v1/goals"
ACCOUNTS_API = "/api/v1/accounts"
CATEGORIES_API = "/api/v1/categories"
TRANSACTIONS_API = "/api/v1/transactions"
VALID_PASSWORD = "SecurePass1"


async def _register_token(client: AsyncClient, prefix: str = "user") -> str:
    email = f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_account(
    client: AsyncClient,
    token: str,
    *,
    name: str,
    opening_balance: str = "1000.0000",
) -> str:
    response = await client.post(
        ACCOUNTS_API,
        json={
            "name": name,
            "account_type": "bank",
            "currency": "USD",
            "opening_balance": opening_balance,
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _category_id(client: AsyncClient, token: str, *, name: str) -> str:
    response = await client.get(
        f"{CATEGORIES_API}?include_system=false&page_size=100",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        if item["name"] == name:
            return item["id"]
    raise AssertionError(f"Category {name!r} not found")


def _goal_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Emergency Fund",
        "target_amount": "1000.0000",
        "current_amount": "0.0000",
        "currency": "USD",
        "target_date": "2026-12-31",
    }
    payload.update(overrides)
    return payload


async def test_create_goal(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    response = await auth_client.post(
        API,
        json=_goal_payload(current_amount="250.0000"),
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Emergency Fund"
    assert body["current_amount"] == "250.0000"
    assert body["status"] == "active"


async def test_goal_progress_calculations(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    created = await auth_client.post(
        API,
        json=_goal_payload(current_amount="250.0000"),
        headers=_auth_headers(token),
    )
    goal_id = created.json()["id"]

    progress = await auth_client.get(
        f"{API}/{goal_id}/progress?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    assert progress.status_code == 200
    body = progress.json()
    assert body["remaining_amount"] == "750.0000"
    assert body["completion_percentage"] == "25.0000"
    assert body["required_average_contribution"] is not None


async def test_target_already_reached_marks_completed(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    created = await auth_client.post(
        API,
        json=_goal_payload(current_amount="1000.0000"),
        headers=_auth_headers(token),
    )
    assert created.json()["status"] == "completed"

    progress = await auth_client.get(
        f"{API}/{created.json()['id']}/progress?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    body = progress.json()
    assert body["remaining_amount"] == "0.0000"
    assert body["completion_percentage"] == "100.0000"
    assert body["projected_completion_date"] == "2026-01-15"


async def test_past_target_date_required_average_is_null(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    created = await auth_client.post(
        API,
        json=_goal_payload(
            current_amount="100.0000",
            target_date="2025-12-31",
        ),
        headers=_auth_headers(token),
    )
    goal_id = created.json()["id"]

    progress = await auth_client.get(
        f"{API}/{goal_id}/progress?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    assert progress.json()["required_average_contribution"] is None


async def test_linked_account_contribution_history(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Savings")
    income_category = await _category_id(auth_client, token, name="Salary")
    start = datetime.now(UTC).date()
    mid = start + timedelta(days=10)
    as_of = start + timedelta(days=14)

    created = await auth_client.post(
        API,
        json=_goal_payload(
            current_amount="0.0000",
            linked_account_id=account_id,
            target_date=(as_of + timedelta(days=120)).isoformat(),
        ),
        headers=_auth_headers(token),
    )
    goal_id = created.json()["id"]

    for tx_day, amount in ((start, "100.0000"), (mid, "100.0000")):
        await auth_client.post(
            TRANSACTIONS_API,
            json={
                "account_id": account_id,
                "category_id": income_category,
                "transaction_type": "income",
                "amount": amount,
                "description": "Deposit",
                "transaction_date": tx_day.isoformat(),
            },
            headers=_auth_headers(token),
        )

    progress = await auth_client.get(
        f"{API}/{goal_id}/progress?as_of_date={as_of.isoformat()}",
        headers=_auth_headers(token),
    )
    body = progress.json()
    assert body["average_contribution_rate"] == "10.0000"
    assert body["projected_completion_date"] is not None


async def test_update_and_archive_goal(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    created = await auth_client.post(
        API,
        json=_goal_payload(),
        headers=_auth_headers(token),
    )
    goal_id = created.json()["id"]

    updated = await auth_client.patch(
        f"{API}/{goal_id}",
        json={"current_amount": "500.0000", "name": "Updated Goal"},
        headers=_auth_headers(token),
    )
    assert updated.status_code == 200
    assert updated.json()["current_amount"] == "500.0000"

    archived = await auth_client.post(
        f"{API}/{goal_id}/archive",
        headers=_auth_headers(token),
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["archived_at"] is not None


async def test_goal_ownership_enforced(auth_client: AsyncClient) -> None:
    owner_token = await _register_token(auth_client, prefix="owner")
    other_token = await _register_token(auth_client, prefix="other")

    created = await auth_client.post(
        API,
        json=_goal_payload(),
        headers=_auth_headers(owner_token),
    )
    goal_id = created.json()["id"]

    for method, url, kwargs in (
        ("get", f"{API}/{goal_id}", {}),
        ("patch", f"{API}/{goal_id}", {"json": {"name": "Hacked"}}),
        ("post", f"{API}/{goal_id}/archive", {}),
        ("get", f"{API}/{goal_id}/progress", {}),
    ):
        response = await getattr(auth_client, method)(
            url,
            headers=_auth_headers(other_token),
            **kwargs,
        )
        assert response.status_code == 404


async def test_linked_account_currency_mismatch_rejected(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    eur_account = await auth_client.post(
        ACCOUNTS_API,
        json={
            "name": "EUR",
            "account_type": "bank",
            "currency": "EUR",
            "opening_balance": "100.0000",
        },
        headers=_auth_headers(token),
    )
    account_id = eur_account.json()["id"]

    response = await auth_client.post(
        API,
        json=_goal_payload(linked_account_id=account_id, currency="USD"),
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CURRENCY_MISMATCH"
