#!/usr/bin/env bash
# Roll back Monetra to a previous Git ref without running forward migrations.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ $# -lt 1 ]]; then
  printf 'Usage: %s <git-ref>\n' "$0" >&2
  exit 1
fi

ROLLBACK_REF="$1"
COMPOSE_FILE="docker-compose.prod.yml"

printf '[rollback] WARNING: Rolling back application code to %s\n' "$ROLLBACK_REF" >&2
printf '[rollback] Database schema is NOT downgraded automatically.\n' >&2
printf '[rollback] Only use when the target ref is schema-compatible with the current DB.\n' >&2

git fetch origin --tags --prune
git checkout "$ROLLBACK_REF"

docker compose -f "$COMPOSE_FILE" build
RUN_DB_MIGRATIONS=false docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

exec "$ROOT/scripts/smoke-production.sh" "${SMOKE_BASE_URL:-https://127.0.0.1}"
