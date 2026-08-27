"""Notification persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationType
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference


async def create_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        is_read=False,
        read_at=None,
        metadata_=metadata,
    )
    session.add(notification)
    await session.flush()
    return notification


async def get_notification_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> Notification | None:
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def list_notifications_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    unread_only: bool,
    offset: int,
    limit: int,
) -> tuple[list[Notification], int]:
    filters = [Notification.user_id == user_id]
    if unread_only:
        filters.append(Notification.is_read.is_(False))
    total = await session.scalar(
        select(func.count()).select_from(Notification).where(*filters),
    )
    result = await session.execute(
        select(Notification)
        .where(*filters)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all()), int(total or 0)


async def mark_notification_read(
    session: AsyncSession,
    notification: Notification,
) -> None:
    if notification.is_read:
        return
    notification.is_read = True
    notification.read_at = datetime.now(UTC)
    await session.flush()


async def mark_all_notifications_read(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    result = await session.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=datetime.now(UTC)),
    )
    await session.flush()
    return int(getattr(result, "rowcount", 0) or 0)


async def has_matching_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_type: NotificationType,
    metadata_contains: dict[str, Any],
) -> bool:
    """Return True when a notification exists with matching metadata keys."""
    result = await session.execute(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.notification_type == notification_type,
            Notification.metadata_.contains(metadata_contains),
        ),
    )
    return result.scalar_one_or_none() is not None


async def get_preferences_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> NotificationPreference | None:
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id),
    )
    return result.scalar_one_or_none()


async def create_default_preferences(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> NotificationPreference:
    prefs = NotificationPreference(user_id=user_id)
    session.add(prefs)
    await session.flush()
    return prefs
