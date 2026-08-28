# Backup and restore

Monetra stores authoritative financial data in PostgreSQL. Production runs PostgreSQL in a Docker volume on EC2. **You are responsible for backups**—AWS does not back up Docker volumes automatically.

This document defines the operational backup strategy, retention policy, secure off-host storage, restore procedures, and disaster recovery. All commands are copy-paste ready; substitute placeholders such as `<backup-file>` and `<your-domain>` with your values. **Never paste real secrets into tickets, chat, or documentation.**

## Strategy overview

| Parameter | Value |
|-----------|-------|
| Backup type | Logical (`pg_dump -Fc` custom format) |
| Schedule | Daily at 02:15 UTC (cron) |
| Local retention | 7 daily, 4 weekly (Sunday copies), 12 monthly (1st-of-month copies) |
| Off-host storage | S3 with server-side encryption (SSE-S3 or SSE-KMS) |
| Pre-deploy backup | Automatic when `BACKUP_BEFORE_DEPLOY=true` (default) |
| Restore verification | Financial balance invariants + Alembic revision check |
| RPO | Backup interval (24 h with daily schedule; lower if you add hourly jobs) |
| RTO | Plan 1–2 hours for full EC2 rebuild including DNS |

### Why logical backups

- Portable across PostgreSQL minor versions and future RDS migration.
- Restorable into a fresh container without copying raw volume files.
- Appropriate size for portfolio deployments.

Add **EBS volume snapshots** of the EC2 data disk as a complement for faster host-level recovery. Snapshots do not replace logical exports when migrating to RDS or verifying row-level integrity.

## What is backed up

| Asset | Location | Method |
|-------|----------|--------|
| PostgreSQL data | Docker volume `postgres_data` | `scripts/backup-database.sh` |
| Environment configuration | `/opt/monetra/.env` | Encrypted offline secret store (not in Git) |
| TLS private keys | `/opt/monetra/nginx/certs/` | Let's Encrypt re-issue, or secure offline copy |
| Application code | Git remote | Tagged releases; server is disposable |

## Repository scripts

| Script | Purpose |
|--------|---------|
| `scripts/backup-database.sh` | Create logical dump, checksum, tiered retention, optional S3 upload |
| `scripts/backup-database.ps1` | Windows PowerShell equivalent of `backup-database.sh` |
| `scripts/restore-database.sh` | Destructive restore into production Compose postgres |
| `scripts/test-backup-restore.sh` | Non-production drill (isolated restore DB + integrity checks) |
| `scripts/test-backup-restore.ps1` | Windows equivalent of the drill |
| `scripts/cron/monetra-backup.cron` | Cron template for EC2 |
| `backend/scripts/verify_restored_database.py` | Balance invariant + Alembic revision verification |

## Scheduled backups (production EC2)

### 1. Install the backup script

The script ships with the repository. On first deploy it is made executable by `scripts/deploy-production.sh`.

```bash
chmod +x /opt/monetra/scripts/backup-database.sh
```

### 2. Configure optional S3 upload

Add to `/opt/monetra/.env` (values are examples—use your bucket and region):

```bash
MONETRA_BACKUP_S3_URI=s3://your-backup-bucket/monetra/postgres/
MONETRA_BACKUP_S3_SSE=AES256
```

The EC2 instance role needs `s3:PutObject` (and `s3:PutObjectAcl` only if your bucket policy requires it) on that prefix. Prefer an IAM role attached to the instance—**do not** store AWS access keys in `.env`.

### 3. Install cron

```bash
sudo cp /opt/monetra/scripts/cron/monetra-backup.cron /etc/cron.d/monetra-backup
sudo chmod 644 /etc/cron.d/monetra-backup
sudo touch /var/log/monetra-backup.log
sudo chown monetra:monetra /var/log/monetra-backup.log
```

Cron entry (02:15 UTC daily):

```cron
15 2 * * * monetra /opt/monetra/scripts/backup-database.sh >> /var/log/monetra-backup.log 2>&1
```

### 4. Retention policy

Controlled by environment variables (defaults in parentheses):

