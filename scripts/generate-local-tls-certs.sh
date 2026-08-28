#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$ROOT/nginx/certs"

mkdir -p "$CERT_DIR"

if [[ -f "$CERT_DIR/fullchain.pem" && -f "$CERT_DIR/privkey.pem" ]]; then
  echo "TLS certificates already exist in nginx/certs"
  exit 0
fi

openssl req -x509 -nodes -newkey rsa:4096 \
  -keyout "$CERT_DIR/privkey.pem" \
  -out "$CERT_DIR/fullchain.pem" \
  -days 365 \
  -subj "/CN=localhost/O=Monetra Local Production/C=US"

echo "Generated self-signed TLS certificates in nginx/certs"
