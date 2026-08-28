"""Authentication service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.domain.email import normalize_email
from app.domain.password_policy import validate_password
from app.models.user import User
from app.repositories import refresh_token_repository as refresh_repo
from app.repositories import user_repository as user_repo
from app.services.default_categories import build_default_categories


@dataclass(frozen=True, slots=True)
class AuthTokens:
    access_token: str
    refresh_token: str
    expires_in: int


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    settings: Settings,
) -> tuple[User, AuthTokens]:
    normalized_email = normalize_email(email)
    validate_password(password, settings)

    existing = await user_repo.get_user_by_email(session, normalized_email)
    if existing is not None:
        raise ConflictError(
            code="REGISTRATION_FAILED",
            message=(
                "Unable to complete registration. "
                "Please try again or sign in."
            ),
        )

    user = await user_repo.create_user(
        session,
        email=normalized_email,
        password_hash=hash_password(password),
    )
    for category in build_default_categories(user.id):
        session.add(category)
    await session.flush()

    tokens = await _issue_tokens(session, user=user, settings=settings)
    await session.commit()
    return user, tokens


async def login_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    settings: Settings,
) -> tuple[User, AuthTokens]:
    normalized_email = normalize_email(email)
    user = await user_repo.get_user_by_email(session, normalized_email)
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError(
            code="INVALID_CREDENTIALS",
            message="Invalid email or password.",
        )

    tokens = await _issue_tokens(session, user=user, settings=settings)
    await session.commit()
    return user, tokens


async def refresh_session(
    session: AsyncSession,
    *,
    refresh_token: str,
    settings: Settings,
) -> AuthTokens:
    token_hash = hash_refresh_token(refresh_token)
    stored = await refresh_repo.get_refresh_token_by_hash(session, token_hash)
    if stored is None:
        raise UnauthorizedError(
            code="INVALID_REFRESH_TOKEN",
            message="Refresh token is invalid or expired.",
        )

    now = datetime.now(UTC)
    if stored.revoked_at is not None:
        await refresh_repo.revoke_refresh_token_family(session, stored.family_id)
        await session.commit()
        raise UnauthorizedError(
            code="INVALID_REFRESH_TOKEN",
            message="Refresh token is invalid or expired.",
        )

    if stored.expires_at <= now:
        await refresh_repo.revoke_refresh_token(session, stored)
        await session.commit()
        raise UnauthorizedError(
            code="INVALID_REFRESH_TOKEN",
            message="Refresh token is invalid or expired.",
        )

    user = await user_repo.get_user_by_id(session, stored.user_id)
    if user is None:
        raise UnauthorizedError(
            code="INVALID_REFRESH_TOKEN",
            message="Refresh token is invalid or expired.",
        )

    new_refresh_value = generate_refresh_token()
    new_refresh = await refresh_repo.create_refresh_token(
        session,
        user_id=user.id,
        token_hash=hash_refresh_token(new_refresh_value),
        family_id=stored.family_id,
        expires_at=_refresh_expiry(settings),
    )
    await refresh_repo.revoke_refresh_token(
        session,
        stored,
        replaced_by_token_id=new_refresh.id,
    )
    await session.commit()

    return AuthTokens(
        access_token=create_access_token(str(user.id), settings=settings),
        refresh_token=new_refresh_value,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def logout_user(
    session: AsyncSession,
    *,
    refresh_token: str | None,
) -> None:
    if not refresh_token:
        return
    token_hash = hash_refresh_token(refresh_token)
    stored = await refresh_repo.get_refresh_token_by_hash(session, token_hash)
    if stored is None or stored.revoked_at is not None:
        return
    await refresh_repo.revoke_refresh_token(session, stored)
    await session.commit()


async def _issue_tokens(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
) -> AuthTokens:
    refresh_value = generate_refresh_token()
    family_id = uuid.uuid4()
    await refresh_repo.create_refresh_token(
        session,
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_value),
        family_id=family_id,
        expires_at=_refresh_expiry(settings),
    )
    return AuthTokens(
        access_token=create_access_token(str(user.id), settings=settings),
        refresh_token=refresh_value,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def _refresh_expiry(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
