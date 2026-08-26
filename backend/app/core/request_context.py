"""Request-scoped context values (correlation IDs)."""

from contextvars import ContextVar, Token

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def set_request_id(request_id: str) -> Token[str | None]:
    """Bind a request ID for the current context; return a reset token."""
    return request_id_ctx.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the previous request ID binding."""
    request_id_ctx.reset(token)
