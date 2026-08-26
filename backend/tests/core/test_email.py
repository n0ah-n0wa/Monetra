"""Email normalization tests."""

from app.domain.email import normalize_email


def test_normalize_email_strips_and_casefolds() -> None:
    assert normalize_email("  User@Example.COM  ") == "user@example.com"


def test_normalize_email_preserves_plus_addressing() -> None:
    assert normalize_email("Name+Tag@Example.com") == "name+tag@example.com"
