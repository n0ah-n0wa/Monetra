"""Audit event endpoints (actor-scoped)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.schemas.audit import AuditEventResponse
from app.schemas.pagination import PaginatedResponse
from app.services import audit_service

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=PaginatedResponse[AuditEventResponse])
async def list_audit_events(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    entity_type: Annotated[str | None, Query(max_length=64)] = None,
) -> PaginatedResponse[AuditEventResponse]:
    return await audit_service.list_audit_events(
        session,
        actor_id=current_user.id,
        settings=settings,
        page=page,
        page_size=page_size,
        entity_type=entity_type,
    )
