"""Refresh token persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


async def get_refresh_token_by_hash(
    session: AsyncSession,
    token_hash: str,
) -> RefreshToken | None:
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash),
    )
    return result.scalar_one_or_none()


async def create_refresh_token(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    family_id: uuid.UUID,
    expires_at: datetime,
) -> RefreshToken:
    token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        family_id=family_id,
        expires_at=expires_at,
    )
    session.add(token)
    await session.flush()
    return token


async def revoke_refresh_token(
    session: AsyncSession,
    token: RefreshToken,
    *,
    replaced_by_token_id: uuid.UUID | None = None,
) -> None:
    token.revoked_at = datetime.now(UTC)
    if replaced_by_token_id is not None:
        token.replaced_by_token_id = replaced_by_token_id
    await session.flush()


async def revoke_refresh_token_family(
    session: AsyncSession,
    family_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now),
    )
    await session.flush()


async def revoke_all_refresh_tokens_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now),
    )
    await session.flush()
