"""Telemetry integration boundaries for OpenTelemetry and Sentry.

The initial implementation is intentionally lightweight: hooks and context
fields exist so future SDK wiring does not require middleware or logging
rewrites. When disabled, all functions are no-ops.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

from app.core.config import Settings

trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)
span_id_ctx: ContextVar[str | None] = ContextVar("span_id", default=None)


def get_trace_id() -> str | None:
    return trace_id_ctx.get()


def get_span_id() -> str | None:
    return span_id_ctx.get()


def set_trace_context(
    *,
    trace_id: str | None,
    span_id: str | None,
) -> tuple[Token[str | None], Token[str | None]]:
    """Bind trace identifiers for the current context."""
    trace_token = trace_id_ctx.set(trace_id)
    span_token = span_id_ctx.set(span_id)
    return trace_token, span_token


def reset_trace_context(
    trace_token: Token[str | None],
    span_token: Token[str | None],
) -> None:
    trace_id_ctx.reset(trace_token)
    span_id_ctx.reset(span_token)


def init_observability(settings: Settings) -> dict[str, Any]:
    """Initialize optional telemetry backends.

    Returns provider metadata for structured startup logs. SDK wiring is added
    here when OpenTelemetry or Sentry are enabled in a future change.
    """
    providers: dict[str, Any] = {
        "otel_enabled": settings.otel_enabled,
        "sentry_enabled": bool(settings.sentry_dsn),
    }
    if settings.otel_enabled:
        providers["otel_exporter"] = settings.otel_exporter
    return providers


def shutdown_observability() -> None:
    """Flush and shut down telemetry providers when configured."""
