"""Balance invariant domain tests."""

from decimal import Decimal

from app.domain.balance import compute_balance_from_ledger


def test_compute_balance_from_ledger_applies_full_invariant() -> None:
    result = compute_balance_from_ledger(
        opening_balance=Decimal("1000.0000"),
        income_total=Decimal("500.0000"),
        expense_total=Decimal("200.0000"),
        incoming_transfer_total=Decimal("75.0000"),
        outgoing_transfer_total=Decimal("125.0000"),
    )
    assert result == Decimal("1250.0000")


def test_compute_balance_from_ledger_uses_decimal_precision() -> None:
    result = compute_balance_from_ledger(
        opening_balance=Decimal("0.0000"),
        income_total=Decimal("0.0001"),
        expense_total=Decimal("0.0000"),
        incoming_transfer_total=Decimal("0.0000"),
        outgoing_transfer_total=Decimal("0.0000"),
    )
    assert result == Decimal("0.0001")
