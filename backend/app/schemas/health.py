"""Health and readiness response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    database: bool = Field(description="Whether PostgreSQL is reachable.")
