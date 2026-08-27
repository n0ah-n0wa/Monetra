"""CSV export formatting for transactions."""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.transactions import normalize_money

EXPORT_HEADERS = (
    "transaction_date",
    "transaction_type",
    "amount",
    "currency",
    "description",
    "category",
    "account",
)

# OWASP CSV injection prefixes (Excel / LibreOffice formula execution).
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


@dataclass(frozen=True, slots=True)
class ExportTransactionRow:
    transaction_date: date
    transaction_type: str
    amount: Decimal
    currency: str
    description: str
    category: str
    account: str


def format_export_amount(amount: Decimal) -> str:
    """Format ledger amounts without scientific notation."""
    return format(normalize_money(amount), "f")


def neutralize_csv_formula(value: str) -> str:
    """Prefix formula-like cells so spreadsheets treat them as text."""
    if value and value[0] in _CSV_FORMULA_PREFIXES:
        return f"'{value}"
    return value


def render_transactions_csv(rows: Sequence[ExportTransactionRow]) -> str:
    """Render export rows as UTF-8 CSV with RFC-style escaping."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(EXPORT_HEADERS)
    for row in rows:
        writer.writerow(
            [
                row.transaction_date.isoformat(),
                row.transaction_type,
                format_export_amount(row.amount),
                row.currency,
                neutralize_csv_formula(row.description),
                neutralize_csv_formula(row.category),
                neutralize_csv_formula(row.account),
            ],
        )
    return buffer.getvalue()
