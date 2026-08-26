"""Password policy validation."""

import re

from app.core.config import Settings
from app.core.exceptions import ValidationAppError

_PASSWORD_HAS_LETTER = re.compile(r"[A-Za-z]")
_PASSWORD_HAS_DIGIT = re.compile(r"\d")


def validate_password(password: str, settings: Settings) -> None:
    """Raise ValidationAppError when the password does not meet policy."""
    errors: list[str] = []
    if len(password) < settings.auth_password_min_length:
        errors.append(
            "Password must be at least "
            f"{settings.auth_password_min_length} characters.",
        )
    if settings.auth_password_require_letter and not _PASSWORD_HAS_LETTER.search(
        password,
    ):
        errors.append("Password must contain at least one letter.")
    if settings.auth_password_require_digit and not _PASSWORD_HAS_DIGIT.search(
        password,
    ):
        errors.append("Password must contain at least one digit.")
    if errors:
        raise ValidationAppError(
            code="WEAK_PASSWORD",
            message="Password does not meet security requirements.",
            details={"errors": errors},
        )
