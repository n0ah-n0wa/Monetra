"""Transfer persistence helpers."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transfer import Transfer


async def get_transfer_by_id(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    transfer_id: uuid.UUID,
) -> Transfer | None:
    result = await session.execute(
        select(Transfer).where(
            Transfer.id == transfer_id,
            Transfer.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def get_transfer_by_idempotency_key(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    idempotency_key: str,
) -> Transfer | None:
    result = await session.execute(
        select(Transfer).where(
            Transfer.user_id == user_id,
            Transfer.idempotency_key == idempotency_key,
        ),
    )
    return result.scalar_one_or_none()


async def create_transfer(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    source_amount: Decimal,
    source_currency: str,
    destination_amount: Decimal,
    destination_currency: str,
    exchange_rate: Decimal | None,
    transaction_date: date,
    description: str | None,
    idempotency_key: str | None,
    metadata: dict[str, Any] | None = None,
) -> Transfer:
    transfer = Transfer(
        user_id=user_id,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        source_amount=source_amount,
        source_currency=source_currency,
        destination_amount=destination_amount,
        destination_currency=destination_currency,
        exchange_rate=exchange_rate,
        transaction_date=transaction_date,
        description=description,
        idempotency_key=idempotency_key,
        metadata_=metadata,
    )
    session.add(transfer)
    await session.flush()
    return transfer


async def list_transfers_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    offset: int,
    limit: int,
) -> tuple[list[Transfer], int]:
    filters = [Transfer.user_id == user_id]
    total = await session.scalar(
        select(func.count()).select_from(Transfer).where(*filters),
    )
    result = await session.execute(
        select(Transfer)
        .where(*filters)
        .order_by(Transfer.transaction_date.desc(), Transfer.id.desc())
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all()), int(total or 0)
