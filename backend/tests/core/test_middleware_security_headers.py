"""Security header middleware tests."""

from __future__ import annotations

from app.core.config import Settings
from app.core.middleware import SecurityHeadersMiddleware
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


async def _ok(_request):
    return PlainTextResponse("ok")


async def _get_headers(
    settings: Settings,
    *,
    forwarded_proto: str | None = None,
) -> dict[str, str]:
    app = Starlette(routes=[Route("/", _ok)])
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    headers = {"X-Forwarded-Proto": forwarded_proto} if forwarded_proto else {}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/", headers=headers)
    return dict(response.headers)


async def test_hsts_header_set_in_production_over_https() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret_key="production-secret-key-with-enough-length",
        debug=False,
        cors_origins=["https://app.example.com"],
    )
    headers = await _get_headers(settings, forwarded_proto="https")
    assert headers.get("strict-transport-security") == (
        "max-age=31536000; includeSubDomains"
    )


async def test_hsts_header_omitted_for_plain_http() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret_key="production-secret-key-with-enough-length",
        debug=False,
        cors_origins=["https://app.example.com"],
    )
    headers = await _get_headers(settings)
    assert "strict-transport-security" not in headers
