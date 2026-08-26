"""Transaction and account balance domain rules."""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.core.exceptions import ValidationAppError
from app.models.enums import CategoryType, TransactionType

MONEY_QUANTIZE = Decimal("0.0001")
MONEY_MAX = Decimal("999999999999999.9999")
MONEY_MIN = Decimal("-999999999999999.9999")


def normalize_money(amount: Decimal) -> Decimal:
    """Normalize a monetary amount to the ledger scale."""
    return amount.quantize(MONEY_QUANTIZE)


def validate_positive_amount(amount: Decimal) -> Decimal:
    normalized = normalize_money(amount)
    if normalized <= Decimal("0"):
        raise ValidationAppError(
            code="INVALID_AMOUNT",
            message="Transaction amount must be greater than zero.",
        )
    return normalized


def signed_transaction_amount(
    transaction_type: TransactionType,
    amount: Decimal,
) -> Decimal:
    """Return the signed ledger delta for a transaction amount."""
    positive = validate_positive_amount(amount)
    if transaction_type == TransactionType.INCOME:
        return positive
    return -positive


def apply_balance_delta(current_balance: Decimal, delta: Decimal) -> Decimal:
    """Apply a signed delta to an account balance using exact decimal math."""
    result = normalize_money(current_balance + delta)
    if result > MONEY_MAX or result < MONEY_MIN:
        raise ValidationAppError(
            code="BALANCE_OVERFLOW",
            message="The resulting account balance is outside the supported range.",
        )
    return result


def category_supports_transaction_type(
    category_type: CategoryType,
    transaction_type: TransactionType,
) -> bool:
    if category_type == CategoryType.UNIVERSAL:
        return True
    if transaction_type == TransactionType.INCOME:
        return category_type == CategoryType.INCOME
    return category_type == CategoryType.EXPENSE


def compute_update_balance_adjustments(
    *,
    old_account_id: uuid.UUID,
    new_account_id: uuid.UUID,
    old_type: TransactionType,
    old_amount: Decimal,
    new_type: TransactionType,
    new_amount: Decimal,
) -> dict[uuid.UUID, Decimal]:
    """Return per-account balance deltas when a transaction is updated."""
    old_signed = signed_transaction_amount(old_type, old_amount)
    new_signed = signed_transaction_amount(new_type, new_amount)

    if old_account_id == new_account_id:
        delta = new_signed - old_signed
        if delta == Decimal("0"):
            return {}
        return {old_account_id: delta}

    return {
        old_account_id: -old_signed,
        new_account_id: new_signed,
    }
