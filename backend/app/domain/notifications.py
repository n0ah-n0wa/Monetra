"""Notification and email delivery abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.models.enums import NotificationType


@dataclass(frozen=True, slots=True)
class PasswordResetNotification:
    """Payload for a password reset email."""

    to_email: str
    reset_token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AppNotificationMessage:
    """Payload for delivering a persisted application notification by email."""

    to_email: str
    notification_type: NotificationType
    title: str
    message: str
    metadata: dict[str, Any] | None = None


class NotificationProvider(Protocol):
    """Deliver transactional notifications without coupling to a vendor."""

    async def send_password_reset(
        self,
        notification: PasswordResetNotification,
    ) -> None:
        """Send password reset instructions to the recipient."""

    async def send_app_notification(
        self,
        notification: AppNotificationMessage,
    ) -> None:
        """Deliver an application notification through an external channel."""
