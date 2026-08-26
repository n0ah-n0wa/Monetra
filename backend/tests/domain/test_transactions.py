"""Transaction domain rule tests."""

import uuid
from decimal import Decimal

import pytest
from app.core.exceptions import ValidationAppError
from app.domain.transactions import (
    apply_balance_delta,
    category_supports_transaction_type,
    compute_update_balance_adjustments,
    signed_transaction_amount,
    validate_positive_amount,
)
from app.models.enums import CategoryType, TransactionType


def test_validate_positive_amount_rejects_zero() -> None:
    with pytest.raises(ValidationAppError) as exc:
        validate_positive_amount(Decimal("0"))
    assert exc.value.code == "INVALID_AMOUNT"


def test_signed_transaction_amount_expense_is_negative() -> None:
    assert signed_transaction_amount(
        TransactionType.EXPENSE,
        Decimal("10.5000"),
    ) == Decimal("-10.5000")


def test_signed_transaction_amount_income_is_positive() -> None:
    assert signed_transaction_amount(
        TransactionType.INCOME,
        Decimal("10.5000"),
    ) == Decimal("10.5000")


def test_apply_balance_delta_uses_exact_decimal_math() -> None:
    result = apply_balance_delta(Decimal("1000.0000"), Decimal("-0.0001"))
    assert result == Decimal("999.9999")


def test_apply_balance_delta_rejects_overflow() -> None:
    with pytest.raises(ValidationAppError) as exc:
        apply_balance_delta(Decimal("999999999999999.9999"), Decimal("0.0001"))
    assert exc.value.code == "BALANCE_OVERFLOW"


def test_category_supports_transaction_type() -> None:
    assert category_supports_transaction_type(
        CategoryType.INCOME,
        TransactionType.INCOME,
    )
    assert category_supports_transaction_type(
        CategoryType.UNIVERSAL,
        TransactionType.EXPENSE,
    )
    assert not category_supports_transaction_type(
        CategoryType.EXPENSE,
        TransactionType.INCOME,
    )


def test_compute_update_balance_adjustments_same_account() -> None:
    account_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    adjustments = compute_update_balance_adjustments(
        old_account_id=account_id,
        new_account_id=account_id,
        old_type=TransactionType.EXPENSE,
        old_amount=Decimal("100.0000"),
        new_type=TransactionType.EXPENSE,
        new_amount=Decimal("150.0000"),
    )
    assert adjustments == {account_id: Decimal("-50.0000")}


def test_compute_update_balance_adjustments_account_change() -> None:
    old_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    new_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    adjustments = compute_update_balance_adjustments(
        old_account_id=old_id,
        new_account_id=new_id,
        old_type=TransactionType.INCOME,
        old_amount=Decimal("100.0000"),
        new_type=TransactionType.EXPENSE,
        new_amount=Decimal("40.0000"),
    )
    assert adjustments == {
        old_id: Decimal("-100.0000"),
        new_id: Decimal("-40.0000"),
    }
