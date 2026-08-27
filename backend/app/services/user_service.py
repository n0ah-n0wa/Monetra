"""User profile service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.currency import normalize_currency
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.users import UserUpdateRequest


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        reporting_currency=user.reporting_currency,
    )


async def update_user_profile(
    session: AsyncSession,
    *,
    user: User,
    payload: UserUpdateRequest,
) -> UserResponse:
    user.reporting_currency = normalize_currency(payload.reporting_currency)
    await session.commit()
    await session.refresh(user)
    return to_user_response(user)
