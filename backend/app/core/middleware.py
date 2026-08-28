"""HTTP middleware for cross-cutting concerns.

Implemented as pure ASGI middleware so FastAPI exception handlers remain
effective (BaseHTTPMiddleware can re-raise and bypass handlers).
"""

from __future__ import annotations

import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.logging import get_logger, log_event
from app.core.request_context import reset_request_id, set_request_id

REQUEST_ID_HEADER = "X-Request-ID"
logger = get_logger(__name__)


class RequestIdMiddleware:
    """Propagate or generate a request/correlation ID for each request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        header_map = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        incoming = header_map.get(REQUEST_ID_HEADER.lower(), "")
        request_id = incoming.strip() if incoming.strip() else str(uuid.uuid4())

        # Persist on scope.state so ServerErrorMiddleware handlers (outside this
        # middleware) can still resolve the correlation ID after context reset.
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id
        token = set_request_id(request_id)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            reset_request_id(token)


class AccessLogMiddleware:
    """Emit structured HTTP access logs with latency and status."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.app = app
        self._settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = self._settings
        if settings is not None and not settings.access_log_enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if settings is not None and path in settings.access_log_skip_paths:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        started = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            log_event(
                logger,
                "http.request.completed",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
            )


class SecurityHeadersMiddleware:
    """Attach baseline security headers to every response."""

    def __init__(self, app: ASGIApp, *, settings: Settings | None = None) -> None:
        self.app = app
        self._settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        header_map = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        forwarded_proto = header_map.get("x-forwarded-proto", "").split(",")[0].strip()
        is_https = forwarded_proto == "https"

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault(
                    "Referrer-Policy",
                    "strict-origin-when-cross-origin",
                )
                headers.setdefault(
                    "Permissions-Policy",
                    "geolocation=(), microphone=(), camera=()",
                )
                settings = self._settings
                if settings is not None and settings.is_production and is_https:
                    headers.setdefault(
                        "Strict-Transport-Security",
                        "max-age=31536000; includeSubDomains",
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)
