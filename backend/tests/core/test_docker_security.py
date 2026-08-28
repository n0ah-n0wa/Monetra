"""Docker image security regression tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKEND_DOCKERFILE = ROOT / "backend" / "Dockerfile"
FRONTEND_DOCKERFILE = ROOT / "frontend" / "Dockerfile"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_backend_production_runs_as_non_root() -> None:
    content = _read(BACKEND_DOCKERFILE)
    _, _, production = content.partition("FROM base AS production")
    assert "USER monetra" in production
    assert production.index("USER monetra") < production.index("CMD")


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


def test_dockerignore_excludes_env_files() -> None:
    for name in ("backend/.dockerignore", "frontend/.dockerignore"):
        content = _read(ROOT / name)
        assert ".env" in content


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is not available")
def test_production_images_run_as_non_root() -> None:
    for image, context, target in (
        ("monetra-backend:security-test", "backend", "production"),
        ("monetra-frontend:security-test", "frontend", "production"),
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
            ["docker", "run", "--rm", image, "id", "-u"],
            check=True,
            capture_output=True,
            text=True,
        )
        uid = result.stdout.strip()
        assert uid != "0", f"{image} runs as root"
