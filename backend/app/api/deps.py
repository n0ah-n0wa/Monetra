"""Shared FastAPI dependencies."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

__all__ = ["AsyncGenerator", "AsyncSession", "get_db"]
