"""Notification API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import NotificationType


class NotificationResponse(BaseModel):
    id: str
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool
    read_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class NotificationPreferenceResponse(BaseModel):
    budget_warning_enabled: bool
    budget_exceeded_enabled: bool
    recurring_executed_enabled: bool
    goal_milestone_enabled: bool
    import_completed_enabled: bool
    import_failed_enabled: bool
    email_enabled: bool
    updated_at: datetime


class NotificationPreferenceUpdateRequest(BaseModel):
    budget_warning_enabled: bool | None = None
    budget_exceeded_enabled: bool | None = None
    recurring_executed_enabled: bool | None = None
    goal_milestone_enabled: bool | None = None
    import_completed_enabled: bool | None = None
    import_failed_enabled: bool | None = None
    email_enabled: bool | None = None


class MarkAllReadResponse(BaseModel):
    updated_count: int = Field(ge=0)
