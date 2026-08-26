"""Financial balance invariant integration tests."""

from __future__ import annotations

import uuid
from uuid import UUID

from app.db.session import get_session_factory
from app.services.balance_service import assert_user_balance_invariant
from httpx import AsyncClient

ACCOUNTS_API = "/api/v1/accounts"
CATEGORIES_API = "/api/v1/categories"
TRANSACTIONS_API = "/api/v1/transactions"
TRANSFERS_API = "/api/v1/transfers"
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


async def _user_id(client: AsyncClient, token: str) -> UUID:
    response = await client.get(
        "/api/v1/users/me",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    return UUID(response.json()["id"])


async def _assert_invariant(client: AsyncClient, token: str) -> None:
    user_id = await _user_id(client, token)
    factory = get_session_factory()
    async with factory() as session:
        await assert_user_balance_invariant(session, user_id=user_id)


async def _create_account(
    client: AsyncClient,
    token: str,
    *,
    name: str,
    currency: str = "USD",
    opening_balance: str = "1000.0000",
) -> str:
    response = await client.post(
        ACCOUNTS_API,
        json={
            "name": name,
            "account_type": "bank",
            "currency": currency,
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


async def test_invariant_after_account_creation(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    await _create_account(auth_client, token, name=f"A-{uuid.uuid4().hex[:6]}")
    await _create_account(
        auth_client,
        token,
        name=f"B-{uuid.uuid4().hex[:6]}",
        opening_balance="250.5000",
    )
    await _assert_invariant(auth_client, token)


async def test_invariant_across_mixed_operations(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    checking = await _create_account(
        auth_client,
        token,
        name="Checking",
        opening_balance="2000.0000",
    )
    savings = await _create_account(
        auth_client,
        token,
        name="Savings",
        opening_balance="500.0000",
    )
    eur = await _create_account(
        auth_client,
        token,
        name="EUR Wallet",
        currency="EUR",
        opening_balance="100.0000",
    )
    expense_category = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )
    income_category = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )

    await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": checking,
            "category_id": income_category,
            "transaction_type": "income",
            "amount": "1500.2500",
            "description": "Paycheck",
            "transaction_date": "2026-01-01",
        },
        headers=_auth_headers(token),
    )
    await _assert_invariant(auth_client, token)

    expense = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": checking,
            "category_id": expense_category,
            "transaction_type": "expense",
            "amount": "123.4567",
            "description": "Groceries",
            "transaction_date": "2026-01-31",
        },
        headers=_auth_headers(token),
    )
    assert expense.status_code == 201
    await _assert_invariant(auth_client, token)

    transfer = await auth_client.post(
        TRANSFERS_API,
        json={
            "source_account_id": checking,
            "destination_account_id": savings,
            "source_amount": "400.0000",
            "transaction_date": "2026-02-01",
            "description": "Save",
        },
        headers=_auth_headers(token),
    )
    assert transfer.status_code == 201
    await _assert_invariant(auth_client, token)

    fx = await auth_client.post(
        TRANSFERS_API,
        json={
            "source_account_id": checking,
            "destination_account_id": eur,
            "source_amount": "100.0000",
            "exchange_rate": "0.85000000",
            "transaction_date": "2026-02-15",
        },
        headers=_auth_headers(token),
    )
    assert fx.status_code == 201
    await _assert_invariant(auth_client, token)

    tx_id = expense.json()["id"]
    updated = await auth_client.patch(
        f"{TRANSACTIONS_API}/{tx_id}",
        json={"amount": "150.0000"},
        headers=_auth_headers(token),
    )
    assert updated.status_code == 200
    await _assert_invariant(auth_client, token)

    moved = await auth_client.patch(
        f"{TRANSACTIONS_API}/{tx_id}",
        json={"account_id": savings},
        headers=_auth_headers(token),
    )
    assert moved.status_code == 200
    await _assert_invariant(auth_client, token)

    deleted = await auth_client.delete(
        f"{TRANSACTIONS_API}/{tx_id}",
        headers=_auth_headers(token),
    )
    assert deleted.status_code == 204
    await _assert_invariant(auth_client, token)


