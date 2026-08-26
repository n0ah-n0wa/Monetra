"""Email normalization helpers."""


def normalize_email(email: str) -> str:
    """Normalize an email address for storage and lookup."""
    return email.strip().casefold()
