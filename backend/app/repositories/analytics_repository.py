"""SQL aggregation queries for analytics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import ColumnElement, func, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.financial_account import FinancialAccount
from app.models.transaction import Transaction
from app.models.transfer import Transfer


@dataclass(frozen=True)
class CurrencyTotal:
    currency: str
    total: Decimal


@dataclass(frozen=True)
class TypedDatedCurrencyTotal:
    transaction_type: TransactionType
    bucket_date: date
    currency: str
    total: Decimal


@dataclass(frozen=True)
class DatedCurrencyTotal:
    bucket_date: date
    currency: str
    total: Decimal


@dataclass(frozen=True)
class DatedCategoryExpenseTotal:
    category_id: uuid.UUID
    category_name: str
    currency: str
    bucket_date: date
    total: Decimal


@dataclass(frozen=True)
class LedgerDeltaRow:
    bucket_date: date
    account_id: uuid.UUID
    currency: str
    delta: Decimal


@dataclass(frozen=True)
class TopTransactionRow:
    transaction_id: uuid.UUID
    description: str
    amount: Decimal
    currency: str
    transaction_date: date
    category_name: str
    account_name: str


def _active_transactions_filter(
    user_id: uuid.UUID,
) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
    return (
        Transaction.user_id == user_id,
        Transaction.deleted_at.is_(None),
    )


async def sum_income_expenses_by_currency_and_date(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[TypedDatedCurrencyTotal]:
    result = await session.execute(
        select(
            Transaction.transaction_type,
            Transaction.transaction_date.label("bucket_date"),
            Transaction.currency,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .where(
            *_active_transactions_filter(user_id),
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .group_by(
            Transaction.transaction_type,
            Transaction.transaction_date,
            Transaction.currency,
        ),
    )
    return [
        TypedDatedCurrencyTotal(
            transaction_type=row.transaction_type,
            bucket_date=row.bucket_date,
            currency=row.currency,
            total=Decimal(row.total),
        )
        for row in result.all()
    ]


async def sum_daily_expenses_by_currency(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[DatedCurrencyTotal]:
    result = await session.execute(
        select(
            Transaction.transaction_date.label("bucket_date"),
            Transaction.currency,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .where(
            *_active_transactions_filter(user_id),
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .group_by(Transaction.transaction_date, Transaction.currency),
    )
    return [
        DatedCurrencyTotal(
            bucket_date=row.bucket_date,
            currency=row.currency,
            total=Decimal(row.total),
        )
        for row in result.all()
    ]


async def sum_expenses_by_category_and_date(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[DatedCategoryExpenseTotal]:
    result = await session.execute(
        select(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            Transaction.currency,
            Transaction.transaction_date.label("bucket_date"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(
            *_active_transactions_filter(user_id),
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .group_by(
            Category.id,
            Category.name,
            Transaction.currency,
            Transaction.transaction_date,
        ),
    )
    return [
        DatedCategoryExpenseTotal(
            category_id=row.category_id,
            category_name=row.category_name,
            currency=row.currency,
            bucket_date=row.bucket_date,
            total=Decimal(row.total),
        )
        for row in result.all()
    ]


async def sum_ledger_deltas_by_day(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[LedgerDeltaRow]:
    txn_income = select(
        Transaction.transaction_date.label("bucket_date"),
        Transaction.account_id.label("account_id"),
        Transaction.currency.label("currency"),
        Transaction.amount.label("delta"),
    ).where(
        *_active_transactions_filter(user_id),
        Transaction.transaction_type == TransactionType.INCOME,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date,
    )
    txn_expense = select(
        Transaction.transaction_date.label("bucket_date"),
        Transaction.account_id.label("account_id"),
        Transaction.currency.label("currency"),
        (-Transaction.amount).label("delta"),
    ).where(
        *_active_transactions_filter(user_id),
        Transaction.transaction_type == TransactionType.EXPENSE,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date,
    )
    transfer_out = select(
        Transfer.transaction_date.label("bucket_date"),
        Transfer.source_account_id.label("account_id"),
        Transfer.source_currency.label("currency"),
        (-Transfer.source_amount).label("delta"),
    ).where(
        Transfer.user_id == user_id,
        Transfer.transaction_date >= start_date,
        Transfer.transaction_date <= end_date,
    )
    transfer_in = select(
        Transfer.transaction_date.label("bucket_date"),
        Transfer.destination_account_id.label("account_id"),
        Transfer.destination_currency.label("currency"),
        Transfer.destination_amount.label("delta"),
    ).where(
        Transfer.user_id == user_id,
        Transfer.transaction_date >= start_date,
        Transfer.transaction_date <= end_date,
    )

    combined = union_all(txn_income, txn_expense, transfer_out, transfer_in).subquery()
    result = await session.execute(
        select(
            combined.c.bucket_date,
            combined.c.account_id,
            combined.c.currency,
            func.coalesce(func.sum(combined.c.delta), 0).label("delta"),
        ).group_by(
            combined.c.bucket_date,
            combined.c.account_id,
            combined.c.currency,
        ),
    )
    return [
        LedgerDeltaRow(
            bucket_date=row.bucket_date,
            account_id=row.account_id,
            currency=row.currency,
            delta=Decimal(row.delta),
        )
        for row in result.all()
    ]


async def sum_ledger_deltas_before_date(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    before_date: date,
) -> list[DatedCurrencyTotal]:
    """Return daily currency net ledger deltas strictly before ``before_date``.

    Keeping the transaction date is required so multi-currency balances convert
    with the historical rate for each day rather than a single snapshot rate.
    """
    txn_income = select(
        Transaction.transaction_date.label("bucket_date"),
        Transaction.currency.label("currency"),
        Transaction.amount.label("delta"),
    ).where(
        *_active_transactions_filter(user_id),
        Transaction.transaction_type == TransactionType.INCOME,
        Transaction.transaction_date < before_date,
    )
    txn_expense = select(
        Transaction.transaction_date.label("bucket_date"),
        Transaction.currency.label("currency"),
        (-Transaction.amount).label("delta"),
    ).where(
        *_active_transactions_filter(user_id),
        Transaction.transaction_type == TransactionType.EXPENSE,
        Transaction.transaction_date < before_date,
    )
    transfer_out = select(
        Transfer.transaction_date.label("bucket_date"),
        Transfer.source_currency.label("currency"),
        (-Transfer.source_amount).label("delta"),
    ).where(
        Transfer.user_id == user_id,
        Transfer.transaction_date < before_date,
    )
    transfer_in = select(
        Transfer.transaction_date.label("bucket_date"),
        Transfer.destination_currency.label("currency"),
        Transfer.destination_amount.label("delta"),
    ).where(
        Transfer.user_id == user_id,
        Transfer.transaction_date < before_date,
    )

    combined = union_all(txn_income, txn_expense, transfer_out, transfer_in).subquery()
    result = await session.execute(
        select(
            combined.c.bucket_date,
            combined.c.currency,
            func.coalesce(func.sum(combined.c.delta), 0).label("total"),
        ).group_by(combined.c.bucket_date, combined.c.currency),
    )
    return [
        DatedCurrencyTotal(
            bucket_date=row.bucket_date,
            currency=row.currency,
            total=Decimal(row.total),
        )
        for row in result.all()
    ]


async def sum_opening_balances_by_currency(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[CurrencyTotal]:
    result = await session.execute(
        select(
            FinancialAccount.currency,
            func.coalesce(func.sum(FinancialAccount.opening_balance), 0).label("total"),
        )
        .where(FinancialAccount.user_id == user_id)
        .group_by(FinancialAccount.currency),
    )
    return [
        CurrencyTotal(currency=row.currency, total=Decimal(row.total))
        for row in result.all()
    ]


async def list_transactions_for_ranking(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    transaction_type: TransactionType,
    start_date: date,
    end_date: date,
    max_candidates: int,
) -> list[TopTransactionRow]:
    """Load candidate transactions for reporting-currency ranking.

    Native-currency ORDER BY is insufficient when amounts must be converted
    before ranking. Candidates are capped to keep analytics queries bounded.
    """
    result = await session.execute(
        select(
            Transaction.id,
            Transaction.description,
            Transaction.amount,
            Transaction.currency,
            Transaction.transaction_date,
            Category.name.label("category_name"),
            FinancialAccount.name.label("account_name"),
        )
        .join(Category, Category.id == Transaction.category_id)
        .join(FinancialAccount, FinancialAccount.id == Transaction.account_id)
        .where(
            *_active_transactions_filter(user_id),
            Transaction.transaction_type == transaction_type,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .limit(max_candidates),
    )
    return [
        TopTransactionRow(
            transaction_id=row.id,
            description=row.description,
            amount=Decimal(row.amount),
            currency=row.currency,
            transaction_date=row.transaction_date,
            category_name=row.category_name,
            account_name=row.account_name,
        )
        for row in result.all()
    ]
