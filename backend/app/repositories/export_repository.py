"""Export query helpers."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.csv_export import ExportTransactionRow
from app.models.category import Category
from app.models.enums import TransactionType
from app.models.financial_account import FinancialAccount
from app.models.transaction import Transaction
from app.schemas.transactions import SortOrder, TransactionSortField


async def list_transactions_for_export(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    transaction_type: TransactionType | None,
    date_from: date | None,
    date_to: date | None,
    amount_min: Decimal | None,
    amount_max: Decimal | None,
    currency: str | None,
    description: str | None,
    sort_by: TransactionSortField,
    sort_order: SortOrder,
    limit: int,
) -> list[ExportTransactionRow]:
    """Return owned transactions with account/category names for CSV export."""
    filters = [
        Transaction.user_id == user_id,
        Transaction.deleted_at.is_(None),
    ]
    if account_id is not None:
        filters.append(Transaction.account_id == account_id)
    if category_id is not None:
        filters.append(Transaction.category_id == category_id)
    if transaction_type is not None:
        filters.append(Transaction.transaction_type == transaction_type)
    if date_from is not None:
        filters.append(Transaction.transaction_date >= date_from)
    if date_to is not None:
        filters.append(Transaction.transaction_date <= date_to)
    if amount_min is not None:
        filters.append(Transaction.amount >= amount_min)
    if amount_max is not None:
        filters.append(Transaction.amount <= amount_max)
    if currency is not None:
        filters.append(Transaction.currency == currency)
    if description:
        escaped = (
            description.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        filters.append(Transaction.description.ilike(f"%{escaped}%", escape="\\"))

    sort_column = {
        TransactionSortField.TRANSACTION_DATE: Transaction.transaction_date,
        TransactionSortField.AMOUNT: Transaction.amount,
        TransactionSortField.CREATED_AT: Transaction.created_at,
        TransactionSortField.DESCRIPTION: Transaction.description,
    }[sort_by]
    order_clause = (
        sort_column.asc() if sort_order == SortOrder.ASC else sort_column.desc()
    )

    result = await session.execute(
        select(
            Transaction.transaction_date,
            Transaction.transaction_type,
            Transaction.amount,
            Transaction.currency,
            Transaction.description,
            Category.name,
            FinancialAccount.name,
        )
        .join(FinancialAccount, FinancialAccount.id == Transaction.account_id)
        .join(Category, Category.id == Transaction.category_id)
        .where(*filters)
        .order_by(order_clause, Transaction.id.desc())
        .limit(limit),
    )
    rows: list[ExportTransactionRow] = []
    for (
        transaction_date,
        txn_type,
        amount,
        currency_code,
        description_text,
        category_name,
        account_name,
    ) in result.all():
        rows.append(
            ExportTransactionRow(
                transaction_date=transaction_date,
                transaction_type=txn_type.value,
                amount=amount,
                currency=currency_code,
                description=description_text,
                category=category_name,
                account=account_name,
            ),
        )
    return rows
