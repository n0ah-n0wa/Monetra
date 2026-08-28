"""Category persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.enums import CategoryStatus, CategoryType


async def create_category(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    category_type: CategoryType,
    icon: str | None = None,
    color: str | None = None,
) -> Category:
    category = Category(
        user_id=user_id,
        name=name,
        category_type=category_type,
        icon=icon,
        color=color,
        is_system=False,
        status=CategoryStatus.ACTIVE,
    )
    session.add(category)
    await session.flush()
    return category


async def list_categories_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    status: CategoryStatus | None,
    category_type: CategoryType | None,
    include_system: bool,
    offset: int,
    limit: int,
) -> tuple[list[Category], int]:
    ownership = Category.user_id == user_id
    if include_system:
        ownership_filter = or_(ownership, Category.user_id.is_(None))
    else:
        ownership_filter = ownership

    filters = [ownership_filter]
    if status is not None:
        filters.append(Category.status == status)
    if category_type is not None:
        filters.append(Category.category_type == category_type)

    total = await session.scalar(
        select(func.count()).select_from(Category).where(*filters),
    )
    result = await session.execute(
        select(Category)
        .where(*filters)
        .order_by(Category.is_system.desc(), Category.name.asc(), Category.id.asc())
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all()), int(total or 0)


async def build_active_category_lookup_by_name(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Category]:
    """Load active user and system categories keyed by lowercased name."""
    result = await session.execute(
        select(Category).where(
            or_(Category.user_id == user_id, Category.user_id.is_(None)),
            Category.status == CategoryStatus.ACTIVE,
        ),
    )
    lookup: dict[str, Category] = {}
    for category in result.scalars().all():
        lookup[category.name.strip().lower()] = category
    return lookup


async def find_active_category_by_name(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
) -> Category | None:
    """Resolve a user or system category by exact name (case-insensitive)."""
    result = await session.execute(
        select(Category).where(
            or_(Category.user_id == user_id, Category.user_id.is_(None)),
            Category.status == CategoryStatus.ACTIVE,
            func.lower(Category.name) == name.strip().lower(),
        ),
    )
    return result.scalars().first()


async def archive_category(session: AsyncSession, category: Category) -> None:
    category.status = CategoryStatus.ARCHIVED
    category.archived_at = datetime.now(UTC)
    await session.flush()
