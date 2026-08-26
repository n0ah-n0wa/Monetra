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
from app.db.session import dispose_db, init_db

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
