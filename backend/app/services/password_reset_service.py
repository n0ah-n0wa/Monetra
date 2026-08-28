"""Password reset service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    generate_password_reset_token,
    hash_opaque_token,
    hash_password,
)
from app.domain.email import normalize_email
from app.domain.notifications import NotificationProvider, PasswordResetNotification
from app.domain.password_policy import validate_password
from app.repositories import password_reset_token_repository as reset_repo
from app.repositories import refresh_token_repository as refresh_repo
from app.repositories import user_repository as user_repo

RESET_REQUEST_ACK_MESSAGE = (
    "If an account exists for this email, password reset instructions have been sent."
)


async def request_password_reset(
    session: AsyncSession,
    *,
    email: str,
    settings: Settings,
    notification_provider: NotificationProvider,
) -> str:
    """Queue a password reset email when the account exists.

    Always returns the same acknowledgement message to prevent email enumeration.
    """
    normalized_email = normalize_email(email)
    user = await user_repo.get_user_by_email(session, normalized_email)
    if user is not None:
        now = datetime.now(UTC)
        cooldown = timedelta(seconds=settings.password_reset_request_cooldown_seconds)
        active = await reset_repo.get_latest_active_reset_token_for_user(
            session,
            user.id,
        )
        if active is not None and active.created_at > now - cooldown:
            return RESET_REQUEST_ACK_MESSAGE

        await reset_repo.invalidate_active_tokens_for_user(session, user.id)
        reset_token = generate_password_reset_token()
        expires_at = _reset_expiry(settings)
        await reset_repo.create_password_reset_token(
            session,
            user_id=user.id,
            token_hash=hash_opaque_token(reset_token),
            expires_at=expires_at,
        )
        await notification_provider.send_password_reset(
            PasswordResetNotification(
                to_email=user.email,
                reset_token=reset_token,
                expires_at=expires_at,
            ),
        )
        await session.commit()
    return RESET_REQUEST_ACK_MESSAGE


async def confirm_password_reset(
    session: AsyncSession,
    *,
    token: str,
    new_password: str,
    settings: Settings,
) -> None:
    """Replace the user's password using a valid single-use reset token."""
    validate_password(new_password, settings)
    token_hash = hash_opaque_token(token)
    stored = await reset_repo.get_password_reset_token_by_hash(session, token_hash)
    if stored is None or stored.used_at is not None:
        raise UnauthorizedError(
            code="INVALID_RESET_TOKEN",
            message="Password reset token is invalid or expired.",
        )

    now = datetime.now(UTC)
    if stored.expires_at <= now:
        await reset_repo.mark_password_reset_token_used(session, stored)
        await session.commit()
        raise UnauthorizedError(
            code="INVALID_RESET_TOKEN",
            message="Password reset token is invalid or expired.",
        )

    user = await user_repo.get_user_by_id(session, stored.user_id)
    if user is None:
        raise UnauthorizedError(
            code="INVALID_RESET_TOKEN",
            message="Password reset token is invalid or expired.",
        )

    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(UTC) + timedelta(seconds=1)
    await reset_repo.mark_password_reset_token_used(session, stored)
    await refresh_repo.revoke_all_refresh_tokens_for_user(session, user.id)
    await session.commit()


def _reset_expiry(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(
        minutes=settings.password_reset_token_expire_minutes,
    )