| Tier | Directory | Retention variable | Default |
|------|-----------|-------------------|---------|
| Daily | `backups/daily/` | `BACKUP_DAILY_RETENTION_DAYS` | 7 days |
| Weekly | `backups/weekly/` | `BACKUP_WEEKLY_RETENTION_DAYS` | 28 days (Sunday copies) |
| Monthly | `backups/monthly/` | `BACKUP_MONTHLY_RETENTION_DAYS` | 365 days (1st-of-month copies) |

Old files are pruned automatically after each successful backup.

### 5. Manual backup

Run before upgrades and before risky schema changes:

```bash
cd /opt/monetra
./scripts/backup-database.sh
ls -lh backups/daily/
```

Verify non-zero size and optional `.sha256` sidecar:

```bash
sha256sum -c backups/daily/monetra-20260101T021500Z.dump.sha256
```

## Secure backup storage

### On the EC2 host

- Store dumps under `/opt/monetra/backups/` (gitignored).
- Restrict directory permissions: `chmod 700 /opt/monetra/backups` (owner `monetra` only).
- Dumps contain full database contents including password hashes—treat as **confidential**.

### Off-host (recommended)

Upload to a dedicated S3 bucket in the same region as EC2:

```bash
# Configured automatically when MONETRA_BACKUP_S3_URI is set; manual example:
aws s3 cp backups/daily/monetra-20260101T021500Z.dump \
  s3://your-backup-bucket/monetra/postgres/monetra-20260101T021500Z.dump \
  --sse AES256
```

Bucket policy guidelines:

- Block public access (S3 Block Public Access = on).
- Enable default encryption (SSE-S3 or SSE-KMS).
- Grant `s3:PutObject` / `s3:GetObject` only to the EC2 instance role and break-glass admin principals.
- Enable S3 versioning for accidental-delete protection.
- Enable server access logging or CloudTrail data events for audit.

Optional: encrypt with GPG before upload if policy requires client-side encryption:

```bash
gpg --symmetric --cipher-algo AES256 backups/daily/monetra-20260101T021500Z.dump
aws s3 cp backups/daily/monetra-20260101T021500Z.dump.gpg s3://your-backup-bucket/monetra/postgres/ --sse AES256
```

## Restore procedure (production)

**Warning:** restore overwrites the target database. Stop application writes first.

### 1. Obtain a backup

```bash
cd /opt/monetra
# Local copy:
BACKUP_FILE=backups/daily/monetra-20260101T021500Z.dump

# Or download from S3:
aws s3 cp s3://your-backup-bucket/monetra/postgres/monetra-20260101T021500Z.dump "$BACKUP_FILE"
aws s3 cp s3://your-backup-bucket/monetra/postgres/monetra-20260101T021500Z.dump.sha256 "${BACKUP_FILE}.sha256"
```

### 2. Run restore

```bash
cd /opt/monetra
./scripts/restore-database.sh --file "$BACKUP_FILE" --confirm
```

The script:

1. Verifies checksum when `.sha256` is present.
2. Stops `backend`, `frontend`, and `nginx`.
3. Drops and recreates the PostgreSQL database.
4. Runs `pg_restore`.
5. Verifies financial integrity and Alembic revision via `verify_restored_database.py`.
6. Restarts the application tier.

### 3. Manual restore (step-by-step)

If you need explicit control:

```bash
cd /opt/monetra
docker compose -f docker-compose.prod.yml stop backend frontend nginx

BACKUP_FILE=backups/daily/monetra-20260101T021500Z.dump

docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U monetra -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'monetra' AND pid <> pg_backend_pid();"

docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U monetra -d postgres -c "DROP DATABASE IF EXISTS monetra;"
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U monetra -d postgres -c "CREATE DATABASE monetra OWNER monetra;"

docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U monetra -d monetra --no-owner --role=monetra < "$BACKUP_FILE"

docker compose -f docker-compose.prod.yml run --rm --no-deps \
  -e DATABASE_URL=postgresql+psycopg://monetra:<db-password>@postgres:5432/monetra \
  --entrypoint python \
  backend -m scripts.verify_restored_database

docker compose -f docker-compose.prod.yml up -d
curl -sf https://<your-domain>/ready
```

Replace `<db-password>` with the value from `.env` on the server—do not commit it.

### 4. Post-restore checks

```bash
curl -sf https://<your-domain>/ready | jq .
curl -sf -o /dev/null -w '%{http_code}\n' https://<your-domain>/api/v1/users/me   # expect 401
```

