"""User persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password_hash: str,
    reporting_currency: str = "USD",
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        reporting_currency=reporting_currency,
        password_changed_at=datetime.now(UTC),
    )
    session.add(user)
    await session.flush()
    return user
