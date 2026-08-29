# Testing

Monetra uses layered automated testing: backend unit/integration tests, frontend unit tests, Playwright E2E, Docker build verification, and optional API load tests.

## Quick reference

| Layer | Location | Command |
|-------|----------|---------|
| Backend unit/integration | `backend/tests/` | `cd backend && pytest` |
| Frontend unit | `frontend/tests/` | `cd frontend && npm run test` |
| Frontend E2E | `frontend/e2e/` | `cd frontend && npm run test:e2e` |
| Accessibility unit | `frontend/tests/accessibility.test.tsx` | `cd frontend && npm run test:a11y` |
| Local quality gate | — | `make verify` or `.\scripts\dev.ps1 verify` |
| Load tests | `backend/loadtest/` | `.\scripts\dev.ps1 loadtest` |

## Local quality gate

From the repository root:

```bash
make verify
# Windows
.\scripts\dev.ps1 verify
# Unix
./scripts/dev.sh verify
```

`verify` runs:

1. Backend Ruff lint + format check
2. Frontend ESLint + Prettier check
3. Backend mypy
4. Frontend TypeScript (`tsc`)
5. Backend pytest
6. Frontend Vitest
7. Frontend production build (`vite build`)
8. Docker image builds (dev and production Compose files)

**E2E tests are not included in `verify`.** They run in CI and should be run locally before significant UI changes.

## Backend tests

```bash
cd backend
python -m pip install -e ".[dev]"
pytest                    # all tests
pytest tests/path/test.py # single file
pytest -k "test_name"     # by name
```

Requirements:

- PostgreSQL is **not** required for most unit tests (in-memory SQLite or mocks).
- Integration tests that need Postgres use the test database URL from CI or a local `DATABASE_URL` pointing at a test database.

Stack: **pytest**, **pytest-asyncio**, **httpx** ASGI transport for API tests.

```bash
cd backend && ruff check app tests && mypy app && pytest
```

## Frontend unit tests

```bash
cd frontend
npm install
npm run test          # single run
npm run test:watch    # watch mode
npm run test:a11y     # accessibility-focused tests only
```

Stack: **Vitest**, **Testing Library**, **jsdom**.

```bash
cd frontend && npm run lint && npm run typecheck && npm run test && npm run build
```

## End-to-end tests (Playwright)

E2E tests exercise real browser flows against a live backend and Vite dev server.

### Prerequisites

1. PostgreSQL running (e.g. `docker compose up postgres -d`)
2. Backend running on port 8000 with migrations applied
3. Playwright browsers installed

### Run locally

```bash
# Terminal 1 — backend
cd backend
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — E2E (starts Vite automatically via playwright.config.ts)
cd frontend
npx playwright install chromium   # first time only
$env:VITE_PROXY_TARGET='http://127.0.0.1:8000'   # PowerShell
$env:AUTH_RATE_LIMIT_MAX_REQUESTS='1000'
npm run test:e2e
```

On Unix:

```bash
VITE_PROXY_TARGET=http://127.0.0.1:8000 AUTH_RATE_LIMIT_MAX_REQUESTS=1000 npm run test:e2e
```

`playwright.config.ts` starts `npm run dev` on port 5173 and waits for the health endpoint.

### E2E coverage (22 tests)

| Spec | Coverage |
|------|----------|
| `auth.spec.ts` | Login, register, logout, session expiry |
| `accounts.spec.ts` | Account create and detail |
| `transactions.spec.ts` | Create, edit, filter |
| `transfers.spec.ts` | Transfer between accounts |
| `budgets.spec.ts` | Budget creation and utilization |
| `goals.spec.ts` | Goal creation |
| `categories.spec.ts` | Category CRUD |
| `dashboard.spec.ts` | Dashboard widgets |
| `import.spec.ts` | CSV import workflow |
| `export.spec.ts` | Transaction CSV export |
| `notifications.spec.ts` | Notification list and preferences |
| `a11y.spec.ts` | Landmarks, primary actions, dialog Escape |

Helpers: `frontend/e2e/helpers/` (`auth.ts`, `api.ts`, `ui.ts`).

### Debug E2E

```bash
cd frontend
npm run test:e2e:ui    # interactive Playwright UI
```

Failed CI runs upload `playwright-report/` as an artifact.

## CI pipeline

`.github/workflows/ci.yml` runs on every push and pull request:

| Job | What it runs |
|-----|--------------|
| `backend-lint` | `ruff check`, `ruff format --check` |
| `backend-typecheck` | `mypy app` |
| `backend-test` | `alembic upgrade head` + `pytest` (Postgres 16 service) |
| `frontend-lint` | `npm run lint` + `npm run format:check` |
| `frontend-typecheck` | `npm run typecheck` |
| `frontend-test` | `npm run test` (Vitest) |
| `frontend-build` | `npm run build` |
| `docker` | `docker compose build` + production image builds + non-root UID check |
| `e2e` | Migrate DB → start uvicorn → `npm run test:e2e` |
| `quality-gate` | Requires all jobs above |

E2E job environment variables match local requirements (`VITE_PROXY_TARGET`, `AUTH_RATE_LIMIT_MAX_REQUESTS=1000`).

## Load testing

Optional API load tests for local performance baselines:

```bash
.\scripts\dev.ps1 loadtest
# or
./scripts/dev.sh loadtest
```

Requires a running local stack. Configuration via `LOADTEST_*` variables in `.env.example`. Results and methodology: [load-testing.md](./load-testing.md).

## Pre-commit hooks

`.pre-commit-config.yaml` runs Ruff and Prettier on staged files:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Writing tests

Follow `AGENTS.md`:

- No fake production functionality — mocks belong in tests only
- Test meaningful behavior, not implementation details
- Frontend user-facing work needs loading, empty, and error state coverage
- API contract changes require doc updates in `docs/api-*.md`

## Related

- [troubleshooting.md](./troubleshooting.md) — test failures and environment issues
- [development.md](./development.md) — daily development workflow
