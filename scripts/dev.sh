#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

cmd="${1:-help}"

backend() {
  (cd "$ROOT/backend" && "$@")
}

frontend() {
  (cd "$ROOT/frontend" && "$@")
}

case "$cmd" in
  help)
    cat <<'EOF'
Monetra development commands
  ./scripts/dev.sh install       Install dependencies
  ./scripts/dev.sh up            Start Docker Compose
  ./scripts/dev.sh down          Stop Docker Compose
  ./scripts/dev.sh lint          Lint backend and frontend
  ./scripts/dev.sh typecheck     Type-check backend and frontend
  ./scripts/dev.sh test          Run unit tests
  ./scripts/dev.sh build         Build frontend
  ./scripts/dev.sh docker-build  Build Docker images
  ./scripts/dev.sh prod-build    Build production Docker images
  ./scripts/dev.sh prod-up       Start production Compose stack
  ./scripts/dev.sh prod-down     Stop production Compose stack
  ./scripts/dev.sh prod-verify   Build and smoke-test production stack
  ./scripts/dev.sh prod-clean-test  Clean-volume production deploy test
  ./scripts/dev.sh backup-restore-test  Backup/restore drill (non-production)
  ./scripts/dev.sh verify        Full quality gate
  ./scripts/dev.sh loadtest      Run API load tests (local stack)
EOF
    ;;
  install)
    backend python -m pip install -e ".[dev]"
    frontend npm install
    ;;
  up)
    docker compose up --build -d
    ;;
  down)
    docker compose down
    ;;
  lint)
    backend ruff check app tests
    backend ruff format --check app tests
    frontend npm run lint
    frontend npm run format:check
    ;;
  typecheck)
    backend mypy app
    frontend npm run typecheck
    ;;
  test)
    backend pytest
    frontend npm run test
    ;;
  build)
    frontend npm run build
    ;;
  docker-build)
    docker compose build
    docker compose -f docker-compose.prod.yml build
    ;;
  prod-build)
    docker compose -f docker-compose.prod.yml build
    ;;
  prod-up)
    ./scripts/generate-local-tls-certs.sh
    docker compose -f docker-compose.prod.yml up --build -d
    ;;
  prod-down)
    docker compose -f docker-compose.prod.yml down
    ;;
  prod-verify)
    ./scripts/generate-local-tls-certs.sh
    export JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(openssl rand -hex 32)}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-monetra}"
    export POSTGRES_DB="${POSTGRES_DB:-monetra}"
    export POSTGRES_USER="${POSTGRES_USER:-monetra}"
    docker compose down || true
    docker compose -f docker-compose.prod.yml down || true
    docker compose -f docker-compose.prod.yml up --build -d
    sleep 30
    curl -f http://localhost/nginx-health
    curl -k -f https://localhost/health
    curl -k -f https://localhost/ready
    curl -k -f https://localhost/
    status="$(curl -k -s -o /dev/null -w '%{http_code}' https://localhost/api/v1/users/me)"
    if [ "$status" != "401" ]; then
      echo "Protected API route expected 401, got ${status}" >&2
      exit 1
    fi
    status="$(curl -s -o /dev/null -w '%{http_code}' http://localhost/health)"
    if [ "$status" != "301" ]; then
      echo "HTTP to HTTPS redirect expected 301, got ${status}" >&2
      exit 1
    fi
    echo "Production stack smoke checks passed."
    ;;
  prod-clean-test)
    ./scripts/prod-clean-deploy-test.sh
    ;;
  backup-restore-test)
    ./scripts/test-backup-restore.sh
    ;;
  verify)
    "$0" lint
    "$0" typecheck
    "$0" test
    "$0" build
    "$0" docker-build
    echo "Verification complete."
    ;;
  loadtest)
    shift
    backend python -m loadtest --quick-seed "$@"
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    exit 1
    ;;
esac
