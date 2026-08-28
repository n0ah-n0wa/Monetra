"""Health and readiness endpoints required by the specification."""

import logging

from fastapi import APIRouter, Response, status

from app.core.logging import get_logger, log_event
from app.db.session import check_database_connectivity
from app.schemas.errors import ErrorResponse
from app.schemas.health import DependencyCheck, HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Verifies that the backend process is alive.",
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    },
)
async def health() -> HealthResponse:
    """Verify that the backend process is alive."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness probe",
    description=(
        "Verifies that required dependencies such as PostgreSQL are available."
    ),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadyResponse,
            "description": "One or more dependencies are unavailable.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    },
)
async def ready(response: Response) -> ReadyResponse:
    """Verify that required dependencies such as PostgreSQL are available."""
    database_result = await check_database_connectivity()
    database_check = DependencyCheck(
        status="ok" if database_result.ok else "unavailable",
        latency_ms=database_result.latency_ms,
        error=database_result.error,
    )
    checks = {"database": database_check}
    database_ok = database_result.ok

    if database_ok:
        log_event(
            logger,
            "readiness.checked",
            status="ready",
            database_latency_ms=database_result.latency_ms,
        )
        return ReadyResponse(status="ready", database=True, checks=checks)

    log_event(
        logger,
        "readiness.checked",
        level=logging.ERROR,
        status="unavailable",
        database_error=database_result.error,
        database_latency_ms=database_result.latency_ms,
    )
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(status="unavailable", database=False, checks=checks)
