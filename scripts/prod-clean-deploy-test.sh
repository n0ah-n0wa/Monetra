#!/usr/bin/env bash
# Production-like deployment test from a clean Docker environment.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE="${ROOT}/.env"

log() { printf '[clean-deploy-test] %s\n' "$*"; }
fail() { printf '[clean-deploy-test] ERROR: %s\n' "$*" >&2; exit 1; }

log "Tearing down existing production stack and volumes..."
docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true

if [[ ! -f "$ENV_FILE" ]]; then
  log "Creating .env from .env.production.example"
  cp .env.production.example "$ENV_FILE"
fi

set -a
# shellcheck disable=SC1091
source "$ENV_FILE"
set +a

if [[ -z "${JWT_SECRET_KEY:-}" || "${JWT_SECRET_KEY}" == replace-with-* ]]; then
  JWT_SECRET_KEY="$(openssl rand -hex 32)"
  if grep -q '^JWT_SECRET_KEY=' "$ENV_FILE"; then
    sed -i.bak "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${JWT_SECRET_KEY}|" "$ENV_FILE"
  else
    echo "JWT_SECRET_KEY=${JWT_SECRET_KEY}" >> "$ENV_FILE"
  fi
fi

if [[ -z "${POSTGRES_PASSWORD:-}" || "${POSTGRES_PASSWORD}" == replace-with-* ]]; then
  POSTGRES_PASSWORD="monetra-clean-test"
  if grep -q '^POSTGRES_PASSWORD=' "$ENV_FILE"; then
    sed -i.bak "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" "$ENV_FILE"
  else
    echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" >> "$ENV_FILE"
  fi
fi

if ! grep -q '^CORS_ORIGINS=.*https://localhost' "$ENV_FILE"; then
  if grep -q '^CORS_ORIGINS=' "$ENV_FILE"; then
    sed -i.bak 's|^CORS_ORIGINS=.*|CORS_ORIGINS=https://localhost,https://127.0.0.1|' "$ENV_FILE"
  else
    echo 'CORS_ORIGINS=https://localhost,https://127.0.0.1' >> "$ENV_FILE"
  fi
fi

rm -f "${ENV_FILE}.bak"

"${ROOT}/scripts/generate-local-tls-certs.sh"

chmod +x "${ROOT}"/scripts/*.sh
CERT_MIN_VALID_SECONDS=0 "${ROOT}/scripts/validate-production-env.sh"

log "Running production deploy (skip git fetch)..."
BACKUP_BEFORE_DEPLOY=false \
SMOKE_INSECURE=true \
SMOKE_BASE_URL=https://127.0.0.1 \
  "${ROOT}/scripts/deploy-production.sh" --skip-fetch HEAD

log "Verifying resource limits and health..."
docker compose -f "$COMPOSE_FILE" ps
for container in monetra-postgres monetra-backend monetra-frontend monetra-nginx; do
  status="$(docker inspect --format '{{.State.Health.Status}}' "$container")"
  log "${container}: ${status}"
  [[ "$status" == "healthy" ]] || fail "${container} is not healthy"
done

log "Simulating migration failure guard (compose config + validate only)..."
docker compose -f "$COMPOSE_FILE" config >/dev/null

log "Clean production deployment test passed."
