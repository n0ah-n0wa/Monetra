"""Current-user endpoints."""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.auth import UserResponse
from app.schemas.users import UserUpdateRequest
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: CurrentUserDep,
) -> UserResponse:
    return user_service.to_user_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    payload: UserUpdateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserResponse:
    return await user_service.update_user_profile(
        session,
        user=current_user,
        payload=payload,
    )
