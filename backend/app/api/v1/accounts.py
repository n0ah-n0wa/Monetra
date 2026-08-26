"""Financial account endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.models.enums import AccountStatus
from app.models.financial_account import FinancialAccount
from app.schemas.accounts import (
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
)
from app.schemas.mappers import format_datetime
from app.schemas.pagination import PaginatedResponse
from app.services import account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _to_account_response(account: FinancialAccount) -> AccountResponse:
    return AccountResponse(
        id=str(account.id),
        name=account.name,
        account_type=account.account_type,
        currency=account.currency,
        opening_balance=account.opening_balance,
        current_balance=account.current_balance,
        status=account.status,
        archived_at=format_datetime(account.archived_at),
        created_at=format_datetime(account.created_at) or "",
        updated_at=format_datetime(account.updated_at) or "",
    )


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AccountResponse:
    account = await account_service.create_account(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    return _to_account_response(account)


@router.get("", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    status: AccountStatus | None = None,
) -> PaginatedResponse[AccountResponse]:
    effective_page_size = page_size or settings.api_default_page_size
    result = await account_service.list_accounts(
        session,
        user_id=current_user.id,
        settings=settings,
        status=status,
        page=page,
        page_size=effective_page_size,
    )
    return PaginatedResponse(
        items=[_to_account_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total_items=result.total_items,
        total_pages=result.total_pages,
    )


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AccountResponse:
    account = await account_service.get_account(
        session,
        user_id=current_user.id,
        account_id=account_id,
    )
    return _to_account_response(account)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    payload: AccountUpdateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AccountResponse:
    account = await account_service.update_account(
        session,
        user_id=current_user.id,
        account_id=account_id,
        payload=payload,
    )
    return _to_account_response(account)


@router.post("/{account_id}/archive", response_model=AccountResponse)
async def archive_account(
    account_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AccountResponse:
    account = await account_service.archive_account(
        session,
        user_id=current_user.id,
        account_id=account_id,
    )
    return _to_account_response(account)
