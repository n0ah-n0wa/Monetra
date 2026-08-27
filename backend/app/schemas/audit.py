"""Audit event API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import AuditAction


class AuditEventResponse(BaseModel):
    id: str
    actor_id: str
    action: AuditAction
    entity_type: str
    entity_id: str
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class AuditEventListParams(BaseModel):
    entity_type: str | None = Field(default=None, max_length=64)
