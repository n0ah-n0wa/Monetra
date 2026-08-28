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
    docker build -t monetra-frontend:local ./frontend --target production
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
