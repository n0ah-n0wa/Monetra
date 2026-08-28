# Deployment runbook

End-to-end procedure for deploying and operating Monetra on EC2 with `docker-compose.prod.yml`.

## Prerequisites

- EC2 host prepared ([aws-ec2.md](./aws-ec2.md))
- `.env` configured ([configuration.md](./configuration.md))
- Git access to the release tag or CI-built images

## DNS

Point your domain to the EC2 **Elastic IP**.

### Route 53 (recommended)

1. Create a hosted zone for `example.com` (or use an existing zone).
2. Create an **A record**:
   - Name: `app` (or `@` for apex)
   - Type: `A`
   - Value: Elastic IP of the EC2 instance
   - TTL: `300` (low TTL eases future migrations)
3. Optional: `AAAA` record if you assign an IPv6 address.

### External DNS provider

Create the same A record at your registrar/DNS host. Verify propagation:

```bash
dig +short app.example.com
```

Wait until the record resolves to your Elastic IP before requesting TLS certificates.

Update `.env`:

```dotenv
CORS_ORIGINS=https://app.example.com
NGINX_SERVER_NAME=app.example.com
```

## HTTPS (TLS)

Production Nginx expects two PEM files on the host:

```text
/opt/monetra/nginx/certs/fullchain.pem
/opt/monetra/nginx/certs/privkey.pem
```

Compose mounts `nginx/certs` read-only into the container. The entrypoint copies them to a tmpfs with correct permissions.

### Option A — Let's Encrypt (recommended for EC2)

Use Certbot on the **host** (not inside the app container). Stop Nginx temporarily for standalone issuance, or use webroot/nginx plugin after first deploy.

**First-time issuance (standalone):**

```bash
cd /opt/monetra
docker compose -f docker-compose.prod.yml stop nginx

sudo apt-get install -y certbot
sudo certbot certonly --standalone \
  -d app.example.com \
  --agree-tos \
  -m admin@example.com \
  --non-interactive

sudo install -d -o monetra -g monetra nginx/certs
sudo cp /etc/letsencrypt/live/app.example.com/fullchain.pem nginx/certs/
sudo cp /etc/letsencrypt/live/app.example.com/privkey.pem nginx/certs/
sudo chown monetra:monetra nginx/certs/*.pem
sudo chmod 644 nginx/certs/fullchain.pem
sudo chmod 640 nginx/certs/privkey.pem

docker compose -f docker-compose.prod.yml up -d nginx
```

