#!/usr/bin/env bash
# Smoke-test a running Monetra production deployment through the edge proxy.
set -euo pipefail

BASE_URL="${1:?Base URL required, e.g. https://app.example.com}"
SMOKE_INSECURE="${SMOKE_INSECURE:-false}"
HTTP_BASE_URL="${SMOKE_HTTP_BASE_URL:-${BASE_URL/https:/http:}}"

curl_args=(-fsS)
if [[ "$SMOKE_INSECURE" == "true" ]]; then
  curl_args+=(-k)
fi

check_status() {
  local base="$1"
  local method="$2"
  local path="$3"
  local expected="$4"
  local label="$5"
  local status

  status="$(curl "${curl_args[@]}" -o /dev/null -w '%{http_code}' -X "$method" "${base}${path}")"
  if [[ "$status" != "$expected" ]]; then
    printf '[smoke] ERROR: %s expected HTTP %s, got %s\n' "$label" "$expected" "$status" >&2
    exit 1
  fi
  printf '[smoke] OK %s %s -> %s\n' "$method" "$path" "$status"
}

printf '[smoke] Verifying %s\n' "$BASE_URL"

check_status "$HTTP_BASE_URL" GET /nginx-health 200 "nginx health (HTTP)"
check_status "$BASE_URL" GET /health 200 "API health"
check_status "$BASE_URL" GET /ready 200 "API readiness"
check_status "$BASE_URL" GET / 200 "frontend root"
check_status "$BASE_URL" GET /api/v1/users/me 401 "protected API route"

if [[ "$BASE_URL" == https://* ]]; then
  check_status "$HTTP_BASE_URL" GET /health 301 "HTTP to HTTPS redirect"
fi

printf '[smoke] All checks passed.\n'
