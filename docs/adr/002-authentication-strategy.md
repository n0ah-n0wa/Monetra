# ADR 002: Authentication strategy

## Status

Accepted

## Context

Monetra requires secure user authentication for a browser-based SPA. The specification calls for:

- Stateless API suitable for horizontal scaling
- Protection against XSS token theft
- Refresh without re-entering credentials
- Server-side session revocation on logout

## Decision

Use a **dual-token** model:

1. **Access token** — short-lived JWT (default 15 minutes) returned in the JSON response body. The frontend stores it in memory (via React context / TanStack Query bootstrap) and sends it as `Authorization: Bearer <token>`.

2. **Refresh token** — long-lived opaque token (default 14 days) stored in an **HttpOnly, Secure (production), SameSite=Lax** cookie scoped to `/api/v1/auth`. The cookie is not accessible to JavaScript, reducing XSS exfiltration risk.

### Password storage

Passwords are hashed with **Argon2id** before persistence. Plain-text passwords are never stored.

### Token rotation

Each `POST /auth/refresh` call issues a new access token and rotates the refresh token. Old refresh tokens are invalidated server-side.

### Logout

`POST /auth/logout` revokes the refresh token in the database and clears the cookie.

### Password reset

Single-use tokens with expiry (`PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`). Rate limiting prevents abuse. Email delivery is abstracted behind `NotificationProvider`; production currently uses `NoOpNotificationProvider` (tokens created but not emailed).

## Consequences

### Positive

- SPA-friendly: access token in memory, refresh via cookie
- Refresh tokens survive page reload without localStorage
- Server can revoke sessions by invalidating refresh tokens
- Argon2id is memory-hard against offline cracking

### Negative

- CSRF on refresh/logout mitigated by SameSite cookies and same-site API origin in production
- Cross-origin SPA setups require careful CORS and cookie configuration
- JWT access tokens cannot be revoked before expiry without a denylist (acceptable given short TTL)

## Implementation references

- `backend/app/core/security.py` — hashing and JWT helpers
- `backend/app/api/v1/auth.py` — auth endpoints
- `backend/app/services/auth_service.py` — login, register, refresh, logout
- `frontend/src/api/client.ts` — token attachment and refresh interceptor
- `frontend/src/features/auth/context.tsx` — session state

## Related ADRs

- [ADR 001: Backend layered architecture](./001-backend-architecture.md)
- [ADR 006: Deployment strategy](./006-deployment-strategy.md) — TLS and secure cookies in production
