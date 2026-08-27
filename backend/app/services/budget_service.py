"""Budget service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.domain.budgets import (
    compute_budget_utilization,
    resolve_period_window,
    validate_budget_date_range,
)
from app.domain.transactions import normalize_money
from app.models.budget import Budget
from app.models.enums import (
    AuditAction,
    BudgetPeriod,
    BudgetScope,
    CategoryStatus,
    CategoryType,
)
from app.repositories import budget_repository as budget_repo
from app.schemas.budgets import (
    BudgetAnalyticsItem,
    BudgetAnalyticsResponse,
    BudgetCategorySummary,
    BudgetCreateRequest,
    BudgetResponse,
    BudgetUpdateRequest,
    BudgetUtilizationResponse,
)
from app.schemas.mappers import format_datetime
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)
from app.services import audit_service, ownership


async def _validate_budget_categories(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    category_ids: list[uuid.UUID],
) -> None:
    for category_id in category_ids:
        category = await ownership.get_accessible_category(
            session,
            user_id=user_id,
            category_id=category_id,
        )
        if category.status == CategoryStatus.ARCHIVED:
            raise ValidationAppError(
                code="CATEGORY_ARCHIVED",
                message="Archived categories cannot be assigned to budgets.",
            )
        if category.category_type not in {
            CategoryType.EXPENSE,
            CategoryType.UNIVERSAL,
        }:
            raise ValidationAppError(
                code="CATEGORY_TYPE_MISMATCH",
                message="Budget categories must be expense or universal type.",
            )


def _category_summaries(budget: Budget) -> list[BudgetCategorySummary]:
    return [
        BudgetCategorySummary(id=str(category.id), name=category.name)
        for category in budget.categories
    ]


def _to_budget_response(
    budget: Budget,
    *,
    utilization: BudgetUtilizationResponse | None = None,
) -> BudgetResponse:
    return BudgetResponse(
        id=str(budget.id),
        name=budget.name,
        amount=budget.amount,
        currency=budget.currency,
        period=budget.period,
        scope=budget.scope,
        start_date=budget.start_date,
        end_date=budget.end_date,
        warning_threshold_percent=budget.warning_threshold_percent,
        categories=_category_summaries(budget),
        archived_at=format_datetime(budget.archived_at),
        created_at=format_datetime(budget.created_at) or "",
        updated_at=format_datetime(budget.updated_at) or "",
        utilization=utilization,
    )


async def _compute_utilization(
    session: AsyncSession,
    *,
    budget: Budget,
    as_of_date: date,
) -> BudgetUtilizationResponse | None:
    window = resolve_period_window(
        period=budget.period,
        budget_start=budget.start_date,
        budget_end=budget.end_date,
        as_of=as_of_date,
    )
    if window is None:
        return None

    period_start, period_end = window
    category_ids = None
    if budget.scope == BudgetScope.CATEGORY:
        category_ids = [category.id for category in budget.categories]

    spent = await budget_repo.sum_budget_expenses(
        session,
        user_id=budget.user_id,
        currency=budget.currency,
        period_start=period_start,
        period_end=period_end,
        category_ids=category_ids,
    )
    utilization = compute_budget_utilization(
        period_start=period_start,
        period_end=period_end,
        budget_amount=budget.amount,
        spent_amount=spent,
        warning_threshold_percent=budget.warning_threshold_percent,
    )
    return BudgetUtilizationResponse(
        as_of_date=as_of_date,
        period_start=utilization.period_start,
        period_end=utilization.period_end,
        budget_amount=utilization.budget_amount,
        spent_amount=utilization.spent_amount,
        remaining_amount=utilization.remaining_amount,
        percentage_used=utilization.percentage_used,
        status=utilization.status,
    )


async def create_budget(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: BudgetCreateRequest,
) -> Budget:
    if payload.scope == BudgetScope.CATEGORY:
        await _validate_budget_categories(
            session,
            user_id=user_id,
            category_ids=payload.category_ids,
        )

    try:
        budget = await budget_repo.create_budget(
            session,
            user_id=user_id,
            name=payload.name,
            amount=normalize_money(payload.amount),
            currency=payload.currency,
            period=payload.period,
            scope=payload.scope,
            start_date=payload.start_date,
            end_date=payload.end_date,
            warning_threshold_percent=payload.warning_threshold_percent,
            category_ids=payload.category_ids,
        )
        await audit_service.record_event(
            session,
            actor_id=user_id,
            action=AuditAction.CREATED,
            entity_type=audit_service.ENTITY_BUDGET,
            entity_id=budget.id,
            metadata={
                "name": budget.name,
                "amount": budget.amount,
                "currency": budget.currency,
                "period": budget.period.value,
                "scope": budget.scope.value,
                "category_ids": [str(cid) for cid in payload.category_ids],
            },
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ValidationAppError(
            code="BUDGET_CREATE_FAILED",
            message="The budget could not be created.",
        ) from exc

    loaded = await budget_repo.get_budget(
        session,
        user_id=user_id,
        budget_id=budget.id,
    )
    assert loaded is not None
    return loaded


async def get_budget(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> Budget:
    budget = await budget_repo.get_budget(
        session,
        user_id=user_id,
        budget_id=budget_id,
    )
    if budget is None:
        raise NotFoundError(
            code="BUDGET_NOT_FOUND",
            message="Budget was not found.",
        )
    return budget


async def list_budgets(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    include_archived: bool,
    page: int,
    page_size: int,
) -> PaginatedResponse[Budget]:
    offset, limit = pagination_params(
        page=page,
        page_size=page_size,
        max_page_size=settings.api_max_page_size,
    )
    items, total = await budget_repo.list_budgets_for_user(
        session,
        user_id=user_id,
        include_archived=include_archived,
        offset=offset,
        limit=limit,
    )
    return build_paginated_response(
        items=items,
        page=max(page, 1),
        page_size=limit,
        total_items=total,
    )


async def update_budget(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
    payload: BudgetUpdateRequest,
) -> Budget:
    if (
        payload.name is None
        and payload.amount is None
        and payload.currency is None
        and payload.period is None
        and payload.scope is None
        and payload.start_date is None
        and payload.end_date is None
        and payload.warning_threshold_percent is None
        and payload.category_ids is None
    ):
        raise ValidationAppError(
            code="VALIDATION_ERROR",
            message="At least one field must be provided for update.",
        )

    budget = await get_budget(session, user_id=user_id, budget_id=budget_id)
    if budget.archived_at is not None:
        raise ValidationAppError(
            code="BUDGET_ARCHIVED",
            message="Archived budgets cannot be modified.",
        )

    new_scope = payload.scope or budget.scope
    new_period = payload.period or budget.period
    new_start = payload.start_date or budget.start_date
    if "end_date" in payload.model_fields_set:
        new_end = payload.end_date
    else:
        new_end = budget.end_date

    validate_budget_date_range(start_date=new_start, end_date=new_end)
    if new_period == BudgetPeriod.CUSTOM and new_end is None:
        raise ValidationAppError(
            code="INVALID_BUDGET_PERIOD",
            message="Custom budgets require an end_date.",
        )

    if payload.name is not None:
        budget.name = payload.name.strip()
    if payload.amount is not None:
        budget.amount = normalize_money(payload.amount)
    if payload.currency is not None:
        budget.currency = payload.currency
    if payload.period is not None:
        budget.period = payload.period
    if payload.scope is not None:
        budget.scope = payload.scope
    if payload.start_date is not None:
        budget.start_date = payload.start_date
    if "end_date" in payload.model_fields_set:
        budget.end_date = payload.end_date
    if payload.warning_threshold_percent is not None:
        budget.warning_threshold_percent = payload.warning_threshold_percent

    if payload.category_ids is not None:
        if new_scope == BudgetScope.OVERALL:
            raise ValidationAppError(
                code="VALIDATION_ERROR",
                message="Overall budgets cannot include category_ids.",
            )
        if not payload.category_ids:
            raise ValidationAppError(
                code="VALIDATION_ERROR",
                message="Category budgets require at least one category_id.",
            )
        await _validate_budget_categories(
            session,
            user_id=user_id,
            category_ids=payload.category_ids,
        )
        await budget_repo.replace_budget_categories(
            session,
            budget_id=budget.id,
            category_ids=payload.category_ids,
        )
    elif payload.scope == BudgetScope.OVERALL:
        await budget_repo.replace_budget_categories(
            session,
            budget_id=budget.id,
            category_ids=[],
        )
    elif new_scope == BudgetScope.CATEGORY and not budget.categories:
        raise ValidationAppError(
            code="VALIDATION_ERROR",
            message="Category budgets require at least one category_id.",
        )

    await audit_service.record_event(
        session,
        actor_id=user_id,
        action=AuditAction.UPDATED,
        entity_type=audit_service.ENTITY_BUDGET,
        entity_id=budget.id,
        metadata={
            "name": budget.name,
            "amount": budget.amount,
            "currency": budget.currency,
            "period": budget.period.value,
            "scope": budget.scope.value,
            "warning_threshold_percent": budget.warning_threshold_percent,
            "category_ids": [str(category.id) for category in budget.categories],
        },
    )
    await session.commit()
    loaded = await budget_repo.get_budget(
        session,
        user_id=user_id,
        budget_id=budget.id,
    )
    assert loaded is not None
    return loaded


async def archive_budget(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> Budget:
    budget = await get_budget(session, user_id=user_id, budget_id=budget_id)
    if budget.archived_at is None:
        await budget_repo.archive_budget(session, budget)
        await audit_service.record_event(
            session,
            actor_id=user_id,
            action=AuditAction.ARCHIVED,
            entity_type=audit_service.ENTITY_BUDGET,
            entity_id=budget.id,
            metadata={
                "name": budget.name,
                "amount": budget.amount,
                "currency": budget.currency,
            },
        )
        await session.commit()
        await session.refresh(budget)
    return budget


async def compute_utilization(
    session: AsyncSession,
    *,
    budget: Budget,
    as_of_date: date,
) -> BudgetUtilizationResponse | None:
    return await _compute_utilization(session, budget=budget, as_of_date=as_of_date)


def build_budget_response(
    budget: Budget,
    *,
    utilization: BudgetUtilizationResponse | None = None,
) -> BudgetResponse:
    return _to_budget_response(budget, utilization=utilization)


async def get_budget_utilization(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
    as_of_date: date | None = None,
) -> BudgetUtilizationResponse:
    budget = await get_budget(session, user_id=user_id, budget_id=budget_id)
    effective_date = as_of_date or datetime.now(UTC).date()
    utilization = await _compute_utilization(
        session,
        budget=budget,
        as_of_date=effective_date,
    )
    if utilization is None:
        raise ValidationAppError(
            code="BUDGET_NOT_ACTIVE",
            message="The budget is not active on the requested date.",
        )
    return utilization


async def get_budget_analytics(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    as_of_date: date | None = None,
) -> BudgetAnalyticsResponse:
    effective_date = as_of_date or datetime.now(UTC).date()
    _, limit = pagination_params(
        page=1,
        page_size=settings.api_max_page_size,
        max_page_size=settings.api_max_page_size,
    )
    budgets, _ = await budget_repo.list_budgets_for_user(
        session,
        user_id=user_id,
        include_archived=False,
        offset=0,
        limit=limit,
    )

    items: list[BudgetAnalyticsItem] = []
    for budget in budgets:
        utilization = await _compute_utilization(
            session,
            budget=budget,
            as_of_date=effective_date,
        )
        if utilization is None:
            continue
        items.append(
            BudgetAnalyticsItem(
                budget=_to_budget_response(budget),
                utilization=utilization,
            ),
        )

    return BudgetAnalyticsResponse(as_of_date=effective_date, items=items)
