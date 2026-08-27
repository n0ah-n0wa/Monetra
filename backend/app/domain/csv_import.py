"""CSV import parsing, validation, and deterministic duplicate detection."""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.core.exceptions import ValidationAppError
from app.domain.transactions import MONEY_MAX, normalize_money, validate_positive_amount
from app.models.enums import TransactionType

REQUIRED_HEADERS = (
    "transaction_date",
    "transaction_type",
    "amount",
    "description",
    "category",
)
OPTIONAL_HEADERS = ("external_reference", "notes")
ALLOWED_HEADERS = set(REQUIRED_HEADERS) | set(OPTIONAL_HEADERS)

MAX_DESCRIPTION_LENGTH = 500
MAX_NOTES_LENGTH = 2000
MAX_EXTERNAL_REFERENCE_LENGTH = 255
MAX_CATEGORY_NAME_LENGTH = 120
MAX_FILENAME_LENGTH = 255


@dataclass(frozen=True, slots=True)
class ParsedImportRow:
    row_number: int
    transaction_date: date
    transaction_type: TransactionType
    amount: Decimal
    description: str
    category_name: str
    external_reference: str | None
    notes: str | None
    raw: dict[str, str]


@dataclass(frozen=True, slots=True)
class ImportRowError:
    row_number: int
    code: str
    message: str
    raw: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_number": self.row_number,
            "code": self.code,
            "message": self.message,
            "raw": self.raw,
        }


@dataclass(frozen=True, slots=True)
class CsvParseResult:
    rows: list[ParsedImportRow]
    errors: list[ImportRowError]
    total_rows: int


def normalize_description_for_duplicate(description: str) -> str:
    """Collapse whitespace and lowercase for deterministic fingerprinting."""
    return " ".join(description.strip().lower().split())


def duplicate_fingerprint(
    *,
    account_id: str,
    transaction_date: date,
    amount: Decimal,
    description: str,
    external_reference: str | None,
) -> str:
    """Deterministic duplicate key (SPEC §25).

    Prefer external_reference when present; otherwise use
    account + date + amount + normalized description.
    """
    if external_reference:
        return f"ext|{account_id}|{external_reference}"
    return (
        f"fp|{account_id}|{transaction_date.isoformat()}|"
        f"{normalize_money(amount)}|"
        f"{normalize_description_for_duplicate(description)}"
    )


def sanitize_upload_filename(filename: str | None) -> str:
    """Return a safe basename ending in .csv (rejects path traversal)."""
    raw = (filename or "upload.csv").replace("\x00", "").strip()
    name = Path(raw).name
    if not name or name in {".", ".."}:
        name = "upload.csv"
    if len(name) > MAX_FILENAME_LENGTH:
        stem = name[: max(1, MAX_FILENAME_LENGTH - 4)]
        name = f"{stem}.csv"
    if not name.lower().endswith(".csv"):
        raise ValidationAppError(
            code="INVALID_FILE_TYPE",
            message="Only .csv files are supported.",
        )
    return name


def _normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("\x00", "")


def validate_csv_headers(fieldnames: Sequence[str] | None) -> list[str]:
    if not fieldnames:
        raise ValidationAppError(
            code="CSV_MISSING_HEADERS",
            message="CSV file is missing a header row.",
        )
    headers = [_normalize_header(name) for name in fieldnames if name is not None]
    if any(not header for header in headers):
        raise ValidationAppError(
            code="CSV_INVALID_HEADERS",
            message="CSV header row contains an empty column name.",
        )
    if len(headers) != len(set(headers)):
        raise ValidationAppError(
            code="CSV_DUPLICATE_COLUMNS",
            message="CSV header row contains duplicate column names.",
        )
    missing = [name for name in REQUIRED_HEADERS if name not in headers]
    if missing:
        raise ValidationAppError(
            code="CSV_MISSING_COLUMNS",
            message="CSV is missing required columns.",
            details={"missing_columns": missing},
        )
    unknown = [name for name in headers if name not in ALLOWED_HEADERS]
    if unknown:
        raise ValidationAppError(
            code="CSV_UNKNOWN_COLUMNS",
            message="CSV contains unsupported columns.",
            details={"unknown_columns": unknown},
        )
    return headers


def _parse_transaction_type(raw: str) -> TransactionType:
    value = raw.strip().lower()
    try:
        return TransactionType(value)
    except ValueError as exc:
        raise ValidationAppError(
            code="INVALID_TRANSACTION_TYPE",
            message="transaction_type must be 'income' or 'expense'.",
        ) from exc


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw.strip())
    except ValueError as exc:
        raise ValidationAppError(
            code="INVALID_TRANSACTION_DATE",
            message="transaction_date must be an ISO date (YYYY-MM-DD).",
        ) from exc


