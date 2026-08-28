#!/usr/bin/env bash
# Non-production backup and restore drill.
#
# 1. Ensures the production-shaped local stack is running with seeded data
# 2. Creates a logical backup via scripts/backup-database.sh
# 3. Restores into an isolated PostgreSQL instance (docker-compose.restore-test.yml)
# 4. Verifies financial integrity and Alembic migration compatibility
#
# Safe to run on a developer machine. Does not modify production EC2 data.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_PROD="docker-compose.prod.yml"
COMPOSE_RESTORE="docker-compose.restore-test.yml"
RESTORE_DB="${POSTGRES_RESTORE_DB:-monetra_restore}"
RESTORE_PORT="${POSTGRES_RESTORE_PORT:-5433}"

log() {
  printf '[backup-restore-test] %s\n' "$*"
}

fail() {
  printf '[backup-restore-test] ERROR: %s\n' "$*" >&2
  exit 1
}

ensure_env() {
  if [[ ! -f .env ]]; then
    log "Creating .env from .env.production.example"
    cp .env.production.example .env
    if sed --version >/dev/null 2>&1; then
      sed -i "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$(openssl rand -hex 32)/" .env
      sed -i 's/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=monetra-restore-test/' .env
    else
      sed -i '' "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$(openssl rand -hex 32)/" .env
      sed -i '' 's/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=monetra-restore-test/' .env
    fi
  fi
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  export JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(openssl rand -hex 32)}"
  : "${POSTGRES_DB:?POSTGRES_DB is required}"
  : "${POSTGRES_USER:?POSTGRES_USER is required}"
  : "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
}

wait_postgres() {
  local compose_file="$1"
  local service="$2"
  local user="$3"
  local database="$4"
  for _ in $(seq 1 40); do
    if docker compose -f "$compose_file" exec -T "$service" \
      pg_isready -U "$user" -d "$database" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  fail "PostgreSQL did not become ready (${compose_file}/${service})"
}

stack_ready() {
  curl -k -sf https://localhost/ready >/dev/null 2>&1
}

ensure_env

if [[ ! -f nginx/certs/fullchain.pem || ! -f nginx/certs/privkey.pem ]]; then
  "$ROOT/scripts/generate-local-tls-certs.sh"
fi

log "Resetting local production-shaped stack for a deterministic drill..."
docker compose -f "$COMPOSE_PROD" down -v --remove-orphans >/dev/null 2>&1 || true

log "Starting production-shaped stack..."
docker compose -f "$COMPOSE_PROD" up -d postgres
wait_postgres "$COMPOSE_PROD" postgres "$POSTGRES_USER" "$POSTGRES_DB"
docker compose -f "$COMPOSE_PROD" run --rm --no-deps --entrypoint alembic backend upgrade head
export RUN_DB_MIGRATIONS=false
docker compose -f "$COMPOSE_PROD" up -d --remove-orphans
unset RUN_DB_MIGRATIONS

for _ in $(seq 1 60); do
  if stack_ready; then
    break
  fi
  sleep 3
done
stack_ready || fail "/ready did not become healthy"

log "Building backend image with restore-test scripts..."
docker compose -f "$COMPOSE_PROD" build backend

log "Seeding representative financial data..."
docker compose -f "$COMPOSE_PROD" run --rm --no-deps \
  --entrypoint python \
  backend -m scripts.seed_restore_test_data

log "Creating backup..."
chmod +x "$ROOT/scripts/backup-database.sh"
"$ROOT/scripts/backup-database.sh"
BACKUP_FILE="$(ls -1t backups/daily/monetra-*.dump | head -n1)"
[[ -f "$BACKUP_FILE" ]] || fail "backup file not found"

log "Preparing isolated restore target..."
docker compose -f "$COMPOSE_RESTORE" down -v --remove-orphans >/dev/null 2>&1 || true
export POSTGRES_RESTORE_DB="$RESTORE_DB"
docker compose -f "$COMPOSE_RESTORE" up -d postgres-restore
wait_postgres "$COMPOSE_RESTORE" postgres-restore "$POSTGRES_USER" "$RESTORE_DB"

log "Restoring backup into ${RESTORE_DB} on port ${RESTORE_PORT}..."
docker compose -f "$COMPOSE_RESTORE" exec -T postgres-restore \
  pg_restore -U "$POSTGRES_USER" -d "$RESTORE_DB" --no-owner --role="$POSTGRES_USER" \
  < "$BACKUP_FILE"

RESTORE_DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${RESTORE_PORT}/${RESTORE_DB}"

log "Verifying financial integrity on restored database..."
docker compose -f "$COMPOSE_PROD" run --rm --no-deps \
  -e "DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres-restore:5432/${RESTORE_DB}" \
  --entrypoint python \
  backend -m scripts.verify_restored_database

log "Testing migration compatibility (alembic upgrade head)..."
docker compose -f "$COMPOSE_PROD" run --rm --no-deps \
  -e "DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres-restore:5432/${RESTORE_DB}" \
  --entrypoint alembic \
  backend upgrade head

log "Re-verifying after migrations..."
docker compose -f "$COMPOSE_PROD" run --rm --no-deps \
  -e "DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres-restore:5432/${RESTORE_DB}" \
  --entrypoint python \
  backend -m scripts.verify_restored_database --require-head

log "Cleaning up restore-test stack..."
docker compose -f "$COMPOSE_RESTORE" down -v --remove-orphans

log "Backup file: ${BACKUP_FILE}"
log "Backup and restore drill passed."
