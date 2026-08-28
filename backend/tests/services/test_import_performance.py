"""Performance-oriented import service tests."""

from __future__ import annotations

from datetime import date

from app.services.import_service import _budget_evaluation_dates


def test_budget_evaluation_dates_collapses_to_month_ends() -> None:
    expense_dates = {
        date(2026, 1, 5),
        date(2026, 1, 28),
        date(2026, 2, 3),
    }
    assert _budget_evaluation_dates(expense_dates) == [
        date(2026, 1, 31),
        date(2026, 2, 28),
    ]


def test_budget_evaluation_dates_empty_set() -> None:
    assert _budget_evaluation_dates(set()) == []
