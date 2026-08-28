"""HTTP middleware for cross-cutting concerns.

Implemented as pure ASGI middleware so FastAPI exception handlers remain
effective (BaseHTTPMiddleware can re-raise and bypass handlers).
"""

import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.request_context import reset_request_id, set_request_id

REQUEST_ID_HEADER = "X-Request-ID"


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
