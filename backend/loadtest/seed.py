"""Seed realistic non-sensitive data for API load tests."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import httpx

from loadtest.client import LoadTestClient
from loadtest.config import LoadTestConfig


@dataclass(frozen=True, slots=True)
class SeedContext:
    account_id: str
    category_id: str
    existing_transactions: int


async def _ensure_account(client: LoadTestClient, token: str) -> str:
    accounts = await client.get_json("/api/v1/accounts", token=token)
    items = accounts.get("items", [])
    if isinstance(items, list) and items:
        return str(items[0]["id"])
    created = await client.post_json(
        "/api/v1/accounts",
        token=token,
        json={
            "name": "Load Test Checking",
            "account_type": "bank",
            "currency": "USD",
            "opening_balance": "5000.0000",
        },
    )
    return str(created["id"])


async def _pick_expense_category(client: LoadTestClient, token: str) -> str:
    categories = await client.get_json(
        "/api/v1/categories",
        token=token,
        params={"status": "active", "page_size": 100, "include_system": True},
    )
    items = categories.get("items", [])
    if not isinstance(items, list):
        msg = "Unexpected categories response"
        raise TypeError(msg)
    for item in items:
        if item.get("category_type") in {"expense", "universal"}:
            return str(item["id"])
    msg = "No expense category available for load test seed"
    raise RuntimeError(msg)


async def _seed_budgets(
    client: LoadTestClient,
    token: str,
    *,
    count: int,
    category_id: str,
) -> None:
    today = date.today()
    start = today.replace(day=1)
    for index in range(count):
        payload: dict[str, Any] = {
            "name": f"Load budget {index + 1}",
            "amount": "500.0000",
            "currency": "USD",
            "period": "monthly",
            "scope": "overall" if index % 2 == 0 else "category",
            "start_date": start.isoformat(),
            "warning_threshold_percent": 80,
        }
        if payload["scope"] == "category":
            payload["category_ids"] = [category_id]
        try:
            await client.post_json("/api/v1/budgets", token=token, json=payload)
        except httpx.HTTPStatusError:
            continue


async def _count_transactions(client: LoadTestClient, token: str) -> int:
    payload = await client.get_json(
        "/api/v1/transactions",
        token=token,
        params={"page": 1, "page_size": 1},
    )
    return int(payload.get("total_items", 0))


async def _seed_transactions(
    client: LoadTestClient,
    token: str,
    *,
    account_id: str,
    category_id: str,
    target_count: int,
) -> None:
    existing = await _count_transactions(client, token)
    if existing >= target_count:
        return

    today = date.today()
    rng = random.Random(42)  # noqa: S311
    descriptions = [
        "Grocery run",
        "Coffee shop",
        "Utility bill",
        "Fuel",
        "Pharmacy",
        "Restaurant",
        "Online subscription",
        "Transit fare",
    ]

    to_create = target_count - existing
    for offset in range(to_create):
        days_ago = rng.randint(0, 364)
        txn_date = today - timedelta(days=days_ago)
        amount = Decimal(rng.randint(500, 25000)) / Decimal("100")
        await client.post_json(
            "/api/v1/transactions",
            token=token,
            json={
                "account_id": account_id,
                "category_id": category_id,
                "transaction_type": "expense",
                "amount": format(amount, "f"),
                "description": f"{rng.choice(descriptions)} #{offset}",
                "transaction_date": txn_date.isoformat(),
            },
        )


async def resolve_seed_context(
    client: LoadTestClient,
    token: str,
) -> SeedContext:
    account_id = await _ensure_account(client, token)
    category_id = await _pick_expense_category(client, token)
    total = await _count_transactions(client, token)
    return SeedContext(
        account_id=account_id,
        category_id=category_id,
        existing_transactions=total,
    )


async def seed_loadtest_data(
    client: LoadTestClient,
    config: LoadTestConfig,
    *,
    token: str | None = None,
) -> SeedContext:
    """Ensure a load-test user has representative finance data."""
    access_token = token or await client.register()
    account_id = await _ensure_account(client, access_token)
    category_id = await _pick_expense_category(client, access_token)
    await _seed_budgets(
        client,
        access_token,
        count=config.budget_seed_count,
        category_id=category_id,
    )
    await _seed_transactions(
        client,
        access_token,
        account_id=account_id,
        category_id=category_id,
        target_count=config.transaction_seed_count,
    )
    total = await _count_transactions(client, access_token)
    return SeedContext(
        account_id=account_id,
        category_id=category_id,
        existing_transactions=total,
    )
