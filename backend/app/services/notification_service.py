"""Application notification orchestration."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.domain.notification_events import (
    completion_percentage,
    crossed_goal_milestones,
)
from app.domain.notifications import AppNotificationMessage, NotificationProvider
from app.models.enums import BudgetStatus, NotificationType
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.repositories import budget_repository as budget_repo
from app.repositories import notification_repository as notification_repo
from app.repositories import user_repository as user_repo
from app.schemas.mappers import format_datetime
from app.schemas.notifications import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    NotificationResponse,
)
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)
from app.services import budget_service


def _preference_enabled(
    prefs: NotificationPreference,
    notification_type: NotificationType,
) -> bool:
    mapping = {
        NotificationType.BUDGET_WARNING: prefs.budget_warning_enabled,
        NotificationType.BUDGET_EXCEEDED: prefs.budget_exceeded_enabled,
        NotificationType.RECURRING_CREATED: prefs.recurring_executed_enabled,
        NotificationType.GOAL_MILESTONE: prefs.goal_milestone_enabled,
        NotificationType.IMPORT_COMPLETED: prefs.import_completed_enabled,
        NotificationType.IMPORT_FAILED: prefs.import_failed_enabled,
        NotificationType.GENERAL: True,
    }
    return mapping.get(notification_type, True)


def to_notification_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=str(notification.id),
        notification_type=notification.notification_type,
        title=notification.title,
        message=notification.message,
        is_read=notification.is_read,
        read_at=format_datetime(notification.read_at),
        metadata=notification.metadata_,
        created_at=format_datetime(notification.created_at) or "",
        updated_at=format_datetime(notification.updated_at) or "",
    )


def to_preference_response(
    prefs: NotificationPreference,
) -> NotificationPreferenceResponse:
    return NotificationPreferenceResponse(
        budget_warning_enabled=prefs.budget_warning_enabled,
        budget_exceeded_enabled=prefs.budget_exceeded_enabled,
        recurring_executed_enabled=prefs.recurring_executed_enabled,
        goal_milestone_enabled=prefs.goal_milestone_enabled,
        import_completed_enabled=prefs.import_completed_enabled,
        import_failed_enabled=prefs.import_failed_enabled,
        email_enabled=prefs.email_enabled,
        updated_at=format_datetime(prefs.updated_at) or "",
    )


async def get_or_create_preferences(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> NotificationPreference:
    prefs = await notification_repo.get_preferences_for_user(session, user_id=user_id)
    if prefs is not None:
        return prefs
    return await notification_repo.create_default_preferences(session, user_id=user_id)


async def create_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    metadata: dict[str, Any] | None = None,
    provider: NotificationProvider | None = None,
) -> Notification | None:
    prefs = await get_or_create_preferences(session, user_id=user_id)
    if not _preference_enabled(prefs, notification_type):
        return None

    notification = await notification_repo.create_notification(
        session,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        metadata=metadata,
    )

    if prefs.email_enabled and provider is not None:
        user = await user_repo.get_user_by_id(session, user_id)
        if user is not None:
            await provider.send_app_notification(
                AppNotificationMessage(
                    to_email=user.email,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    metadata=metadata,
                ),
            )
    return notification


async def list_notifications(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    page: int,
    page_size: int | None,
    unread_only: bool = False,
) -> PaginatedResponse[NotificationResponse]:
    offset, limit = pagination_params(
        page=page,
        page_size=page_size or settings.api_default_page_size,
        max_page_size=settings.api_max_page_size,
    )
    items, total = await notification_repo.list_notifications_for_user(
        session,
        user_id=user_id,
        unread_only=unread_only,
        offset=offset,
        limit=limit,
    )
    return build_paginated_response(
        items=[to_notification_response(item) for item in items],
        page=max(page, 1),
        page_size=limit,
        total_items=total,
    )


async def mark_as_read(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> NotificationResponse:
    notification = await notification_repo.get_notification_for_user(
        session,
        user_id=user_id,
        notification_id=notification_id,
    )
    if notification is None:
        raise NotFoundError(
            code="NOTIFICATION_NOT_FOUND",
            message="Notification was not found.",
        )
    await notification_repo.mark_notification_read(session, notification)
    await session.commit()
    await session.refresh(notification)
    return to_notification_response(notification)


async def mark_all_as_read(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    updated = await notification_repo.mark_all_notifications_read(
        session,
        user_id=user_id,
    )
    await session.commit()
    return updated


async def get_preferences(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> NotificationPreferenceResponse:
    prefs = await get_or_create_preferences(session, user_id=user_id)
    await session.commit()
    await session.refresh(prefs)
    return to_preference_response(prefs)


async def update_preferences(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: NotificationPreferenceUpdateRequest,
) -> NotificationPreferenceResponse:
    if not payload.model_fields_set:
        raise ValidationAppError(
            code="VALIDATION_ERROR",
            message="At least one preference field must be provided.",
        )
    prefs = await get_or_create_preferences(session, user_id=user_id)
    for field_name in payload.model_fields_set:
        setattr(prefs, field_name, getattr(payload, field_name))
    await session.commit()
    await session.refresh(prefs)
    return to_preference_response(prefs)


async def notify_import_completed(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    imported_rows: int,
    provider: NotificationProvider | None = None,
) -> Notification | None:
    return await create_notification(
        session,
        user_id=user_id,
        notification_type=NotificationType.IMPORT_COMPLETED,
        title="Import completed",
        message=(
            f"Your CSV import finished successfully ({imported_rows} rows imported)."
        ),
        metadata={"import_job_id": str(job_id), "imported_rows": imported_rows},
        provider=provider,
    )


async def notify_import_failed(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    error_code: str,
    provider: NotificationProvider | None = None,
) -> Notification | None:
    return await create_notification(
        session,
        user_id=user_id,
        notification_type=NotificationType.IMPORT_FAILED,
        title="Import failed",
        message=(
            "Your CSV import failed and was rolled back. No financial data was changed."
        ),
        metadata={"import_job_id": str(job_id), "error_code": error_code},
        provider=provider,
    )


async def notify_recurring_executed(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
    transaction_id: uuid.UUID,
    execution_date: date,
    description: str,
    provider: NotificationProvider | None = None,
) -> Notification | None:
    return await create_notification(
        session,
        user_id=user_id,
        notification_type=NotificationType.RECURRING_CREATED,
        title="Recurring transaction executed",
        message=(
            f"Recurring transaction '{description}' was executed "
            f"on {execution_date.isoformat()}."
        ),
        metadata={
            "recurring_transaction_id": str(recurring_id),
            "transaction_id": str(transaction_id),
            "execution_date": execution_date.isoformat(),
        },
        provider=provider,
    )


async def notify_goal_milestones(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    goal_name: str,
    previous_current: Decimal,
    previous_target: Decimal,
    current_amount: Decimal,
    target_amount: Decimal,
    provider: NotificationProvider | None = None,
) -> list[Notification]:
    previous_pct = completion_percentage(
        current_amount=previous_current,
        target_amount=previous_target,
    )
    current_pct = completion_percentage(
        current_amount=current_amount,
        target_amount=target_amount,
    )
    created: list[Notification] = []
    for milestone in crossed_goal_milestones(
        previous_percentage=previous_pct,
        current_percentage=current_pct,
    ):
        metadata = {"goal_id": str(goal_id), "milestone_percent": milestone}
        exists = await notification_repo.has_matching_notification(
            session,
            user_id=user_id,
            notification_type=NotificationType.GOAL_MILESTONE,
            metadata_contains=metadata,
        )
        if exists:
            continue
        notification = await create_notification(
            session,
            user_id=user_id,
            notification_type=NotificationType.GOAL_MILESTONE,
            title="Goal milestone reached",
            message=f"Goal '{goal_name}' reached {milestone}% of its target.",
            metadata=metadata,
            provider=provider,
        )
        if notification is not None:
            created.append(notification)
    return created


async def evaluate_budgets_after_expense(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of_date: date,
    provider: NotificationProvider | None = None,
    settings: Settings | None = None,
) -> list[Notification]:
    """Emit warning/exceeded notifications for budgets newly in those states."""
    from app.core.config import get_settings

    effective_settings = settings or get_settings()
    page_size = effective_settings.api_max_page_size
    offset = 0
    created: list[Notification] = []
    while True:
        budgets, total = await budget_repo.list_budgets_for_user(
            session,
            user_id=user_id,
            offset=offset,
            limit=page_size,
            include_archived=False,
        )
        for budget in budgets:
            utilization = await budget_service.compute_utilization(
                session,
                budget=budget,
                as_of_date=as_of_date,
            )
            if utilization is None:
                continue
            status = utilization.status
            if status == BudgetStatus.HEALTHY:
                continue

            notification_type = (
                NotificationType.BUDGET_EXCEEDED
                if status == BudgetStatus.EXCEEDED
                else NotificationType.BUDGET_WARNING
            )
            metadata = {
                "budget_id": str(budget.id),
                "period_start": utilization.period_start.isoformat(),
                "period_end": utilization.period_end.isoformat(),
                "status": status.value,
            }
            exists = await notification_repo.has_matching_notification(
                session,
                user_id=user_id,
                notification_type=notification_type,
                metadata_contains={
                    "budget_id": metadata["budget_id"],
                    "period_start": metadata["period_start"],
                    "status": metadata["status"],
                },
            )
            if exists:
                continue

            spent = utilization.spent_amount
            limit_amount = utilization.budget_amount
            if status == BudgetStatus.EXCEEDED:
                title = "Budget exceeded"
                message = (
                    f"Budget '{budget.name}' is over limit "
                    f"({spent} spent of {limit_amount})."
                )
            else:
                title = "Budget approaching limit"
                message = (
                    f"Budget '{budget.name}' is approaching its limit "
                    f"({spent} spent of {limit_amount})."
                )
            notification = await create_notification(
                session,
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                metadata=metadata,
                provider=provider,
            )
            if notification is not None:
                created.append(notification)
        offset += page_size
        if offset >= total:
            break
    return created
