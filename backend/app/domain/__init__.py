"""Domain layer package.

Pure financial calculations and domain rules belong here.
Domain code must not depend on FastAPI or HTTP concerns.
"""

from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationAppError,
)

__all__ = [
    "AppError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "UnauthorizedError",
    "ValidationAppError",
]
