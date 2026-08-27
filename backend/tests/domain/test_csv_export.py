"""Unit tests for CSV export rendering and escaping."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.csv_export import (
    EXPORT_HEADERS,
    ExportTransactionRow,
    format_export_amount,
    render_transactions_csv,
)


def test_empty_export_has_header_only() -> None:
    csv = render_transactions_csv([])
    assert csv == ",".join(EXPORT_HEADERS) + "\n"


def test_format_export_amount_preserves_scale() -> None:
    assert format_export_amount(Decimal("12.5")) == "12.5000"
    assert format_export_amount(Decimal("1000.0000")) == "1000.0000"


def test_csv_escaping_for_special_characters() -> None:
    rows = [
        ExportTransactionRow(
            transaction_date=date(2026, 1, 15),
            transaction_type="expense",
            amount=Decimal("9.9900"),
            currency="USD",
            description='Coffee, "latte"\nextra',
            category="Groceries",
            account="Checking, Main",
        ),
    ]
    csv = render_transactions_csv(rows)
    lines = csv.strip().split("\n")
    assert lines[0] == ",".join(EXPORT_HEADERS)
    # Fields with commas/quotes/newlines must be quoted; quotes doubled.
    assert '"Coffee, ""latte""\nextra"' in csv or '"Coffee, ""latte""' in csv
    assert '"Checking, Main"' in csv
    assert "9.9900" in csv
    assert "expense" in csv


def test_csv_formula_injection_neutralized() -> None:
    from app.domain.csv_export import neutralize_csv_formula

    assert neutralize_csv_formula("=1+1") == "'=1+1"
    assert neutralize_csv_formula("+cmd") == "'+cmd"
    assert neutralize_csv_formula("-2+3") == "'-2+3"
    assert neutralize_csv_formula("@SUM(A1)") == "'@SUM(A1)"
    assert neutralize_csv_formula("normal") == "normal"

    rows = [
        ExportTransactionRow(
            transaction_date=date(2026, 1, 15),
            transaction_type="expense",
            amount=Decimal("1.0000"),
            currency="USD",
            description='=HYPERLINK("http://evil")',
            category="+Danger",
            account="@Account",
        ),
    ]
    rendered = render_transactions_csv(rows)
    assert "'=HYPERLINK" in rendered
    assert "'+Danger" in rendered
    assert "'@Account" in rendered
