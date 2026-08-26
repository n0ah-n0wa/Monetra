"""Pydantic schema package."""

from app.schemas.errors import ErrorBody, ErrorResponse
from app.schemas.health import HealthResponse, ReadyResponse

__all__ = [
    "ErrorBody",
    "ErrorResponse",
    "HealthResponse",
    "ReadyResponse",
]
