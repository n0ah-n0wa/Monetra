"""Transfer amount and exchange-rate domain rules."""

from __future__ import annotations

from decimal import Decimal

from app.core.exceptions import ValidationAppError
from app.domain.transactions import normalize_money, validate_positive_amount

EXCHANGE_RATE_QUANTIZE = Decimal("0.00000001")


def normalize_exchange_rate(rate: Decimal) -> Decimal:
    """Normalize an exchange rate to the stored precision."""
    return rate.quantize(EXCHANGE_RATE_QUANTIZE)


def validate_exchange_rate(rate: Decimal) -> Decimal:
    normalized = normalize_exchange_rate(rate)
    if normalized <= Decimal("0"):
        raise ValidationAppError(
            code="INVALID_EXCHANGE_RATE",
            message="Exchange rate must be greater than zero.",
        )
    return normalized


def compute_destination_amount(
    source_amount: Decimal,
    exchange_rate: Decimal,
) -> Decimal:
    """Compute destination amount: source_amount * exchange_rate."""
    return normalize_money(source_amount * exchange_rate)


def resolve_transfer_amounts(
    *,
    source_currency: str,
    destination_currency: str,
    source_amount: Decimal,
    destination_amount: Decimal | None,
    exchange_rate: Decimal | None,
) -> tuple[Decimal, Decimal, Decimal | None]:
    """Resolve validated source/destination amounts and optional exchange rate."""
    normalized_source = validate_positive_amount(source_amount)

    if source_currency == destination_currency:
        if exchange_rate is not None:
            raise ValidationAppError(
                code="INVALID_EXCHANGE_RATE",
                message=(
                    "Exchange rate must not be provided for same-currency transfers."
                ),
            )
        if (
            destination_amount is not None
            and normalize_money(destination_amount) != normalized_source
        ):
            raise ValidationAppError(
                code="TRANSFER_AMOUNT_MISMATCH",
                message=(
                    "Destination amount must equal source amount "
                    "for same-currency transfers."
                ),
            )
        return normalized_source, normalized_source, None

    if exchange_rate is None and destination_amount is None:
        raise ValidationAppError(
            code="VALIDATION_ERROR",
            message=(
                "Cross-currency transfers require an exchange rate "
                "or destination amount."
            ),
        )

    if exchange_rate is not None:
        rate = validate_exchange_rate(exchange_rate)
        computed_destination = compute_destination_amount(normalized_source, rate)
        if destination_amount is not None:
            provided_destination = normalize_money(destination_amount)
            if provided_destination != computed_destination:
                raise ValidationAppError(
                    code="TRANSFER_AMOUNT_MISMATCH",
                    message=(
                        "Destination amount does not match the supplied exchange rate."
                    ),
                )
        return normalized_source, computed_destination, rate

    assert destination_amount is not None
    normalized_destination = validate_positive_amount(destination_amount)
    rate = validate_exchange_rate(
        normalize_exchange_rate(normalized_destination / normalized_source),
    )
    if compute_destination_amount(normalized_source, rate) != normalized_destination:
        raise ValidationAppError(
            code="TRANSFER_AMOUNT_MISMATCH",
            message=(
                "Destination amount is incompatible with the derived exchange rate."
            ),
        )
    return normalized_source, normalized_destination, rate


def assert_sufficient_balance(current_balance: Decimal, source_amount: Decimal) -> None:
    if current_balance < source_amount:
        raise ValidationAppError(
            code="INSUFFICIENT_BALANCE",
            message="Source account has insufficient available balance.",
        )
