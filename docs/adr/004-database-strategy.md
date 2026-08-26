# ADR 004: Database strategy

## Status

Accepted

## Context

PostgreSQL is the system of record. Schema drift and silent auto-create are unacceptable for a financial ledger.

## Decision

- PostgreSQL is authoritative.
- Alembic owns all schema changes.
- Application startup never mutates schema.
- Development may run Postgres in Docker; production remains compatible with Amazon RDS.

## Consequences

- Every model change needs a migration.
- CI and deploy pipelines must apply migrations explicitly.
