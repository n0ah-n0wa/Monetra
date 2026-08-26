# ADR 001: Backend layered architecture

## Status

Accepted

## Context

The specification requires explicit business logic, testability, and an API-first design without scattering financial rules across handlers and UI.

## Decision

Organize the FastAPI backend into clear layers:

- `api` — transport
- `services` — use-case orchestration
- `domain` — pure rules and financial calculations
- `repositories` — persistence
- `models` / `schemas` — ORM and I/O contracts

## Consequences

- Handlers stay thin.
- Domain logic can be unit-tested without HTTP or database.
- Duplication of financial rules between frontend and backend is avoided by keeping authoritative logic on the server.
