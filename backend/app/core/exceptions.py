"""Application domain and API exception types."""

from typing import Any


class AppError(Exception):
    """Base application error mapped to a stable API error response."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(
        self,
        *,
        code: str = "RESOURCE_NOT_FOUND",
        message: str = "Resource was not found.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=404,
            details=details,
        )


class ConflictError(AppError):
    def __init__(
        self,
        *,
        code: str = "CONFLICT",
        message: str = "The request conflicts with the current state.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=409,
            details=details,
        )


class UnauthorizedError(AppError):
    def __init__(
        self,
        *,
        code: str = "UNAUTHORIZED",
        message: str = "Authentication is required.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=401,
            details=details,
        )


class ForbiddenError(AppError):
    def __init__(
        self,
        *,
        code: str = "FORBIDDEN",
        message: str = "You are not allowed to perform this action.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=403,
            details=details,
        )


class ValidationAppError(AppError):
    def __init__(
        self,
        *,
        code: str = "VALIDATION_ERROR",
        message: str = "Request validation failed.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=422,
            details=details,
        )


class RateLimitError(AppError):
    def __init__(
        self,
        *,
        code: str = "RATE_LIMIT_EXCEEDED",
        message: str = "Too many requests. Please try again later.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=429,
            details=details,
        )
