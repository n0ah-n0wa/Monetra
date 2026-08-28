#!/usr/bin/env bash
# Restore a Monetra PostgreSQL logical backup (pg_dump -Fc format).
#
# Usage:
#   ./scripts/restore-database.sh --file backups/daily/monetra-20260101T020000Z.dump --confirm
#
# Destructive: drops and recreates the target database. Stop application tiers first.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_FILE=""
CONFIRM=false
SKIP_VERIFY=false
STOP_APP=true

log() {
  printf '[restore] %s\n' "$*"
}

fail() {
  printf '[restore] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: restore-database.sh --file <path.dump> --confirm [options]

Options:
  --file PATH       Backup file (pg_dump -Fc custom format)
  --confirm         Required acknowledgement (restore is destructive)
  --skip-verify     Skip post-restore integrity verification
  --no-stop-app     Do not stop backend/frontend/nginx before restore
  -h, --help        Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file)
      BACKUP_FILE="${2:-}"
      shift 2
      ;;
    --confirm)
      CONFIRM=true
      shift
      ;;
    --skip-verify)
      SKIP_VERIFY=true
      shift
      ;;
    --no-stop-app)
      STOP_APP=false
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

if [[ -z "$BACKUP_FILE" ]]; then
  usage
  fail "--file is required"
fi

if [[ "$CONFIRM" != "true" ]]; then
  fail "refusing to restore without --confirm"
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
  fail "backup file not found: ${BACKUP_FILE}"
fi

if [[ ! -s "$BACKUP_FILE" ]]; then
  fail "backup file is empty: ${BACKUP_FILE}"
fi

if [[ ! -f .env ]]; then
  fail ".env not found"
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

checksum_file="${BACKUP_FILE}.sha256"
if [[ -f "$checksum_file" ]]; then
  log "Verifying checksum..."
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "$checksum_file"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c "$checksum_file"
  else
    log "checksum file present but sha256sum/shasum unavailable; skipping verify"
  fi
fi

if [[ "$STOP_APP" == "true" ]]; then
  log "Stopping application tier (backend, frontend, nginx)..."
  docker compose -f "$COMPOSE_FILE" stop backend frontend nginx 2>/dev/null || true
fi

log "Ensuring PostgreSQL is running..."
docker compose -f "$COMPOSE_FILE" up -d postgres
for _ in $(seq 1 30); do
  if docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_isready -U "$POSTGRES_USER" -d postgres >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

log "Terminating active connections to ${POSTGRES_DB}..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();"

log "Recreating database ${POSTGRES_DB}..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -c \
  "DROP DATABASE IF EXISTS \"${POSTGRES_DB}\";"
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -c \
  "CREATE DATABASE \"${POSTGRES_DB}\" OWNER \"${POSTGRES_USER}\";"

log "Restoring from ${BACKUP_FILE}..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --role="$POSTGRES_USER" \
  < "$BACKUP_FILE"

if [[ "$SKIP_VERIFY" != "true" ]]; then
  log "Verifying restored database integrity..."
  docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
    -e "DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}" \
    --entrypoint python \
    backend -m scripts.verify_restored_database
fi

if [[ "$STOP_APP" == "true" ]]; then
  log "Starting application tier..."
  docker compose -f "$COMPOSE_FILE" up -d
fi

log "Restore complete."
