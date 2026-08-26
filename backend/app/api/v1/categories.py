"""Category endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.models.category import Category
from app.models.enums import CategoryStatus, CategoryType
from app.schemas.categories import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
)
from app.schemas.mappers import format_datetime
from app.schemas.pagination import PaginatedResponse
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


def _to_category_response(category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=str(category.id),
        name=category.name,
        category_type=category.category_type,
        icon=category.icon,
        color=category.color,
        is_system=category.is_system,
        status=category.status,
        archived_at=format_datetime(category.archived_at),
        created_at=format_datetime(category.created_at) or "",
        updated_at=format_datetime(category.updated_at) or "",
    )


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CategoryResponse:
    category = await category_service.create_category(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    return _to_category_response(category)


@router.get("", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    status: CategoryStatus | None = None,
    category_type: CategoryType | None = None,
    include_system: bool = True,
) -> PaginatedResponse[CategoryResponse]:
    effective_page_size = page_size or settings.api_default_page_size
    result = await category_service.list_categories(
        session,
        user_id=current_user.id,
        settings=settings,
        status=status,
        category_type=category_type,
        include_system=include_system,
        page=page,
        page_size=effective_page_size,
    )
    return PaginatedResponse(
        items=[_to_category_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total_items=result.total_items,
        total_pages=result.total_pages,
    )


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CategoryResponse:
    category = await category_service.update_category(
        session,
        user_id=current_user.id,
        category_id=category_id,
        payload=payload,
    )
    return _to_category_response(category)


@router.post("/{category_id}/archive", response_model=CategoryResponse)
async def archive_category(
    category_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CategoryResponse:
    category = await category_service.archive_category(
        session,
        user_id=current_user.id,
        category_id=category_id,
    )
    return _to_category_response(category)