async def test_invariant_after_transaction_type_change(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    expense_category = await _category_id(
        auth_client,
        token,
        name="Food",
        category_type="expense",
    )
    income_category = await _category_id(
        auth_client,
        token,
        name="Bonus",
        category_type="income",
    )

    created = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": income_category,
            "transaction_type": "income",
            "amount": "200.0000",
            "description": "Bonus",
            "transaction_date": "2026-03-01",
        },
        headers=_auth_headers(token),
    )
    tx_id = created.json()["id"]

    flipped = await auth_client.patch(
        f"{TRANSACTIONS_API}/{tx_id}",
        json={
            "transaction_type": "expense",
            "category_id": expense_category,
        },
        headers=_auth_headers(token),
    )
    assert flipped.status_code == 200
    await _assert_invariant(auth_client, token)


async def test_invariant_with_large_values(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(
        auth_client,
        token,
        name="Large",
        opening_balance="0.0000",
    )
    income_category = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )

    response = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": income_category,
            "transaction_type": "income",
            "amount": "999999999999999.9999",
            "description": "Large credit",
            "transaction_date": "2026-04-01",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    await _assert_invariant(auth_client, token)


async def test_zero_amount_rejected_without_balance_drift(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Zero")
    expense_category = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    response = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": expense_category,
            "transaction_type": "expense",
            "amount": "0.0000",
            "description": "Invalid",
            "transaction_date": "2026-05-01",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    await _assert_invariant(auth_client, token)


async def test_idempotent_transfer_preserves_invariant(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    source_id = await _create_account(auth_client, token, name="Source")
    dest_id = await _create_account(auth_client, token, name="Dest")

    payload = {
        "source_account_id": source_id,
        "destination_account_id": dest_id,
        "source_amount": "100.0000",
        "transaction_date": "2026-06-01",
        "idempotency_key": "integrity-audit-key",
    }
    first = await auth_client.post(
        TRANSFERS_API,
        json=payload,
        headers=_auth_headers(token),
    )
    assert first.status_code == 201
    await _assert_invariant(auth_client, token)

    second = await auth_client.post(
        TRANSFERS_API,
        json=payload,
        headers=_auth_headers(token),
    )
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    await _assert_invariant(auth_client, token)


async def test_failed_transfer_does_not_drift_balances(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    source_id = await _create_account(
        auth_client,
        token,
        name="Low",
        opening_balance="10.0000",
    )
    dest_id = await _create_account(auth_client, token, name="Dest")

    response = await auth_client.post(
        TRANSFERS_API,
        json={
            "source_account_id": source_id,
            "destination_account_id": dest_id,
            "source_amount": "50.0000",
            "transaction_date": "2026-06-15",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
    await _assert_invariant(auth_client, token)


async def test_date_boundaries_do_not_affect_balance_totals(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Dates")
    expense_category = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    for day, amount in (
        ("2026-01-01", "10.0000"),
        ("2026-06-15", "20.0000"),
        ("2026-12-31", "30.0000"),
    ):
        response = await auth_client.post(
            TRANSACTIONS_API,
            json={
                "account_id": account_id,
                "category_id": expense_category,
                "transaction_type": "expense",
                "amount": amount,
                "description": f"Expense {day}",
                "transaction_date": day,
            },
            headers=_auth_headers(token),
        )
        assert response.status_code == 201

    await _assert_invariant(auth_client, token)

    filtered = await auth_client.get(
        f"{TRANSACTIONS_API}?date_from=2026-06-01&date_to=2026-06-30",
        headers=_auth_headers(token),
    )
    assert filtered.json()["total_items"] == 1
    await _assert_invariant(auth_client, token)
