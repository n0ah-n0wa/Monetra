"""Recurring transaction API integration tests."""

from __future__ import annotations

import uuid
from decimal import Decimal

from httpx import AsyncClient

API = "/api/v1/recurring-transactions"
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


async def _category_id(
    client: AsyncClient,
    token: str,
    *,
    name: str,
    category_type: str,
) -> str:
    response = await client.get(
        f"{CATEGORIES_API}?include_system=false&page_size=100",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        if item["name"] == name and item["category_type"] == category_type:
            return item["id"]
    raise AssertionError(f"Category {name!r} not found")


def _recurring_payload(
    *,
    account_id: str,
    category_id: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "account_id": account_id,
        "category_id": category_id,
        "transaction_type": "expense",
        "amount": "50.0000",
        "description": "Rent",
        "frequency": "monthly",
        "start_date": "2026-01-01",
    }
    payload.update(overrides)
    return payload


async def _account_balance(
    client: AsyncClient,
    token: str,
    account_id: str,
) -> Decimal:
    response = await client.get(
        f"{ACCOUNTS_API}/{account_id}",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    return Decimal(response.json()["current_balance"])


async def test_create_recurring_transaction_sets_next_execution_date(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    category_id = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    response = await auth_client.post(
        API,
        json=_recurring_payload(
            account_id=account_id,
            category_id=category_id,
            start_date="2026-02-01",
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["next_execution_date"] == "2026-02-01"
    assert body["is_active"] is True
    assert body["frequency"] == "monthly"


async def test_process_due_creates_transaction_and_advances_schedule(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    category_id = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    created = await auth_client.post(
        API,
        json=_recurring_payload(
            account_id=account_id,
            category_id=category_id,
            frequency="daily",
            start_date="2026-01-01",
            amount="10.0000",
        ),
        headers=_auth_headers(token),
    )
    recurring_id = created.json()["id"]

    processed = await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2026-01-03"},
        headers=_auth_headers(token),
    )
    assert processed.status_code == 200, processed.text
    body = processed.json()
    assert body["as_of_date"] == "2026-01-03"
    assert len(body["executions"]) == 3
    assert all(item["created"] for item in body["executions"])
    assert {item["execution_date"] for item in body["executions"]} == {
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
    }

    recurring = await auth_client.get(
        f"{API}/{recurring_id}",
        headers=_auth_headers(token),
    )
    assert recurring.json()["next_execution_date"] == "2026-01-04"
    assert await _account_balance(auth_client, token, account_id) == Decimal("970.0000")

    tx_list = await auth_client.get(TRANSACTIONS_API, headers=_auth_headers(token))
    assert tx_list.json()["total_items"] == 3


async def test_process_due_is_idempotent(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    category_id = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    await auth_client.post(
        API,
        json=_recurring_payload(
            account_id=account_id,
            category_id=category_id,
            frequency="weekly",
            start_date="2026-01-01",
        ),
        headers=_auth_headers(token),
    )

    first = await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2026-01-01"},
        headers=_auth_headers(token),
    )
    assert first.status_code == 200
    assert first.json()["executions"][0]["created"] is True

    second = await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2026-01-01"},
        headers=_auth_headers(token),
    )
    assert second.status_code == 200
    assert second.json()["executions"] == []

    balance_after_first = await _account_balance(auth_client, token, account_id)
    await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2026-01-01"},
        headers=_auth_headers(token),
    )
    assert await _account_balance(auth_client, token, account_id) == balance_after_first


async def test_monthly_execution_handles_month_end(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    category_id = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    created = await auth_client.post(
        API,
        json=_recurring_payload(
            account_id=account_id,
            category_id=category_id,
            frequency="monthly",
            start_date="2026-01-31",
        ),
        headers=_auth_headers(token),
    )
    recurring_id = created.json()["id"]

    await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2026-01-31"},
        headers=_auth_headers(token),
    )
    await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2026-02-28"},
        headers=_auth_headers(token),
    )

    recurring = await auth_client.get(
        f"{API}/{recurring_id}",
        headers=_auth_headers(token),
    )
    assert recurring.json()["next_execution_date"] == "2026-03-31"


async def test_end_date_stops_future_executions(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    category_id = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    created = await auth_client.post(
        API,
        json=_recurring_payload(
            account_id=account_id,
            category_id=category_id,
            frequency="daily",
            start_date="2026-01-01",
            end_date="2026-01-02",
        ),
        headers=_auth_headers(token),
    )
    recurring_id = created.json()["id"]

    processed = await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2026-01-10"},
        headers=_auth_headers(token),
    )
    assert len(processed.json()["executions"]) == 2

    recurring = await auth_client.get(
        f"{API}/{recurring_id}",
        headers=_auth_headers(token),
    )
    assert recurring.json()["is_active"] is False


async def test_update_recurring_transaction(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    category_id = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    created = await auth_client.post(
        API,
        json=_recurring_payload(
            account_id=account_id,
            category_id=category_id,
        ),
        headers=_auth_headers(token),
    )
    recurring_id = created.json()["id"]

    updated = await auth_client.patch(
        f"{API}/{recurring_id}",
        json={"amount": "75.0000", "description": "Updated rent"},
        headers=_auth_headers(token),
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["amount"] == "75.0000"
    assert body["description"] == "Updated rent"


async def test_archive_recurring_transaction(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    category_id = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    created = await auth_client.post(
        API,
        json=_recurring_payload(
            account_id=account_id,
            category_id=category_id,
            start_date="2026-01-01",
        ),
        headers=_auth_headers(token),
    )
    recurring_id = created.json()["id"]

    archived = await auth_client.post(
        f"{API}/{recurring_id}/archive",
        headers=_auth_headers(token),
    )
    assert archived.status_code == 200
    assert archived.json()["is_active"] is False

    processed = await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2026-01-01"},
        headers=_auth_headers(token),
    )
    assert processed.json()["executions"] == []


async def test_recurring_ownership_enforced(auth_client: AsyncClient) -> None:
    owner_token = await _register_token(auth_client, prefix="owner")
    other_token = await _register_token(auth_client, prefix="other")
    account_id = await _create_account(auth_client, owner_token, name="Main")
    category_id = await _category_id(
        auth_client,
        owner_token,
        name="Groceries",
        category_type="expense",
    )

    created = await auth_client.post(
        API,
        json=_recurring_payload(account_id=account_id, category_id=category_id),
        headers=_auth_headers(owner_token),
    )
    recurring_id = created.json()["id"]

    for method, url, kwargs in (
        ("get", f"{API}/{recurring_id}", {}),
        ("patch", f"{API}/{recurring_id}", {"json": {"description": "Blocked"}}),
        ("post", f"{API}/{recurring_id}/archive", {}),
    ):
        response = await getattr(auth_client, method)(
            url,
            headers=_auth_headers(other_token),
            **kwargs,
        )
        assert response.status_code == 404


async def test_recurring_requires_authentication(auth_client: AsyncClient) -> None:
    auth_client.headers.pop("Authorization", None)
    response = await auth_client.get(API)
    assert response.status_code == 401


async def test_create_rejects_end_date_before_start(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    category_id = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    response = await auth_client.post(
        API,
        json=_recurring_payload(
            account_id=account_id,
            category_id=category_id,
            start_date="2026-02-01",
            end_date="2026-01-01",
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 422


async def test_process_due_advances_pointer_when_execution_already_recorded(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    category_id = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    created = await auth_client.post(
        API,
        json=_recurring_payload(
            account_id=account_id,
            category_id=category_id,
            frequency="weekly",
            start_date="2026-01-01",
        ),
        headers=_auth_headers(token),
    )
    recurring_id = created.json()["id"]

    first = await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2026-01-01"},
        headers=_auth_headers(token),
    )
    assert first.status_code == 200
    assert len(first.json()["executions"]) == 1

    recurring = await auth_client.get(
        f"{API}/{recurring_id}",
        headers=_auth_headers(token),
    )
    assert recurring.json()["next_execution_date"] == "2026-01-08"

    replay = await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2026-01-01"},
        headers=_auth_headers(token),
    )
    assert replay.status_code == 200
    assert replay.json()["executions"] == []

    recurring_after = await auth_client.get(
        f"{API}/{recurring_id}",
        headers=_auth_headers(token),
    )
    assert recurring_after.json()["next_execution_date"] == "2026-01-08"


async def test_yearly_leap_day_execution(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    category_id = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    created = await auth_client.post(
        API,
        json=_recurring_payload(
            account_id=account_id,
            category_id=category_id,
            frequency="yearly",
            start_date="2024-02-29",
        ),
        headers=_auth_headers(token),
    )
    recurring_id = created.json()["id"]

    await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2024-02-29"},
        headers=_auth_headers(token),
    )
    await auth_client.post(
        f"{API}/process-due",
        json={"as_of_date": "2025-02-28"},
        headers=_auth_headers(token),
    )

    recurring = await auth_client.get(
        f"{API}/{recurring_id}",
        headers=_auth_headers(token),
    )
    assert recurring.json()["next_execution_date"] == "2026-02-28"
