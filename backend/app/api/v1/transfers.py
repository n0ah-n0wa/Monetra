"""Transfer endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.models.transfer import Transfer
from app.schemas.mappers import format_datetime
from app.schemas.pagination import PaginatedResponse
from app.schemas.transfers import TransferCreateRequest, TransferResponse
from app.services import transfer_service

router = APIRouter(prefix="/transfers", tags=["transfers"])


def _to_transfer_response(transfer: Transfer) -> TransferResponse:
    return TransferResponse(
        id=str(transfer.id),
        source_account_id=str(transfer.source_account_id),
        destination_account_id=str(transfer.destination_account_id),
        source_amount=transfer.source_amount,
        source_currency=transfer.source_currency,
        destination_amount=transfer.destination_amount,
        destination_currency=transfer.destination_currency,
        exchange_rate=transfer.exchange_rate,
        transaction_date=transfer.transaction_date,
        description=transfer.description,
        idempotency_key=transfer.idempotency_key,
        created_at=format_datetime(transfer.created_at) or "",
        updated_at=format_datetime(transfer.updated_at) or "",
    )


@router.post("", response_model=TransferResponse)
async def create_transfer(
    payload: TransferCreateRequest,
    response: Response,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransferResponse:
    transfer, created = await transfer_service.create_transfer(
        session,
        user_id=current_user.id,
        payload=payload,
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return _to_transfer_response(transfer)


@router.get("", response_model=PaginatedResponse[TransferResponse])
async def list_transfers(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
) -> PaginatedResponse[TransferResponse]:
    effective_page_size = page_size or settings.api_default_page_size
    result = await transfer_service.list_transfers(
        session,
        user_id=current_user.id,
        settings=settings,
        page=page,
        page_size=effective_page_size,
    )
    return PaginatedResponse(
        items=[_to_transfer_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total_items=result.total_items,
        total_pages=result.total_pages,
    )


@router.get("/{transfer_id}", response_model=TransferResponse)
async def get_transfer(
    transfer_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransferResponse:
    transfer = await transfer_service.get_transfer(
        session,
        user_id=current_user.id,
        transfer_id=transfer_id,
    )
    return _to_transfer_response(transfer)
