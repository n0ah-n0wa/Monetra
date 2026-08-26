"""API error response schemas matching SPECIFICATIONS.md."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Human-readable error message.")
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody
    request_id: str | None = Field(
        default=None,
        description="Request correlation ID for support and log tracing.",
    )
