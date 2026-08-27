"""CSV export endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.models.enums import TransactionType
from app.schemas.transactions import SortOrder, TransactionSortField
from app.services import export_service

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/transactions")
async def export_transactions(
    session: SessionDep,
    settings: SettingsDep,
    current_user: CurrentUserDep,
    account_id: UUID | None = None,
    category_id: UUID | None = None,
    transaction_type: TransactionType | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    currency: str | None = None,
    description: Annotated[str | None, Query(max_length=500)] = None,
    sort_by: TransactionSortField = TransactionSortField.TRANSACTION_DATE,
    sort_order: SortOrder = SortOrder.ASC,
) -> Response:
    csv_body = await export_service.export_transactions_csv(
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
    )
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="monetra-transactions.csv"',
        },
    )
