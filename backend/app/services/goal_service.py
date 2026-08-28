"""Financial goal service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.domain.goals import (
    ContributionPoint,
    build_cumulative_contribution_history,
    compute_goal_progress,
)
from app.domain.notifications import NotificationProvider
from app.domain.transactions import normalize_money
from app.models.enums import AccountStatus, GoalStatus
from app.models.financial_goal import FinancialGoal
from app.repositories import goal_repository as goal_repo
from app.schemas.goals import (
    GoalCreateRequest,
    GoalProgressResponse,
    GoalResponse,
    GoalUpdateRequest,
)
from app.schemas.mappers import format_datetime
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)
from app.services import notification_service, ownership


def _goal_status_for_amounts(
    *, target_amount: Decimal, current_amount: Decimal
) -> GoalStatus:
    if current_amount >= target_amount:
        return GoalStatus.COMPLETED
    return GoalStatus.ACTIVE


async def _validate_linked_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    linked_account_id: uuid.UUID,
    currency: str,
) -> None:
    account = await ownership.get_owned_account(
        session,
        user_id=user_id,
        account_id=linked_account_id,
    )
    if account.status == AccountStatus.ARCHIVED:
        raise ValidationAppError(
            code="ACCOUNT_ARCHIVED",
            message="Archived accounts cannot be linked to financial goals.",
        )
    if account.currency != currency:
        raise ValidationAppError(
            code="CURRENCY_MISMATCH",
            message="Linked account currency must match the goal currency.",
        )


async def _build_contribution_history(
    session: AsyncSession,
    *,
    goal: FinancialGoal,
    as_of_date: date,
) -> list[ContributionPoint]:
    created_date = goal.created_at.date() if goal.created_at else as_of_date

    if goal.linked_account_id is not None:
        daily = await goal_repo.sum_daily_net_contributions_for_account(
            session,
            user_id=goal.user_id,
            account_id=goal.linked_account_id,
            currency=goal.currency,
            start_date=created_date,
            end_date=as_of_date,
        )
        return build_cumulative_contribution_history(daily)

    if created_date >= as_of_date:
        return [
            ContributionPoint(
                contribution_date=as_of_date,
                cumulative_amount=goal.current_amount,
            ),
        ]

    return [
        ContributionPoint(
            contribution_date=created_date, cumulative_amount=Decimal("0.0000")
        ),
        ContributionPoint(
            contribution_date=as_of_date,
            cumulative_amount=goal.current_amount,
        ),
    ]


def _to_goal_response(
    goal: FinancialGoal,
    *,
    progress: GoalProgressResponse | None = None,
) -> GoalResponse:
    return GoalResponse(
        id=str(goal.id),
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        currency=goal.currency,
        target_date=goal.target_date,
        linked_account_id=str(goal.linked_account_id)
        if goal.linked_account_id
        else None,
        status=goal.status,
        archived_at=format_datetime(goal.archived_at),
        created_at=format_datetime(goal.created_at) or "",
        updated_at=format_datetime(goal.updated_at) or "",
        progress=progress,
    )


async def _compute_progress(
    session: AsyncSession,
    *,
    goal: FinancialGoal,
    as_of_date: date,
) -> GoalProgressResponse:
    history = await _build_contribution_history(
        session,
        goal=goal,
        as_of_date=as_of_date,
    )
    current_amount = goal.current_amount
    if goal.linked_account_id is not None and history:
        current_amount = history[-1].cumulative_amount
    metrics = compute_goal_progress(
        target_amount=goal.target_amount,
        current_amount=current_amount,
        target_date=goal.target_date,
        as_of_date=as_of_date,
        contribution_history=history,
    )
    return GoalProgressResponse(
        as_of_date=as_of_date,
        remaining_amount=metrics.remaining_amount,
        completion_percentage=metrics.completion_percentage,
        required_average_contribution=metrics.required_average_contribution,
        average_contribution_rate=metrics.average_contribution_rate,
        projected_completion_date=metrics.projected_completion_date,
        target_date_achievable=metrics.target_date_achievable,
    )


async def create_goal(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: GoalCreateRequest,
    provider: NotificationProvider | None = None,
) -> FinancialGoal:
    target_amount = normalize_money(payload.target_amount)
    current_amount = normalize_money(payload.current_amount)

    if payload.linked_account_id is not None:
        await _validate_linked_account(
            session,
            user_id=user_id,
            linked_account_id=payload.linked_account_id,
            currency=payload.currency,
        )

    status = _goal_status_for_amounts(
        target_amount=target_amount,
        current_amount=current_amount,
    )

    goal = await goal_repo.create_goal(
        session,
        user_id=user_id,
        name=payload.name.strip(),
        target_amount=target_amount,
        current_amount=current_amount,
        currency=payload.currency,
        target_date=payload.target_date,
        linked_account_id=payload.linked_account_id,
        status=status,
    )
    await notification_service.notify_goal_milestones(
        session,
        user_id=user_id,
        goal_id=goal.id,
        goal_name=goal.name,
        previous_current=Decimal("0"),
        previous_target=target_amount,
        current_amount=current_amount,
        target_amount=target_amount,
        provider=provider,
    )
    await session.commit()
    loaded = await goal_repo.get_goal(session, user_id=user_id, goal_id=goal.id)
    assert loaded is not None
    return loaded


async def get_goal(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
) -> FinancialGoal:
    goal = await goal_repo.get_goal(session, user_id=user_id, goal_id=goal_id)
    if goal is None:
        raise NotFoundError(
            code="GOAL_NOT_FOUND",
            message="Financial goal was not found.",
        )
    return goal


async def list_goals(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    status: GoalStatus | None,
    include_archived: bool,
    page: int,
    page_size: int,
) -> PaginatedResponse[FinancialGoal]:
    offset, limit = pagination_params(
        page=page,
        page_size=page_size,
        max_page_size=settings.api_max_page_size,
    )
    items, total = await goal_repo.list_goals_for_user(
        session,
        user_id=user_id,
        status=status,
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


async def update_goal(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    payload: GoalUpdateRequest,
    provider: NotificationProvider | None = None,
) -> FinancialGoal:
    if (
        payload.name is None
        and payload.target_amount is None
        and payload.current_amount is None
        and payload.currency is None
        and payload.target_date is None
        and payload.linked_account_id is None
        and "target_date" not in payload.model_fields_set
    ):
        raise ValidationAppError(
            code="VALIDATION_ERROR",
            message="At least one field must be provided for update.",
        )

    goal = await get_goal(session, user_id=user_id, goal_id=goal_id)
    if goal.archived_at is not None:
        raise ValidationAppError(
            code="GOAL_ARCHIVED",
            message="Archived goals cannot be modified.",
        )

    previous_current = goal.current_amount
    previous_target = goal.target_amount

    new_currency = payload.currency or goal.currency
    if payload.linked_account_id is not None:
        await _validate_linked_account(
            session,
            user_id=user_id,
            linked_account_id=payload.linked_account_id,
            currency=new_currency,
        )
    elif payload.currency is not None and goal.linked_account_id is not None:
        await _validate_linked_account(
            session,
            user_id=user_id,
            linked_account_id=goal.linked_account_id,
            currency=new_currency,
        )

    if payload.name is not None:
        goal.name = payload.name.strip()
    if payload.target_amount is not None:
        goal.target_amount = normalize_money(payload.target_amount)
    if payload.current_amount is not None:
        goal.current_amount = normalize_money(payload.current_amount)
    if payload.currency is not None:
        goal.currency = payload.currency
    if "target_date" in payload.model_fields_set:
        goal.target_date = payload.target_date
    if payload.linked_account_id is not None:
        goal.linked_account_id = payload.linked_account_id

    if goal.status != GoalStatus.ARCHIVED:
        goal.status = _goal_status_for_amounts(
            target_amount=goal.target_amount,
            current_amount=goal.current_amount,
        )

    await notification_service.notify_goal_milestones(
        session,
        user_id=user_id,
        goal_id=goal.id,
        goal_name=goal.name,
        previous_current=previous_current,
        previous_target=previous_target,
        current_amount=goal.current_amount,
        target_amount=goal.target_amount,
        provider=provider,
    )

    await session.commit()
    loaded = await goal_repo.get_goal(session, user_id=user_id, goal_id=goal.id)
    assert loaded is not None
    return loaded


async def archive_goal(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
) -> FinancialGoal:
    goal = await get_goal(session, user_id=user_id, goal_id=goal_id)
    if goal.archived_at is None:
        await goal_repo.archive_goal(session, goal)
        await session.commit()
        await session.refresh(goal)
    return goal


async def get_goal_progress(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    as_of_date: date | None = None,
) -> GoalProgressResponse:
    goal = await get_goal(session, user_id=user_id, goal_id=goal_id)
    effective_date = as_of_date or datetime.now(UTC).date()
    return await _compute_progress(session, goal=goal, as_of_date=effective_date)


def build_goal_response(
    goal: FinancialGoal,
    *,
    progress: GoalProgressResponse | None = None,
) -> GoalResponse:
    return _to_goal_response(goal, progress=progress)


async def sync_linked_goals_for_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    as_of_date: date,
    provider: NotificationProvider | None = None,
) -> None:
    """Update linked-goal balances from account activity and emit milestones."""
    goals = await goal_repo.list_active_goals_linked_to_account(
        session,
        user_id=user_id,
        account_id=account_id,
    )
    history_cache: dict[tuple[date, str], list[ContributionPoint]] = {}
    for goal in goals:
        previous_current = goal.current_amount
        previous_target = goal.target_amount
        if goal.linked_account_id is None:
            history = await _build_contribution_history(
                session,
                goal=goal,
                as_of_date=as_of_date,
            )
        else:
            created_date = goal.created_at.date() if goal.created_at else as_of_date
            cache_key = (created_date, goal.currency)
            if cache_key not in history_cache:
                daily = await goal_repo.sum_daily_net_contributions_for_account(
                    session,
                    user_id=goal.user_id,
                    account_id=goal.linked_account_id,
                    currency=goal.currency,
                    start_date=created_date,
                    end_date=as_of_date,
                )
                history_cache[cache_key] = build_cumulative_contribution_history(daily)
            history = history_cache[cache_key]
        if not history:
            continue
        new_current = normalize_money(history[-1].cumulative_amount)
        if new_current < Decimal("0"):
            new_current = Decimal("0.0000")
        if new_current == previous_current:
            continue
        goal.current_amount = new_current
        if goal.status != GoalStatus.ARCHIVED:
            goal.status = _goal_status_for_amounts(
                target_amount=goal.target_amount,
                current_amount=new_current,
            )
        await notification_service.notify_goal_milestones(
            session,
            user_id=user_id,
            goal_id=goal.id,
            goal_name=goal.name,
            previous_current=previous_current,
            previous_target=previous_target,
            current_amount=new_current,
            target_amount=goal.target_amount,
            provider=provider,
        )
