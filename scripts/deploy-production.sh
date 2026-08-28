#!/usr/bin/env bash
# Deploy Monetra production stack on the EC2 host.
# Intended to run on the server (manually or via GitHub Actions over SSH).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="docker-compose.prod.yml"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-300}"
SKIP_FETCH=false
DEPLOY_REF="main"

for arg in "$@"; do
  case "$arg" in
    --skip-fetch) SKIP_FETCH=true ;;
    -h | --help)
      printf 'Usage: %s [--skip-fetch] [git-ref]\n' "$0"
      exit 0
      ;;
    *)
      DEPLOY_REF="$arg"
      ;;
  esac
done

log() {
  printf '[deploy] %s\n' "$*"
}

fail() {
  printf '[deploy] ERROR: %s\n' "$*" >&2
  printf '[deploy] Collecting diagnostic output...\n' >&2
  docker compose -f "$COMPOSE_FILE" ps 2>/dev/null || true
  docker compose -f "$COMPOSE_FILE" logs --tail=80 backend postgres nginx 2>/dev/null || true
  exit 1
}

on_error() {
  printf '[deploy] Deployment failed.\n' >&2
}
trap on_error ERR

if [[ "$SKIP_FETCH" != "true" ]]; then
  log "Fetching source (${DEPLOY_REF})..."
  git fetch origin --tags --prune
  git checkout "$DEPLOY_REF"
  if git symbolic-ref -q HEAD >/dev/null 2>&1; then
    git pull --ff-only origin "$(git symbolic-ref --short HEAD)"
  fi
else
  log "Skipping git fetch (--skip-fetch); deploying current checkout."
fi

chmod +x "$ROOT"/scripts/validate-production-env.sh \
  "$ROOT"/scripts/smoke-production.sh \
  "$ROOT"/scripts/backup-database.sh \
  "$ROOT"/scripts/restore-database.sh \
  "$ROOT"/scripts/test-backup-restore.sh 2>/dev/null || true

"$ROOT/scripts/validate-production-env.sh"

set -a
# shellcheck disable=SC1091
source .env
set +a

if docker inspect monetra-postgres >/dev/null 2>&1; then
  pg_running="$(docker inspect --format '{{.State.Running}}' monetra-postgres 2>/dev/null || echo false)"
else
  pg_running=false
fi

if [[ "${BACKUP_BEFORE_DEPLOY:-true}" == "true" ]]; then
  if [[ "$pg_running" == "true" ]]; then
    log "Creating pre-deploy database backup..."
    "$ROOT/scripts/backup-database.sh"
  else
    log "Skipping backup (PostgreSQL not yet running — first deploy)."
  fi
fi

log "Building production images..."
docker compose -f "$COMPOSE_FILE" build

log "Ensuring PostgreSQL is running..."
docker compose -f "$COMPOSE_FILE" up -d postgres

log "Waiting for PostgreSQL to become healthy..."
deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
until docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    fail "PostgreSQL did not become ready within ${HEALTH_TIMEOUT_SECONDS}s"
  fi
  sleep 3
done

log "Applying database migrations..."
if ! docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
  --entrypoint alembic backend upgrade head; then
  fail "Database migration failed. Deployment aborted before service restart."
fi

log "Starting application services (migrations already applied)..."
RUN_DB_MIGRATIONS=false docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

log "Waiting for container health checks..."
containers=(monetra-postgres monetra-backend monetra-frontend monetra-nginx)
deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
healthy=0
while (( SECONDS < deadline )); do
  healthy=1
  for container in "${containers[@]}"; do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container" 2>/dev/null || echo missing)"
    if [[ "$status" == "missing" ]]; then
      log "Container ${container} not found yet"
      healthy=0
      continue
    fi
    if [[ "$status" != "healthy" ]]; then
      log "Container ${container} status=${status}"
      healthy=0
    fi
  done
  if [[ "$healthy" -eq 1 ]]; then
    break
  fi
  sleep 5
done

if [[ "$healthy" -ne 1 ]]; then
  fail "One or more services did not become healthy within ${HEALTH_TIMEOUT_SECONDS}s"
fi

log "Running on-host smoke checks..."
SMOKE_INSECURE="${SMOKE_INSECURE:-true}" \
  "$ROOT/scripts/smoke-production.sh" "${SMOKE_BASE_URL:-https://127.0.0.1}"

log "Deployment completed successfully."
