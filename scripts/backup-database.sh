#!/usr/bin/env bash
# Logical PostgreSQL backup for Monetra production.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT}/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILENAME="monetra-${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

if [[ ! -f .env ]]; then
  printf '[backup] ERROR: .env not found\n' >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

if docker inspect monetra-postgres >/dev/null 2>&1; then
  running="$(docker inspect --format '{{.State.Running}}' monetra-postgres 2>/dev/null || echo false)"
else
  running=false
fi

if [[ "$running" != "true" ]]; then
  docker compose -f "$COMPOSE_FILE" up -d postgres
  for _ in $(seq 1 30); do
    if docker compose -f "$COMPOSE_FILE" exec -T postgres \
      pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi

output="${BACKUP_DIR}/${FILENAME}"
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$output"

if [[ ! -s "$output" ]]; then
  printf '[backup] ERROR: backup file is empty\n' >&2
  exit 1
fi

find "$BACKUP_DIR" -name 'monetra-*.dump' -mtime +"$RETENTION_DAYS" -delete 2>/dev/null || true

printf '[backup] Wrote %s (%s bytes)\n' "$output" "$(wc -c < "$output" | tr -d ' ')"
