"""Audit event persistence helpers."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.models.enums import AuditAction


async def create_audit_event(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID,
    action: AuditAction,
    entity_type: str,
    entity_id: uuid.UUID,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_=metadata,
    )
    session.add(event)
    await session.flush()
    return event


async def list_audit_events_for_actor(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID,
    entity_type: str | None,
    offset: int,
    limit: int,
) -> tuple[list[AuditEvent], int]:
    filters = [AuditEvent.actor_id == actor_id]
    if entity_type is not None:
        filters.append(AuditEvent.entity_type == entity_type)
    total = await session.scalar(
        select(func.count()).select_from(AuditEvent).where(*filters),
    )
    result = await session.execute(
        select(AuditEvent)
        .where(*filters)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all()), int(total or 0)
