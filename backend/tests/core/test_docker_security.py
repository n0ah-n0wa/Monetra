"""Docker image security regression tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKEND_DOCKERFILE = ROOT / "backend" / "Dockerfile"
FRONTEND_DOCKERFILE = ROOT / "frontend" / "Dockerfile"
NGINX_DOCKERFILE = ROOT / "nginx" / "Dockerfile"
PROD_COMPOSE = ROOT / "docker-compose.prod.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_backend_production_runs_as_non_root() -> None:
    content = _read(BACKEND_DOCKERFILE)
    _, _, production = content.partition("FROM base AS production")
    assert "USER monetra" in production
    assert production.index("USER monetra") < production.index("ENTRYPOINT")


def test_backend_production_uses_multi_stage_builder() -> None:
    content = _read(BACKEND_DOCKERFILE)
    assert "FROM python:3.13-slim AS builder" in content
    assert "COPY --from=builder /opt/venv /opt/venv" in content


def test_backend_production_installs_runtime_dependencies_only() -> None:
    content = _read(BACKEND_DOCKERFILE)
    _, _, production = content.partition("FROM base AS production")
    assert 'pip install -e ".[dev]"' not in production
    assert "pip install ." in content


def test_backend_production_runs_migrations_on_start() -> None:
    content = _read(BACKEND_DOCKERFILE)
    assert "docker-entrypoint.sh" in content
    entrypoint = _read(ROOT / "backend" / "docker-entrypoint.sh")
    assert "alembic upgrade head" in entrypoint


def test_backend_production_healthcheck_does_not_require_curl() -> None:
    content = _read(BACKEND_DOCKERFILE)
    _, _, production = content.partition("FROM base AS production")
    assert "curl" not in production
    assert "urllib.request" in production


def test_frontend_production_uses_unprivileged_nginx() -> None:
    content = _read(FRONTEND_DOCKERFILE)
    assert "nginxinc/nginx-unprivileged" in content
    assert "NODE_TLS_REJECT_UNAUTHORIZED" not in content


def test_frontend_production_uses_reproducible_install() -> None:
    content = _read(FRONTEND_DOCKERFILE)
    build, _, _ = content.partition("FROM nginxinc/nginx-unprivileged")
    assert "npm ci" in build


def test_nginx_production_uses_unprivileged_image() -> None:
    content = _read(NGINX_DOCKERFILE)
    assert "nginxinc/nginx-unprivileged" in content
    assert "su-exec nginx" in _read(ROOT / "nginx" / "docker-entrypoint.sh")


def test_prod_compose_uses_python_healthcheck_for_backend() -> None:
    content = _read(PROD_COMPOSE)
    assert "curl" not in content
    assert "urllib.request" in content


def test_prod_compose_builds_custom_nginx_image() -> None:
    content = _read(PROD_COMPOSE)
    assert "context: ./nginx" in content


def test_dockerignore_excludes_env_files() -> None:
    for name in ("backend/.dockerignore", "frontend/.dockerignore"):
        content = _read(ROOT / name)
        assert ".env" in content


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is not available")
def test_production_images_run_as_non_root() -> None:
    for image, context, target in (
        ("monetra-backend:security-test", "backend", "production"),
        ("monetra-frontend:security-test", "frontend", "production"),
        ("monetra-nginx:security-test", "nginx", "production"),
    ):
        subprocess.run(
            [
                "docker",
                "build",
                "-t",
                image,
                str(ROOT / context),
                "--target",
                target,
            ],
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "id", image, "-u"],
            check=True,
            capture_output=True,
            text=True,
        )
        uid = result.stdout.strip()
        if image.startswith("monetra-nginx:"):
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--entrypoint",
                    "su-exec",
                    image,
                    "nginx",
                    "id",
                    "-u",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            uid = result.stdout.strip()
        assert uid != "0", f"{image} runs as root"


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is not available")
def test_backend_production_image_has_no_baked_jwt_secret() -> None:
    subprocess.run(
        [
            "docker",
            "build",
            "-t",
            "monetra-backend:security-test",
            str(ROOT / "backend"),
            "--target",
            "production",
        ],
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "env",
            "monetra-backend:security-test",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "JWT_SECRET_KEY=change-me" not in result.stdout
