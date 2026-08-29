# Troubleshooting

Common issues when developing, testing, or deploying Monetra. Commands assume repository root unless noted.

## Development setup

### `docker compose up` fails immediately

**Symptom:** Backend container exits; logs mention `JWT_SECRET_KEY` or database connection.

**Fix:**

1. Copy environment file: `cp .env.example .env`
2. Ensure `DATABASE_URL` matches Compose Postgres credentials (`monetra`/`monetra` by default)
3. Ensure `JWT_SECRET_KEY` is at least 32 characters

### Frontend cannot reach API (network errors in browser)

**Symptom:** Login or API calls fail with connection errors on http://localhost:5173.

**Fix:**

- Vite proxies `/api` to `VITE_PROXY_TARGET` (default `http://localhost:8000`). Ensure the backend is running.
- If backend runs in Docker on port 8000, `docker compose ps` should show `backend` healthy.
- Check `CORS_ORIGINS` includes `http://localhost:5173`.

### Nginx returns 502 for the frontend

**Symptom:** http://localhost loads but shows bad gateway.

**Fix:**

- Start Vite on the host: `cd frontend && npm run dev`
- Nginx expects Vite at `host.docker.internal:5173` (default dev config)
- On Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` to the nginx service if needed

### `alembic upgrade head` fails

**Symptom:** Connection refused or authentication failed.

**Fix:**

```bash
docker compose up postgres -d
# Wait for healthy, then:
cd backend && alembic upgrade head
```

Verify `DATABASE_URL` in `.env` uses `localhost:5432` when running Alembic from the host (not `postgres:5432`).

### npm install fails with TLS/certificate errors

**Symptom:** `UNABLE_TO_VERIFY_LEAF_SIGNATURE` on Windows corporate networks.

**Workarounds:**

- Run frontend on the host with system Node (recommended for Windows dev)
- Use `docker compose --profile frontend up` on Linux where container npm works
- Do **not** set `NODE_TLS_REJECT_UNAUTHORIZED=0` in production

## Testing

### Playwright E2E: port 5173 already in use

**Symptom:** `Error: http://localhost:5173 is already in use`

**Fix:** Stop the existing Vite or Playwright process, or set `reuseExistingServer: true` in `playwright.config.ts` for local runs (CI always starts fresh).

### Playwright E2E: modal clicks time out (`body intercepts pointer events`)

**Symptom:** Dialog buttons visible but not clickable in E2E.

**Cause:** Modal `inert` was applied to `#root` while the dialog rendered inside it.

**Fix:** Modals portal to `document.body` (`frontend/src/components/ui/Modal.tsx`). If this regresses, verify `createPortal` is used.

### Playwright strict mode: duplicate buttons

**Symptom:** `getByRole('button', { name: 'Add account' }) resolved to 2 elements`

**Cause:** Empty-state CTAs duplicate page-header actions.

**Fix:** Scope E2E selectors to `.page-header__actions` (see `frontend/e2e/helpers/ui.ts`).

### Backend tests fail on import

**Fix:**

```bash
cd backend
python -m pip install -e ".[dev]"
pytest
```

Ensure Python 3.13+.

## Production deployment

### `/ready` returns 503

**Symptom:** Health check passes but readiness fails.

**Fix:**

1. Check Postgres: `docker compose -f docker-compose.prod.yml logs postgres`
2. Verify `DATABASE_URL` inside the backend container points to the `postgres` service hostname
3. Run migrations: `docker compose -f docker-compose.prod.yml exec backend alembic upgrade head`

### TLS certificate errors

**Symptom:** Browser shows certificate warning; smoke tests fail.

**Fix:**

- Production: use Let's Encrypt or valid certs at `nginx/certs/fullchain.pem` and `privkey.pem`
- Local prod test: `./scripts/generate-local-tls-certs.sh` (self-signed; browser will warn)

Validate with:

```bash
./scripts/validate-production-env.sh
./scripts/smoke-production.sh
```

### `JWT_SECRET_KEY` rejected at startup

**Symptom:** Backend refuses to start in production.

**Fix:** Generate a strong key:

```bash
openssl rand -hex 32
```

Set in `.env`. The default `change-me-in-production-...` value is blocked when `APP_ENV=production`.

### CORS errors in production

**Fix:** Set `CORS_ORIGINS` to the exact public HTTPS origin(s):

```dotenv
CORS_ORIGINS=https://app.example.com
```

No wildcards in production. Include both apex and `www` if both serve the app.

### Deploy script fails at migration step

**Fix:**

```bash
cd /opt/monetra
docker compose -f docker-compose.prod.yml up -d postgres
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

See [deployment/deploy.md](./deployment/deploy.md).

## Backup and restore

### Backup script: permission denied

**Fix:** Ensure the backup user can run `docker compose exec postgres pg_dump` and write to `BACKUP_DIR`.

### Restore verification fails

**Fix:** Run `python backend/scripts/verify_restored_database.py` against the restored database URL. Check migration compatibility with `scripts/test-backup-restore.sh`.

Full procedure: [deployment/backup-restore.md](./deployment/backup-restore.md).

## Security

| Topic | Guidance |
|-------|----------|
| Secrets | Never commit `.env`, TLS private keys, or JWT secrets. Use `.env.example` templates only. |
| Default JWT | Production rejects the development default secret. |
| Refresh cookies | Set `REFRESH_TOKEN_COOKIE_SECURE=true` in production (enforced by settings validation). |
| Rate limits | Tune `AUTH_RATE_LIMIT_*` if legitimate users hit limits behind NAT. |
| Proxy trust | Set `TRUSTED_PROXY_COUNT=1` when behind Nginx so client IP rate limiting works. |
| OpenAPI | `/docs` is disabled when `APP_ENV=production`. |
| Container users | Production images run as non-root (verified in CI). |

## Known product limitations

These are intentional gaps, not bugs:

| Limitation | Workaround |
|------------|------------|
| No outbound email | Use password-reset token from server logs in dev; integrate SMTP provider for production |
| No recurring scheduler | Call `POST /api/v1/recurring-transactions/process-due` manually or via cron |
| No live FX provider | Configure `EXCHANGE_RATE_STATIC_RATES` or insert rates via API |
| No audit UI | Query `GET /api/v1/audit-events` directly |
| Settings read-only | Change reporting currency via `PATCH /api/v1/users/me` API |
| Cross-currency transfers in UI | Use accounts with the same currency |

## Getting help

1. Check container logs: `docker compose logs -f backend`
2. Check request ID in API error responses and backend logs
3. Review [architecture.md](./architecture.md) and [deployment/sre-audit.md](./deployment/sre-audit.md)
4. OpenAPI schema at http://localhost:8000/docs (development only)

## Related

- [development.md](./development.md)
- [testing.md](./testing.md)
- [deployment/README.md](./deployment/README.md)
