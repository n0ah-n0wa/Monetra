"""Notification provider failure isolation tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from app.domain.notifications import AppNotificationMessage
from app.models.enums import NotificationType
from app.models.notification_preference import NotificationPreference
from app.services import notification_service


class _RaisingProvider:
    async def send_app_notification(
        self,
        notification: AppNotificationMessage,
    ) -> None:
        raise RuntimeError("provider down")


@pytest.mark.asyncio
async def test_create_notification_persists_when_provider_delivery_fails(
    db_session,
    user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefs = NotificationPreference(
        user_id=user.id,
        budget_warning_enabled=True,
        budget_exceeded_enabled=True,
        recurring_executed_enabled=True,
        goal_milestone_enabled=True,
        import_completed_enabled=True,
        import_failed_enabled=True,
        email_enabled=True,
    )
    db_session.add(prefs)
    await db_session.flush()

    monkeypatch.setattr(
        notification_service.user_repo,
        "get_user_by_id",
        AsyncMock(return_value=user),
    )

    notification = await notification_service.create_notification(
        db_session,
        user_id=user.id,
        notification_type=NotificationType.IMPORT_FAILED,
        title="Import failed",
        message="Rolled back.",
        metadata={"import_job_id": str(uuid.uuid4())},
        provider=_RaisingProvider(),
    )

    assert notification is not None
    assert notification.title == "Import failed"
