"""Centralized FastAPI exception handlers."""

from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.core.logging import get_logger, log_event
from app.core.redaction import redact_mapping
from app.core.request_context import get_request_id
from app.schemas.errors import ErrorBody, ErrorResponse

logger = get_logger(__name__)


def _resolve_request_id(request: Request) -> str | None:
    state_id = getattr(request.state, "request_id", None)
    if isinstance(state_id, str) and state_id:
        return state_id
    return get_request_id()


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details or {}),
        request_id=_resolve_request_id(request),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
    )


def _request_context(request: Request) -> dict[str, Any]:
    return {
        "method": request.method,
        "path": request.url.path,
    }


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(AppError, exc)
    level = logging.ERROR if error.status_code >= 500 else logging.WARNING
    log_event(
        logger,
        "app.error",
        level=level,
        code=error.code,
        status_code=error.status_code,
        details=redact_mapping(error.details),
        **_request_context(request),
    )
    return _error_response(
        request=request,
        status_code=error.status_code,
        code=error.code,
        message=error.message,
        details=error.details,
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)
    detail = http_exc.detail
    details: dict[str, Any]
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        code = str(detail["code"])
        message = str(detail["message"])
        raw_details = detail.get("details") or {}
        details = cast(dict[str, Any], raw_details)
    elif isinstance(detail, str):
        code = "HTTP_ERROR"
        message = detail
        details = {}
    else:
        code = "HTTP_ERROR"
        message = "Request failed."
        details = {"detail": detail}

    if http_exc.status_code >= 500:
        log_event(
            logger,
            "http.error",
            level=logging.ERROR,
            code=code,
            status_code=http_exc.status_code,
            **_request_context(request),
        )

    return _error_response(
        request=request,
        status_code=http_exc.status_code,
        code=code,
        message=message,
        details=details,
    )


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    validation_exc = cast(RequestValidationError, exc)
    return _error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details={"errors": jsonable_encoder(validation_exc.errors())},
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = _resolve_request_id(request)
    log_event(
        logger,
        "app.unhandled_error",
        level=logging.ERROR,
        request_id=request_id,
        error_type=type(exc).__name__,
        **_request_context(request),
        exc_info=exc,
    )
    return _error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
    )


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    application.add_exception_handler(Exception, unhandled_exception_handler)
