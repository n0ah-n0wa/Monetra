#!/usr/bin/env bash
# Validate production .env, TLS certificates, and Compose configuration.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
CERT_MIN_VALID_SECONDS="${CERT_MIN_VALID_SECONDS:-86400}"
DEFAULT_JWT_PATTERN='change-me-in-production-use-a-long-random-secret'

fail() {
  printf '[validate] ERROR: %s\n' "$*" >&2
  exit 1
}

warn() {
  printf '[validate] WARN: %s\n' "$*" >&2
}

log() {
  printf '[validate] %s\n' "$*"
}

[[ -f .env ]] || fail ".env not found in ${ROOT}"

set -a
# shellcheck disable=SC1091
source .env
set +a

for var in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD JWT_SECRET_KEY; do
  if [[ -z "${!var:-}" ]]; then
    fail "${var} is required in .env"
  fi
done

if [[ "${#JWT_SECRET_KEY}" -lt 32 ]]; then
  fail "JWT_SECRET_KEY must be at least 32 characters"
fi

if [[ "$JWT_SECRET_KEY" == "$DEFAULT_JWT_PATTERN" ]] || [[ "$JWT_SECRET_KEY" == change-me* ]]; then
  fail "JWT_SECRET_KEY must not use the development default"
fi

if [[ "${CORS_ORIGINS:-}" == *"*"* ]]; then
  fail "CORS_ORIGINS must not contain wildcard '*' in production"
fi

for cert in nginx/certs/fullchain.pem nginx/certs/privkey.pem; do
  [[ -f "$cert" ]] || fail "Missing TLS certificate: ${cert}"
done

if command -v openssl >/dev/null 2>&1; then
  if ! openssl x509 -in nginx/certs/fullchain.pem -noout -checkend "$CERT_MIN_VALID_SECONDS" >/dev/null 2>&1; then
    expiry="$(openssl x509 -in nginx/certs/fullchain.pem -noout -enddate 2>/dev/null || echo unknown)"
    fail "TLS certificate expires within ${CERT_MIN_VALID_SECONDS}s (${expiry})"
  fi
  cert_mod="$(openssl x509 -noout -modulus -in nginx/certs/fullchain.pem | openssl md5)"
  key_mod="$(openssl pkey -noout -modulus -in nginx/certs/privkey.pem 2>/dev/null | openssl md5)"
  if [[ "$cert_mod" != "$key_mod" ]]; then
    fail "TLS fullchain.pem and privkey.pem do not match"
  fi
else
  warn "openssl not available; skipping TLS expiry and key-pair checks"
fi

if [[ "${APP_ENV:-}" != "production" ]]; then
  fail "APP_ENV must be production (got: ${APP_ENV:-unset})"
fi

if [[ "${DEBUG:-false}" == "true" ]]; then
  fail "DEBUG must be false in production"
fi

if ! docker compose -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
  fail "docker compose config failed for ${COMPOSE_FILE}"
fi

log "Production environment validation passed."
