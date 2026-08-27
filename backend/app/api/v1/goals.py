"""Financial goal endpoints."""

from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.models.enums import GoalStatus
from app.schemas.goals import (
    GoalCreateRequest,
    GoalProgressResponse,
    GoalResponse,
    GoalUpdateRequest,
)
from app.schemas.pagination import PaginatedResponse
from app.services import goal_service

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GoalResponse:
    goal = await goal_service.create_goal(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    return goal_service.build_goal_response(goal)


@router.get("", response_model=PaginatedResponse[GoalResponse])
async def list_goals(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    status: GoalStatus | None = None,
    include_archived: bool = False,
    as_of_date: date | None = None,
    include_progress: bool = False,
) -> PaginatedResponse[GoalResponse]:
    effective_page_size = page_size or settings.api_default_page_size
    result = await goal_service.list_goals(
        session,
        user_id=current_user.id,
        settings=settings,
        status=status,
        include_archived=include_archived,
        page=page,
        page_size=effective_page_size,
    )
    effective_date = as_of_date or datetime.now(UTC).date()
    items: list[GoalResponse] = []
    for goal in result.items:
        progress = None
        if include_progress:
            progress = await goal_service._compute_progress(
                session,
                goal=goal,
                as_of_date=effective_date,
            )
        items.append(goal_service.build_goal_response(goal, progress=progress))

    return PaginatedResponse(
        items=items,
        page=result.page,
        page_size=result.page_size,
        total_items=result.total_items,
        total_pages=result.total_pages,
    )


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    as_of_date: date | None = None,
    include_progress: bool = False,
) -> GoalResponse:
    goal = await goal_service.get_goal(
        session,
        user_id=current_user.id,
        goal_id=goal_id,
    )
    progress = None
    if include_progress:
        progress = await goal_service.get_goal_progress(
            session,
            user_id=current_user.id,
            goal_id=goal_id,
            as_of_date=as_of_date,
        )
    return goal_service.build_goal_response(goal, progress=progress)


@router.get("/{goal_id}/progress", response_model=GoalProgressResponse)
async def get_goal_progress(
    goal_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    as_of_date: date | None = None,
) -> GoalProgressResponse:
    return await goal_service.get_goal_progress(
        session,
        user_id=current_user.id,
        goal_id=goal_id,
        as_of_date=as_of_date,
    )


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: UUID,
    payload: GoalUpdateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GoalResponse:
    goal = await goal_service.update_goal(
        session,
        user_id=current_user.id,
        goal_id=goal_id,
        payload=payload,
    )
    return goal_service.build_goal_response(goal)


@router.post("/{goal_id}/archive", response_model=GoalResponse)
async def archive_goal(
    goal_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> GoalResponse:
    goal = await goal_service.archive_goal(
        session,
        user_id=current_user.id,
        goal_id=goal_id,
    )
    return goal_service.build_goal_response(goal)
