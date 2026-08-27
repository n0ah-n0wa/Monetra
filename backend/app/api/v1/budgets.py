"""Budget endpoints."""

from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.schemas.budgets import (
    BudgetAnalyticsResponse,
    BudgetCreateRequest,
    BudgetResponse,
    BudgetUpdateRequest,
    BudgetUtilizationResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> BudgetResponse:
    budget = await budget_service.create_budget(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    return budget_service.build_budget_response(budget)


@router.get("/analytics/utilization", response_model=BudgetAnalyticsResponse)
async def get_budget_analytics(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    as_of_date: date | None = None,
) -> BudgetAnalyticsResponse:
    return await budget_service.get_budget_analytics(
        session,
        user_id=current_user.id,
        settings=settings,
        as_of_date=as_of_date,
    )


@router.get("", response_model=PaginatedResponse[BudgetResponse])
async def list_budgets(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    include_archived: bool = False,
    as_of_date: date | None = None,
    include_utilization: bool = False,
) -> PaginatedResponse[BudgetResponse]:
    effective_page_size = page_size or settings.api_default_page_size
    result = await budget_service.list_budgets(
        session,
        user_id=current_user.id,
        settings=settings,
        include_archived=include_archived,
        page=page,
        page_size=effective_page_size,
    )
    effective_date = as_of_date or datetime.now(UTC).date()
    items: list[BudgetResponse] = []
    for budget in result.items:
        utilization = None
        if include_utilization:
            utilization = await budget_service.compute_utilization(
                session,
                budget=budget,
                as_of_date=effective_date,
            )
        items.append(
            budget_service.build_budget_response(
                budget,
                utilization=utilization,
            ),
        )

    return PaginatedResponse(
        items=items,
        page=result.page,
        page_size=result.page_size,
        total_items=result.total_items,
        total_pages=result.total_pages,
    )


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    as_of_date: date | None = None,
    include_utilization: bool = False,
) -> BudgetResponse:
    budget = await budget_service.get_budget(
        session,
        user_id=current_user.id,
        budget_id=budget_id,
    )
    utilization = None
    if include_utilization:
        utilization = await budget_service.compute_utilization(
            session,
            budget=budget,
            as_of_date=as_of_date or datetime.now(UTC).date(),
        )
    return budget_service.build_budget_response(
        budget,
        utilization=utilization,
    )


@router.get("/{budget_id}/utilization", response_model=BudgetUtilizationResponse)
async def get_budget_utilization(
    budget_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    as_of_date: date | None = None,
) -> BudgetUtilizationResponse:
    return await budget_service.get_budget_utilization(
        session,
        user_id=current_user.id,
        budget_id=budget_id,
        as_of_date=as_of_date,
    )


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: UUID,
    payload: BudgetUpdateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> BudgetResponse:
    budget = await budget_service.update_budget(
        session,
        user_id=current_user.id,
        budget_id=budget_id,
        payload=payload,
    )
    return budget_service.build_budget_response(budget)


@router.post("/{budget_id}/archive", response_model=BudgetResponse)
async def archive_budget(
    budget_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> BudgetResponse:
    budget = await budget_service.archive_budget(
        session,
        user_id=current_user.id,
        budget_id=budget_id,
    )
    return budget_service.build_budget_response(budget)
