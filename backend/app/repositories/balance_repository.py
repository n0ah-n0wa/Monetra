"""Ledger aggregation for balance reconciliation."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.balance import compute_balance_from_ledger
from app.models.enums import TransactionType
from app.models.financial_account import FinancialAccount
from app.models.transaction import Transaction
from app.models.transfer import Transfer


async def sum_active_income(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.deleted_at.is_(None),
            Transaction.transaction_type == TransactionType.INCOME,
        ),
    )
    return Decimal(total or 0)


async def sum_active_expenses(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.deleted_at.is_(None),
            Transaction.transaction_type == TransactionType.EXPENSE,
        ),
    )
    return Decimal(total or 0)


async def sum_incoming_transfers(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(Transfer.destination_amount), 0)).where(
            Transfer.destination_account_id == account_id,
        ),
    )
    return Decimal(total or 0)


async def sum_outgoing_transfers(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(Transfer.source_amount), 0)).where(
            Transfer.source_account_id == account_id,
        ),
    )
    return Decimal(total or 0)


async def compute_expected_balance(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    opening_balance: Decimal,
) -> Decimal:
    income_total = await sum_active_income(session, account_id=account_id)
    expense_total = await sum_active_expenses(session, account_id=account_id)
    incoming_total = await sum_incoming_transfers(session, account_id=account_id)
    outgoing_total = await sum_outgoing_transfers(session, account_id=account_id)
    return compute_balance_from_ledger(
        opening_balance=opening_balance,
        income_total=income_total,
        expense_total=expense_total,
        incoming_transfer_total=incoming_total,
        outgoing_transfer_total=outgoing_total,
    )


async def reconcile_account(
    session: AsyncSession,
    account: FinancialAccount,
) -> tuple[Decimal, Decimal]:
    """Return cached and ledger-derived balances for an account."""
    expected = await compute_expected_balance(
        session,
        account_id=account.id,
        opening_balance=account.opening_balance,
    )
    return account.current_balance, expected


async def reconcile_user_accounts(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[tuple[FinancialAccount, Decimal, Decimal]]:
    result = await session.execute(
        select(FinancialAccount).where(FinancialAccount.user_id == user_id),
    )
    accounts = list(result.scalars().all())
    reconciled: list[tuple[FinancialAccount, Decimal, Decimal]] = []
    for account in accounts:
        cached, expected = await reconcile_account(session, account)
        reconciled.append((account, cached, expected))
    return reconciled
