# Authentication API

Authenticated endpoints use a **JWT bearer access token** in the `Authorization` header. **Refresh tokens** are stored in an **HttpOnly cookie** and rotated on refresh.

Base path: `/api/v1/auth`

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/register` | No | Create account; returns access token |
| `POST` | `/login` | No | Authenticate; returns access token; sets refresh cookie |
| `POST` | `/refresh` | Cookie | Issue new access token from refresh cookie |
| `POST` | `/logout` | Cookie | Revoke refresh session; clear cookie |
| `POST` | `/password-reset/request` | No | Request password reset (rate limited) |
| `POST` | `/password-reset/confirm` | No | Set new password with reset token |

## Registration

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass1"
}
```

Response (`201`):

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

Password policy (enforced server-side):

- Minimum 8 characters
- At least one letter
- At least one digit

Configurable via `AUTH_PASSWORD_*` environment variables.

## Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass1"
}
```

Response (`200`): same token shape as registration.

Additionally sets an HttpOnly cookie:

| Cookie | Default name | Path |
|--------|--------------|------|
| Refresh token | `monetra_refresh_token` | `/api/v1/auth` |

Cookie attributes are configured via `REFRESH_TOKEN_COOKIE_*` variables. Production requires `REFRESH_TOKEN_COOKIE_SECURE=true`.

## Using the access token

```http
GET /api/v1/users/me
Authorization: Bearer eyJ...
```

Access tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 15). The frontend API client (`frontend/src/api/client.ts`) attaches the token and handles `401` by attempting refresh.

## Refresh

```http
POST /api/v1/auth/refresh
Cookie: monetra_refresh_token=...
```

Returns a new access token. The refresh cookie is rotated. No request body required.

## Logout

```http
POST /api/v1/auth/logout
Cookie: monetra_refresh_token=...
```

Revokes the refresh token server-side and clears the cookie.

## Password reset

### Request

```http
POST /api/v1/auth/password-reset/request
Content-Type: application/json

{ "email": "user@example.com" }
```

Always returns `200` with a generic message (no email enumeration). Rate limited per IP and per email (`PASSWORD_RESET_EMAIL_RATE_LIMIT_*`, `PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS`).

**Note:** Email delivery is not implemented in production. Tokens are created and can be used via API; outbound email is logged only (`NoOpNotificationProvider`).

### Confirm

```http
POST /api/v1/auth/password-reset/confirm
Content-Type: application/json

{
  "token": "reset-token-from-email-or-admin",
  "new_password": "NewSecure1"
}
```

## Error responses

All errors use the standard shape:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password.",
    "details": {}
  },
  "request_id": "..."
}
```

Common auth error codes:

| Code | HTTP | Meaning |
|------|------|---------|
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `INVALID_TOKEN` | 401 | Expired or malformed JWT |
| `EMAIL_ALREADY_REGISTERED` | 409 | Duplicate registration |
| `WEAK_PASSWORD` | 422 | Password policy violation |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many auth attempts |

## Security implementation

| Concern | Implementation |
|---------|----------------|
| Password hashing | Argon2id (`backend/app/core/security.py`) |
| Access tokens | JWT (HS256 by default) |
| Refresh tokens | Opaque tokens, hashed at rest |
| Rate limiting | `AUTH_RATE_LIMIT_*` on login/register |
| Production hardening | Rejects default JWT secret, requires secure cookies |

See [ADR 002](./adr/002-authentication-strategy.md).

## Frontend integration

- `frontend/src/features/auth/` — login, register, password reset pages
- `frontend/src/features/auth/context.tsx` — session bootstrap via `/users/me` and refresh
- `frontend/src/components/routing/ProtectedRoute.tsx` — redirects unauthenticated users to `/login`

## Related

- [api-accounts-categories.md](./api-accounts-categories.md) — resources requiring authentication
- [deployment/configuration.md](./deployment/configuration.md) — JWT and cookie env vars
