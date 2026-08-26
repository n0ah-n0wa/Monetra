"""Shared FastAPI dependencies."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.csrf import validate_cookie_auth_origin
from app.core.exceptions import RateLimitError, UnauthorizedError
from app.core.rate_limit import get_rate_limiter
from app.core.security import assert_access_token_active_for_user, decode_access_token
from app.db.session import get_db
from app.domain.notifications import NotificationProvider
from app.models.user import User
from app.repositories import user_repository as user_repo
from app.services.notification_providers import get_notification_provider


def get_app_settings(request: Request) -> Settings:
    """Return settings bound to the running app (supports create_app overrides)."""
    bound = getattr(request.app.state, "settings", None)
    if isinstance(bound, Settings):
        return bound
    return get_settings()


def get_app_notification_provider(request: Request) -> NotificationProvider:
    return get_notification_provider(request.app)


async def enforce_auth_rate_limit(request: Request, settings: SettingsDep) -> None:
    client = request.client
    client_host = client.host if client is not None else "unknown"
    key = f"{client_host}:{request.url.path}"
    limiter = get_rate_limiter(request.app)
    allowed = limiter.allow(
        key,
        limit=settings.auth_rate_limit_max_requests,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )
    if not allowed:
        raise RateLimitError()


async def enforce_cookie_auth_origin(request: Request, settings: SettingsDep) -> None:
    validate_cookie_auth_origin(request, settings)


async def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise UnauthorizedError(
            code="UNAUTHORIZED",
            message="Authentication is required.",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise UnauthorizedError(
            code="UNAUTHORIZED",
            message="Authentication is required.",
        )

    payload = decode_access_token(token, settings=settings)
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise UnauthorizedError(
            code="INVALID_TOKEN",
            message="Token is invalid or expired.",
        )

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise UnauthorizedError(
            code="INVALID_TOKEN",
            message="Token is invalid or expired.",
        ) from exc

    user = await user_repo.get_user_by_id(session, user_id)
    if user is None:
        raise UnauthorizedError(
            code="INVALID_TOKEN",
            message="Token is invalid or expired.",
        )
    assert_access_token_active_for_user(
        payload,
        password_changed_at=user.password_changed_at,
    )
    return user


SessionDep = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
NotificationProviderDep = Annotated[
    NotificationProvider,
    Depends(get_app_notification_provider),
]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

__all__ = [
    "CurrentUserDep",
    "NotificationProviderDep",
    "SessionDep",
    "SettingsDep",
    "enforce_auth_rate_limit",
    "enforce_cookie_auth_origin",
    "get_app_notification_provider",
    "get_app_settings",
    "get_current_user",
    "get_db",
    "get_settings",
]
