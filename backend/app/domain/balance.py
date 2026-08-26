"""Account balance computation from authoritative ledger records."""

from __future__ import annotations

from decimal import Decimal

from app.domain.transactions import normalize_money


def compute_balance_from_ledger(
    *,
    opening_balance: Decimal,
    income_total: Decimal,
    expense_total: Decimal,
    incoming_transfer_total: Decimal,
    outgoing_transfer_total: Decimal,
) -> Decimal:
    """Compute expected cached balance from ledger aggregates.

    Invariant (SPEC §82):

        current_balance = opening_balance + income - expenses
                          + incoming_transfers - outgoing_transfers
    """
    return normalize_money(
        opening_balance
        + income_total
        - expense_total
        + incoming_transfer_total
        - outgoing_transfer_total,
    )


def balances_match(cached_balance: Decimal, expected_balance: Decimal) -> bool:
    return normalize_money(cached_balance) == normalize_money(expected_balance)
