# Development workflow

## Setup

1. Copy `.env.example` to `.env`.
2. Start infrastructure: `docker compose up --build -d` (Postgres, backend, Nginx).
3. Install frontend deps and run Vite on the host: `cd frontend && npm install && npm run dev`.
4. Optionally install backend tooling: `make install` or `.\scripts\dev.ps1 install`.

On Windows, the default Compose stack expects the Vite dev server on the host. Nginx reaches it via `host.docker.internal:5173`. Use `docker compose --profile frontend up` only in environments where `npm install` inside containers works reliably.

Apply database migrations after first clone:

```bash
cd backend && alembic upgrade head
```

## Daily loop

1. Create a focused branch for one concern.
2. Implement the smallest coherent change.
3. Add or update tests for meaningful behavior.
4. Run `make lint`, `make typecheck`, and `make test` (or PowerShell/Bash equivalents).
5. For UI changes, run `cd frontend && npm run test:e2e` (requires backend on port 8000).
6. Open a pull request; GitHub Actions runs the full CI pipeline including E2E.

## Backend notes

- Package: `backend/pyproject.toml` (Python ≥ 3.13)
- Lint/format: Ruff (`ruff check`, `ruff format`)
- Types: mypy (strict on `app/`)
- Tests: pytest + pytest-asyncio
- Migrations: Alembic in `backend/alembic/`

```bash
cd backend
ruff check app tests && ruff format --check app tests
mypy app
pytest
```

Create a migration after model changes:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
# Review generated file, then:
alembic upgrade head
```

## Frontend notes

- Package: `frontend/package.json` (Node 22+)
- Lint: ESLint; format: Prettier
- Types: `tsc` via `npm run typecheck`
- Unit tests: Vitest + Testing Library (`npm run test`)
- E2E: Playwright — 22 specs in `frontend/e2e/` (`npm run test:e2e`)
- Accessibility unit tests: `npm run test:a11y`

```bash
cd frontend
npm run lint && npm run format:check
npm run typecheck
npm run test
npm run build
```

Feature code lives under `frontend/src/features/`. Shared UI in `frontend/src/components/`.

## Scripts

Cross-platform helpers in `scripts/`:

| Command | PowerShell | Bash |
|---------|------------|------|
| Install deps | `.\scripts\dev.ps1 install` | `./scripts/dev.sh install` |
| Start stack | `.\scripts\dev.ps1 up` | `./scripts/dev.sh up` |
| Lint | `.\scripts\dev.ps1 lint` | `./scripts/dev.sh lint` |
| Typecheck | `.\scripts\dev.ps1 typecheck` | `./scripts/dev.sh typecheck` |
| Unit tests | `.\scripts\dev.ps1 test` | `./scripts/dev.sh test` |
| Quality gate | `.\scripts\dev.ps1 verify` | `./scripts/dev.sh verify` |
| Load tests | `.\scripts\dev.ps1 loadtest` | `./scripts/dev.sh loadtest` |
| Prod-shaped test | `.\scripts\dev.ps1 prod-verify` | `./scripts/dev.sh prod-verify` |
| Backup drill | `.\scripts\dev.ps1 backup-restore-test` | `./scripts/dev.sh backup-restore-test` |

`make verify` mirrors `dev.ps1 verify` (lint, typecheck, unit tests, build, Docker builds).

## Definition of done

Follow `AGENTS.md` and section 74 of `SPECIFICATIONS.md`. A feature is incomplete without:

- tests for meaningful behavior;
- lint and typecheck passing;
- honest documentation updates when API contracts or behavior change;
- frontend loading, empty, and error states for user-facing work;
- Alembic migration when schema changes.

## Load testing

See [load-testing.md](./load-testing.md) for the local API load-test runner.

## Related documentation

| Document | Topic |
|----------|-------|
| [testing.md](./testing.md) | Full testing guide (unit, E2E, CI) |
| [troubleshooting.md](./troubleshooting.md) | Common issues |
| [architecture.md](./architecture.md) | System design |
| [database.md](./database.md) | Schema and migrations |
| [api-auth.md](./api-auth.md) | Authentication API |
