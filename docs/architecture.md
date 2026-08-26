# Architecture overview

## High-level topology

```text
Browser
   ↓
Nginx (TLS termination in production)
   ↓
├── Frontend (React / Vite)
└── Backend (FastAPI)
         ↓
      PostgreSQL
```

## Backend layers

```text
api/           HTTP adapters, dependency injection, exception handlers
services/      Application orchestration
domain/        Pure financial and business rules; shared domain errors
repositories/  Persistence abstractions
models/        SQLAlchemy ORM models
schemas/       Pydantic request/response models (including ErrorResponse)
db/            Engine, sessions, declarative base
core/          Settings, logging, security helpers, middleware, exceptions
```

Cross-cutting foundation:

- Request correlation via `X-Request-ID` and structured logs (`request_id=…`)
- Centralized `AppError` → `{ "error": { "code", "message", "details" }, "request_id" }`
- Argon2id + JWT helpers in `core/security.py` (auth routes not implemented yet)
- Production settings reject default JWT secrets, `DEBUG=true`, and wildcard CORS

Health endpoints live at the application root:

- `GET /health` — process liveness
- `GET /ready` — dependency readiness (PostgreSQL)

Versioned business API routes mount under `/api/v1/`.

## Frontend organization

```text
src/
  api/         Central HTTP client and resource modules
  features/    Feature modules (auth, accounts, …)
  pages/       Route-level screens
  components/  Shared UI
  hooks/       Shared hooks
  lib/         Utilities (currency, dates, …)
  types/       Shared TypeScript types
```

Server state is managed with TanStack Query. Forms use React Hook Form + Zod.

## Configuration

All environment-specific values come from environment variables (see `.env.example`).

Development and production Compose files share the same service topology; differences are configuration, secrets, and image targets.

## Database changes

Schema evolves only through Alembic migrations. The application does not create or alter tables on startup.

## Related ADRs

See `docs/adr/` for recorded decisions as the system grows.
