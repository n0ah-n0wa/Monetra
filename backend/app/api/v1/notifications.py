"""Notification endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.schemas.notifications import (
    MarkAllReadResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    NotificationResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    unread_only: Annotated[bool, Query()] = False,
) -> PaginatedResponse[NotificationResponse]:
    return await notification_service.list_notifications(
        session,
        user_id=current_user.id,
        settings=settings,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> NotificationPreferenceResponse:
    return await notification_service.get_preferences(
        session,
        user_id=current_user.id,
    )


@router.patch("/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    payload: NotificationPreferenceUpdateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> NotificationPreferenceResponse:
    return await notification_service.update_preferences(
        session,
        user_id=current_user.id,
        payload=payload,
    )


@router.post("/read-all", response_model=MarkAllReadResponse)
async def mark_all_notifications_read(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> MarkAllReadResponse:
    updated = await notification_service.mark_all_as_read(
        session,
        user_id=current_user.id,
    )
    return MarkAllReadResponse(updated_count=updated)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> NotificationResponse:
    return await notification_service.mark_as_read(
        session,
        user_id=current_user.id,
        notification_id=notification_id,
    )
