#!/usr/bin/env bash
# Logical PostgreSQL backup for Monetra production.
#
# Writes a custom-format pg_dump, optional SHA-256 checksum, tiered local
# retention (daily / weekly / monthly), and optional encrypted S3 upload.
#
# Environment (all optional unless noted):
#   COMPOSE_FILE              docker-compose.prod.yml (default)
#   BACKUP_DIR                ./backups
#   BACKUP_DAILY_RETENTION_DAYS   7
#   BACKUP_WEEKLY_RETENTION_DAYS  28
#   BACKUP_MONTHLY_RETENTION_DAYS 365
#   MONETRA_BACKUP_S3_URI     s3://bucket/prefix/ (upload when set)
#   MONETRA_BACKUP_S3_SSE     AES256 | aws:kms (default AES256)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT}/backups}"
DAILY_DIR="${BACKUP_DIR}/daily"
WEEKLY_DIR="${BACKUP_DIR}/weekly"
MONTHLY_DIR="${BACKUP_DIR}/monthly"
DAILY_RETENTION_DAYS="${BACKUP_DAILY_RETENTION_DAYS:-7}"
WEEKLY_RETENTION_DAYS="${BACKUP_WEEKLY_RETENTION_DAYS:-28}"
MONTHLY_RETENTION_DAYS="${BACKUP_MONTHLY_RETENTION_DAYS:-365}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILENAME="monetra-${TIMESTAMP}.dump"
LOCK_FILE="${BACKUP_DIR}/.backup.lock"

log() {
  printf '[backup] %s\n' "$*"
}

fail() {
  printf '[backup] ERROR: %s\n' "$*" >&2
  exit 1
}

mkdir -p "$DAILY_DIR" "$WEEKLY_DIR" "$MONTHLY_DIR"

if [[ ! -f .env ]]; then
  fail ".env not found"
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

exec 200>"$LOCK_FILE"
if ! flock -n 200; then
  fail "another backup is already running (lock: ${LOCK_FILE})"
fi

if docker inspect monetra-postgres >/dev/null 2>&1; then
  running="$(docker inspect --format '{{.State.Running}}' monetra-postgres 2>/dev/null || echo false)"
else
  running=false
fi

if [[ "$running" != "true" ]]; then
  log "PostgreSQL not running; starting postgres service..."
  docker compose -f "$COMPOSE_FILE" up -d postgres
  for _ in $(seq 1 30); do
    if docker compose -f "$COMPOSE_FILE" exec -T postgres \
      pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi

output="${DAILY_DIR}/${FILENAME}"
log "Creating logical backup for database ${POSTGRES_DB}..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$output"

if [[ ! -s "$output" ]]; then
  fail "backup file is empty: ${output}"
fi

bytes="$(wc -c < "$output" | tr -d ' ')"
checksum_file="${output}.sha256"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$output" > "$checksum_file"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$output" > "$checksum_file"
else
  log "sha256sum/shasum not found; skipping checksum"
fi

weekday="$(date -u +%u)"
day_of_month="$(date -u +%d)"
if [[ "$weekday" == "7" ]]; then
  cp "$output" "${WEEKLY_DIR}/${FILENAME}"
  [[ -f "$checksum_file" ]] && cp "$checksum_file" "${WEEKLY_DIR}/${FILENAME}.sha256"
  log "Copied to weekly retention (${WEEKLY_DIR})"
fi
if [[ "$day_of_month" == "01" ]]; then
  cp "$output" "${MONTHLY_DIR}/${FILENAME}"
  [[ -f "$checksum_file" ]] && cp "$checksum_file" "${MONTHLY_DIR}/${FILENAME}.sha256"
  log "Copied to monthly retention (${MONTHLY_DIR})"
fi

find "$DAILY_DIR" -name 'monetra-*.dump' -mtime +"$DAILY_RETENTION_DAYS" -delete 2>/dev/null || true
find "$DAILY_DIR" -name 'monetra-*.dump.sha256' -mtime +"$DAILY_RETENTION_DAYS" -delete 2>/dev/null || true
find "$WEEKLY_DIR" -name 'monetra-*.dump' -mtime +"$WEEKLY_RETENTION_DAYS" -delete 2>/dev/null || true
find "$WEEKLY_DIR" -name 'monetra-*.dump.sha256' -mtime +"$WEEKLY_RETENTION_DAYS" -delete 2>/dev/null || true
find "$MONTHLY_DIR" -name 'monetra-*.dump' -mtime +"$MONTHLY_RETENTION_DAYS" -delete 2>/dev/null || true
find "$MONTHLY_DIR" -name 'monetra-*.dump.sha256' -mtime +"$MONTHLY_RETENTION_DAYS" -delete 2>/dev/null || true

if [[ -n "${MONETRA_BACKUP_S3_URI:-}" ]]; then
  if ! command -v aws >/dev/null 2>&1; then
    fail "MONETRA_BACKUP_S3_URI is set but aws CLI is not installed"
  fi
  sse="${MONETRA_BACKUP_S3_SSE:-AES256}"
  s3_dest="${MONETRA_BACKUP_S3_URI%/}/${FILENAME}"
  log "Uploading to ${s3_dest} (SSE: ${sse})..."
  aws s3 cp "$output" "$s3_dest" --sse "$sse"
  if [[ -f "$checksum_file" ]]; then
    aws s3 cp "$checksum_file" "${s3_dest}.sha256" --sse "$sse"
  fi
fi

log "Wrote ${output} (${bytes} bytes)"
if [[ -f "$checksum_file" ]]; then
  log "Checksum: ${checksum_file}"
fi
