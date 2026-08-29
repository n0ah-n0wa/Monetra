"""CSV import orchestration: upload → preview → confirm → report."""

from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.domain.csv_import import (
    ParsedImportRow,
    duplicate_fingerprint,
    mark_intra_file_duplicates,
    normalize_description_for_duplicate,
    parse_csv_content,
    sanitize_upload_filename,
)
from app.domain.notifications import NotificationProvider
from app.domain.transactions import (
    apply_balance_delta,
    category_supports_transaction_type,
    normalize_money,
    signed_transaction_amount,
)
from app.models.category import Category
from app.models.enums import (
    AccountStatus,
    AuditAction,
    CategoryStatus,
    ImportJobStatus,
    TransactionType,
)
from app.models.import_job import ImportJob
from app.repositories import category_repository as category_repo
from app.repositories import import_repository as import_repo
from app.repositories import transaction_repository as transaction_repo
from app.schemas.imports import (
    ImportJobResponse,
    ImportJobStats,
    ImportPreviewRowResponse,
    ImportRowErrorResponse,
)
from app.schemas.mappers import format_datetime
from app.schemas.pagination import (
    PaginatedResponse,
    build_paginated_response,
    pagination_params,
)
from app.services import audit_service, goal_service, notification_service, ownership

_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",
    "application/octet-stream",
}
_UPLOAD_READ_CHUNK_SIZE = 64 * 1024


def _stats_from_job(job: ImportJob) -> ImportJobStats:
    return ImportJobStats(
        total_rows=job.total_rows,
        valid_rows=job.valid_rows,
        invalid_rows=job.invalid_rows,
        imported_rows=job.imported_rows,
        skipped_rows=job.skipped_rows,
        duplicate_rows=job.duplicate_rows,
    )


def _payload(job: ImportJob) -> dict[str, Any]:
    details = job.error_details or {}
    return details if isinstance(details, dict) else {}


def build_import_job_response(
    job: ImportJob,
    *,
    preview_limit: int | None = None,
) -> ImportJobResponse:
    payload = _payload(job)
    preview_rows = [
        ImportPreviewRowResponse.model_validate(row)
        for row in payload.get("preview_rows", [])
    ]
    errors = [
        ImportRowErrorResponse.model_validate(row) for row in payload.get("errors", [])
    ]
    if preview_limit is not None:
        preview_rows = preview_rows[:preview_limit]
    return ImportJobResponse(
        id=str(job.id),
        target_account_id=(
            str(job.target_account_id) if job.target_account_id is not None else None
        ),
        original_filename=job.original_filename,
        content_type=job.content_type,
        status=job.status,
        stats=_stats_from_job(job),
        preview_rows=preview_rows,
        errors=errors,
        completed_at=format_datetime(job.completed_at),
        created_at=format_datetime(job.created_at) or "",
        updated_at=format_datetime(job.updated_at) or "",
    )


def _fingerprint_key(
    *,
    transaction_date: date,
    amount: Decimal,
    description: str,
) -> tuple[date, Decimal, str]:
    return (
        transaction_date,
        normalize_money(amount),
        normalize_description_for_duplicate(description),
    )


