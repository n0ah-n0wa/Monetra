# ADR 005: Frontend state management

## Status

Accepted

## Context

The UI primarily displays and mutates server-owned financial data.

## Decision

- Use TanStack Query for server state.
- Avoid a large global client store for remote data.
- Keep form state in React Hook Form with Zod schemas.
- Centralize HTTP in `src/api`.

## Consequences

- Features organize around queries/mutations rather than Redux-style stores.
- Auth token refresh and error handling belong in the API client, not page components.