Sign in through the UI and spot-check accounts, recent transactions, and balances.

## Non-production restore drill

The drill resets the **local** production-shaped Compose stack (`docker compose down -v`) to guarantee a deterministic run. Do not run it on EC2 production.

### Linux / macOS / WSL

```bash
./scripts/test-backup-restore.sh
```

### Windows (PowerShell)

```powershell
.\scripts\test-backup-restore.ps1
```

### Via dev helper

```bash
./scripts/dev.sh backup-restore-test
```

```powershell
.\scripts\dev.ps1 backup-restore-test
```

The drill:

1. Starts the local production-shaped stack and seeds financial data.
2. Creates a backup with `backup-database.sh`.
3. Restores into `monetra_restore` on port `5433`.
4. Runs `verify_restored_database.py` (balance invariants for every user).
5. Runs `alembic upgrade head` against the restored database (migration compatibility).
6. Re-runs verification and tears down the restore-test stack.

Record the date and outcome in your operations log.

## Verify restored database (standalone)

```bash
cd backend
DATABASE_URL=postgresql+psycopg://monetra:<password>@127.0.0.1:5433/monetra_restore \
  python -m scripts.verify_restored_database
```

Checks performed:

- Row counts for users, accounts, transactions, transfers.
- `alembic_version` matches a current migration head.
- Cached account balances match ledger-derived balances for **every** user.

Exit code `0` means all checks passed.

## Full disaster recovery (new EC2 instance)

1. Provision a new EC2 host ([aws-ec2.md](./aws-ec2.md)).
2. Clone the repository and restore `.env` from your secret store.
3. Install TLS certificates under `nginx/certs/`.
4. Download the latest S3 backup (or copy from old host `backups/`).
5. Start PostgreSQL only:

   ```bash
   cd /opt/monetra
   docker compose -f docker-compose.prod.yml up -d postgres
   ```

6. Restore:

   ```bash
   ./scripts/restore-database.sh --file backups/daily/<latest>.dump --confirm
   ```

7. If DNS changed, update Route 53 A record to the new Elastic IP.
8. Verify `/ready`, run smoke checks, and confirm application access.

## Restore to Amazon RDS (future migration)

1. Create RDS PostgreSQL 16 (same major version).
2. Restore the dump:

   ```bash
   pg_restore -h <rds-endpoint> -U monetra -d monetra --no-owner backup.dump
   ```

3. Update `DATABASE_URL` in `.env` to the RDS endpoint.
4. Remove the `postgres` service from Compose or stop using it.
5. Deploy backend, frontend, and nginx only.
6. Run `verify_restored_database.py` against RDS before cutover.

## Migration compatibility after restore

A restored database carries the `alembic_version` row from backup time. After restore:

- If the deployed application matches the backup era, `alembic current` equals `alembic heads` and `upgrade head` is a no-op.
- If you deploy newer code after restore, run migrations **once** before serving traffic:

  ```bash
  docker compose -f docker-compose.prod.yml run --rm --no-deps --entrypoint alembic backend upgrade head
  ```

The restore drill runs `alembic upgrade head` against the isolated restore database to prove this path works without touching production.

## Troubleshooting

| Symptom | Action |
|---------|--------|
| `another backup is already running` | Remove stale `backups/.backup.lock` only if no backup process is active |
| Empty dump file | Check postgres health: `docker compose -f docker-compose.prod.yml exec postgres pg_isready` |
| `pg_restore` warnings | Review output; object-exists warnings can be benign after partial restores |
| Balance invariant failure | Do not serve traffic; investigate corruption or partial restore |
| Alembic revision mismatch | Run `alembic upgrade head` or restore a backup matching the deployed release |

## Security checklist

- Encrypt backups at rest (S3 SSE, optional GPG).
- Restrict filesystem and IAM access to backup paths.
- Never store unencrypted dumps in public buckets.
- Rotate credentials if a dump may have leaked.
- Audit S3 access logs periodically.

## Related documents

- [Deployment runbook](./deploy.md)
- [Configuration and secrets](./configuration.md)
- [AWS EC2 host setup](./aws-ec2.md)
- [SRE audit](./sre-audit.md)
