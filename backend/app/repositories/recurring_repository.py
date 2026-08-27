"""Recurring transaction persistence helpers."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RecurringFrequency, TransactionType
from app.models.recurring_transaction import RecurringTransaction
from app.models.recurring_transaction_execution import RecurringTransactionExecution


async def create_recurring_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    category_id: uuid.UUID,
    transaction_type: TransactionType,
    amount: Decimal,
    currency: str,
    description: str,
    frequency: RecurringFrequency,
    start_date: date,
    end_date: date | None,
    next_execution_date: date,
) -> RecurringTransaction:
    recurring = RecurringTransaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        amount=amount,
        currency=currency,
        description=description,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        next_execution_date=next_execution_date,
        is_active=True,
    )
    session.add(recurring)
    await session.flush()
    return recurring


async def get_recurring_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
) -> RecurringTransaction | None:
    result = await session.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == recurring_id,
            RecurringTransaction.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def get_recurring_transaction_for_update(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
) -> RecurringTransaction | None:
    result = await session.execute(
        select(RecurringTransaction)
        .where(
            RecurringTransaction.id == recurring_id,
            RecurringTransaction.user_id == user_id,
        )
        .with_for_update(),
    )
    return result.scalar_one_or_none()


async def list_recurring_transactions_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    is_active: bool | None,
    offset: int,
    limit: int,
) -> tuple[list[RecurringTransaction], int]:
    filters = [RecurringTransaction.user_id == user_id]
    if is_active is not None:
        filters.append(RecurringTransaction.is_active.is_(is_active))

    total = await session.scalar(
        select(func.count()).select_from(RecurringTransaction).where(*filters),
    )
    result = await session.execute(
        select(RecurringTransaction)
        .where(*filters)
        .order_by(
            RecurringTransaction.next_execution_date.asc(),
            RecurringTransaction.id.asc(),
        )
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all()), int(total or 0)


async def list_due_recurring_transactions_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of_date: date,
) -> list[RecurringTransaction]:
    result = await session.execute(
        select(RecurringTransaction)
        .where(
            RecurringTransaction.user_id == user_id,
            RecurringTransaction.is_active.is_(True),
            RecurringTransaction.next_execution_date <= as_of_date,
        )
        .order_by(
            RecurringTransaction.next_execution_date.asc(),
            RecurringTransaction.id.asc(),
        )
        .with_for_update(),
    )
    return list(result.scalars().all())


async def list_due_recurring_transactions(
    session: AsyncSession,
    *,
    as_of_date: date,
) -> list[RecurringTransaction]:
    """Return all active recurring definitions due on or before ``as_of_date``."""
    result = await session.execute(
        select(RecurringTransaction)
        .where(
            RecurringTransaction.is_active.is_(True),
            RecurringTransaction.next_execution_date <= as_of_date,
        )
        .order_by(
            RecurringTransaction.user_id.asc(),
            RecurringTransaction.next_execution_date.asc(),
            RecurringTransaction.id.asc(),
        )
        .with_for_update(),
    )
    return list(result.scalars().all())


async def get_execution_for_update(
    session: AsyncSession,
    *,
    recurring_id: uuid.UUID,
    execution_date: date,
) -> RecurringTransactionExecution | None:
    result = await session.execute(
        select(RecurringTransactionExecution)
        .where(
            RecurringTransactionExecution.recurring_transaction_id == recurring_id,
            RecurringTransactionExecution.execution_date == execution_date,
        )
        .with_for_update(),
    )
    return result.scalar_one_or_none()


async def get_execution(
    session: AsyncSession,
    *,
    recurring_id: uuid.UUID,
    execution_date: date,
) -> RecurringTransactionExecution | None:
    result = await session.execute(
        select(RecurringTransactionExecution).where(
            RecurringTransactionExecution.recurring_transaction_id == recurring_id,
            RecurringTransactionExecution.execution_date == execution_date,
        ),
    )
    return result.scalar_one_or_none()


async def list_executed_dates(
    session: AsyncSession,
    *,
    recurring_id: uuid.UUID,
) -> set[date]:
    result = await session.execute(
        select(RecurringTransactionExecution.execution_date).where(
            RecurringTransactionExecution.recurring_transaction_id == recurring_id,
        ),
    )
    return set(result.scalars().all())


async def create_execution(
    session: AsyncSession,
    *,
    recurring_id: uuid.UUID,
    execution_date: date,
    transaction_id: uuid.UUID,
) -> RecurringTransactionExecution:
    execution = RecurringTransactionExecution(
        recurring_transaction_id=recurring_id,
        execution_date=execution_date,
        transaction_id=transaction_id,
    )
    session.add(execution)
    await session.flush()
    return execution
