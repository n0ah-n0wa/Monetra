# Monetra

Production-oriented personal finance platform.

Monetra helps individuals track income and expenses, manage accounts, budgets, and goals, and analyze cash flow through a versioned REST API and a modern React frontend.

> **Status:** Repository foundation is in place. Application features are not implemented yet. See `SPECIFICATIONS.md` for the full product and engineering specification.

## Technology stack

| Layer | Stack |
|-------|--------|
| Backend | Python 3.13+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, PostgreSQL, psycopg |
| Frontend | React, TypeScript, Vite, TanStack Query, React Hook Form, Zod, React Router |
| Infra | Docker, Docker Compose, Nginx, GitHub Actions, AWS EC2 (deployment target) |

## Repository structure

```text
backend/          FastAPI application, Alembic, tests
frontend/         React + Vite application and tests
nginx/            Reverse proxy configuration
docker/           Shared container assets
docs/             Architecture and ADRs
scripts/          Development helpers
.github/workflows CI pipeline
```

## Prerequisites

- Docker and Docker Compose
- Python 3.13+ (for local backend tooling)
- Node.js 22+ (for local frontend tooling)

## Quick start

```bash
cp .env.example .env
docker compose up --build -d
cd frontend && npm install && npm run dev
```

Default development topology:

| Service | How it runs | URL |
|---------|-------------|-----|
| PostgreSQL | Docker | `localhost:5432` |
| Backend API | Docker | http://localhost:8000 |
| Nginx | Docker | http://localhost |
| Frontend (Vite) | Host process | http://localhost:5173 |

Nginx proxies `/`, `/api`, `/health`, and `/ready`. Open http://localhost once Vite is running.

Optional fully containerized frontend (Linux / CI-friendly npm TLS):

```bash
docker compose --profile frontend up --build
```

Then set `nginx/conf.d/default.conf` upstream `monetra_frontend` to `frontend:5173` if you want Nginx to reach the container instead of the host.

## Services

| Service | URL |
|---------|-----|
| App via Nginx | http://localhost |
| Frontend (Vite) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Ready | http://localhost:8000/ready |
| PostgreSQL | localhost:5432 |

## Local development (without full Compose)

```bash
cp .env.example .env

# Terminal 1 — database
docker compose up postgres -d

# Terminal 2 — backend
cd backend
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Terminal 3 — frontend
cd frontend
npm install
npm run dev
```

## Quality gate

```bash
make verify
# Windows: .\scripts\dev.ps1 verify
# Unix:    ./scripts/dev.sh verify
```

This runs lint, typecheck, unit tests, frontend build, and Docker image builds.

## Documentation

- [SPECIFICATIONS.md](./SPECIFICATIONS.md) — authoritative product & engineering spec
- [AGENTS.md](./AGENTS.md) — AI agent development rules
- [docs/architecture.md](./docs/architecture.md) — architecture overview
- [docs/development.md](./docs/development.md) — development workflow
- [docs/adr/](./docs/adr/) — architecture decision records

## License

Proprietary / portfolio project — rights reserved by the author unless otherwise stated.
