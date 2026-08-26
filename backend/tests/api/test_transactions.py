"""Transaction API integration tests."""

from __future__ import annotations

import uuid
from decimal import Decimal

from httpx import AsyncClient

API = "/api/v1/transactions"
ACCOUNTS_API = "/api/v1/accounts"
CATEGORIES_API = "/api/v1/categories"
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


async def _category_id_by_name(
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
    raise AssertionError(f"Category {name!r} ({category_type}) not found")


def _transaction_payload(
    *,
    account_id: str,
    category_id: str,
    transaction_type: str,
    amount: str = "100.0000",
    description: str = "Test transaction",
    transaction_date: str = "2026-01-15",
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "account_id": account_id,
        "category_id": category_id,
        "transaction_type": transaction_type,
        "amount": amount,
        "description": description,
        "transaction_date": transaction_date,
    }
    payload.update(overrides)
    return payload


async def _setup_user_context(client: AsyncClient, token: str) -> tuple[str, str, str]:
    account_id = await _create_account(
        client, token, name=f"Acct-{uuid.uuid4().hex[:6]}"
    )
    expense_category_id = await _category_id_by_name(
        client,
        token,
        name="Groceries",
        category_type="expense",
    )
    income_category_id = await _category_id_by_name(
        client,
        token,
        name="Salary",
        category_type="income",
    )
    return account_id, expense_category_id, income_category_id


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


async def test_create_expense_transaction_updates_balance(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, _ = await _setup_user_context(auth_client, token)

    response = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
            amount="125.5000",
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["transaction_type"] == "expense"
    assert body["amount"] == "125.5000"
    assert body["currency"] == "USD"

    balance = await _account_balance(auth_client, token, account_id)
    assert balance == Decimal("874.5000")


async def test_create_income_transaction_updates_balance(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id, _, income_category_id = await _setup_user_context(auth_client, token)

    response = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=income_category_id,
            transaction_type="income",
            amount="250.0000",
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["transaction_type"] == "income"

    balance = await _account_balance(auth_client, token, account_id)
    assert balance == Decimal("1250.0000")


async def test_create_transaction_rejects_invalid_amount(
    authenticated_client: AsyncClient,
) -> None:
    token = authenticated_client.headers["Authorization"].removeprefix("Bearer ")
    account_id, expense_category_id, _ = await _setup_user_context(
        authenticated_client,
        token,
    )

    response = await authenticated_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
            amount="0.0000",
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_AMOUNT"


async def test_create_transaction_rejects_category_type_mismatch(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, _ = await _setup_user_context(auth_client, token)

    response = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="income",
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATEGORY_TYPE_MISMATCH"


async def test_get_transaction(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, _ = await _setup_user_context(auth_client, token)

    created = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
            description="Retrieve me",
        ),
        headers=_auth_headers(token),
    )
    transaction_id = created.json()["id"]

    response = await auth_client.get(
        f"{API}/{transaction_id}",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Retrieve me"


async def test_update_transaction_adjusts_balance(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, _ = await _setup_user_context(auth_client, token)

    created = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
            amount="100.0000",
        ),
        headers=_auth_headers(token),
    )
    transaction_id = created.json()["id"]
    assert await _account_balance(auth_client, token, account_id) == Decimal("900.0000")

    updated = await auth_client.patch(
        f"{API}/{transaction_id}",
        json={"amount": "150.0000"},
        headers=_auth_headers(token),
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == "150.0000"
    assert await _account_balance(auth_client, token, account_id) == Decimal("850.0000")


async def test_delete_transaction_soft_deletes_and_reverses_balance(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, _ = await _setup_user_context(auth_client, token)

    created = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
            amount="75.2500",
        ),
        headers=_auth_headers(token),
    )
    transaction_id = created.json()["id"]
    assert await _account_balance(auth_client, token, account_id) == Decimal("924.7500")

    deleted = await auth_client.delete(
        f"{API}/{transaction_id}",
        headers=_auth_headers(token),
    )
    assert deleted.status_code == 204

    assert await _account_balance(auth_client, token, account_id) == Decimal(
        "1000.0000"
    )

    missing = await auth_client.get(
        f"{API}/{transaction_id}",
        headers=_auth_headers(token),
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


async def test_list_transactions_empty_dataset(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)

    response = await auth_client.get(API, headers=_auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total_items"] == 0
    assert body["total_pages"] == 0


async def test_list_transactions_pagination_and_sorting(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, income_category_id = await _setup_user_context(
        auth_client,
        token,
    )

    payloads = [
        _transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
            amount="10.0000",
            description="Small",
            transaction_date="2026-01-10",
        ),
        _transaction_payload(
            account_id=account_id,
            category_id=income_category_id,
            transaction_type="income",
            amount="500.0000",
            description="Large",
            transaction_date="2026-01-20",
        ),
        _transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
            amount="50.0000",
            description="Medium",
            transaction_date="2026-01-15",
        ),
    ]
    for payload in payloads:
        response = await auth_client.post(
            API,
            json=payload,
            headers=_auth_headers(token),
        )
        assert response.status_code == 201

    by_amount = await auth_client.get(
        f"{API}?sort_by=amount&sort_order=asc&page_size=2&page=1",
        headers=_auth_headers(token),
    )
    assert by_amount.status_code == 200
    amounts = [item["amount"] for item in by_amount.json()["items"]]
    assert amounts == ["10.0000", "50.0000"]
    assert by_amount.json()["total_items"] == 3

    by_date = await auth_client.get(
        f"{API}?sort_by=transaction_date&sort_order=desc",
        headers=_auth_headers(token),
    )
    dates = [item["transaction_date"] for item in by_date.json()["items"]]
    assert dates == ["2026-01-20", "2026-01-15", "2026-01-10"]


async def test_list_transactions_filters(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, income_category_id = await _setup_user_context(
        auth_client,
        token,
    )
    other_account_id = await _create_account(
        auth_client,
        token,
        name=f"Other-{uuid.uuid4().hex[:6]}",
    )

    await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
            amount="25.0000",
            description="Coffee shop",
            transaction_date="2026-02-01",
        ),
        headers=_auth_headers(token),
    )
    await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=other_account_id,
            category_id=income_category_id,
            transaction_type="income",
            amount="300.0000",
            description="Paycheck",
            transaction_date="2026-02-05",
        ),
        headers=_auth_headers(token),
    )

    filtered = await auth_client.get(
        f"{API}?account_id={account_id}&transaction_type=expense"
        "&date_from=2026-02-01&date_to=2026-02-01"
        "&amount_min=20&amount_max=30&currency=USD&description=coffee",
        headers=_auth_headers(token),
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["total_items"] == 1
    assert body["items"][0]["description"] == "Coffee shop"


async def test_list_transactions_date_boundaries_inclusive(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, _ = await _setup_user_context(auth_client, token)

    for day in ("2026-03-01", "2026-03-02", "2026-03-03"):
        response = await auth_client.post(
            API,
            json=_transaction_payload(
                account_id=account_id,
                category_id=expense_category_id,
                transaction_type="expense",
                transaction_date=day,
                description=f"Day {day}",
            ),
            headers=_auth_headers(token),
        )
        assert response.status_code == 201

    response = await auth_client.get(
        f"{API}?date_from=2026-03-02&date_to=2026-03-02",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["total_items"] == 1
    assert response.json()["items"][0]["transaction_date"] == "2026-03-02"


async def test_create_large_amount_transaction(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(
        auth_client,
        token,
        name=f"Large-{uuid.uuid4().hex[:6]}",
        opening_balance="0.0000",
    )
    income_category_id = await _category_id_by_name(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )
    large = "999999999999999.9999"

    response = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=income_category_id,
            transaction_type="income",
            amount=large,
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["amount"] == large


async def test_transaction_ownership_enforced(auth_client: AsyncClient) -> None:
    owner_token = await _register_token(auth_client, prefix="owner")
    other_token = await _register_token(auth_client, prefix="other")
    account_id, expense_category_id, _ = await _setup_user_context(
        auth_client,
        owner_token,
    )

    created = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
        ),
        headers=_auth_headers(owner_token),
    )
    transaction_id = created.json()["id"]

    for method, url, kwargs in (
        ("get", f"{API}/{transaction_id}", {}),
        ("patch", f"{API}/{transaction_id}", {"json": {"description": "Hack"}}),
        ("delete", f"{API}/{transaction_id}", {}),
    ):
        response = await getattr(auth_client, method)(
            url,
            headers=_auth_headers(other_token),
            **kwargs,
        )
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


async def test_transactions_require_authentication(auth_client: AsyncClient) -> None:
    auth_client.headers.pop("Authorization", None)

    for method, url, kwargs in (
        ("post", API, {"json": {}}),
        ("get", API, {}),
        ("get", f"{API}/{uuid.uuid4()}", {}),
        ("patch", f"{API}/{uuid.uuid4()}", {"json": {"description": "X"}}),
        ("delete", f"{API}/{uuid.uuid4()}", {}),
    ):
        response = await getattr(auth_client, method)(url, **kwargs)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_update_transaction_requires_field(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, _ = await _setup_user_context(auth_client, token)

    created = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
        ),
        headers=_auth_headers(token),
    )
    transaction_id = created.json()["id"]

    response = await auth_client.patch(
        f"{API}/{transaction_id}",
        json={},
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_invalid_date_range_rejected(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)

    response = await auth_client.get(
        f"{API}?date_from=2026-05-01&date_to=2026-04-01",
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DATE_RANGE"


async def test_list_with_unknown_account_filter_returns_not_found(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)

    response = await auth_client.get(
        f"{API}?account_id={uuid.uuid4()}",
        headers=_auth_headers(token),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


async def test_update_metadata_on_archived_account_allowed(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, _ = await _setup_user_context(auth_client, token)

    created = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
        ),
        headers=_auth_headers(token),
    )
    transaction_id = created.json()["id"]

    archived = await auth_client.post(
        f"{ACCOUNTS_API}/{account_id}/archive",
        headers=_auth_headers(token),
    )
    assert archived.status_code == 200

    updated = await auth_client.patch(
        f"{API}/{transaction_id}",
        json={"description": "Updated after archive"},
        headers=_auth_headers(token),
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated after archive"


async def test_cannot_change_amount_on_archived_account(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    account_id, expense_category_id, _ = await _setup_user_context(auth_client, token)

    created = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=account_id,
            category_id=expense_category_id,
            transaction_type="expense",
            amount="50.0000",
        ),
        headers=_auth_headers(token),
    )
    transaction_id = created.json()["id"]

    await auth_client.post(
        f"{ACCOUNTS_API}/{account_id}/archive",
        headers=_auth_headers(token),
    )

    response = await auth_client.patch(
        f"{API}/{transaction_id}",
        json={"amount": "75.0000"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ACCOUNT_ARCHIVED"


async def test_move_transaction_off_archived_account(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client)
    archived_account_id, expense_category_id, _ = await _setup_user_context(
        auth_client,
        token,
    )
    active_account_id = await _create_account(
        auth_client,
        token,
        name=f"Active-{uuid.uuid4().hex[:6]}",
    )

    created = await auth_client.post(
        API,
        json=_transaction_payload(
            account_id=archived_account_id,
            category_id=expense_category_id,
            transaction_type="expense",
            amount="40.0000",
        ),
        headers=_auth_headers(token),
    )
    transaction_id = created.json()["id"]

    await auth_client.post(
        f"{ACCOUNTS_API}/{archived_account_id}/archive",
        headers=_auth_headers(token),
    )

    moved = await auth_client.patch(
        f"{API}/{transaction_id}",
        json={"account_id": active_account_id},
        headers=_auth_headers(token),
    )
    assert moved.status_code == 200
    assert moved.json()["account_id"] == active_account_id

    archived_balance = await _account_balance(
        auth_client,
        token,
        archived_account_id,
    )
    active_balance = await _account_balance(auth_client, token, active_account_id)
    assert archived_balance == Decimal("1000.0000")
    assert active_balance == Decimal("960.0000")
