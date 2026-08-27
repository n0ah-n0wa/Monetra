"""Notification provider unit tests."""

from datetime import UTC, datetime

import pytest
from app.core.config import Settings
from app.domain.notifications import AppNotificationMessage, PasswordResetNotification
from app.models.enums import NotificationType
from app.services.notification_providers import (
    InMemoryNotificationProvider,
    NoOpNotificationProvider,
    create_notification_provider,
)


@pytest.mark.asyncio
async def test_in_memory_provider_captures_password_reset() -> None:
    provider = InMemoryNotificationProvider()
    notification = PasswordResetNotification(
        to_email="user@example.com",
        reset_token="secret-reset-token",
        expires_at=datetime.now(UTC),
    )
    await provider.send_password_reset(notification)
    assert provider.latest_password_reset() == notification


@pytest.mark.asyncio
async def test_in_memory_provider_captures_app_notification() -> None:
    provider = InMemoryNotificationProvider()
    message = AppNotificationMessage(
        to_email="user@example.com",
        notification_type=NotificationType.IMPORT_COMPLETED,
        title="Import completed",
        message="done",
        metadata={"imported_rows": 1},
    )
    await provider.send_app_notification(message)
    assert provider.latest_app_notification() == message


@pytest.mark.asyncio
async def test_no_op_provider_accepts_password_reset() -> None:
    provider = NoOpNotificationProvider()
    await provider.send_password_reset(
        PasswordResetNotification(
            to_email="user@example.com",
            reset_token="secret-reset-token",
            expires_at=datetime.now(UTC),
        ),
    )
    await provider.send_app_notification(
        AppNotificationMessage(
            to_email="user@example.com",
            notification_type=NotificationType.GENERAL,
            title="Hi",
            message="There",
        ),
    )


def test_create_notification_provider_uses_in_memory_in_test_env() -> None:
    settings = Settings(
        app_env="test",
        jwt_secret_key="test-secret-key-must-be-at-least-32-chars",
    )
    provider = create_notification_provider(settings)
    assert isinstance(provider, InMemoryNotificationProvider)


def test_create_notification_provider_uses_no_op_in_development() -> None:
    settings = Settings(
        app_env="development",
        jwt_secret_key="test-secret-key-must-be-at-least-32-chars",
    )
    provider = create_notification_provider(settings)
    assert isinstance(provider, NoOpNotificationProvider)
