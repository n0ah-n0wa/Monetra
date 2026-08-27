"""CSV export orchestration."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ValidationAppError
from app.domain.csv_export import render_transactions_csv
from app.domain.currency import normalize_currency
from app.domain.transactions import normalize_money
from app.models.enums import TransactionType
from app.repositories import export_repository as export_repo
from app.schemas.transactions import SortOrder, TransactionSortField
from app.services import ownership


async def export_transactions_csv(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    account_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    transaction_type: TransactionType | None,
    date_from: date | None,
    date_to: date | None,
    amount_min: Decimal | None,
    amount_max: Decimal | None,
    currency: str | None,
    description: str | None,
    sort_by: TransactionSortField = TransactionSortField.TRANSACTION_DATE,
    sort_order: SortOrder = SortOrder.ASC,
) -> str:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValidationAppError(
            code="INVALID_DATE_RANGE",
            message="date_from must be on or before date_to.",
        )
    if amount_min is not None:
        amount_min = normalize_money(amount_min)
        if amount_min < Decimal("0"):
            raise ValidationAppError(
                code="INVALID_AMOUNT_RANGE",
                message="amount_min must be greater than or equal to zero.",
            )
    if amount_max is not None:
        amount_max = normalize_money(amount_max)
        if amount_max < Decimal("0"):
            raise ValidationAppError(
                code="INVALID_AMOUNT_RANGE",
                message="amount_max must be greater than or equal to zero.",
            )
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise ValidationAppError(
            code="INVALID_AMOUNT_RANGE",
            message="amount_min must be less than or equal to amount_max.",
        )
    if currency is not None:
        currency = normalize_currency(currency)

    if account_id is not None:
        await ownership.get_owned_account(
            session,
            user_id=user_id,
            account_id=account_id,
        )
    if category_id is not None:
        await ownership.get_accessible_category(
            session,
            user_id=user_id,
            category_id=category_id,
        )

    max_rows = settings.export_max_rows
    rows = await export_repo.list_transactions_for_export(
        session,
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        currency=currency,
        description=description.strip() if description else None,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=max_rows + 1,
    )
    if len(rows) > max_rows:
        raise ValidationAppError(
            code="EXPORT_TOO_MANY_ROWS",
            message=f"Export exceeds the maximum of {max_rows} rows.",
            details={"max_rows": max_rows},
        )
    return render_transactions_csv(rows)
