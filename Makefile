.PHONY: help install install-backend install-frontend up down logs ps \
	lint lint-backend lint-frontend typecheck typecheck-backend typecheck-frontend \
	test test-backend test-frontend build build-frontend docker-build verify \
	fmt fmt-backend fmt-frontend

help:
	@echo "Monetra development commands"
	@echo "  make install           Install backend and frontend dependencies"
	@echo "  make up                Start Docker Compose stack"
	@echo "  make down              Stop Docker Compose stack"
	@echo "  make lint              Lint backend and frontend"
	@echo "  make typecheck         Type-check backend and frontend"
	@echo "  make test              Run backend and frontend unit tests"
	@echo "  make build             Build frontend production bundle"
	@echo "  make docker-build      Build all Docker images"
	@echo "  make verify            Full quality gate (lint, typecheck, test, build)"

install: install-backend install-frontend

install-backend:
	cd backend && python -m pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check app tests && ruff format --check app tests

lint-frontend:
	cd frontend && npm run lint && npm run format:check

fmt: fmt-backend fmt-frontend

fmt-backend:
	cd backend && ruff check --fix app tests && ruff format app tests

fmt-frontend:
	cd frontend && npm run lint:fix && npm run format

typecheck: typecheck-backend typecheck-frontend

typecheck-backend:
	cd backend && mypy app

typecheck-frontend:
	cd frontend && npm run typecheck

test: test-backend test-frontend

test-backend:
	cd backend && pytest

test-frontend:
	cd frontend && npm run test

build: build-frontend

build-frontend:
	cd frontend && npm run build

docker-build:
	docker compose build
	docker build -t monetra-frontend:local ./frontend --target production

verify: lint typecheck test build docker-build
	@echo "Verification complete."
