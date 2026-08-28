"""CLI entrypoint for Monetra API load tests."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict

from loadtest.client import LoadTestClient
from loadtest.config import LoadTestConfig
from loadtest.scenarios import (
    run_auth_scenario,
    run_budget_analytics_scenario,
    run_dashboard_analytics_scenario,
    run_transaction_create_scenario,
    run_transaction_list_scenario,
)
from loadtest.seed import resolve_seed_context, seed_loadtest_data
from loadtest.stats import RequestResult, format_stats_table, summarize_scenario


async def _health_check(client: LoadTestClient) -> None:
    result = await client.request(
        scenario="health",
        method="GET",
        path="/health",
    )
    if not result.success:
        msg = (
            f"API health check failed ({result.status_code}): "
            f"{result.error or 'unknown error'}"
        )
        raise RuntimeError(msg)


async def run_load_tests(
    config: LoadTestConfig,
    *,
    seed_only: bool,
    skip_seed: bool,
    quick_seed: bool,
) -> int:
    if quick_seed:
        config = LoadTestConfig(
            base_url=config.base_url,
            email=config.email,
            password=config.password,
            concurrency=config.concurrency,
            iterations=config.iterations,
            transaction_seed_count=min(config.transaction_seed_count, 200),
            budget_seed_count=min(config.budget_seed_count, 3),
            request_timeout_seconds=config.request_timeout_seconds,
        )

    client = LoadTestClient(config)
    try:
        await _health_check(client)
        token = await client.register()
        seed = None
        if not skip_seed:
            print(
                f"Seeding load-test data for {config.email} "
                f"(target {config.transaction_seed_count} transactions)...",
            )
            seed = await seed_loadtest_data(client, config, token=token)
            print(
                f"Seed complete: account={seed.account_id}, "
                f"transactions={seed.existing_transactions}",
            )
            if seed_only:
                return 0
        else:
            seed = await resolve_seed_context(client, token)

        print(f"Running scenarios against {config.base_url} ...")
        all_results: list[RequestResult] = []
        all_results.extend(await run_auth_scenario(client, config))
        token = await client.login()
        all_results.extend(
            await run_transaction_list_scenario(client, config, token=token),
        )
        all_results.extend(
            await run_transaction_create_scenario(
                client,
                config,
                token=token,
                seed=seed,
            ),
        )
        all_results.extend(
            await run_dashboard_analytics_scenario(client, config, token=token),
        )
        all_results.extend(
            await run_budget_analytics_scenario(client, config, token=token),
        )

        grouped: dict[str, list[RequestResult]] = defaultdict(list)
        for result in all_results:
            grouped[result.scenario].append(result)

        stats = [
            summarize_scenario(name, rows)
            for name, rows in sorted(grouped.items())
        ]
        print()
        print(format_stats_table(stats))
        print()
        print(
            "Notes: latencies are end-to-end HTTP times from this runner. "
            "Run against a dedicated local stack; do not use production.",
        )
        failures = sum(row.failures for row in stats)
        return 1 if failures else 0
    finally:
        await client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Monetra API load tests.")
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Only seed data; do not run scenarios.",
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Skip seeding (use existing load-test user data).",
    )
    parser.add_argument(
        "--quick-seed",
        action="store_true",
        help="Seed a smaller dataset for faster local runs.",
    )
    args = parser.parse_args(argv)
    config = LoadTestConfig.from_env()
    return asyncio.run(
        run_load_tests(
            config,
            seed_only=args.seed_only,
            skip_seed=args.skip_seed,
            quick_seed=args.quick_seed,
        ),
    )


if __name__ == "__main__":
    sys.exit(main())
