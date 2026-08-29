# Monetra backend

FastAPI application for the Monetra personal finance platform.

## Stack

- Python 3.13+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, PostgreSQL, psycopg 3
- Auth: Argon2id + JWT access tokens + HttpOnly refresh cookies
- Tests: pytest, pytest-asyncio, httpx

## Quick start

```bash
# From repository root
cp .env.example .env
docker compose up postgres -d

cd backend
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs (development): http://localhost:8000/docs

## Layout

```text
app/
  api/v1/       HTTP routers
  services/     Use-case orchestration
  domain/       Pure business rules
  repositories/ Persistence
  models/       SQLAlchemy ORM
  schemas/      Pydantic I/O
  core/         Config, security, middleware
  providers/    Exchange rates, notifications
alembic/        Database migrations
tests/          pytest suite
loadtest/       Optional API load tests
```

## Commands

```bash
cd backend
ruff check app tests && ruff format --check app tests  # lint
mypy app                                                # types
pytest                                                  # tests
alembic upgrade head                                    # migrate
```

## Documentation

- [../README.md](../README.md) — project overview
- [../docs/architecture.md](../docs/architecture.md) — system design
- [../docs/database.md](../docs/database.md) — schema and migrations
- [../docs/api-auth.md](../docs/api-auth.md) — authentication API
- [../docs/api-*.md](../docs/) — endpoint reference
- [../SPECIFICATIONS.md](../SPECIFICATIONS.md) — authoritative specification
