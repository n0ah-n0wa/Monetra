"""CSV export API integration tests."""

from __future__ import annotations

import csv
import io
import uuid
from decimal import Decimal

from httpx import AsyncClient

API = "/api/v1/exports/transactions"
ACCOUNTS_API = "/api/v1/accounts"
TRANSACTIONS_API = "/api/v1/transactions"
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


async def _create_transaction(
    client: AsyncClient,
    token: str,
    *,
    account_id: str,
    category_id: str,
    transaction_type: str,
    amount: str,
    description: str,
    transaction_date: str,
) -> None:
    response = await client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": category_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "description": description,
            "transaction_date": transaction_date,
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text


def _parse_csv(body: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(body)))


async def test_empty_export(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    response = await auth_client.get(API, headers=_auth_headers(token))
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.text.startswith(
        "transaction_date,transaction_type,amount,currency,description,category,account",
    )
    assert _parse_csv(response.text) == []


async def test_export_all_and_filtered(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    checking = await _create_account(auth_client, token, name="Checking")
    savings = await _create_account(auth_client, token, name="Savings")
    groceries = await _category_id(
        auth_client, token, name="Groceries", category_type="expense"
    )
    salary = await _category_id(
        auth_client, token, name="Salary", category_type="income"
    )

    await _create_transaction(
        auth_client,
        token,
        account_id=checking,
        category_id=groceries,
        transaction_type="expense",
        amount="12.5000",
        description="Coffee",
        transaction_date="2026-01-10",
    )
    await _create_transaction(
        auth_client,
        token,
        account_id=savings,
        category_id=salary,
        transaction_type="income",
        amount="100.0000",
        description="Bonus",
        transaction_date="2026-02-01",
    )

    all_export = await auth_client.get(API, headers=_auth_headers(token))
    assert all_export.status_code == 200
    all_rows = _parse_csv(all_export.text)
    assert len(all_rows) == 2

    filtered = await auth_client.get(
        f"{API}?account_id={checking}&transaction_type=expense",
        headers=_auth_headers(token),
    )
    assert filtered.status_code == 200
    rows = _parse_csv(filtered.text)
    assert len(rows) == 1
    assert rows[0]["description"] == "Coffee"
    assert rows[0]["account"] == "Checking"
    assert rows[0]["category"] == "Groceries"
    assert rows[0]["amount"] == "12.5000"
    assert rows[0]["currency"] == "USD"
    assert rows[0]["transaction_type"] == "expense"


async def test_export_date_range(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Range Acct")
    groceries = await _category_id(
        auth_client, token, name="Groceries", category_type="expense"
    )
    for day, desc in (
        ("2026-01-05", "Early"),
        ("2026-01-15", "Mid"),
        ("2026-02-01", "Late"),
    ):
        await _create_transaction(
            auth_client,
            token,
            account_id=account_id,
            category_id=groceries,
            transaction_type="expense",
            amount="1.0000",
            description=desc,
            transaction_date=day,
        )

    response = await auth_client.get(
        f"{API}?date_from=2026-01-10&date_to=2026-01-31",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    rows = _parse_csv(response.text)
    assert [row["description"] for row in rows] == ["Mid"]


async def test_export_multiple_currencies(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    usd = await _create_account(auth_client, token, name="USD Cash", currency="USD")
    eur = await _create_account(auth_client, token, name="EUR Cash", currency="EUR")
    groceries = await _category_id(
        auth_client, token, name="Groceries", category_type="expense"
    )
    await _create_transaction(
        auth_client,
        token,
        account_id=usd,
        category_id=groceries,
        transaction_type="expense",
        amount="10.0000",
        description="USD spend",
        transaction_date="2026-03-01",
    )
    await _create_transaction(
        auth_client,
        token,
        account_id=eur,
        category_id=groceries,
        transaction_type="expense",
        amount="20.0000",
        description="EUR spend",
        transaction_date="2026-03-02",
    )

    response = await auth_client.get(API, headers=_auth_headers(token))
    assert response.status_code == 200
    rows = _parse_csv(response.text)
    by_desc = {row["description"]: row for row in rows}
    assert by_desc["USD spend"]["currency"] == "USD"
    assert by_desc["USD spend"]["amount"] == "10.0000"
    assert by_desc["EUR spend"]["currency"] == "EUR"
    assert by_desc["EUR spend"]["amount"] == "20.0000"

    eur_only = await auth_client.get(
        f"{API}?currency=EUR",
        headers=_auth_headers(token),
    )
    assert len(_parse_csv(eur_only.text)) == 1
    assert _parse_csv(eur_only.text)[0]["description"] == "EUR spend"


async def test_export_csv_escaping(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name='Acct, "Primary"')
    groceries = await _category_id(
        auth_client, token, name="Groceries", category_type="expense"
    )
    await _create_transaction(
        auth_client,
        token,
        account_id=account_id,
        category_id=groceries,
        transaction_type="expense",
        amount="5.2500",
        description='Lunch, "special"\nline',
        transaction_date="2026-04-01",
    )

    response = await auth_client.get(API, headers=_auth_headers(token))
    assert response.status_code == 200
    rows = _parse_csv(response.text)
    assert len(rows) == 1
    assert rows[0]["description"] == 'Lunch, "special"\nline'
    assert rows[0]["account"] == 'Acct, "Primary"'
    assert Decimal(rows[0]["amount"]) == Decimal("5.2500")


async def test_export_neutralizes_csv_formulas(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client)
    account_id = await _create_account(auth_client, token, name="Safe Acct")
    groceries = await _category_id(
        auth_client, token, name="Groceries", category_type="expense"
    )
    await _create_transaction(
        auth_client,
        token,
        account_id=account_id,
        category_id=groceries,
        transaction_type="expense",
        amount="1.0000",
        description="=1+2",
        transaction_date="2026-04-02",
    )
    response = await auth_client.get(API, headers=_auth_headers(token))
    assert response.status_code == 200
    assert "'=1+2" in response.text
    rows = _parse_csv(response.text)
    assert rows[0]["description"] == "'=1+2"


async def test_export_ownership(auth_client: AsyncClient) -> None:
    token_a = await _register_token(auth_client, prefix="expa")
    token_b = await _register_token(auth_client, prefix="expb")
    account_a = await _create_account(auth_client, token_a, name="A Only")
    account_b = await _create_account(auth_client, token_b, name="B Only")
    groceries_a = await _category_id(
        auth_client, token_a, name="Groceries", category_type="expense"
    )
    groceries_b = await _category_id(
        auth_client, token_b, name="Groceries", category_type="expense"
    )

    await _create_transaction(
        auth_client,
        token_a,
        account_id=account_a,
        category_id=groceries_a,
        transaction_type="expense",
        amount="11.0000",
        description="Secret A",
        transaction_date="2026-05-01",
    )
    await _create_transaction(
        auth_client,
        token_b,
        account_id=account_b,
        category_id=groceries_b,
        transaction_type="expense",
        amount="22.0000",
        description="Secret B",
        transaction_date="2026-05-02",
    )

    export_a = await auth_client.get(API, headers=_auth_headers(token_a))
    rows_a = _parse_csv(export_a.text)
    assert [row["description"] for row in rows_a] == ["Secret A"]

    export_b = await auth_client.get(API, headers=_auth_headers(token_b))
    rows_b = _parse_csv(export_b.text)
    assert [row["description"] for row in rows_b] == ["Secret B"]

    cross = await auth_client.get(
        f"{API}?account_id={account_b}",
        headers=_auth_headers(token_a),
    )
    assert cross.status_code == 404
