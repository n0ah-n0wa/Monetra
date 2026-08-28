# Configuration and secrets

Monetra is configured entirely through environment variables. Production values live in a `.env` file on the EC2 host (or are injected from a secret store). **Never commit `.env` or TLS private keys to Git.**

## Production `.env` file

On the server:

```bash
cd /opt/monetra
cp .env.production.example .env
chmod 600 .env
```

Edit `.env` with your domain, secrets, and tuning values. `docker-compose.prod.yml` reads this file for Compose interpolation and passes it to the backend via `env_file`.

## Required variables

These must be set before `docker compose -f docker-compose.prod.yml up`:

| Variable | Example | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `monetra` | Database name |
| `POSTGRES_USER` | `monetra` | Database role |
| `POSTGRES_PASSWORD` | *(strong random)* | Database password; generate with `openssl rand -base64 32` |
| `JWT_SECRET_KEY` | *(≥ 32 chars)* | Signing key for access tokens; generate with `openssl rand -hex 32` |

Compose enforces `JWT_SECRET_KEY` at startup. The backend rejects the development default when `APP_ENV=production`.

## Domain and CORS

Set origins to your **public HTTPS URL(s)**. Do not use `*` in production.

```dotenv
CORS_ORIGINS=https://app.example.com
```

Multiple origins (e.g. apex + `www`) are comma-separated:

```dotenv
CORS_ORIGINS=https://app.example.com,https://www.example.com
```

Nginx uses the request `Host` header for redirects (`https://$host/...`). You do **not** need to hardcode the domain in Nginx config unless you want to restrict `server_name`:

```dotenv
NGINX_SERVER_NAME=app.example.com
```

Default `_` accepts any hostname that resolves to the server (useful behind a load balancer or for initial bring-up).

## Application settings (recommended production values)

| Variable | Production value | Notes |
|----------|------------------|-------|
| `APP_ENV` | `production` | Set by Compose for backend; keep in `.env` for clarity |
| `DEBUG` | `false` | Enforced in Compose |
| `LOG_FORMAT` | `json` | Structured logs for production |
| `LOG_LEVEL` | `INFO` | Use `WARNING` if volume is high |
| `TRUSTED_PROXY_COUNT` | `1` | One Nginx hop in front of the API |
| `RUN_DB_MIGRATIONS` | `true` | Run Alembic on backend container start |
| `ACCESS_LOG_ENABLED` | `true` | |
| `ACCESS_LOG_SKIP_PATHS` | `/health` | Reduces noise from probes |

## Nginx / TLS tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `NGINX_HTTP_PORT` | `80` | Host port mapped to Nginx HTTP listener |
| `NGINX_HTTPS_PORT` | `443` | Host port mapped to Nginx HTTPS listener |
| `NGINX_CLIENT_MAX_BODY_SIZE` | `10m` | Upload limit (align with `IMPORT_MAX_FILE_BYTES`) |
| `NGINX_HSTS_MAX_AGE` | `31536000` | HSTS max-age in seconds; set `0` to disable |
| `NGINX_CSP` | *(see entrypoint default)* | Override Content-Security-Policy if needed |

TLS certificate **files** are not environment variables. Mount PEM files at `nginx/certs/` (see [deploy.md](./deploy.md#https-tls)).

## Auth and rate limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_RATE_LIMIT_MAX_REQUESTS` | `10` | Auth endpoint rate limit per window |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | Refresh token TTL |

Production automatically sets `REFRESH_TOKEN_COOKIE_SECURE=true` when `APP_ENV=production`.

## Data import / export limits

| Variable | Default |
|----------|---------|
| `IMPORT_MAX_FILE_BYTES` | `5242880` (5 MiB) |
| `IMPORT_MAX_ROWS` | `10000` |
| `EXPORT_MAX_ROWS` | `10000` |

Ensure `NGINX_CLIENT_MAX_BODY_SIZE` ≥ import file limit.

## Exchange rates

| Variable | Production recommendation |
|----------|---------------------------|
| `EXCHANGE_RATE_PROVIDER` | `none` until an external provider is configured |
| `EXCHANGE_RATE_CACHE_TTL_SECONDS` | `300` |
| `EXCHANGE_RATE_ALLOW_STALE_ON_FAILURE` | `true` |

## Observability (optional)

| Variable | Description |
|----------|-------------|
| `OTEL_ENABLED` | `false` unless exporting traces |
| `OTEL_EXPORTER` | `otlp` when enabled |
| `SENTRY_DSN` | Error reporting endpoint |

## Variables set by Compose (do not override casually)

`docker-compose.prod.yml` sets these for the backend container:

```yaml
DATABASE_URL: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
APP_ENV: production
DEBUG: "false"
LOG_FORMAT: json
```

The hostname `postgres` is the Docker service name, not `localhost`.

## Secrets management

### Tier 1 — `.env` on the host (portfolio default)

Appropriate for a single EC2 deployment:

1. Generate secrets locally or on the server.
2. Store in `/opt/monetra/.env` with mode `600`.
3. Restrict SSH/SSM access to administrators only.
4. Back up `.env` securely (password manager or encrypted offline copy)—**not** in the Git repository.

```bash
openssl rand -base64 32   # POSTGRES_PASSWORD
openssl rand -hex 32      # JWT_SECRET_KEY
```

### Tier 2 — AWS Systems Manager Parameter Store

Store secrets as `SecureString` parameters:

```text
/monetra/prod/POSTGRES_PASSWORD
/monetra/prod/JWT_SECRET_KEY
```

Retrieve at deploy time and write `.env`, or use a small wrapper script:

```bash
export POSTGRES_PASSWORD="$(aws ssm get-parameter --name /monetra/prod/POSTGRES_PASSWORD --with-decryption --query Parameter.Value --output text)"
export JWT_SECRET_KEY="$(aws ssm get-parameter --name /monetra/prod/JWT_SECRET_KEY --with-decryption --query Parameter.Value --output text)"
```

The EC2 instance role needs `ssm:GetParameter` on those ARNs.

### Tier 3 — AWS Secrets Manager

Use when you need automatic rotation or audit trails. Same pattern: fetch at deploy time, never bake into images.

## What must never appear in images or Git

- `.env` with real values
- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- TLS private keys (`privkey.pem`)
- Database dumps containing user data (unless encrypted and access-controlled)

CI verifies production images do not contain `JWT_SECRET_KEY=change-me`.

## Rotating secrets

### JWT secret rotation

1. Generate a new `JWT_SECRET_KEY`.
2. Update `.env`.
3. `docker compose -f docker-compose.prod.yml up -d backend`
4. **All existing access tokens invalidate immediately.** Users must sign in again. Plan a maintenance window.

### Database password rotation

1. Change password inside PostgreSQL.
2. Update `POSTGRES_PASSWORD` and `DATABASE_URL` in `.env`.
3. Restart backend (and ensure postgres container env matches on next recreate).

For password changes on an existing volume, coordinate `ALTER USER` with Compose env updates.

## Complete template

Start from `.env.production.example` in the repository root. It lists all production-oriented variables with safe placeholders.
