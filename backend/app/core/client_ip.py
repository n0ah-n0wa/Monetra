"""Resolve the client IP for rate limiting and auditing behind reverse proxies."""

from __future__ import annotations

import ipaddress

from starlette.requests import Request

from app.core.config import Settings

_FORWARDED_FOR_HEADER = "x-forwarded-for"


def _parse_forwarded_for(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def resolve_client_ip(request: Request, settings: Settings) -> str:
    """Return the best-effort client IP for this request.

    When ``trusted_proxy_count`` is greater than zero, the leftmost untrusted
    hop from ``X-Forwarded-For`` is used (nginx appends the connecting client).
    Without trusted proxies, only ``request.client.host`` is trusted so clients
    cannot spoof their IP through forwarded headers.
    """
    direct = request.client.host if request.client is not None else "unknown"

    if settings.trusted_proxy_count <= 0:
        return direct

    forwarded = request.headers.get(_FORWARDED_FOR_HEADER)
    if not forwarded:
        return direct

    chain = [ip for ip in _parse_forwarded_for(forwarded) if _is_valid_ip(ip)]
    if not chain:
        return direct

    # With one trusted proxy (nginx), the client is the first hop.
    index = len(chain) - settings.trusted_proxy_count
    if index < 0:
        return chain[0]
    return chain[index]
