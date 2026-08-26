"""Category service."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError, ValidationAppError
from app.models.category import Category
from app.models.enums import CategoryStatus, CategoryType
from app.repositories import category_repository as category_repo
from app.schemas.categories import CategoryCreateRequest, CategoryUpdateRequest
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)
from app.services import ownership


def _ensure_user_mutable_category(category: Category) -> None:
    if category.is_system or category.user_id is None:
        raise ForbiddenError(
            code="FORBIDDEN",
            message="System categories cannot be modified.",
        )


async def create_category(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: CategoryCreateRequest,
) -> Category:
    if payload.category_type == CategoryType.UNIVERSAL:
        raise ValidationAppError(
            code="INVALID_CATEGORY_TYPE",
            message="User categories must be income or expense type.",
        )

    try:
        category = await category_repo.create_category(
            session,
            user_id=user_id,
            name=payload.name.strip(),
            category_type=payload.category_type,
            icon=payload.icon,
            color=payload.color,
        )
        await session.commit()
        return category
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            code="CATEGORY_NAME_CONFLICT",
            message="A category with this name and type already exists.",
        ) from exc


async def list_categories(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    status: CategoryStatus | None,
    category_type: CategoryType | None,
    include_system: bool,
    page: int,
    page_size: int,
) -> PaginatedResponse[Category]:
    offset, limit = pagination_params(
        page=page,
        page_size=page_size,
        max_page_size=settings.api_max_page_size,
    )
    categories, total = await category_repo.list_categories_for_user(
        session,
        user_id=user_id,
        status=status,
        category_type=category_type,
        include_system=include_system,
        offset=offset,
        limit=limit,
    )
    return build_paginated_response(
        items=categories,
        page=max(page, 1),
        page_size=limit,
        total_items=total,
    )


async def get_category(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category:
    return await ownership.get_accessible_category(
        session,
        user_id=user_id,
        category_id=category_id,
    )


async def update_category(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    payload: CategoryUpdateRequest,
) -> Category:
    if payload.name is None and payload.icon is None and payload.color is None:
        raise ValidationAppError(
            code="VALIDATION_ERROR",
            message="At least one field must be provided for update.",
        )

    category = await ownership.get_owned_user_category(
        session,
        user_id=user_id,
        category_id=category_id,
    )
    _ensure_user_mutable_category(category)
    if category.status == CategoryStatus.ARCHIVED:
        raise ValidationAppError(
            code="CATEGORY_ARCHIVED",
            message="Archived categories cannot be modified.",
        )

    if payload.name is not None:
        category.name = payload.name.strip()
    if payload.icon is not None:
        category.icon = payload.icon
    if payload.color is not None:
        category.color = payload.color

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            code="CATEGORY_NAME_CONFLICT",
            message="A category with this name and type already exists.",
        ) from exc
    await session.refresh(category)
    return category


async def archive_category(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category:
    category = await ownership.get_owned_user_category(
        session,
        user_id=user_id,
        category_id=category_id,
    )
    _ensure_user_mutable_category(category)
    if category.status != CategoryStatus.ARCHIVED:
        await category_repo.archive_category(session, category)
        await session.commit()
        await session.refresh(category)
    return category
