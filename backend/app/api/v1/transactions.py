"""Transaction endpoints."""

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.schemas.mappers import format_datetime
from app.schemas.pagination import PaginatedResponse
from app.schemas.transactions import (
    SortOrder,
    TransactionCreateRequest,
    TransactionResponse,
    TransactionSortField,
    TransactionUpdateRequest,
)
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _to_transaction_response(transaction: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=str(transaction.id),
        account_id=str(transaction.account_id),
        category_id=str(transaction.category_id),
        transaction_type=transaction.transaction_type,
        amount=transaction.amount,
        currency=transaction.currency,
        description=transaction.description,
        transaction_date=transaction.transaction_date,
        notes=transaction.notes,
        created_at=format_datetime(transaction.created_at) or "",
        updated_at=format_datetime(transaction.updated_at) or "",
    )


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    payload: TransactionCreateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransactionResponse:
    transaction = await transaction_service.create_transaction(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    return _to_transaction_response(transaction)


@router.get("", response_model=PaginatedResponse[TransactionResponse])
async def list_transactions(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    account_id: UUID | None = None,
    category_id: UUID | None = None,
    transaction_type: TransactionType | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    currency: str | None = None,
    description: str | None = None,
    sort_by: TransactionSortField = TransactionSortField.TRANSACTION_DATE,
    sort_order: SortOrder = SortOrder.DESC,
) -> PaginatedResponse[TransactionResponse]:
    effective_page_size = page_size or settings.api_default_page_size
    result = await transaction_service.list_transactions(
        session,
        user_id=current_user.id,
        settings=settings,
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        currency=currency,
        description=description,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=effective_page_size,
    )
    return PaginatedResponse(
        items=[_to_transaction_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total_items=result.total_items,
        total_pages=result.total_pages,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransactionResponse:
    transaction = await transaction_service.get_transaction(
        session,
        user_id=current_user.id,
        transaction_id=transaction_id,
    )
    return _to_transaction_response(transaction)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransactionResponse:
    transaction = await transaction_service.update_transaction(
        session,
        user_id=current_user.id,
        transaction_id=transaction_id,
        payload=payload,
    )
    return _to_transaction_response(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    await transaction_service.delete_transaction(
        session,
        user_id=current_user.id,
        transaction_id=transaction_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
