"""Notification and email delivery abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PasswordResetNotification:
    """Payload for a password reset email."""

    to_email: str
    reset_token: str
    expires_at: datetime


class NotificationProvider(Protocol):
    """Deliver transactional notifications without coupling to a vendor."""

    async def send_password_reset(
        self,
        notification: PasswordResetNotification,
    ) -> None:
        """Send password reset instructions to the recipient."""
