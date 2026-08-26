"""Current-user endpoints."""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: CurrentUserDep,
) -> UserResponse:
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        reporting_currency=current_user.reporting_currency,
    )
