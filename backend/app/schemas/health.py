"""Health and readiness response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class DependencyCheck(BaseModel):
    status: Literal["ok", "unavailable"]
    latency_ms: float | None = Field(
        default=None,
        description="Round-trip time for the dependency check in milliseconds.",
    )
    error: str | None = Field(
        default=None,
        description="Operator-safe error category when the check fails.",
    )


class ReadyResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    database: bool = Field(description="Whether PostgreSQL is reachable.")
    checks: dict[str, DependencyCheck] = Field(
        description="Per-dependency readiness diagnostics.",
    )
