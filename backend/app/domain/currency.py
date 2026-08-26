"""Currency code validation."""

import re

from app.core.exceptions import ValidationAppError

_CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")


def normalize_currency(currency: str) -> str:
    """Normalize and validate an ISO 4217 currency code."""
    normalized = currency.strip().upper()
    if not _CURRENCY_CODE.fullmatch(normalized):
        raise ValidationAppError(
            code="INVALID_CURRENCY",
            message="Currency must be a three-letter ISO 4217 code.",
        )
    return normalized
