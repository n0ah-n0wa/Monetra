"""Import job persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.csv_import import normalize_description_for_duplicate
from app.domain.transactions import normalize_money
from app.models.enums import ImportJobStatus
from app.models.import_job import ImportJob
from app.models.transaction import Transaction


async def create_import_job(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_account_id: uuid.UUID,
    original_filename: str,
    content_type: str | None,
) -> ImportJob:
    job = ImportJob(
        user_id=user_id,
        target_account_id=target_account_id,
        original_filename=original_filename,
        content_type=content_type,
        status=ImportJobStatus.PENDING,
    )
    session.add(job)
    await session.flush()
    return job


async def get_import_job_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
) -> ImportJob | None:
    result = await session.execute(
        select(ImportJob).where(
            ImportJob.id == job_id,
            ImportJob.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def get_import_job_for_update(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
) -> ImportJob | None:
    result = await session.execute(
        select(ImportJob)
        .where(
            ImportJob.id == job_id,
            ImportJob.user_id == user_id,
        )
        .with_for_update(),
    )
    return result.scalar_one_or_none()


async def list_import_jobs_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    offset: int,
    limit: int,
) -> tuple[list[ImportJob], int]:
    filters = [ImportJob.user_id == user_id]
    total = await session.scalar(
        select(func.count()).select_from(ImportJob).where(*filters),
    )
    result = await session.execute(
        select(ImportJob)
        .where(*filters)
        .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
        .offset(offset)
        .limit(limit),
    )
    return list(result.scalars().all()), int(total or 0)


async def find_existing_external_references(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    references: set[str],
) -> set[str]:
    if not references:
        return set()
    result = await session.execute(
        select(Transaction.external_reference).where(
            Transaction.user_id == user_id,
            Transaction.account_id == account_id,
            Transaction.deleted_at.is_(None),
            Transaction.external_reference.in_(sorted(references)),
        ),
    )
    return {value for value in result.scalars().all() if value is not None}


async def find_fingerprint_matches(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    candidates: list[tuple[Any, ...]],
) -> set[tuple[Any, ...]]:
    """Match (date, amount, normalized description) already present on the account."""
    if not candidates:
        return set()
    dates = {item[0] for item in candidates}
    result = await session.execute(
        select(
            Transaction.transaction_date,
            Transaction.amount,
            Transaction.description,
        ).where(
            Transaction.user_id == user_id,
            Transaction.account_id == account_id,
            Transaction.deleted_at.is_(None),
            Transaction.transaction_date.in_(sorted(dates)),
        ),
    )
    existing = {
        (
            row.transaction_date,
            normalize_money(row.amount),
            normalize_description_for_duplicate(row.description),
        )
        for row in result.all()
    }
    matched: set[tuple[Any, ...]] = set()
    for transaction_date, amount, description in candidates:
        key = (
            transaction_date,
            normalize_money(amount),
            normalize_description_for_duplicate(str(description)),
        )
        if key in existing:
            matched.add(key)
    return matched


def mark_completed(
    job: ImportJob,
    *,
    status: ImportJobStatus,
    error_details: dict[str, Any] | None = None,
) -> None:
    job.status = status
    job.completed_at = datetime.now(UTC)
    if error_details is not None:
        job.error_details = error_details
