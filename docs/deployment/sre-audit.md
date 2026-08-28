# Production deployment SRE audit

Audit date: 2026-08-28. Scope: single EC2 + Docker Compose portfolio deployment.

## Executive summary

The production topology (Nginx → frontend/backend → PostgreSQL) is sound for a portfolio-scale deployment. This audit identified gaps in **deploy script ordering**, **pre-flight validation**, **migration idempotency**, **backup automation**, and **failure diagnostics**. Fixes were applied to scripts, Compose, Nginx entrypoint, and GitHub Actions.

## Architecture review

| Area | Status | Notes |
|------|--------|-------|
| Docker Compose | ✅ Good | Internal network; only Nginx publishes 80/443 |
| EC2 configuration | ✅ Documented | `t3.small`+, Elastic IP, UFW + security groups in docs |
| Networking | ✅ Good | Postgres/backend not exposed; bridge network `monetra` |
| HTTPS | ✅ Good | TLS at Nginx; HTTP→HTTPS redirect; HSTS configurable |
| Secrets | ⚠️ Improved | `.env` on host; validation rejects defaults; not in images/Git |
| GitHub Actions | ⚠️ Fixed | Deploy now checks out ref **before** running deploy script |
| Deployment ordering | ⚠️ Fixed | validate → backup → build → postgres → migrate → up |
| Migrations | ⚠️ Fixed | Explicit `alembic upgrade` before restart; `RUN_DB_MIGRATIONS=false` on `up` |
| Health checks | ✅ Good | All services have Docker healthchecks + smoke script |
| Rollback | ⚠️ Added | `rollback-production.sh` (code-only; no auto schema downgrade) |
| Backups | ⚠️ Added | `backup-database.sh` + pre-deploy backup hook |
| Logs | ⚠️ Improved | json-file driver with 10m×3 rotation per service |
| Resource usage | ⚠️ Improved | Memory limits: postgres/backend 512M, frontend/nginx 128M |

## Failure scenarios

### Migration failure

| Before | After |
|--------|-------|
| Backend entrypoint and deploy script could both run migrations | Deploy runs `alembic upgrade head` once; `RUN_DB_MIGRATIONS=false` on `up` |
| Failed migration still followed by `up -d` in some paths | Deploy aborts before `up -d` if migration fails |
| No pre-migration backup | `BACKUP_BEFORE_DEPLOY=true` (default) runs `backup-database.sh` when Postgres exists |

**Residual risk:** Irreversible migration + rollback requires forward-fix or restore from backup.

### Container crash

| Mitigation |
|------------|
| `restart: unless-stopped` on all services |
| Docker healthchecks restart unhealthy containers via Compose |
| `docker compose ps` + logs emitted on deploy failure |

### Database unavailable

| Detection | Response |
|-----------|----------|
| Postgres healthcheck | Backend `/ready` returns `"database": false` |
| Deploy waits for `pg_isready` before migrations | Deploy fails fast with diagnostics |
| Nginx still serves `/health` (liveness) | `/ready` fails — use `/ready` for routing decisions |

### Failed deployment

| Mitigation |
|------------|
| Deploy script `trap` + `docker compose ps/logs` on failure |
| GitHub Actions job fails; summary includes debug commands |
| Previous containers keep running if migration step fails (no `up -d`) |

### Invalid environment variable

| Mitigation |
|------------|
| Compose `${VAR:?}` for required secrets |
| `validate-production-env.sh` before deploy |
| Backend rejects default JWT and `DEBUG=true` in production |

### Expired certificate

| Mitigation |
|------------|
| `validate-production-env.sh` checks expiry (configurable `CERT_MIN_VALID_SECONDS`) |
| Nginx entrypoint fails if cert files missing |
| Document certbot renewal in `docs/deployment/deploy.md` |

## Component details

### Docker Compose (`docker-compose.prod.yml`)

- Non-root production images with read-only root filesystems where practical.
- tmpfs for nginx writable paths and certs copy.
- **Added:** memory limits and log rotation per service.

### EC2 / host

- Documented in `docs/deployment/aws-ec2.md`.
- Deploy user, UFW, Docker hardening, Elastic IP.

### Secrets

- Application secrets in `/opt/monetra/.env` (mode 600).
- GitHub secrets limited to SSH + `PRODUCTION_URL` for deploy.
- CI uses ephemeral test credentials only.

### GitHub Actions

- **CI:** parallel lint/typecheck/test/build/docker/e2e → `quality-gate`.
- **Deploy:** reusable CI → SSH deploy → public smoke tests.
- **Fix:** server `git checkout` before `deploy-production.sh --skip-fetch`.

### Rollback

```bash
./scripts/rollback-production.sh <previous-tag>
```

Rolls back **application code only**. Database schema is not downgraded. Use only when schema-compatible or after restore.

### Backups

```bash
./scripts/backup-database.sh
```

Pre-deploy backup enabled by default. Set `BACKUP_BEFORE_DEPLOY=false` for first boot or test runs.

### Logs

- Container logs: `docker compose -f docker-compose.prod.yml logs -f <service>`
- JSON structured backend logs (`LOG_FORMAT=json`).
- Nginx access/error logs inside container (json-file rotation).

### Resource usage (t3.small baseline)

| Service | Memory limit |
|---------|----------------|
| postgres | 512 MB |
| backend | 512 MB |
| frontend | 128 MB |
| nginx | 128 MB |
| **Total limits** | ~1.3 GB + OS/Docker overhead |

Monitor with `docker stats`. Scale instance if sustained memory pressure occurs.

## Clean-environment test

```bash
./scripts/prod-clean-deploy-test.sh
```

Destroys prod volumes, provisions `.env` + TLS certs, runs full deploy pipeline, verifies health.

## Recommendations (future)

1. **RDS migration** when data durability requirements exceed single-volume Postgres.
2. **ALB + ACM** for TLS at load balancer and multi-AZ.
3. **S3 backup upload** in `backup-database.sh` (commented template exists).
4. **CloudWatch alarms** on `/ready`, disk usage, and memory.
5. **GitHub environment protection** requiring manual approval before deploy.

## Related scripts

| Script | Purpose |
|--------|---------|
| `scripts/validate-production-env.sh` | Pre-flight checks |
| `scripts/deploy-production.sh` | Full deploy pipeline |
| `scripts/smoke-production.sh` | HTTP/HTTPS smoke tests |
| `scripts/backup-database.sh` | Logical DB backup |
| `scripts/rollback-production.sh` | Code rollback |
| `scripts/prod-clean-deploy-test.sh` | Clean-environment integration test |
