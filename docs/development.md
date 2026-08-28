# Development workflow

## Setup

1. Copy `.env.example` to `.env`.
2. Start infrastructure: `docker compose up --build -d` (Postgres, backend, Nginx).
3. Install frontend deps and run Vite on the host: `cd frontend && npm install && npm run dev`.
4. Optionally install backend tooling with `make install` / `.\scripts\dev.ps1 install`.

On Windows, the default Compose stack expects the Vite dev server on the host. Nginx reaches it via `host.docker.internal:5173`. Use `docker compose --profile frontend up` only in environments where `npm install` inside containers works reliably.

## Daily loop

1. Create a focused branch for one concern.
2. Implement the smallest coherent change.
3. Add or update tests.
4. Run `make lint`, `make typecheck`, and `make test` (or the PowerShell/Bash equivalents).
5. Open a pull request; GitHub Actions runs the CI quality gates.

## Backend notes

- Package managed via `backend/pyproject.toml`.
- Lint/format: Ruff
- Types: mypy (strict)
- Tests: pytest + pytest-asyncio + HTTPX ASGI transport
- Migrations: `alembic revision --autogenerate` / `alembic upgrade head`

## Frontend notes

- Package managed via `frontend/package.json`.
- Lint: ESLint; format: Prettier
- Types: `tsc -b`
- Unit tests: Vitest + Testing Library
- E2E: Playwright (critical journeys; smoke scaffold present)

## Definition of done

Follow `AGENTS.md` and section 74 of `SPECIFICATIONS.md`. Features are incomplete without tests, lint/type green status, and honest API/docs updates.

## Load testing

See [load-testing.md](./load-testing.md) for the local API load-test runner (`.\scripts\dev.ps1 loadtest`).
