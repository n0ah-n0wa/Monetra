"""Budget API integration tests."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

API = "/api/v1/budgets"
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


async def _create_account(
    client: AsyncClient,
    token: str,
    *,
    name: str,
    opening_balance: str = "5000.0000",
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
    category_type: str = "expense",
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


def _budget_payload(
    *,
    category_ids: list[str] | None = None,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Groceries Budget",
        "amount": "500.0000",
        "currency": "USD",
        "period": "monthly",
        "scope": "category",
        "start_date": "2026-01-01",
        "category_ids": category_ids or [],
    }
    payload.update(overrides)
    return payload


async def _create_expense(
    client: AsyncClient,
    token: str,
    *,
    account_id: str,
    category_id: str,
    amount: str,
    transaction_date: str,
) -> None:
    response = await client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": category_id,
            "transaction_type": "expense",
            "amount": amount,
            "description": "Budget test expense",
            "transaction_date": transaction_date,
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text


async def test_create_category_budget(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    groceries = await _category_id(auth_client, token, name="Groceries")

    response = await auth_client.post(
        API,
        json=_budget_payload(category_ids=[groceries]),
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["scope"] == "category"
    assert len(body["categories"]) == 1
    assert body["amount"] == "500.0000"


async def test_empty_budget_reports_zero_spent(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    groceries = await _category_id(auth_client, token, name="Groceries")

    created = await auth_client.post(
        API,
        json=_budget_payload(category_ids=[groceries]),
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    utilization = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    assert utilization.status_code == 200
    body = utilization.json()
    assert body["spent_amount"] == "0.0000"
    assert body["remaining_amount"] == "500.0000"
    assert body["percentage_used"] == "0.0000"
    assert body["status"] == "healthy"


async def test_budget_utilization_after_expenses(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    groceries = await _category_id(auth_client, token, name="Groceries")
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )

    created = await auth_client.post(
        API,
        json=_budget_payload(category_ids=[groceries], amount="200.0000"),
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    await _create_expense(
        auth_client,
        token,
        account_id=account_id,
        category_id=groceries,
        amount="75.5000",
        transaction_date="2026-01-10",
    )
    await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": salary,
            "transaction_type": "income",
            "amount": "1000.0000",
            "description": "Paycheck",
            "transaction_date": "2026-01-10",
        },
        headers=_auth_headers(token),
    )

    utilization = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    body = utilization.json()
    assert body["spent_amount"] == "75.5000"
    assert body["remaining_amount"] == "124.5000"
    assert body["status"] == "healthy"


async def test_transfers_do_not_affect_budget_spent(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    source_id = await _create_account(auth_client, token, name="Source")
    dest_id = await _create_account(auth_client, token, name="Dest")

    created = await auth_client.post(
        API,
        json={
            "name": "Overall",
            "amount": "1000.0000",
            "currency": "USD",
            "period": "monthly",
            "scope": "overall",
            "start_date": "2026-01-01",
        },
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    transfer = await auth_client.post(
        TRANSFERS_API,
        json={
            "source_account_id": source_id,
            "destination_account_id": dest_id,
            "source_amount": "250.0000",
            "transaction_date": "2026-01-05",
        },
        headers=_auth_headers(token),
    )
    assert transfer.status_code == 201

    utilization = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    assert utilization.json()["spent_amount"] == "0.0000"


async def test_exceeded_budget_status(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    groceries = await _category_id(auth_client, token, name="Groceries")

    created = await auth_client.post(
        API,
        json=_budget_payload(
            category_ids=[groceries],
            amount="100.0000",
            warning_threshold_percent=80,
        ),
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    await _create_expense(
        auth_client,
        token,
        account_id=account_id,
        category_id=groceries,
        amount="150.0000",
        transaction_date="2026-01-12",
    )

    utilization = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    body = utilization.json()
    assert body["status"] == "exceeded"
    assert body["percentage_used"] == "150.0000"
    assert body["remaining_amount"] == "-50.0000"


async def test_warning_budget_status(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    groceries = await _category_id(auth_client, token, name="Groceries")

    created = await auth_client.post(
        API,
        json=_budget_payload(
            category_ids=[groceries],
            amount="100.0000",
            warning_threshold_percent=80,
        ),
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    await _create_expense(
        auth_client,
        token,
        account_id=account_id,
        category_id=groceries,
        amount="85.0000",
        transaction_date="2026-01-12",
    )

    utilization = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    assert utilization.json()["status"] == "warning"


async def test_multiple_categories_in_one_budget(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    groceries = await _category_id(auth_client, token, name="Groceries")
    food = await _category_id(auth_client, token, name="Food")

    created = await auth_client.post(
        API,
        json=_budget_payload(
            category_ids=[groceries, food],
            amount="300.0000",
        ),
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    await _create_expense(
        auth_client,
        token,
        account_id=account_id,
        category_id=groceries,
        amount="50.0000",
        transaction_date="2026-01-05",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=account_id,
        category_id=food,
        amount="40.0000",
        transaction_date="2026-01-06",
    )

    utilization = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    assert utilization.json()["spent_amount"] == "90.0000"


async def test_period_boundary_excludes_previous_month(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    groceries = await _category_id(auth_client, token, name="Groceries")

    created = await auth_client.post(
        API,
        json=_budget_payload(category_ids=[groceries]),
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    await _create_expense(
        auth_client,
        token,
        account_id=account_id,
        category_id=groceries,
        amount="100.0000",
        transaction_date="2026-01-31",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=account_id,
        category_id=groceries,
        amount="50.0000",
        transaction_date="2026-02-01",
    )

    jan = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-01-31",
        headers=_auth_headers(token),
    )
    feb = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-02-15",
        headers=_auth_headers(token),
    )
    assert jan.json()["spent_amount"] == "100.0000"
    assert feb.json()["spent_amount"] == "50.0000"


async def test_custom_period_budget(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    groceries = await _category_id(auth_client, token, name="Groceries")

    created = await auth_client.post(
        API,
        json=_budget_payload(
            category_ids=[groceries],
            period="custom",
            start_date="2026-01-10",
            end_date="2026-01-20",
        ),
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    await _create_expense(
        auth_client,
        token,
        account_id=account_id,
        category_id=groceries,
        amount="20.0000",
        transaction_date="2026-01-15",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=account_id,
        category_id=groceries,
        amount="30.0000",
        transaction_date="2026-01-25",
    )

    utilization = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-01-18",
        headers=_auth_headers(token),
    )
    assert utilization.json()["spent_amount"] == "20.0000"
    assert utilization.json()["period_start"] == "2026-01-10"
    assert utilization.json()["period_end"] == "2026-01-20"


async def test_budget_analytics_endpoint(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    groceries = await _category_id(auth_client, token, name="Groceries")

    await auth_client.post(
        API,
        json=_budget_payload(category_ids=[groceries]),
        headers=_auth_headers(token),
    )

    response = await auth_client.get(
        f"{API}/analytics/utilization?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


async def test_archived_category_rejected_on_create(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    groceries = await _category_id(auth_client, token, name="Groceries")

    archived = await auth_client.post(
        f"{CATEGORIES_API}/{groceries}/archive",
        headers=_auth_headers(token),
    )
    assert archived.status_code == 200

    response = await auth_client.post(
        API,
        json=_budget_payload(category_ids=[groceries]),
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATEGORY_ARCHIVED"


async def test_budget_ownership_enforced(auth_client: AsyncClient) -> None:
    owner_token = await _register_token(auth_client, prefix="owner")
    other_token = await _register_token(auth_client, prefix="other")
    groceries = await _category_id(auth_client, owner_token, name="Groceries")

    created = await auth_client.post(
        API,
        json=_budget_payload(category_ids=[groceries]),
        headers=_auth_headers(owner_token),
    )
    budget_id = created.json()["id"]

    for method, url, kwargs in (
        ("get", f"{API}/{budget_id}", {}),
        ("patch", f"{API}/{budget_id}", {"json": {"name": "Hacked"}}),
        ("post", f"{API}/{budget_id}/archive", {}),
        ("get", f"{API}/{budget_id}/utilization", {}),
    ):
        response = await getattr(auth_client, method)(
            url,
            headers=_auth_headers(other_token),
            **kwargs,
        )
        assert response.status_code == 404


async def test_sequential_expenses_update_utilization(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    groceries = await _category_id(auth_client, token, name="Groceries")

    created = await auth_client.post(
        API,
        json=_budget_payload(category_ids=[groceries], amount="200.0000"),
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    for amount in ("10.0000", "20.0000", "30.0000"):
        await _create_expense(
            auth_client,
            token,
            account_id=account_id,
            category_id=groceries,
            amount=amount,
            transaction_date="2026-01-10",
        )
        utilization = await auth_client.get(
            f"{API}/{budget_id}/utilization?as_of_date=2026-01-15",
            headers=_auth_headers(token),
        )
        assert utilization.status_code == 200

    final = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    assert final.json()["spent_amount"] == "60.0000"


async def test_income_does_not_count_toward_budget(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Main")
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )

    created = await auth_client.post(
        API,
        json={
            "name": "Overall",
            "amount": "500.0000",
            "currency": "USD",
            "period": "monthly",
            "scope": "overall",
            "start_date": "2026-01-01",
        },
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": salary,
            "transaction_type": "income",
            "amount": "1000.0000",
            "description": "Paycheck",
            "transaction_date": "2026-01-10",
        },
        headers=_auth_headers(token),
    )

    utilization = await auth_client.get(
        f"{API}/{budget_id}/utilization?as_of_date=2026-01-15",
        headers=_auth_headers(token),
    )
    assert utilization.json()["spent_amount"] == "0.0000"


async def test_update_and_archive_budget(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    groceries = await _category_id(auth_client, token, name="Groceries")

    created = await auth_client.post(
        API,
        json=_budget_payload(category_ids=[groceries]),
        headers=_auth_headers(token),
    )
    budget_id = created.json()["id"]

    updated = await auth_client.patch(
        f"{API}/{budget_id}",
        json={"amount": "600.0000", "name": "Updated"},
        headers=_auth_headers(token),
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == "600.0000"

    archived = await auth_client.post(
        f"{API}/{budget_id}/archive",
        headers=_auth_headers(token),
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
