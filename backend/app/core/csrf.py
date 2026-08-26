"""CSRF mitigation helpers for cookie-authenticated auth endpoints."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import Request

from app.core.config import Settings
from app.core.exceptions import ForbiddenError


def _origin_allowed(origin: str, allowed_origins: list[str]) -> bool:
    normalized = origin.rstrip("/")
    return normalized in {item.rstrip("/") for item in allowed_origins}


def _referer_allowed(referer: str, allowed_origins: list[str]) -> bool:
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return False
    referer_origin = f"{parsed.scheme}://{parsed.netloc}"
    return _origin_allowed(referer_origin, allowed_origins)


def validate_cookie_auth_origin(request: Request, settings: Settings) -> None:
    """Reject cross-site cookie-authenticated requests when origin is untrusted.

    Browser clients send ``Origin`` on CORS/fetch requests. When absent in
    production, the request is rejected because cookie auth cannot be verified
    as same-site. Development and test environments allow missing origin headers
    to support local tooling and automated tests.
    """
    origin = request.headers.get("origin")
    if origin and not _origin_allowed(origin, settings.cors_origins):
        raise ForbiddenError(
            code="FORBIDDEN",
            message="Origin is not allowed.",
        )

    referer = request.headers.get("referer")
    if referer and not _referer_allowed(referer, settings.cors_origins):
        raise ForbiddenError(
            code="FORBIDDEN",
            message="Referer is not allowed.",
        )

    if settings.is_production and not origin and not referer:
        raise ForbiddenError(
            code="FORBIDDEN",
            message="Origin verification is required.",
        )
