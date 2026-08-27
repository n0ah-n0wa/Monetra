"""Analytics API integration tests."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from app.models.exchange_rate import ExchangeRate
from httpx import AsyncClient

API = "/api/v1/analytics"
ACCOUNTS_API = "/api/v1/accounts"
CATEGORIES_API = "/api/v1/categories"
TRANSACTIONS_API = "/api/v1/transactions"
TRANSFERS_API = "/api/v1/transfers"
BUDGETS_API = "/api/v1/budgets"
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


async def _create_income(
    client: AsyncClient,
    token: str,
    *,
    account_id: str,
    category_id: str,
    amount: str,
    transaction_date: str,
    currency: str = "USD",
) -> None:
    response = await client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": category_id,
            "transaction_type": "income",
            "amount": amount,
            "currency": currency,
            "description": f"Income {amount}",
            "transaction_date": transaction_date,
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text


async def _create_expense(
    client: AsyncClient,
    token: str,
    *,
    account_id: str,
    category_id: str,
    amount: str,
    transaction_date: str,
    currency: str = "USD",
) -> None:
    response = await client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account_id,
            "category_id": category_id,
            "transaction_type": "expense",
            "amount": amount,
            "currency": currency,
            "description": f"Expense {amount}",
            "transaction_date": transaction_date,
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201, response.text


async def _seed_exchange_rate_for_tests(
    application,
    *,
    base_currency: str,
    quote_currency: str,
    rate: str,
    rate_date: date,
) -> None:
    from app.db.session import get_engine
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        await session.execute(
            delete(ExchangeRate).where(
                ExchangeRate.base_currency == base_currency,
                ExchangeRate.quote_currency == quote_currency,
                ExchangeRate.rate_date == rate_date,
            ),
        )
        session.add(
            ExchangeRate(
                base_currency=base_currency,
                quote_currency=quote_currency,
                rate=Decimal(rate),
                rate_date=rate_date,
                source="test",
            ),
        )
        await session.commit()


@pytest.mark.asyncio
async def test_income_vs_expenses_excludes_transfers(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "analytics-transfer")
    checking = await _create_account(auth_client, token, name="Checking")
    savings = await _create_account(auth_client, token, name="Savings")
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )
    groceries = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    await _create_income(
        auth_client,
        token,
        account_id=checking,
        category_id=salary,
        amount="3000.0000",
        transaction_date="2026-01-10",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=checking,
        category_id=groceries,
        amount="500.0000",
        transaction_date="2026-01-12",
    )
    transfer_response = await auth_client.post(
        TRANSFERS_API,
        json={
            "source_account_id": checking,
            "destination_account_id": savings,
            "source_amount": "200.0000",
            "destination_amount": "200.0000",
            "transaction_date": "2026-01-13",
        },
        headers=_auth_headers(token),
    )
    assert transfer_response.status_code == 201, transfer_response.text

    response = await auth_client.get(
        f"{API}/income-vs-expenses?period=custom&date_from=2026-01-01&date_to=2026-01-31",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["income"] == "3000.0000"
    assert body["expenses"] == "500.0000"


@pytest.mark.asyncio
async def test_savings_rate_and_net_cash_flow(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "analytics-savings")
    account = await _create_account(auth_client, token, name="Main")
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )
    food = await _category_id(
        auth_client,
        token,
        name="Food",
        category_type="expense",
    )

    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="2000.0000",
        transaction_date="2026-02-01",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=account,
        category_id=food,
        amount="500.0000",
        transaction_date="2026-02-05",
    )

    savings_response = await auth_client.get(
        f"{API}/savings-rate?period=custom&date_from=2026-02-01&date_to=2026-02-28",
        headers=_auth_headers(token),
    )
    assert savings_response.status_code == 200
    savings_body = savings_response.json()
    assert savings_body["net_cash_flow"] == "1500.0000"
    assert savings_body["savings_rate_percent"] == "75.0000"

    cash_flow_response = await auth_client.get(
        f"{API}/net-cash-flow?period=custom&date_from=2026-02-01&date_to=2026-02-28",
        headers=_auth_headers(token),
    )
    assert cash_flow_response.status_code == 200
    assert cash_flow_response.json()["total_net_cash_flow"] == "1500.0000"


@pytest.mark.asyncio
async def test_spending_by_category(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client, "analytics-category")
    account = await _create_account(auth_client, token, name="Wallet")
    groceries = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )
    transport = await _category_id(
        auth_client,
        token,
        name="Transport",
        category_type="expense",
    )

    await _create_expense(
        auth_client,
        token,
        account_id=account,
        category_id=groceries,
        amount="120.0000",
        transaction_date="2026-03-01",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=account,
        category_id=transport,
        amount="80.0000",
        transaction_date="2026-03-02",
    )

    response = await auth_client.get(
        f"{API}/spending-by-category?period=custom&date_from=2026-03-01&date_to=2026-03-31",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_expenses"] == "200.0000"
    assert len(body["items"]) == 2
    assert body["items"][0]["category_name"] == "Groceries"
    assert body["items"][0]["amount"] == "120.0000"
    assert body["items"][0]["percentage"] == "60.0000"


@pytest.mark.asyncio
async def test_largest_expenses_and_income(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client, "analytics-largest")
    account = await _create_account(auth_client, token, name="Primary")
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )
    shopping = await _category_id(
        auth_client,
        token,
        name="Shopping",
        category_type="expense",
    )

    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="100.0000",
        transaction_date="2026-04-01",
    )
    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="5000.0000",
        transaction_date="2026-04-02",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=account,
        category_id=shopping,
        amount="50.0000",
        transaction_date="2026-04-03",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=account,
        category_id=shopping,
        amount="900.0000",
        transaction_date="2026-04-04",
    )

    expenses = await auth_client.get(
        f"{API}/largest-expenses?period=custom&date_from=2026-04-01&date_to=2026-04-30&limit=1",
        headers=_auth_headers(token),
    )
    assert expenses.status_code == 200
    assert expenses.json()["items"][0]["amount"] == "900.0000"

    income = await auth_client.get(
        f"{API}/largest-income?period=custom&date_from=2026-04-01&date_to=2026-04-30&limit=1",
        headers=_auth_headers(token),
    )
    assert income.status_code == 200
    assert income.json()["items"][0]["amount"] == "5000.0000"


@pytest.mark.asyncio
async def test_period_comparison(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client, "analytics-compare")
    account = await _create_account(auth_client, token, name="Compare")
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )
    food = await _category_id(
        auth_client,
        token,
        name="Food",
        category_type="expense",
    )

    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="1000.0000",
        transaction_date="2026-05-10",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=account,
        category_id=food,
        amount="200.0000",
        transaction_date="2026-05-12",
    )
    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="500.0000",
        transaction_date="2026-04-10",
    )

    response = await auth_client.get(
        f"{API}/period-comparison?period=custom&date_from=2026-05-01&date_to=2026-05-31&as_of_date=2026-05-31",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["income"]["current"] == "1000.0000"
    assert body["income"]["previous"] == "500.0000"
    assert body["net_cash_flow"]["current"] == "800.0000"


@pytest.mark.asyncio
async def test_balance_over_time_includes_transfers(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "analytics-balance")
    checking = await _create_account(
        auth_client,
        token,
        name="Checking",
        opening_balance="1000.0000",
    )
    savings = await _create_account(
        auth_client,
        token,
        name="Savings",
        opening_balance="0.0000",
    )
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )

    await _create_income(
        auth_client,
        token,
        account_id=checking,
        category_id=salary,
        amount="500.0000",
        transaction_date="2026-06-01",
    )
    transfer_response = await auth_client.post(
        TRANSFERS_API,
        json={
            "source_account_id": checking,
            "destination_account_id": savings,
            "source_amount": "300.0000",
            "destination_amount": "300.0000",
            "transaction_date": "2026-06-02",
        },
        headers=_auth_headers(token),
    )
    assert transfer_response.status_code == 201

    response = await auth_client.get(
        f"{API}/balance-over-time?period=custom&date_from=2026-06-01&date_to=2026-06-02",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["opening_balance"] == "1000.0000"
    assert body["points"][0]["balance"] == "1500.0000"
    assert body["points"][1]["balance"] == "1500.0000"
    assert body["closing_balance"] == "1500.0000"


@pytest.mark.asyncio
async def test_empty_period_returns_zero_totals(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client, "analytics-empty")
    await _create_account(auth_client, token, name="Empty")

    response = await auth_client.get(
        f"{API}/income-vs-expenses?period=custom&date_from=2026-07-01&date_to=2026-07-31",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["income"] == "0.0000"
    assert body["expenses"] == "0.0000"


@pytest.mark.asyncio
async def test_multi_currency_conversion(
    auth_client: AsyncClient,
    application,
) -> None:
    token = await _register_token(auth_client, "analytics-fx")
    eur_account = await _create_account(
        auth_client,
        token,
        name="EUR Account",
        currency="EUR",
    )
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )

    await _seed_exchange_rate_for_tests(
        application,
        base_currency="EUR",
        quote_currency="USD",
        rate="1.10000000",
        rate_date=date(2026, 8, 1),
    )
    await _create_income(
        auth_client,
        token,
        account_id=eur_account,
        category_id=salary,
        amount="100.0000",
        transaction_date="2026-08-01",
        currency="EUR",
    )

    response = await auth_client.get(
        f"{API}/income-vs-expenses?period=custom&date_from=2026-08-01&date_to=2026-08-31&reporting_currency=USD",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["income"] == "110.0000"


@pytest.mark.asyncio
async def test_archived_account_transactions_included(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "analytics-archived")
    account = await _create_account(auth_client, token, name="To Archive")
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )

    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="750.0000",
        transaction_date="2026-09-05",
    )
    archive_response = await auth_client.post(
        f"{ACCOUNTS_API}/{account}/archive",
        headers=_auth_headers(token),
    )
    assert archive_response.status_code == 200

    response = await auth_client.get(
        f"{API}/income-vs-expenses?period=custom&date_from=2026-09-01&date_to=2026-09-30",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["income"] == "750.0000"


@pytest.mark.asyncio
async def test_budget_utilization_analytics_endpoint(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "analytics-budget")
    account = await _create_account(auth_client, token, name="Budget Account")
    groceries = await _category_id(
        auth_client,
        token,
        name="Groceries",
        category_type="expense",
    )

    budget_response = await auth_client.post(
        BUDGETS_API,
        json={
            "name": "Food Budget",
            "amount": "300.0000",
            "currency": "USD",
            "period": "monthly",
            "scope": "category",
            "start_date": "2026-10-01",
            "category_ids": [groceries],
        },
        headers=_auth_headers(token),
    )
    assert budget_response.status_code == 201

    await _create_expense(
        auth_client,
        token,
        account_id=account,
        category_id=groceries,
        amount="150.0000",
        transaction_date="2026-10-05",
    )

    response = await auth_client.get(
        f"{API}/budget-utilization?period=custom&date_from=2026-10-01&date_to=2026-10-31",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["utilization"]["spent_amount"] == "150.0000"


@pytest.mark.asyncio
async def test_date_boundaries_are_inclusive(auth_client: AsyncClient) -> None:
    token = await _register_token(auth_client, "analytics-bounds")
    account = await _create_account(auth_client, token, name="Bounds")
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )
    food = await _category_id(
        auth_client,
        token,
        name="Food",
        category_type="expense",
    )

    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="100.0000",
        transaction_date="2026-01-01",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=account,
        category_id=food,
        amount="40.0000",
        transaction_date="2026-01-31",
    )
    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="999.0000",
        transaction_date="2025-12-31",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=account,
        category_id=food,
        amount="999.0000",
        transaction_date="2026-02-01",
    )

    response = await auth_client.get(
        f"{API}/income-vs-expenses?period=custom&date_from=2026-01-01&date_to=2026-01-31",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["income"] == "100.0000"
    assert body["expenses"] == "40.0000"


@pytest.mark.asyncio
async def test_missing_exchange_rate_returns_validation_error(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "analytics-missing-fx")
    cad_account = await _create_account(
        auth_client,
        token,
        name="CAD Missing FX",
        currency="CAD",
        opening_balance="0.0000",
    )
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )
    await _create_income(
        auth_client,
        token,
        account_id=cad_account,
        category_id=salary,
        amount="50.0000",
        transaction_date="2026-11-01",
        currency="CAD",
    )

    response = await auth_client.get(
        f"{API}/income-vs-expenses?period=custom&date_from=2026-11-01&date_to=2026-11-30&reporting_currency=JPY",
        headers=_auth_headers(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MISSING_EXCHANGE_RATE"


@pytest.mark.asyncio
async def test_balance_history_uses_dated_exchange_rates(
    auth_client: AsyncClient,
    application,
) -> None:
    token = await _register_token(auth_client, "analytics-fx-balance")
    eur_account = await _create_account(
        auth_client,
        token,
        name="EUR History",
        currency="EUR",
        opening_balance="0.0000",
    )
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )

    await _seed_exchange_rate_for_tests(
        application,
        base_currency="EUR",
        quote_currency="USD",
        rate="1.00000000",
        rate_date=date(2026, 1, 1),
    )
    await _seed_exchange_rate_for_tests(
        application,
        base_currency="EUR",
        quote_currency="USD",
        rate="2.00000000",
        rate_date=date(2026, 1, 10),
    )
    await _create_income(
        auth_client,
        token,
        account_id=eur_account,
        category_id=salary,
        amount="100.0000",
        transaction_date="2026-01-05",
        currency="EUR",
    )

    # Opening balance before 2026-01-10 must convert the Jan 5 income at rate 1.0,
    # not the later rate 2.0 that applies from Jan 10.
    response = await auth_client.get(
        (
            f"{API}/balance-over-time?period=custom"
            "&date_from=2026-01-10&date_to=2026-01-10&reporting_currency=USD"
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["opening_balance"] == "100.0000"
    assert body["closing_balance"] == "100.0000"


@pytest.mark.asyncio
async def test_period_comparison_current_month_uses_previous_calendar_month(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "analytics-cal-compare")
    account = await _create_account(auth_client, token, name="Calendar Compare")
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )

    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="300.0000",
        transaction_date="2026-02-15",
    )
    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="100.0000",
        transaction_date="2026-03-10",
    )
    # Equal-length preceding window for Mar 1-15 would include late February only
    # partially; calendar previous month must include all of February.
    await _create_income(
        auth_client,
        token,
        account_id=account,
        category_id=salary,
        amount="50.0000",
        transaction_date="2026-02-01",
    )

    response = await auth_client.get(
        f"{API}/period-comparison?period=current_month&as_of_date=2026-03-15",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["previous_period"]["start_date"] == "2026-02-01"
    assert body["previous_period"]["end_date"] == "2026-02-28"
    assert body["income"]["current"] == "100.0000"
    assert body["income"]["previous"] == "350.0000"


@pytest.mark.asyncio
async def test_largest_expenses_ranked_by_reporting_amount(
    auth_client: AsyncClient,
    application,
) -> None:
    token = await _register_token(auth_client, "analytics-rank-fx")
    usd_account = await _create_account(
        auth_client,
        token,
        name="USD Rank",
        currency="USD",
        opening_balance="0.0000",
    )
    eur_account = await _create_account(
        auth_client,
        token,
        name="EUR Rank",
        currency="EUR",
        opening_balance="0.0000",
    )
    shopping = await _category_id(
        auth_client,
        token,
        name="Shopping",
        category_type="expense",
    )
    await _seed_exchange_rate_for_tests(
        application,
        base_currency="EUR",
        quote_currency="USD",
        rate="2.00000000",
        rate_date=date(2026, 12, 1),
    )
    await _create_expense(
        auth_client,
        token,
        account_id=usd_account,
        category_id=shopping,
        amount="150.0000",
        transaction_date="2026-12-02",
        currency="USD",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=eur_account,
        category_id=shopping,
        amount="100.0000",
        transaction_date="2026-12-03",
        currency="EUR",
    )

    response = await auth_client.get(
        (
            f"{API}/largest-expenses?period=custom"
            "&date_from=2026-12-01&date_to=2026-12-31"
            "&reporting_currency=USD&limit=1"
        ),
        headers=_auth_headers(token),
    )
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["currency"] == "EUR"
    assert item["reporting_amount"] == "200.0000"


@pytest.mark.asyncio
async def test_soft_deleted_transactions_excluded(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "analytics-deleted")
    account = await _create_account(auth_client, token, name="Delete Account")
    salary = await _category_id(
        auth_client,
        token,
        name="Salary",
        category_type="income",
    )
    create_response = await auth_client.post(
        TRANSACTIONS_API,
        json={
            "account_id": account,
            "category_id": salary,
            "transaction_type": "income",
            "amount": "250.0000",
            "currency": "USD",
            "description": "To delete",
            "transaction_date": "2026-01-20",
        },
        headers=_auth_headers(token),
    )
    assert create_response.status_code == 201
    transaction_id = create_response.json()["id"]

    delete_response = await auth_client.delete(
        f"{TRANSACTIONS_API}/{transaction_id}",
        headers=_auth_headers(token),
    )
    assert delete_response.status_code == 204

    response = await auth_client.get(
        f"{API}/income-vs-expenses?period=custom&date_from=2026-01-01&date_to=2026-01-31",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["income"] == "0.0000"


@pytest.mark.asyncio
async def test_spending_trends_exclude_transfers(
    auth_client: AsyncClient,
) -> None:
    token = await _register_token(auth_client, "analytics-trends-xfer")
    checking = await _create_account(auth_client, token, name="Trend Checking")
    savings = await _create_account(auth_client, token, name="Trend Savings")
    food = await _category_id(
        auth_client,
        token,
        name="Food",
        category_type="expense",
    )
    await _create_expense(
        auth_client,
        token,
        account_id=checking,
        category_id=food,
        amount="25.0000",
        transaction_date="2026-01-05",
    )
    transfer_response = await auth_client.post(
        TRANSFERS_API,
        json={
            "source_account_id": checking,
            "destination_account_id": savings,
            "source_amount": "400.0000",
            "destination_amount": "400.0000",
            "transaction_date": "2026-01-06",
        },
        headers=_auth_headers(token),
    )
    assert transfer_response.status_code == 201

    response = await auth_client.get(
        f"{API}/spending-trends?period=custom&date_from=2026-01-01&date_to=2026-01-31",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_expenses"] == "25.0000"
