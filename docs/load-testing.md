# API load testing

Lightweight, local-only load tests for the Monetra API. The runner lives in `backend/loadtest/` and uses **httpx** with asyncio concurrency — no k6, Locust, or other distributed infrastructure.

## Goals

- Exercise representative user journeys under modest concurrent load.
- Measure end-to-end HTTP latency (p50 / p95 / p99).
- Document observed bottlenecks from measurements, not assumptions.
- Use realistic but **non-sensitive** synthetic data (`loadtest-user@example.com`).

## Prerequisites

1. Local stack running (`docker compose up -d` — Postgres + backend on port 8000).
2. Backend dependencies installed (`cd backend && pip install -e ".[dev]"`).
3. Auth rate limits relaxed for local runs (default in `docker-compose.yml`: `AUTH_RATE_LIMIT_MAX_REQUESTS=1000`).

**Never point load tests at production.**

## Quick start

```powershell
# From repo root (seeds ~200 transactions, then runs scenarios)
.\scripts\dev.ps1 loadtest

# Bash
./scripts/dev.sh loadtest
```

Or directly:

```bash
cd backend
python -m loadtest --quick-seed      # seed + run (faster dataset)
python -m loadtest --skip-seed       # run only (existing seed data)
python -m loadtest --seed-only       # seed only
```

Full dataset (default 1,200 transactions) — expect several minutes of seeding via individual POSTs:

```bash
cd backend
python -m loadtest
```

## Configuration

Environment variables (see `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOADTEST_BASE_URL` | `http://127.0.0.1:8000` | API base URL |
| `LOADTEST_EMAIL` | `loadtest-user@example.com` | Dedicated test user |
| `LOADTEST_PASSWORD` | `LoadTest1!` | Test password |
| `LOADTEST_CONCURRENCY` | `8` | Max concurrent workers per scenario |
| `LOADTEST_ITERATIONS` | `40` | Requests per scenario (dashboard fires 5 endpoints per iteration) |
| `LOADTEST_TRANSACTION_COUNT` | `1200` | Target seeded transactions |
| `LOADTEST_BUDGET_COUNT` | `5` | Budgets to create during seed |
| `LOADTEST_REQUEST_TIMEOUT_SECONDS` | `30` | Per-request timeout |

## Scenarios

| Scenario | Endpoint(s) | Concurrency cap | Notes |
|----------|-------------|-----------------|-------|
| `auth_login` | `POST /api/v1/auth/login` | 5 | Respects auth rate limits |
| `transaction_list` | `GET /api/v1/transactions` (page 1, 20 items) | config | Typical list view |
| `transaction_create` | `POST /api/v1/transactions` | 4, max 20 iterations | Write path; creates real rows |
| `dashboard_analytics` | 5 analytics GETs per iteration | config | Mirrors dashboard fan-out |
| `budget_analytics` | `GET /api/v1/budgets/analytics/utilization` | config | Budget utilization rollup |

Seed data: one checking account, expense categories, monthly budgets (overall + category-scoped), and transactions spread over the past 365 days with varied amounts and descriptions.

## Methodology

- **Runner**: single process, asyncio semaphore for concurrency.
- **Metrics**: wall-clock HTTP round-trip per request, aggregated per scenario.
- **Warm-up**: first full run includes seeding; use `--skip-seed` for steady-state measurements.
- **Hardware**: results below are from a single developer machine against Docker Compose (Postgres 16 + uvicorn backend). Treat absolute numbers as directional; compare before/after on the same host.

## Observed performance (2026-08-28)

Environment: Windows host, Docker Compose, backend healthy on `127.0.0.1:8000`, **220 transactions** after quick seed + one create scenario run, **8 concurrent workers**, **40 iterations** (20 for creates).

### Steady state (`python -m loadtest --skip-seed`)

| Scenario | OK | Fail | p50 | p95 | p99 | max |
|----------|-----|------|-----|-----|-----|-----|
| auth_login | 40 | 0 | 1044 ms | 1517 ms | 1607 ms | 1659 ms |
| transaction_list | 40 | 0 | 159 ms | 284 ms | 297 ms | 298 ms |
| transaction_create | 20 | 0 | 239 ms | 837 ms | 851 ms | 855 ms |
| dashboard_analytics | 200 | 0 | 93 ms | 262 ms | 331 ms | 448 ms |
| budget_analytics | 40 | 0 | 125 ms | 232 ms | 242 ms | 247 ms |

All scenarios completed with **0 failures**.

### Cold / concurrent seed run (`python -m loadtest --quick-seed`, includes seeding)

| Scenario | p50 | p95 | p99 |
|----------|-----|-----|-----|
| auth_login | 695 ms | 924 ms | 927 ms |
| transaction_list | 100 ms | 178 ms | 190 ms |
| transaction_create | 241 ms | 757 ms | 1180 ms |
| dashboard_analytics | 169 ms | 349 ms | 468 ms |
| budget_analytics | 257 ms | 426 ms | 450 ms |

Seed phase for 200 transactions took ~25 s (one HTTP POST per transaction).

## Identified bottlenecks

Based on the measurements above (not speculative optimization):

1. **Authentication (`auth_login`)** — Dominant latency (p50 ~1 s, p95 ~1.5 s). Argon2 password verification is intentionally expensive; this is expected security cost, not a database issue.
2. **Transaction creation (`transaction_create`)** — Higher tail latency (p95 ~800 ms) than reads. Each create triggers balance updates and downstream budget/notification evaluation; variance increases under concurrent writes.
3. **Dashboard analytics (`dashboard_analytics`)** — Five parallel aggregation queries per “page load”. Individual endpoints are fast (p50 ~93 ms) but fan-out multiplies perceived load time; slowest endpoint in a batch drives UX.
4. **Budget analytics** — Moderate (p95 ~230 ms steady state). Scales with active budgets and transaction volume in the period.
5. **Transaction listing** — Acceptable for 200+ rows (p95 ~280 ms with pagination). Not the primary bottleneck at this data size.
6. **Seeding** — One POST per transaction is slow for large datasets; use `--quick-seed` for routine runs or `--seed-only` once, then `--skip-seed`.

## What we are not doing (yet)

- No Redis, read replicas, or horizontal scaling — premature for current measured latencies on read paths.
- No code changes driven solely by these numbers; auth cost is by design.
- No CI gate on latency (environment-dependent); unit tests for stats live in `backend/tests/loadtest/`.

## Re-running after changes

1. Seed once: `python -m loadtest --quick-seed --seed-only`
2. Measure: `python -m loadtest --skip-seed`
3. Compare the scenario table; investigate regressions >20% on the same machine before optimizing.

## Related docs

- [Development workflow](./development.md)
- [API analytics](./api-analytics.md)
- [API budgets](./api-budgets.md)