async def read_upload_limited(upload: UploadFile, *, max_bytes: int) -> bytes:
    """Read an upload in chunks, rejecting bodies larger than ``max_bytes``."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(_UPLOAD_READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValidationAppError(
                code="FILE_TOO_LARGE",
                message=(f"CSV file exceeds the maximum size of {max_bytes} bytes."),
                details={"max_bytes": max_bytes},
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_upload(
    *,
    filename: str,
    content_type: str | None,
    raw_bytes: bytes,
    settings: Settings,
) -> str:
    if content_type is None or not content_type.strip():
        raise ValidationAppError(
            code="INVALID_CONTENT_TYPE",
            message="Content-Type header is required for CSV upload.",
        )
    if content_type.split(";")[0].strip().lower() not in (*_ALLOWED_CONTENT_TYPES,):
        raise ValidationAppError(
            code="INVALID_CONTENT_TYPE",
            message="Unsupported content type for CSV upload.",
            details={"content_type": content_type},
        )
    if len(raw_bytes) == 0:
        raise ValidationAppError(
            code="CSV_EMPTY",
            message="CSV file is empty.",
        )
    if len(raw_bytes) > settings.import_max_file_bytes:
        raise ValidationAppError(
            code="FILE_TOO_LARGE",
            message=(
                "CSV file exceeds the maximum size of "
                f"{settings.import_max_file_bytes} bytes."
            ),
            details={"max_bytes": settings.import_max_file_bytes},
        )
    try:
        return raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationAppError(
            code="CSV_INVALID_ENCODING",
            message="CSV file must be UTF-8 encoded.",
        ) from exc


def _budget_evaluation_dates(expense_dates: set[date]) -> list[date]:
    """Collapse expense dates to month-end checkpoints for budget scans."""
    return sorted(
        {date(d.year, d.month, monthrange(d.year, d.month)[1]) for d in expense_dates},
    )


async def _resolve_category_id(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    row: ParsedImportRow,
    category_lookup: dict[str, Category] | None = None,
) -> uuid.UUID:
    if category_lookup is not None:
        category = category_lookup.get(row.category_name.strip().lower())
    else:
        category = await category_repo.find_active_category_by_name(
            session,
            user_id=user_id,
            name=row.category_name,
        )
    if category is None:
        raise ValidationAppError(
            code="CATEGORY_NOT_FOUND",
            message=f"Category '{row.category_name}' was not found.",
        )
    if not category_supports_transaction_type(
        category.category_type,
        row.transaction_type,
    ):
        raise ValidationAppError(
            code="CATEGORY_TYPE_MISMATCH",
            message="Category type does not match the transaction type.",
        )
    return category.id


async def upload_and_preview(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    account_id: uuid.UUID,
    filename: str | None,
    content_type: str | None,
    raw_bytes: bytes,
) -> ImportJobResponse:
    safe_filename = sanitize_upload_filename(filename)
    text = _validate_upload(
        filename=safe_filename,
        content_type=content_type,
        raw_bytes=raw_bytes,
        settings=settings,
    )
    account = await ownership.get_owned_account(
        session,
        user_id=user_id,
        account_id=account_id,
    )
    if account.status == AccountStatus.ARCHIVED:
        raise ValidationAppError(
            code="ACCOUNT_ARCHIVED",
            message="Archived accounts cannot receive imported transactions.",
        )

    parsed = parse_csv_content(text, max_rows=settings.import_max_rows)
    account_key = str(account.id)
    intra_duplicates = mark_intra_file_duplicates(parsed.rows, account_id=account_key)

    external_refs = {
        row.external_reference
        for row in parsed.rows
        if row.external_reference and row.row_number not in intra_duplicates
    }
    existing_refs = await import_repo.find_existing_external_references(
        session,
        user_id=user_id,
        account_id=account.id,
        references=external_refs,
    )
    fingerprint_candidates = [
        (row.transaction_date, row.amount, row.description)
        for row in parsed.rows
        if row.external_reference is None and row.row_number not in intra_duplicates
    ]
    existing_fingerprints = await import_repo.find_fingerprint_matches(
        session,
        user_id=user_id,
        account_id=account.id,
        candidates=fingerprint_candidates,
    )

    category_lookup = await category_repo.build_active_category_lookup_by_name(
        session,
        user_id=user_id,
    )

    preview_rows: list[dict[str, Any]] = []
    row_errors = [error.to_dict() for error in parsed.errors]
    duplicate_count = 0
    valid_count = 0

    for row in parsed.rows:
        is_duplicate = False
        duplicate_reason: str | None = None

        if row.row_number in intra_duplicates:
            is_duplicate = True
            duplicate_reason = "duplicate_in_file"
        elif row.external_reference and row.external_reference in existing_refs:
            is_duplicate = True
            duplicate_reason = "duplicate_external_reference"
        elif row.external_reference is None and (
            _fingerprint_key(
                transaction_date=row.transaction_date,
                amount=row.amount,
                description=row.description,
            )
            in existing_fingerprints
        ):
            is_duplicate = True
            duplicate_reason = "duplicate_existing_transaction"

        try:
            resolved = await _resolve_category_id(
                session,
                user_id=user_id,
                row=row,
                category_lookup=category_lookup,
            )
            category_id = str(resolved)
        except ValidationAppError as exc:
            row_errors.append(
                {
                    "row_number": row.row_number,
                    "code": exc.code,
                    "message": exc.message,
                    "raw": row.raw,
                },
            )
            continue

        if is_duplicate:
            duplicate_count += 1
        else:
            valid_count += 1

        preview_rows.append(
            {
                "row_number": row.row_number,
                "transaction_date": row.transaction_date.isoformat(),
                "transaction_type": row.transaction_type.value,
                "amount": str(row.amount),
                "description": row.description,
                "category": row.category_name,
                "category_id": category_id,
                "external_reference": row.external_reference,
                "notes": row.notes,
                "is_duplicate": is_duplicate,
                "duplicate_reason": duplicate_reason,
                "fingerprint": duplicate_fingerprint(
                    account_id=account_key,
                    transaction_date=row.transaction_date,
                    amount=row.amount,
                    description=row.description,
                    external_reference=row.external_reference,
                ),
            },
        )

    job = await import_repo.create_import_job(
        session,
        user_id=user_id,
        target_account_id=account.id,
        original_filename=safe_filename,
        content_type=content_type,
    )
    job.status = ImportJobStatus.PREVIEW
    job.total_rows = parsed.total_rows
    job.valid_rows = valid_count
    job.invalid_rows = len(row_errors)
    job.duplicate_rows = duplicate_count
    job.imported_rows = 0
    job.skipped_rows = 0
    job.error_details = {
        "preview_rows": preview_rows,
        "errors": row_errors,
    }
    await session.commit()
    await session.refresh(job)
    return build_import_job_response(job, preview_limit=settings.import_preview_limit)


async def get_import_job(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    job_id: uuid.UUID,
) -> ImportJobResponse:
    job = await import_repo.get_import_job_for_user(
        session,
        user_id=user_id,
        job_id=job_id,
    )
    if job is None:
        raise NotFoundError(
            code="IMPORT_JOB_NOT_FOUND",
            message="Import job was not found.",
        )
    return build_import_job_response(job, preview_limit=settings.import_preview_limit)


async def list_import_jobs(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    page: int,
    page_size: int | None,
) -> PaginatedResponse[ImportJobResponse]:
    offset, limit = pagination_params(
        page=page,
        page_size=page_size or settings.api_default_page_size,
        max_page_size=settings.api_max_page_size,
    )
    jobs, total = await import_repo.list_import_jobs_for_user(
        session,
        user_id=user_id,
        offset=offset,
        limit=limit,
    )
    return build_paginated_response(
        items=[
            build_import_job_response(job, preview_limit=settings.import_preview_limit)
            for job in jobs
        ],
        page=max(page, 1),
        page_size=limit,
        total_items=total,
    )


async def _live_duplicate_sets(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    candidates: list[dict[str, Any]],
) -> tuple[set[str], set[tuple[date, Decimal, str]]]:
    external_refs = {
        str(row["external_reference"])
        for row in candidates
        if row.get("external_reference")
    }
    existing_refs = await import_repo.find_existing_external_references(
        session,
        user_id=user_id,
        account_id=account_id,
        references=external_refs,
    )
    fingerprint_candidates = [
        (
            date.fromisoformat(str(row["transaction_date"])),
            Decimal(str(row["amount"])),
            str(row["description"]),
        )
        for row in candidates
        if not row.get("external_reference")
    ]
    existing_fingerprints = await import_repo.find_fingerprint_matches(
        session,
        user_id=user_id,
        account_id=account_id,
        candidates=fingerprint_candidates,
    )
    return existing_refs, existing_fingerprints


def _row_is_live_duplicate(
    row: dict[str, Any],
    *,
    existing_refs: set[str],
    existing_fingerprints: set[tuple[date, Decimal, str]],
) -> bool:
    external_reference = row.get("external_reference")
    if external_reference:
        return str(external_reference) in existing_refs
    return (
        _fingerprint_key(
            transaction_date=date.fromisoformat(str(row["transaction_date"])),
            amount=Decimal(str(row["amount"])),
            description=str(row["description"]),
        )
        in existing_fingerprints
    )


async def confirm_import(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    job_id: uuid.UUID,
    skip_duplicates: bool = True,
    provider: NotificationProvider | None = None,
) -> ImportJobResponse:
    job = await import_repo.get_import_job_for_update(
        session,
        user_id=user_id,
        job_id=job_id,
    )
    if job is None:
        raise NotFoundError(
            code="IMPORT_JOB_NOT_FOUND",
            message="Import job was not found.",
        )
    # Idempotent retry: confirming an already-completed job returns the same result.
    if job.status == ImportJobStatus.COMPLETED:
        return build_import_job_response(
            job,
            preview_limit=settings.import_preview_limit,
        )
    if job.status != ImportJobStatus.PREVIEW:
        raise ConflictError(
            code="IMPORT_NOT_CONFIRMABLE",
            message="Only preview import jobs can be confirmed.",
            details={"status": job.status.value},
        )
    if job.target_account_id is None:
        raise ValidationAppError(
            code="IMPORT_ACCOUNT_REQUIRED",
            message="Import job is missing a target account.",
        )

    payload = _payload(job)
    preview_rows: list[dict[str, Any]] = list(payload.get("preview_rows", []))

    account = await ownership.get_owned_account(
        session,
        user_id=user_id,
        account_id=job.target_account_id,
    )
    if account.status == AccountStatus.ARCHIVED:
        raise ValidationAppError(
            code="ACCOUNT_ARCHIVED",
            message="Archived accounts cannot receive imported transactions.",
        )

    job.status = ImportJobStatus.PROCESSING
    await session.flush()

    try:
        candidates = [row for row in preview_rows if row.get("category_id")]
        existing_refs, existing_fingerprints = await _live_duplicate_sets(
            session,
            user_id=user_id,
            account_id=account.id,
            candidates=candidates,
        )

        importable: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        seen_in_batch_refs: set[str] = set()
        seen_in_batch_fps: set[tuple[date, Decimal, str]] = set()
        validated_category_ids: set[uuid.UUID] = set()

        for row in candidates:
            preview_duplicate = bool(row.get("is_duplicate"))
            live_duplicate = _row_is_live_duplicate(
                row,
                existing_refs=existing_refs,
                existing_fingerprints=existing_fingerprints,
            )
            external_reference = row.get("external_reference")
            batch_duplicate = False
            if external_reference:
                ref = str(external_reference)
                if ref in seen_in_batch_refs:
                    batch_duplicate = True
                else:
                    seen_in_batch_refs.add(ref)
            else:
                fp = _fingerprint_key(
                    transaction_date=date.fromisoformat(str(row["transaction_date"])),
                    amount=Decimal(str(row["amount"])),
                    description=str(row["description"]),
                )
                if fp in seen_in_batch_fps:
                    batch_duplicate = True
                else:
                    seen_in_batch_fps.add(fp)

            is_duplicate = preview_duplicate or live_duplicate or batch_duplicate
            if is_duplicate:
                if skip_duplicates:
                    skipped.append(row)
                    continue
                raise ConflictError(
                    code="IMPORT_DUPLICATE_ROW",
                    message=(
                        "Cannot import rows that duplicate existing transactions "
                        "when skip_duplicates is false."
                    ),
                    details={
                        "transaction_date": str(row.get("transaction_date")),
                        "description": str(row.get("description")),
                    },
                )

            category_id = uuid.UUID(str(row["category_id"]))
            if category_id not in validated_category_ids:
                category = await ownership.get_accessible_category(
                    session,
                    user_id=user_id,
                    category_id=category_id,
                )
                if category.status == CategoryStatus.ARCHIVED:
                    raise ValidationAppError(
                        code="CATEGORY_ARCHIVED",
                        message="Archived categories cannot be used for transactions.",
                    )
                validated_category_ids.add(category_id)
            importable.append(row)

        imported = 0
        expense_dates: set[date] = set()
        imported_dates: set[date] = set()
        batch_size = settings.import_commit_batch_size

        for batch_start in range(0, len(importable), batch_size):
            batch = importable[batch_start : batch_start + batch_size]
            locked = await transaction_repo.lock_accounts_for_update(
                session,
                user_id=user_id,
                account_ids={account.id},
            )
            locked_account = locked.get(account.id)
            if locked_account is None:
                raise NotFoundError(
                    code="ACCOUNT_NOT_FOUND",
                    message="Financial account was not found.",
                )

            for row in batch:
                amount = Decimal(str(row["amount"]))
                transaction_type = TransactionType(str(row["transaction_type"]))
                row_date = date.fromisoformat(str(row["transaction_date"]))
                imported_dates.add(row_date)
                if transaction_type == TransactionType.EXPENSE:
                    expense_dates.add(row_date)
                delta = signed_transaction_amount(transaction_type, amount)
                locked_account.current_balance = apply_balance_delta(
                    locked_account.current_balance,
                    delta,
                )
                await transaction_repo.create_transaction(
                    session,
                    user_id=user_id,
                    account_id=locked_account.id,
                    category_id=uuid.UUID(str(row["category_id"])),
                    transaction_type=transaction_type,
                    amount=amount,
                    currency=locked_account.currency,
                    description=str(row["description"]),
                    transaction_date=row_date,
                    notes=row.get("notes"),
                    import_job_id=job.id,
                    external_reference=row.get("external_reference"),
                )
                imported += 1

            await session.commit()

        job = await import_repo.get_import_job_for_update(
            session,
            user_id=user_id,
            job_id=job_id,
        )
        if job is None:
            raise NotFoundError(
                code="IMPORT_JOB_NOT_FOUND",
                message="Import job was not found.",
            )

        locked = await transaction_repo.lock_accounts_for_update(
            session,
            user_id=user_id,
            account_ids={account.id},
        )
        locked_account = locked.get(account.id)
        if locked_account is None:
            raise NotFoundError(
                code="ACCOUNT_NOT_FOUND",
                message="Financial account was not found.",
            )

        for evaluation_date in _budget_evaluation_dates(expense_dates):
            await notification_service.evaluate_budgets_after_expense(
                session,
                user_id=user_id,
                as_of_date=evaluation_date,
                provider=provider,
            )

        sync_date = max(imported_dates) if imported_dates else datetime.now(UTC).date()
        await goal_service.sync_linked_goals_for_account(
            session,
            user_id=user_id,
            account_id=locked_account.id,
            as_of_date=sync_date,
            provider=provider,
        )

        job.imported_rows = imported
        job.skipped_rows = len(skipped)
        job.duplicate_rows = max(job.duplicate_rows, len(skipped))
        import_repo.mark_completed(job, status=ImportJobStatus.COMPLETED)
        await notification_service.notify_import_completed(
            session,
            user_id=user_id,
            job_id=job.id,
            imported_rows=imported,
            provider=provider,
        )
        await audit_service.record_event(
            session,
            actor_id=user_id,
            action=AuditAction.IMPORT_EXECUTED,
            entity_type=audit_service.ENTITY_IMPORT_JOB,
            entity_id=job.id,
            metadata={
                "status": ImportJobStatus.COMPLETED.value,
                "target_account_id": str(job.target_account_id),
                "imported_rows": imported,
                "skipped_rows": len(skipped),
                "total_rows": job.total_rows,
            },
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        # Re-load job after rollback to persist failure state.
        failed = await import_repo.get_import_job_for_user(
            session,
            user_id=user_id,
            job_id=job_id,
        )
        if failed is not None:
            details = dict(_payload(failed))
            error_code = str(getattr(exc, "code", "IMPORT_FAILED"))
            details["failure"] = {
                "code": error_code,
                "message": str(getattr(exc, "message", exc)),
            }
            import_repo.mark_completed(
                failed,
                status=ImportJobStatus.FAILED,
                error_details=details,
            )
            failed.imported_rows = 0
            await notification_service.notify_import_failed(
                session,
                user_id=user_id,
                job_id=job_id,
                error_code=error_code,
                provider=provider,
            )
            await session.commit()
            await session.refresh(failed)
            if isinstance(exc, (ValidationAppError, NotFoundError, ConflictError)):
                raise
            if isinstance(exc, IntegrityError):
                raise ConflictError(
                    code="IMPORT_INTEGRITY_ERROR",
                    message=(
                        "Import aborted to protect existing data "
                        "(likely a duplicate external reference)."
                    ),
                ) from exc
            raise ValidationAppError(
                code="IMPORT_FAILED",
                message="Import failed and was rolled back.",
            ) from exc
        raise

    await session.refresh(job)
    return build_import_job_response(job, preview_limit=settings.import_preview_limit)