def _parse_amount(raw: str) -> Decimal:
    try:
        amount = Decimal(raw.strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValidationAppError(
            code="INVALID_AMOUNT",
            message="amount must be a valid decimal number.",
        ) from exc
    if not amount.is_finite():
        raise ValidationAppError(
            code="INVALID_AMOUNT",
            message="amount must be a finite decimal number.",
        )
    normalized = validate_positive_amount(amount)
    if normalized > MONEY_MAX:
        raise ValidationAppError(
            code="INVALID_AMOUNT",
            message="amount exceeds the supported monetary range.",
        )
    return normalized


def _clean_text(value: str) -> str:
    return value.replace("\x00", "").strip()


def _parse_row(row_number: int, row: dict[str, str | None]) -> ParsedImportRow:
    raw = {key: _clean_text(value or "") for key, value in row.items() if key}
    normalized = {_normalize_header(key): value for key, value in raw.items()}

    for required in REQUIRED_HEADERS:
        if not normalized.get(required):
            raise ValidationAppError(
                code="CSV_MISSING_FIELD",
                message=f"Missing required field '{required}'.",
            )

    description = normalized["description"]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise ValidationAppError(
            code="INVALID_DESCRIPTION",
            message=f"description must be at most {MAX_DESCRIPTION_LENGTH} characters.",
        )

    category_name = normalized["category"]
    if len(category_name) > MAX_CATEGORY_NAME_LENGTH:
        raise ValidationAppError(
            code="INVALID_CATEGORY",
            message=(
                f"category must be at most {MAX_CATEGORY_NAME_LENGTH} characters."
            ),
        )

    notes_raw = normalized.get("notes") or None
    if notes_raw is not None and len(notes_raw) > MAX_NOTES_LENGTH:
        raise ValidationAppError(
            code="INVALID_NOTES",
            message=f"notes must be at most {MAX_NOTES_LENGTH} characters.",
        )

    external_raw = normalized.get("external_reference") or None
    if external_raw is not None and len(external_raw) > MAX_EXTERNAL_REFERENCE_LENGTH:
        raise ValidationAppError(
            code="INVALID_EXTERNAL_REFERENCE",
            message=(
                "external_reference must be at most "
                f"{MAX_EXTERNAL_REFERENCE_LENGTH} characters."
            ),
        )

    return ParsedImportRow(
        row_number=row_number,
        transaction_date=_parse_date(normalized["transaction_date"]),
        transaction_type=_parse_transaction_type(normalized["transaction_type"]),
        amount=_parse_amount(normalized["amount"]),
        description=description,
        category_name=category_name,
        external_reference=external_raw,
        notes=notes_raw,
        raw=raw,
    )


def parse_csv_content(content: str, *, max_rows: int) -> CsvParseResult:
    """Parse and validate CSV text into rows and per-row errors."""
    if not content or not content.strip():
        raise ValidationAppError(
            code="CSV_EMPTY",
            message="CSV file is empty.",
        )

    reader = csv.DictReader(io.StringIO(content))
    validate_csv_headers(reader.fieldnames)

    rows: list[ParsedImportRow] = []
    errors: list[ImportRowError] = []
    data_row_count = 0

    for index, row in enumerate(reader, start=2):  # header is row 1
        # Skip completely blank lines
        if row is None or all(not (value or "").strip() for value in row.values()):
            continue
        data_row_count += 1
        if data_row_count > max_rows:
            raise ValidationAppError(
                code="CSV_TOO_MANY_ROWS",
                message=f"CSV exceeds the maximum of {max_rows} data rows.",
                details={"max_rows": max_rows},
            )
        try:
            rows.append(_parse_row(index, row))
        except ValidationAppError as exc:
            errors.append(
                ImportRowError(
                    row_number=index,
                    code=exc.code,
                    message=exc.message,
                    raw={k: _clean_text(v or "") for k, v in row.items() if k},
                ),
            )

    if data_row_count == 0 and not errors:
        raise ValidationAppError(
            code="CSV_NO_DATA_ROWS",
            message="CSV contains a header but no data rows.",
        )

    return CsvParseResult(rows=rows, errors=errors, total_rows=data_row_count)


def mark_intra_file_duplicates(
    rows: list[ParsedImportRow],
    *,
    account_id: str,
) -> set[int]:
    """Return row numbers that duplicate an earlier row in the same file."""
    seen: set[str] = set()
    duplicate_rows: set[int] = set()
    for row in rows:
        key = duplicate_fingerprint(
            account_id=account_id,
            transaction_date=row.transaction_date,
            amount=row.amount,
            description=row.description,
            external_reference=row.external_reference,
        )
        if key in seen:
            duplicate_rows.add(row.row_number)
        else:
            seen.add(key)
    return duplicate_rows
