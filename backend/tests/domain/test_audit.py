"""Domain tests for audit metadata sanitization."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.audit import is_sensitive_audit_key, sanitize_audit_metadata


def test_sensitive_keys_detected() -> None:
    assert is_sensitive_audit_key("password")
    assert is_sensitive_audit_key("refresh_token")
    assert is_sensitive_audit_key("Authorization")
    assert is_sensitive_audit_key("api-key")
    assert not is_sensitive_audit_key("amount")
    assert not is_sensitive_audit_key("account_id")


def test_sanitize_strips_secrets_and_serializes() -> None:
    entity_id = uuid4()
    cleaned = sanitize_audit_metadata(
        {
            "amount": Decimal("12.5000"),
            "transaction_date": date(2026, 1, 15),
            "entity_id": entity_id,
            "password": "super-secret",
            "access_token": "tok",
            "nested": {"refresh_token": "r", "currency": "USD"},
        },
    )
    assert cleaned is not None
    assert cleaned["amount"] == "12.5000"
    assert cleaned["transaction_date"] == "2026-01-15"
    assert cleaned["entity_id"] == str(entity_id)
    assert "password" not in cleaned
    assert "access_token" not in cleaned
    assert cleaned["nested"] == {"currency": "USD"}
