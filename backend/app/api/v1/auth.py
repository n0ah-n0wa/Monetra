"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import (
    NotificationProviderDep,
    SessionDep,
    SettingsDep,
    enforce_auth_rate_limit,
    enforce_cookie_auth_origin,
    enforce_password_reset_rate_limit,
)
from app.core.cookies import clear_refresh_token_cookie, set_refresh_token_cookie
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    PasswordResetAckResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
)
from app.services import auth_service, password_reset_service

router = APIRouter(prefix="/auth", tags=["auth"])


async def _enforce_password_reset_request_rate_limit(
    request: Request,
    settings: SettingsDep,
    payload: PasswordResetRequest,
) -> None:
    await enforce_password_reset_rate_limit(request, settings, payload.email)


def _read_refresh_cookie(request: Request, settings: SettingsDep) -> str | None:
    value = request.cookies.get(settings.refresh_token_cookie_name)
    if value is None or not value.strip():
        return None
    return value


def _token_response(
    response: Response,
    *,
    tokens: auth_service.AuthTokens,
    settings: SettingsDep,
) -> AccessTokenResponse:
    set_refresh_token_cookie(response, token=tokens.refresh_token, settings=settings)
    return AccessTokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
    )


@router.post(
    "/register",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[None, Depends(enforce_auth_rate_limit)],
) -> AccessTokenResponse:
    _user, tokens = await auth_service.register_user(
        session,
        email=payload.email,
        password=payload.password,
        settings=settings,
    )
    return _token_response(response, tokens=tokens, settings=settings)


@router.post("/login", response_model=AccessTokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[None, Depends(enforce_auth_rate_limit)],
) -> AccessTokenResponse:
    _user, tokens = await auth_service.login_user(
        session,
        email=payload.email,
        password=payload.password,
        settings=settings,
    )
    return _token_response(response, tokens=tokens, settings=settings)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[None, Depends(enforce_auth_rate_limit)],
    __: Annotated[None, Depends(enforce_cookie_auth_origin)],
) -> AccessTokenResponse:
    refresh_token = _read_refresh_cookie(request, settings)
    tokens = await auth_service.refresh_session(
        session,
        refresh_token=refresh_token or "",
        settings=settings,
    )
    return _token_response(response, tokens=tokens, settings=settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[None, Depends(enforce_auth_rate_limit)],
    __: Annotated[None, Depends(enforce_cookie_auth_origin)],
) -> None:
    await auth_service.logout_user(
        session,
        refresh_token=_read_refresh_cookie(request, settings),
    )
    clear_refresh_token_cookie(response, settings=settings)


@router.post("/password-reset/request", response_model=PasswordResetAckResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    session: SessionDep,
    settings: SettingsDep,
    notification_provider: NotificationProviderDep,
    _: Annotated[None, Depends(_enforce_password_reset_request_rate_limit)],
) -> PasswordResetAckResponse:
    message = await password_reset_service.request_password_reset(
        session,
        email=payload.email,
        settings=settings,
        notification_provider=notification_provider,
    )
    return PasswordResetAckResponse(message=message)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[None, Depends(enforce_auth_rate_limit)],
) -> None:
    await password_reset_service.confirm_password_reset(
        session,
        token=payload.token,
        new_password=payload.new_password,
        settings=settings,
    )
