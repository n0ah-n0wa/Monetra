"""Password reset token persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken


async def get_password_reset_token_by_hash(
    session: AsyncSession,
    token_hash: str,
) -> PasswordResetToken | None:
    result = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
        ),
    )
    return result.scalar_one_or_none()


async def create_password_reset_token(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> PasswordResetToken:
    token = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(token)
    await session.flush()
    return token


async def invalidate_active_tokens_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    """Mark outstanding reset tokens as used so only the latest request is valid."""
    now = datetime.now(UTC)
    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now),
    )
    await session.flush()


async def mark_password_reset_token_used(
    session: AsyncSession,
    token: PasswordResetToken,
) -> None:
    token.used_at = datetime.now(UTC)
    await session.flush()
