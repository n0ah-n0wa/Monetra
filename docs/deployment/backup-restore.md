# Backup and restore

Monetra stores authoritative financial data in PostgreSQL. The production deployment runs PostgreSQL in a Docker volume on EC2. **You are responsible for backups**—AWS does not back up Docker volumes automatically.

## Backup scope

| Asset | Location | Backup method |
|-------|----------|---------------|
| PostgreSQL data | Docker volume `postgres_data` | `pg_dump` (logical) or volume snapshot (physical) |
| Environment secrets | `/opt/monetra/.env` | Encrypted offline copy |
| TLS private keys | `/opt/monetra/nginx/certs/` | Let's Encrypt can re-issue; or backup `privkey.pem` securely |
| Application code | Git remote | Tag releases; server is disposable |

## Backup strategy (recommended)

| Parameter | Recommendation |
|-----------|----------------|
| Type | Logical (`pg_dump -Fc` custom format) |
| Frequency | Daily at minimum; hourly if data churn is high |
| Retention | 7 daily, 4 weekly (adjust for compliance needs) |
| Storage | S3 bucket in the same region, encrypted (SSE-S3 or SSE-KMS) |
| Access | IAM role on EC2 with `s3:PutObject` only to the backup prefix |

### Why logical backups

- Portable across PostgreSQL minor versions.
- Easy to restore into a fresh container or future RDS instance.
- Smaller transfer footprint than raw volume copies for portfolio data sizes.

### When to add EBS snapshots

Snapshot the EC2 root volume (or a dedicated data volume if you split PostgreSQL storage later) **in addition to** `pg_dump` for faster disaster recovery. Snapshots are not a substitute for logical exports when migrating to RDS.

## Automated backup script

Install on the EC2 host at `/opt/monetra/scripts/backup-database.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/monetra
BACKUP_DIR="${APP_DIR}/backups"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILENAME="monetra-${TIMESTAMP}.dump"
COMPOSE="docker compose -f ${APP_DIR}/docker-compose.prod.yml"

mkdir -p "${BACKUP_DIR}"

# Load POSTGRES_* from .env
set -a
# shellcheck disable=SC1091
source "${APP_DIR}/.env"
set +a

${COMPOSE} exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc \
  > "${BACKUP_DIR}/${FILENAME}"

# Optional: upload to S3
# aws s3 cp "${BACKUP_DIR}/${FILENAME}" "s3://your-bucket/monetra/postgres/${FILENAME}"

# Retain last 14 local dumps
find "${BACKUP_DIR}" -name 'monetra-*.dump' -mtime +14 -delete

echo "Backup written: ${BACKUP_DIR}/${FILENAME}"
```

```bash
chmod +x /opt/monetra/scripts/backup-database.sh
```

### Cron schedule

```bash
# /etc/cron.d/monetra-backup
15 2 * * * monetra /opt/monetra/scripts/backup-database.sh >> /var/log/monetra-backup.log 2>&1
```

Run a manual backup before every upgrade ([deploy.md](./deploy.md#routine-upgrades)).

## Manual backup

```bash
cd /opt/monetra
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U monetra -d monetra -Fc > "backups/manual-$(date -u +%Y%m%d).dump"
```

Verify the dump is non-empty:

```bash
ls -lh backups/
```

## Restore procedure

Restores are destructive to the target database. **Stop the application** first to prevent writes during restore.

### 1. Stop application tier

```bash
cd /opt/monetra
docker compose -f docker-compose.prod.yml stop backend frontend nginx
```

PostgreSQL can keep running.

### 2. Restore into existing database

For a same-instance restore (overwrite current data):

```bash
BACKUP_FILE=backups/monetra-20260101T020000Z.dump

# Terminate active connections
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U monetra -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'monetra' AND pid <> pg_backend_pid();"

# Drop and recreate database
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U monetra -d postgres -c "DROP DATABASE IF EXISTS monetra;"
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U monetra -d postgres -c "CREATE DATABASE monetra OWNER monetra;"

# Restore
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U monetra -d monetra --no-owner --role=monetra < "${BACKUP_FILE}"
```

`pg_restore` may emit warnings for existing objects; review output.

### 3. Restart application

```bash
docker compose -f docker-compose.prod.yml up -d
curl -sf https://app.example.com/ready | jq .
```

### 4. Verify data

- Sign in with a known user account.
- Spot-check accounts, recent transactions, and balances.

## Full disaster recovery (new EC2 instance)

1. Provision a new EC2 host ([aws-ec2.md](./aws-ec2.md)).
2. Clone the repository and restore `.env` from secure backup.
3. Install TLS certificates.
4. Start **only** PostgreSQL:

   ```bash
   docker compose -f docker-compose.prod.yml up -d postgres
   ```

5. Wait for `healthy`, then restore the latest dump (steps above).
6. Start the full stack:

   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

7. Update DNS A record if the Elastic IP changed.
8. Verify `/ready` and application functionality.

**Recovery time objective (RTO)** for a portfolio deployment: plan for 1–2 hours including DNS propagation.

**Recovery point objective (RPO)** equals your backup interval (e.g. 24 hours with daily backups).

## Restore to Amazon RDS (future migration)

When moving off containerized PostgreSQL:

1. Create RDS PostgreSQL 16 instance (same major version).
2. Restore the custom-format dump:

   ```bash
   pg_restore -h <rds-endpoint> -U monetra -d monetra --no-owner backup.dump
   ```

3. Update `DATABASE_URL` in `.env` to the RDS endpoint.
4. Remove or disable the `postgres` service in Compose.
5. Deploy backend + frontend + nginx only.

## Testing backups

Quarterly (or before major releases):

1. Restore the latest dump into a **local** or **staging** environment.
2. Run `alembic current` and application smoke tests.
3. Document the test date and result.

Untested backups are a liability.

## Security

- Encrypt backup files at rest (S3 SSE, or `gpg` before upload).
- Restrict S3 bucket policy to the EC2 instance role and break-glass admin principals.
- Never store unencrypted dumps in a public bucket.
- Rotate IAM credentials and audit S3 access logs.

## Related documents

- [Deployment runbook](./deploy.md)
- [Configuration and secrets](./configuration.md)