**Renewal** (Let's Encrypt certs expire every 90 days):

```bash
# /etc/cron.d/monetra-certbot (example — adjust domain and paths)
0 3 * * * root certbot renew --quiet --deploy-hook "/opt/monetra/scripts/renew-tls-certs.sh"
```

Example `scripts/renew-tls-certs.sh` on the server:

```bash
#!/bin/sh
set -eu
DOMAIN=app.example.com
APP_DIR=/opt/monetra
cp "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "${APP_DIR}/nginx/certs/"
cp "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" "${APP_DIR}/nginx/certs/"
chown monetra:monetra "${APP_DIR}/nginx/certs/"*.pem
cd "${APP_DIR}" && docker compose -f docker-compose.prod.yml restart nginx
```

### Option B — AWS Certificate Manager + ALB (future)

For higher availability, terminate TLS at an Application Load Balancer with an ACM certificate. Nginx would listen on an internal port only. This is **not** required for the initial single-instance deployment but is the natural upgrade path.

### Option C — Local self-signed (development only)

Use `scripts/generate-local-tls-certs.sh` for local `prod-verify`. **Do not** use self-signed certificates for a public production domain.

### Verify HTTPS

```bash
curl -I https://app.example.com/health
curl -I http://app.example.com/health    # expect 301 → HTTPS
```

## First-time deployment

### 1. Clone the release

```bash
sudo -u monetra -H bash
cd /opt/monetra
git clone https://github.com/<org>/monetra.git .
git checkout v1.0.0   # use your release tag
```

### 2. Configure environment

```bash
cp .env.production.example .env
chmod 600 .env
nano .env   # set secrets, CORS, domain-related values
```

### 3. Install TLS certificates

Follow [HTTPS (TLS)](#https-tls) above.

### 4. Build and start

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Compose start order:

1. **postgres** — waits until `pg_isready` succeeds
2. **backend** — runs Alembic migrations, then uvicorn (2 workers)
3. **frontend** — static assets via internal nginx
4. **nginx** — exposes ports 80/443 after backend and frontend are healthy

### 5. Post-deploy verification

```bash
docker compose -f docker-compose.prod.yml ps
```

All services should show `healthy`.

```bash
# On the host
curl -f http://127.0.0.1/nginx-health
curl -sf https://app.example.com/health | jq .
curl -sf https://app.example.com/ready | jq .
curl -sf -o /dev/null -w "%{http_code}\n" https://app.example.com/api/v1/users/me   # expect 401
curl -sf -o /dev/null -w "%{http_code}\n" https://app.example.com/                 # expect 200
```

From your workstation:

```bash
./scripts/dev.sh prod-verify   # against localhost only; on server use curl commands above
```

**Deployment succeeds only if `/ready` reports `"database": true` and all containers are healthy.**

## Database initialization

### First volume creation

When the `postgres_data` Docker volume is created for the first time:

1. PostgreSQL initializes an empty data directory.
2. `docker/postgres/init.sql` runs **once** (creates an optional `monetra_test` database—harmless in production).
3. On first backend start, **Alembic** applies all migrations (`RUN_DB_MIGRATIONS=true`).

No application seed data is loaded in production. The first user registers through the UI.

### Manual migration (optional)

To run migrations without restarting the whole stack:

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

To inspect current revision:

```bash
docker compose -f docker-compose.prod.yml exec backend alembic current
```

### Disable automatic migrations

Set in `.env` only when debugging migration issues:

```dotenv
RUN_DB_MIGRATIONS=false
```

Run migrations manually before starting the backend in that mode.

## Routine upgrades

### Automated (GitHub Actions)

Tag a release or run **Deploy Production** from the Actions tab. See [GitHub Actions CI/CD](./github-actions.md).

### Manual

```bash
cd /opt/monetra
git fetch --tags
git checkout v1.1.0

# Review migration release notes
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Watch logs during migration
docker compose -f docker-compose.prod.yml logs -f backend
```

Migrations run automatically when the new backend container starts.

### Zero-downtime expectations

On a **single instance**, expect a brief window during container recreation (typically seconds). For a portfolio deployment this is acceptable. True zero-downtime requires a second instance or load balancer—out of scope for the initial topology.

### Pre-upgrade checklist

- [ ] Database backup completed ([backup-restore.md](./backup-restore.md))
- [ ] `.env` reviewed for new variables in `.env.production.example`
- [ ] Alembic migrations reviewed in the release
- [ ] TLS certificates valid > 7 days

## Health checks

### Endpoints

| Endpoint | Scope | Purpose |
|----------|-------|---------|
| `GET /nginx-health` | Nginx HTTP (port 80 internally) | Edge proxy liveness; no TLS required |
| `GET /health` | Public HTTPS | API process liveness |
| `GET /ready` | Public HTTPS | API readiness; includes PostgreSQL connectivity |

Example `/ready` response:

```json
{
  "status": "ready",
  "database": true,
  "checks": {
    "database": { "status": "ok", "latency_ms": 2.1, "error": null }
  }
}
```

### Docker healthchecks

Defined in `docker-compose.prod.yml` for all services. Inspect:

```bash
docker inspect --format '{{.State.Health.Status}}' monetra-backend
```

### External monitoring

Configure an external HTTP check (UptimeRobot, Route 53 health check, or CloudWatch synthetic canary) against:

```text
https://app.example.com/ready
```

Alert on non-200 or `"database": false`.

## Rollback

### Application rollback (no schema breaking change)

```bash
cd /opt/monetra
git checkout v1.0.0
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Previous Git tag + rebuild restores prior application code. Database schema remains at the latest migration unless you downgrade Alembic.

### Application rollback (with schema downgrade)

Only if the release documents a reversible migration:

```bash
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1
git checkout v1.0.0
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

**Prefer forward-fix migrations** over downgrades in production.

### Emergency stop

```bash
docker compose -f docker-compose.prod.yml down
```

Data persists in the `postgres_data` volume. Nginx stops serving traffic immediately.

### Image tag rollback (if using a registry)

If you push versioned images to ECR:

```bash
export MONETRA_TAG=v1.0.0
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

(Requires Compose file changes to use `image:` instead of `build:`—optional enhancement.)

## Logs and troubleshooting

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f --tail=200

# Single service
docker compose -f docker-compose.prod.yml logs -f backend

# Container resource usage
docker stats
```

Common issues:

| Symptom | Likely cause |
|---------|----------------|
| Backend restart loop | Invalid `JWT_SECRET_KEY`, DB auth failure, migration error |
| Nginx restart loop | Missing or unreadable TLS files in `nginx/certs/` |
| `/ready` database false | Postgres not healthy, wrong `DATABASE_URL` |
| 502 from Nginx | Backend not healthy yet; check `docker compose ps` |

## Maintenance windows

Schedule for:

- PostgreSQL major version upgrades
- Docker Engine upgrades
- OS kernel reboots after security patches
- Irreversible Alembic migrations

Announce JWT secret rotation and schema changes to users when applicable.

## Related documents

- [Configuration and secrets](./configuration.md)
- [Backup and restore](./backup-restore.md)
