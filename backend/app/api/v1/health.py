"""Health and readiness endpoints required by the specification."""

from fastapi import APIRouter, Response, status

from app.db.session import ping_database
from app.schemas.errors import ErrorResponse
from app.schemas.health import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


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
    database_ok = await ping_database()
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(status="unavailable", database=False)
    return ReadyResponse(status="ready", database=True)
