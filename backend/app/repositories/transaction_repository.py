"""Transaction persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionType
from app.models.financial_account import FinancialAccount
from app.models.transaction import Transaction
from app.schemas.transactions import SortOrder, TransactionSortField


async def lock_account_for_update(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> FinancialAccount | None:
    result = await session.execute(
        select(FinancialAccount)
        .where(
            FinancialAccount.id == account_id,
            FinancialAccount.user_id == user_id,
        )
        .with_for_update(),
    )
    return result.scalar_one_or_none()


async def create_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    category_id: uuid.UUID,
    transaction_type: TransactionType,
    amount: Decimal,
    currency: str,
    description: str,
    transaction_date: date,
    notes: str | None,
) -> Transaction:
    transaction = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        amount=amount,
        currency=currency,
        description=description,
        transaction_date=transaction_date,
        notes=notes,
    )
    session.add(transaction)
    await session.flush()
    return transaction


async def get_active_transaction_for_update(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> Transaction | None:
    result = await session.execute(
        select(Transaction)
        .where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
        )
        .with_for_update(),
    )
    return result.scalar_one_or_none()


async def lock_accounts_for_update(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_ids: set[uuid.UUID],
) -> dict[uuid.UUID, FinancialAccount]:
    """Lock accounts in deterministic order to avoid deadlocks."""
    locked: dict[uuid.UUID, FinancialAccount] = {}
    for account_id in sorted(account_ids):
        account = await lock_account_for_update(
            session,
            user_id=user_id,
            account_id=account_id,
        )
        if account is not None:
            locked[account_id] = account
    return locked


async def get_active_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> Transaction | None:
    result = await session.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
        ),
    )
    return result.scalar_one_or_none()


async def list_transactions_for_user(
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
    offset: int,
    limit: int,
) -> tuple[list[Transaction], int]:
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

    total = await session.scalar(
        select(func.count()).select_from(Transaction).where(*filters),
    )
    result = await session.execute(
        select(Transaction)
        .where(*filters)
        .order_by(order_clause, Transaction.id.desc())
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all()), int(total or 0)


async def soft_delete_transaction(
    session: AsyncSession,
    transaction: Transaction,
) -> None:
    transaction.deleted_at = datetime.now(UTC)
    await session.flush()
