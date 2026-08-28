"""Security header middleware tests."""

from __future__ import annotations

from app.core.config import Settings
from app.core.middleware import SecurityHeadersMiddleware
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient


async def _ok(_request):
    return PlainTextResponse("ok")


def test_hsts_header_set_in_production_over_https() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret_key="production-secret-key-with-enough-length",
        debug=False,
        cors_origins=["https://app.example.com"],
    )
    app = Starlette(routes=[Route("/", _ok)])
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    client = TestClient(app)
    response = client.get("/", headers={"X-Forwarded-Proto": "https"})
    assert response.headers.get("Strict-Transport-Security") == (
        "max-age=31536000; includeSubDomains"
    )


def test_hsts_header_omitted_for_plain_http() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret_key="production-secret-key-with-enough-length",
        debug=False,
        cors_origins=["https://app.example.com"],
    )
    app = Starlette(routes=[Route("/", _ok)])
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    client = TestClient(app)
    response = client.get("/")
    assert "Strict-Transport-Security" not in response.headers
