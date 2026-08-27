"""Audit event orchestration."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.domain.audit import sanitize_audit_metadata
from app.models.audit_event import AuditEvent
from app.models.enums import AuditAction
from app.repositories import audit_repository as audit_repo
from app.schemas.audit import AuditEventResponse
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)

ENTITY_TRANSACTION = "transaction"
ENTITY_TRANSFER = "transfer"
ENTITY_ACCOUNT = "financial_account"
ENTITY_BUDGET = "budget"
ENTITY_IMPORT_JOB = "import_job"


async def record_event(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID,
    action: AuditAction,
    entity_type: str,
    entity_id: uuid.UUID,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Persist a financially significant audit event with sanitized metadata."""
    return await audit_repo.create_audit_event(
        session,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=sanitize_audit_metadata(metadata),
    )


def to_audit_event_response(event: AuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        id=str(event.id),
        actor_id=str(event.actor_id),
        action=event.action,
        entity_type=event.entity_type,
        entity_id=str(event.entity_id),
        metadata=event.metadata_,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


async def list_audit_events(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID,
    settings: Settings,
    page: int,
    page_size: int | None,
    entity_type: str | None = None,
) -> PaginatedResponse[AuditEventResponse]:
    offset, limit = pagination_params(
        page=page,
        page_size=page_size or settings.api_default_page_size,
        max_page_size=settings.api_max_page_size,
    )
    items, total = await audit_repo.list_audit_events_for_actor(
        session,
        actor_id=actor_id,
        entity_type=entity_type,
        offset=offset,
        limit=limit,
    )
    return build_paginated_response(
        items=[to_audit_event_response(item) for item in items],
        page=max(page, 1),
        page_size=limit,
        total_items=total,
    )
