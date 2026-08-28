"""Production nginx configuration regression tests."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
NGINX_DIR = ROOT / "nginx"
NGINX_DOCKERFILE = NGINX_DIR / "Dockerfile"
NGINX_MAIN_CONF = NGINX_DIR / "nginx.prod.conf"
NGINX_TEMPLATE = NGINX_DIR / "templates" / "default.conf.template"
NGINX_ENTRYPOINT = NGINX_DIR / "docker-entrypoint.sh"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_nginx_production_uses_env_driven_template() -> None:
    dockerfile = _read(NGINX_DOCKERFILE)
    assert "templates/default.conf.template" in dockerfile
    assert "conf.d/default.prod.conf" not in dockerfile

    template = _read(NGINX_TEMPLATE)
    assert "${NGINX_SERVER_NAME}" in template
    assert "${NGINX_CLIENT_MAX_BODY_SIZE}" in template
    assert "${NGINX_HSTS_DIRECTIVE}" in template
    assert "${NGINX_CSP}" in template


def test_nginx_production_does_not_hardcode_public_domains() -> None:
    content = "\n".join(
        _read(path)
        for path in (
            NGINX_MAIN_CONF,
            NGINX_TEMPLATE,
            NGINX_DIR / "includes" / "proxy_backend.conf",
            NGINX_DIR / "includes" / "proxy_frontend.conf",
        )
    )
    assert not re.search(r"server_name\s+[^_\s;]+\.[^;\s]+", content)
    assert "monetra.example" not in content.lower()


def test_nginx_production_enables_https_architecture() -> None:
    template = _read(NGINX_TEMPLATE)
    assert "listen 8443 ssl" in template
    assert "http2 on" in template
    assert "return 301 https://$host$request_uri" in template
    assert "ssl_protocols TLSv1.2 TLSv1.3" in template


def test_nginx_production_routes_api_and_frontend() -> None:
    template = _read(NGINX_TEMPLATE)
    assert "location /api/" in template
    assert "proxy_pass http://monetra_backend/api/" in template
    assert "proxy_pass http://monetra_frontend" in template
    assert "location = /health" in template
    assert "location = /ready" in template


def test_nginx_production_applies_security_defaults() -> None:
    main_conf = _read(NGINX_MAIN_CONF)
    template = _read(NGINX_TEMPLATE)
    security = _read(NGINX_DIR / "includes" / "security_headers.conf")
    assert "server_tokens off" in main_conf
    assert "X-Content-Type-Options" in security
    assert "X-Frame-Options" in security
    assert "Permissions-Policy" in security
    assert "Content-Security-Policy" in template
    assert "location ~ /\\." in template
    assert "include /etc/nginx/includes/security_headers.conf" in template


def test_nginx_production_enables_compression_and_caching() -> None:
    main_conf = _read(NGINX_MAIN_CONF)
    template = _read(NGINX_TEMPLATE)
    assert "gzip on" in main_conf
    assert "gzip_types" in main_conf
    assert "location ^~ /assets/" in template
    assert "expires 1y" in template
    assert "expires epoch" in template


def test_nginx_production_sets_request_limits_and_timeouts() -> None:
    template = _read(NGINX_TEMPLATE)
    backend_proxy = _read(NGINX_DIR / "includes" / "proxy_backend.conf")
    assert "${NGINX_CLIENT_MAX_BODY_SIZE}" in template
    assert "proxy_connect_timeout" in backend_proxy
    assert "proxy_read_timeout" in backend_proxy
    assert "proxy_read_timeout 120s" in template


def test_nginx_entrypoint_exports_runtime_configuration() -> None:
    entrypoint = _read(NGINX_ENTRYPOINT)
    assert "NGINX_SERVER_NAME" in entrypoint
    assert "NGINX_CLIENT_MAX_BODY_SIZE" in entrypoint
    assert "NGINX_HSTS_DIRECTIVE" in entrypoint
    assert "envsubst" in entrypoint


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is not available")
def test_nginx_production_image_passes_config_test(tmp_path: Path) -> None:
    subprocess.run(
        [
            "docker",
            "build",
            "-t",
            "monetra-nginx:config-test",
            str(NGINX_DIR),
            "--target",
            "production",
        ],
        check=True,
        capture_output=True,
    )
    cert_dir = tmp_path / "certs"
    cert_dir.mkdir()
    if shutil.which("openssl"):
        cert_cmd = [
            "openssl",
            "req",
            "-x509",
            "-nodes",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(cert_dir / "privkey.pem"),
            "-out",
            str(cert_dir / "fullchain.pem"),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
        ]
    else:
        cert_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{cert_dir}:/certs",
            "alpine/openssl",
            "req",
            "-x509",
            "-nodes",
            "-newkey",
            "rsa:2048",
            "-keyout",
            "/certs/privkey.pem",
            "-out",
            "/certs/fullchain.pem",
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
        ]
    subprocess.run(cert_cmd, check=True, capture_output=True)
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{cert_dir}:/etc/nginx/certs-ro:ro",
            "--add-host",
            "backend:127.0.0.1",
            "--add-host",
            "frontend:127.0.0.1",
            "--tmpfs",
            "/etc/nginx/conf.d:uid=0,gid=0,mode=0755",
            "--tmpfs",
            "/var/log/nginx:uid=101,gid=101,mode=0755",
            "--tmpfs",
            "/var/cache/nginx:uid=101,gid=101,mode=0755",
            "--tmpfs",
            "/var/run:uid=101,gid=101,mode=0755",
            "-e",
            "NGINX_HSTS_MAX_AGE=0",
            "--entrypoint",
            "sh",
            "monetra-nginx:config-test",
            "-c",
            "/usr/local/bin/monetra-nginx-entrypoint.sh nginx -t",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "syntax is ok" in result.stderr
    assert "test is successful" in result.stderr
