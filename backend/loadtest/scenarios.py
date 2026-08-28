"""Representative API load-test scenarios."""

from __future__ import annotations

import asyncio
import uuid
from datetime import date
from typing import Any

from loadtest.client import LoadTestClient
from loadtest.config import LoadTestConfig
from loadtest.seed import SeedContext
from loadtest.stats import RequestResult

DASHBOARD_ANALYTICS_PATHS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("/api/v1/analytics/income-vs-expenses", {"period": "current_month"}),
    ("/api/v1/analytics/net-cash-flow", {"period": "current_month"}),
    ("/api/v1/analytics/balance-over-time", {"period": "current_month"}),
    ("/api/v1/analytics/savings-rate", {"period": "current_month"}),
    ("/api/v1/analytics/spending-by-category", {"period": "current_month"}),
)


async def _run_concurrent(
    *,
    concurrency: int,
    iterations: int,
    worker,
) -> list[RequestResult]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[RequestResult] = []

    async def guarded(index: int) -> None:
        async with semaphore:
            outcome = await worker(index)
            if isinstance(outcome, list):
                results.extend(outcome)
            else:
                results.append(outcome)

    await asyncio.gather(*(guarded(index) for index in range(iterations)))
    return results


async def run_auth_scenario(
    client: LoadTestClient,
    config: LoadTestConfig,
) -> list[RequestResult]:
    async def worker(_: int) -> RequestResult:
        return await client.request(
            scenario="auth_login",
            method="POST",
            path="/api/v1/auth/login",
            json={"email": config.email, "password": config.password},
        )

    return await _run_concurrent(
        concurrency=min(config.concurrency, 5),
        iterations=config.iterations,
        worker=worker,
    )


async def run_transaction_list_scenario(
    client: LoadTestClient,
    config: LoadTestConfig,
    *,
    token: str,
) -> list[RequestResult]:
    async def worker(_: int) -> RequestResult:
        return await client.request(
            scenario="transaction_list",
            method="GET",
            path="/api/v1/transactions",
            token=token,
            params={"page": 1, "page_size": 20, "sort": "transaction_date:desc"},
        )

    return await _run_concurrent(
        concurrency=config.concurrency,
        iterations=config.iterations,
        worker=worker,
    )


async def run_transaction_create_scenario(
    client: LoadTestClient,
    config: LoadTestConfig,
    *,
    token: str,
    seed: SeedContext,
) -> list[RequestResult]:
    async def worker(index: int) -> RequestResult:
        return await client.request(
            scenario="transaction_create",
            method="POST",
            path="/api/v1/transactions",
            token=token,
            json={
                "account_id": seed.account_id,
                "category_id": seed.category_id,
                "transaction_type": "expense",
                "amount": "12.3400",
                "description": f"Load test expense {index}-{uuid.uuid4().hex[:8]}",
                "transaction_date": date.today().isoformat(),
            },
        )

    return await _run_concurrent(
        concurrency=min(config.concurrency, 4),
        iterations=min(config.iterations, 20),
        worker=worker,
    )


async def run_dashboard_analytics_scenario(
    client: LoadTestClient,
    config: LoadTestConfig,
    *,
    token: str,
) -> list[RequestResult]:
    async def worker(_: int) -> list[RequestResult]:
        batch: list[RequestResult] = []
        for path, params in DASHBOARD_ANALYTICS_PATHS:
            batch.append(
                await client.request(
                    scenario="dashboard_analytics",
                    method="GET",
                    path=path,
                    token=token,
                    params=params,
                ),
            )
        return batch

    return await _run_concurrent(
        concurrency=config.concurrency,
        iterations=config.iterations,
        worker=worker,
    )


async def run_budget_analytics_scenario(
    client: LoadTestClient,
    config: LoadTestConfig,
    *,
    token: str,
) -> list[RequestResult]:
    async def worker(_: int) -> RequestResult:
        return await client.request(
            scenario="budget_analytics",
            method="GET",
            path="/api/v1/budgets/analytics/utilization",
            token=token,
        )

    return await _run_concurrent(
        concurrency=config.concurrency,
        iterations=config.iterations,
        worker=worker,
    )
