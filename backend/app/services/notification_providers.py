"""Notification provider implementations."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.notifications import (
    AppNotificationMessage,
    NotificationProvider,
    PasswordResetNotification,
)

logger = get_logger(__name__)


class InMemoryNotificationProvider:
    """Capture outbound notifications for automated tests."""

    def __init__(self) -> None:
        self.password_resets: list[PasswordResetNotification] = []
        self.app_notifications: list[AppNotificationMessage] = []

    async def send_password_reset(
        self,
        notification: PasswordResetNotification,
    ) -> None:
        self.password_resets.append(notification)

    async def send_app_notification(
        self,
        notification: AppNotificationMessage,
    ) -> None:
        self.app_notifications.append(notification)

    def clear(self) -> None:
        self.password_resets.clear()
        self.app_notifications.clear()

    def latest_password_reset(self) -> PasswordResetNotification | None:
        if not self.password_resets:
            return None
        return self.password_resets[-1]

    def latest_app_notification(self) -> AppNotificationMessage | None:
        if not self.app_notifications:
            return None
        return self.app_notifications[-1]


class NoOpNotificationProvider:
    """Production-safe stub until a transactional email vendor is wired."""

    async def send_password_reset(
        self,
        notification: PasswordResetNotification,
    ) -> None:
        logger.info(
            "event=password_reset_email_queued recipient=%s",
            notification.to_email,
        )

    async def send_app_notification(
        self,
        notification: AppNotificationMessage,
    ) -> None:
        logger.info(
            "event=app_notification_email_queued recipient=%s type=%s",
            notification.to_email,
            notification.notification_type.value,
        )


def create_notification_provider(settings: Settings) -> NotificationProvider:
    """Return the notification provider appropriate for the runtime environment."""
    if settings.is_test:
        return InMemoryNotificationProvider()
    return NoOpNotificationProvider()


def get_notification_provider(application: object) -> NotificationProvider:
    """Return the shared notification provider stored on the FastAPI app."""
    state = getattr(application, "state", None)
    provider = (
        getattr(state, "notification_provider", None) if state is not None else None
    )
    if isinstance(provider, (InMemoryNotificationProvider, NoOpNotificationProvider)):
        return provider
    return NoOpNotificationProvider()
