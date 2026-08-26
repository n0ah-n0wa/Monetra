"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db


def get_app_settings(request: Request) -> Settings:
    """Return settings bound to the running app (supports create_app overrides)."""
    bound = getattr(request.app.state, "settings", None)
    if isinstance(bound, Settings):
        return bound
    return get_settings()


SessionDep = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]

__all__ = [
    "SessionDep",
    "SettingsDep",
    "get_app_settings",
    "get_db",
    "get_settings",
]
