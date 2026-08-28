"""Client IP resolution tests."""

from __future__ import annotations

from app.core.client_ip import resolve_client_ip
from app.core.config import Settings
from starlette.requests import Request


def _request(
    *,
    client_host: str = "10.0.0.5",
    forwarded_for: str | None = None,
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "client": (client_host, 12345),
        "server": ("test", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_resolve_client_ip_ignores_forwarded_without_trusted_proxies() -> None:
    settings = Settings(trusted_proxy_count=0)
    request = _request(client_host="10.0.0.5", forwarded_for="203.0.113.50")
    assert resolve_client_ip(request, settings) == "10.0.0.5"


def test_resolve_client_ip_uses_forwarded_with_trusted_proxy() -> None:
    settings = Settings(trusted_proxy_count=1)
    request = _request(client_host="172.18.0.4", forwarded_for="203.0.113.50")
    assert resolve_client_ip(request, settings) == "203.0.113.50"


def test_resolve_client_ip_falls_back_to_direct_host() -> None:
    settings = Settings(trusted_proxy_count=1)
    request = _request(client_host="172.18.0.4")
    assert resolve_client_ip(request, settings) == "172.18.0.4"
