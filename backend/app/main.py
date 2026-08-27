"""FastAPI application factory and ASGI entrypoint."""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIdMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import InMemoryRateLimiter
from app.db.session import dispose_db, init_db
from app.services.exchange_rate_providers import create_exchange_rate_provider
from app.services.notification_providers import create_notification_provider

logger = get_logger(__name__)


def create_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        configure_logging(level=settings.log_level)
        # Drop any import-time / previous engine before binding this app's settings.
        await dispose_db()
        init_db(settings)
        _app.state.rate_limiter = InMemoryRateLimiter()
        _app.state.notification_provider = create_notification_provider(settings)
        _app.state.exchange_rate_provider = create_exchange_rate_provider(settings)
        logger.info(
            "event=startup app=%s version=%s env=%s",
            settings.app_name,
            __version__,
            settings.app_env,
        )
        yield
        await dispose_db()
        logger.info("event=shutdown app=%s", settings.app_name)

    return lifespan


def custom_openapi(application: FastAPI, settings: Settings) -> dict[str, object]:
    if application.openapi_schema:
        return application.openapi_schema
    schema = get_openapi(
        title=settings.app_name,
        version=__version__,
        description=settings.api_description,
        routes=application.routes,
        tags=[
            {
                "name": "health",
                "description": "Liveness and readiness probes.",
            },
            {
                "name": "auth",
                "description": (
                    "Registration, login, refresh, logout, and password reset."
                ),
            },
            {
                "name": "users",
                "description": "Authenticated user profile endpoints.",
            },
            {
                "name": "accounts",
                "description": "Financial account management.",
            },
            {
                "name": "categories",
                "description": "Income and expense category management.",
            },
            {
                "name": "budgets",
                "description": "Budget management and utilization analytics.",
            },
            {
                "name": "analytics",
                "description": "Financial analytics and dashboard metrics.",
            },
            {
                "name": "exchange-rates",
                "description": "Stored exchange rates for multi-currency reporting.",
            },
            {
                "name": "goals",
                "description": "Financial goal tracking and progress analytics.",
            },
            {
                "name": "imports",
                "description": "CSV transaction import jobs and previews.",
            },
            {
                "name": "exports",
                "description": "CSV export of owned financial data.",
            },
            {
                "name": "notifications",
                "description": "In-app notifications and delivery preferences.",
            },
            {
                "name": "audit",
                "description": "Actor-scoped financial audit event trail.",
            },
            {
                "name": "transactions",
                "description": "Income and expense transaction management.",
            },
            {
                "name": "transfers",
                "description": "Account-to-account transfer management.",
            },
            {
                "name": "recurring-transactions",
                "description": "Recurring transaction schedule management.",
            },
        ],
    )
    schema["info"]["x-monetra-api-version"] = "v1"
    application.openapi_schema = schema
    return application.openapi_schema


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    cfg = settings or get_settings()
    configure_logging(level=cfg.log_level)

    application = FastAPI(
        title=cfg.app_name,
        version=__version__,
        description=cfg.api_description,
        lifespan=create_lifespan(cfg),
        docs_url=cfg.docs_url,
        redoc_url=cfg.redoc_url,
        openapi_url=cfg.openapi_url,
    )

    application.state.settings = cfg

    # Last added = outermost. Request ID should wrap responses from inner layers.
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(application)

    application.include_router(health_router)
    application.include_router(api_router, prefix=cfg.api_v1_prefix)

    def openapi() -> dict[str, object]:
        return custom_openapi(application, cfg)

    application.openapi = openapi  # type: ignore[method-assign]

    return application


app = create_app()
