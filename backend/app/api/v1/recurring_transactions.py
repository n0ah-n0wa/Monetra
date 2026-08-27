"""Recurring transaction endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import (
    CurrentUserDep,
    NotificationProviderDep,
    SessionDep,
    SettingsDep,
)
from app.models.recurring_transaction import RecurringTransaction
from app.schemas.mappers import format_datetime
from app.schemas.pagination import PaginatedResponse
from app.schemas.recurring_transactions import (
    ProcessDueRecurringRequest,
    ProcessDueRecurringResponse,
    RecurringTransactionCreateRequest,
    RecurringTransactionResponse,
    RecurringTransactionUpdateRequest,
)
from app.services import recurring_service

router = APIRouter(prefix="/recurring-transactions", tags=["recurring-transactions"])


def _to_recurring_response(
    recurring: RecurringTransaction,
) -> RecurringTransactionResponse:
    return RecurringTransactionResponse(
        id=str(recurring.id),
        account_id=str(recurring.account_id),
        category_id=str(recurring.category_id),
        transaction_type=recurring.transaction_type,
        amount=recurring.amount,
        currency=recurring.currency,
        description=recurring.description,
        frequency=recurring.frequency,
        start_date=recurring.start_date,
        end_date=recurring.end_date,
        next_execution_date=recurring.next_execution_date,
        is_active=recurring.is_active,
        created_at=format_datetime(recurring.created_at) or "",
        updated_at=format_datetime(recurring.updated_at) or "",
    )


@router.post(
    "",
    response_model=RecurringTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recurring_transaction(
    payload: RecurringTransactionCreateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> RecurringTransactionResponse:
    recurring = await recurring_service.create_recurring_transaction(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    return _to_recurring_response(recurring)


@router.get("", response_model=PaginatedResponse[RecurringTransactionResponse])
async def list_recurring_transactions(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    is_active: bool | None = None,
) -> PaginatedResponse[RecurringTransactionResponse]:
    effective_page_size = page_size or settings.api_default_page_size
    result = await recurring_service.list_recurring_transactions(
        session,
        user_id=current_user.id,
        settings=settings,
        is_active=is_active,
        page=page,
        page_size=effective_page_size,
    )
    return PaginatedResponse(
        items=[_to_recurring_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total_items=result.total_items,
        total_pages=result.total_pages,
    )


@router.get("/{recurring_id}", response_model=RecurringTransactionResponse)
async def get_recurring_transaction(
    recurring_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> RecurringTransactionResponse:
    recurring = await recurring_service.get_recurring_transaction(
        session,
        user_id=current_user.id,
        recurring_id=recurring_id,
    )
    return _to_recurring_response(recurring)


@router.patch("/{recurring_id}", response_model=RecurringTransactionResponse)
async def update_recurring_transaction(
    recurring_id: UUID,
    payload: RecurringTransactionUpdateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> RecurringTransactionResponse:
    recurring = await recurring_service.update_recurring_transaction(
        session,
        user_id=current_user.id,
        recurring_id=recurring_id,
        payload=payload,
    )
    return _to_recurring_response(recurring)


@router.post("/{recurring_id}/archive", response_model=RecurringTransactionResponse)
async def archive_recurring_transaction(
    recurring_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> RecurringTransactionResponse:
    recurring = await recurring_service.archive_recurring_transaction(
        session,
        user_id=current_user.id,
        recurring_id=recurring_id,
    )
    return _to_recurring_response(recurring)


@router.post("/process-due", response_model=ProcessDueRecurringResponse)
async def process_due_recurring_transactions(
    session: SessionDep,
    current_user: CurrentUserDep,
    notification_provider: NotificationProviderDep,
    payload: ProcessDueRecurringRequest | None = None,
) -> ProcessDueRecurringResponse:
    """Execute due recurring definitions for the authenticated user."""
    request = payload or ProcessDueRecurringRequest()
    return await recurring_service.process_due_recurring_transactions_for_user(
        session,
        user_id=current_user.id,
        as_of_date=request.as_of_date,
        provider=notification_provider,
    )
