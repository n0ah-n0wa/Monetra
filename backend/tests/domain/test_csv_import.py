"""Unit tests for CSV import domain parsing and duplicate detection."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from app.core.exceptions import ValidationAppError
from app.domain.csv_import import (
    duplicate_fingerprint,
    mark_intra_file_duplicates,
    parse_csv_content,
)
from app.models.enums import TransactionType


def _csv(*rows: str) -> str:
    header = (
        "transaction_date,transaction_type,amount,description,category,"
        "external_reference,notes"
    )
    return "\n".join([header, *rows])


def test_parse_valid_rows() -> None:
    content = _csv(
        "2026-01-15,expense,12.50,Coffee,Groceries,ref-1,morning",
        "2026-01-16,income,1000.00,Paycheck,Salary,,",
    )
    result = parse_csv_content(content, max_rows=100)
    assert result.total_rows == 2
    assert len(result.rows) == 2
    assert result.errors == []
    assert result.rows[0].transaction_type == TransactionType.EXPENSE
    assert result.rows[0].amount == Decimal("12.5000")
    assert result.rows[1].external_reference is None


def test_parse_malformed_and_invalid_rows() -> None:
    content = _csv(
        "2026-01-15,expense,12.50,Coffee,Groceries,,",
        "not-a-date,expense,12.50,Bad date,Groceries,,",
        "2026-01-17,transfer,10.00,Bad type,Groceries,,",
        "2026-01-18,expense,-5.00,Negative,Groceries,,",
        "2026-01-19,expense,abc,Bad amount,Groceries,,",
        ",expense,1.00,Missing date,Groceries,,",
    )
    result = parse_csv_content(content, max_rows=100)
    assert result.total_rows == 6
    assert len(result.rows) == 1
    codes = {error.code for error in result.errors}
    assert "INVALID_TRANSACTION_DATE" in codes
    assert "INVALID_TRANSACTION_TYPE" in codes
    assert "INVALID_AMOUNT" in codes or any(
        "amount" in error.message.lower() for error in result.errors
    )
    assert "CSV_MISSING_FIELD" in codes


def test_missing_required_columns() -> None:
    content = "transaction_date,amount\n2026-01-01,10.00\n"
    with pytest.raises(ValidationAppError) as exc:
        parse_csv_content(content, max_rows=100)
    assert exc.value.code == "CSV_MISSING_COLUMNS"


def test_unknown_columns_rejected() -> None:
    content = (
        "transaction_date,transaction_type,amount,description,category,foo\n"
        "2026-01-01,expense,1.00,x,Groceries,y\n"
    )
    with pytest.raises(ValidationAppError) as exc:
        parse_csv_content(content, max_rows=100)
    assert exc.value.code == "CSV_UNKNOWN_COLUMNS"


def test_empty_and_header_only() -> None:
    with pytest.raises(ValidationAppError) as exc:
        parse_csv_content("   ", max_rows=100)
    assert exc.value.code == "CSV_EMPTY"

    header_only = "transaction_date,transaction_type,amount,description,category\n"
    with pytest.raises(ValidationAppError) as exc2:
        parse_csv_content(header_only, max_rows=100)
    assert exc2.value.code == "CSV_NO_DATA_ROWS"


def test_too_many_rows() -> None:
    rows = [
        f"2026-01-{(i % 28) + 1:02d},expense,1.00,Row {i},Groceries,," for i in range(5)
    ]
    with pytest.raises(ValidationAppError) as exc:
        parse_csv_content(_csv(*rows), max_rows=3)
    assert exc.value.code == "CSV_TOO_MANY_ROWS"


def test_duplicate_fingerprint_prefers_external_reference() -> None:
    with_ref = duplicate_fingerprint(
        account_id="acct",
        transaction_date=date(2026, 1, 1),
        amount=Decimal("10.0000"),
        description="Coffee",
        external_reference="bank-1",
    )
    without_ref = duplicate_fingerprint(
        account_id="acct",
        transaction_date=date(2026, 1, 1),
        amount=Decimal("10.0000"),
        description="Coffee",
        external_reference=None,
    )
    assert with_ref.startswith("ext|")
    assert without_ref.startswith("fp|")
    assert with_ref != without_ref


def test_intra_file_duplicates() -> None:
    content = _csv(
        "2026-01-15,expense,12.50,Coffee,Groceries,ref-1,",
        "2026-01-15,expense,12.50,Coffee,Groceries,ref-1,",
        "2026-01-16,expense,5.00,Tea,Groceries,,",
        "2026-01-16,expense,5.00,  TEA  ,Groceries,,",
    )
    result = parse_csv_content(content, max_rows=100)
    duplicates = mark_intra_file_duplicates(result.rows, account_id="acct-1")
    assert duplicates == {3, 5}


def test_duplicate_headers_rejected() -> None:
    content = (
        "transaction_date,transaction_type,amount,description,category,category\n"
        "2026-01-01,expense,1.00,x,Groceries,Groceries\n"
    )
    with pytest.raises(ValidationAppError) as exc:
        parse_csv_content(content, max_rows=100)
    assert exc.value.code == "CSV_DUPLICATE_COLUMNS"


def test_amount_overflow_and_non_finite_rejected() -> None:
    overflow = _csv("2026-01-01,expense,1000000000000000.0000,Too big,Groceries,,")
    result = parse_csv_content(overflow, max_rows=100)
    assert result.rows == []
    assert result.errors[0].code == "INVALID_AMOUNT"

    nan_csv = _csv("2026-01-01,expense,NaN,Bad,Groceries,,")
    nan_result = parse_csv_content(nan_csv, max_rows=100)
    assert nan_result.errors[0].code == "INVALID_AMOUNT"


def test_null_bytes_stripped_from_fields() -> None:
    content = _csv("2026-01-01,expense,1.00,Cof\x00fee,Groceries,,")
    result = parse_csv_content(content, max_rows=100)
    assert len(result.rows) == 1
    assert result.rows[0].description == "Coffee"


def test_sanitize_upload_filename_rejects_non_csv() -> None:
    from app.domain.csv_import import sanitize_upload_filename

    assert sanitize_upload_filename("../../secret.csv") == "secret.csv"
    with pytest.raises(ValidationAppError) as exc:
        sanitize_upload_filename("../../secret.txt")
    assert exc.value.code == "INVALID_FILE_TYPE"


def test_normalize_description_collapses_whitespace() -> None:
    from app.domain.csv_import import normalize_description_for_duplicate

    assert normalize_description_for_duplicate("  Coffee   Shop ") == "coffee shop"
