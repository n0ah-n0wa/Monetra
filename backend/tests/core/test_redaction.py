"""Sensitive data redaction tests."""

from app.core.redaction import (
    REDACTED,
    is_sensitive_key,
    redact_headers,
    redact_mapping,
    redact_string,
)


def test_is_sensitive_key_detects_common_secret_fields() -> None:
    assert is_sensitive_key("password")
    assert is_sensitive_key("access_token")
    assert is_sensitive_key("Authorization")
    assert not is_sensitive_key("account_id")


def test_redact_mapping_redacts_nested_sensitive_keys() -> None:
    payload = {
        "email": "user@example.com",
        "password": "secret-value",
        "profile": {"refresh_token": "abc123"},
    }
    redacted = redact_mapping(payload)
    assert redacted["email"] == "user@example.com"
    assert redacted["password"] == REDACTED
    assert redacted["profile"]["refresh_token"] == REDACTED


def test_redact_string_masks_bearer_tokens_and_database_urls() -> None:
    assert redact_string("Bearer eyJhbGciOiJIUzI1NiJ9") == "Bearer [REDACTED]"
    assert (
        redact_string("postgresql+psycopg://user:pass@localhost:5432/db")
        == "postgresql+psycopg://[REDACTED]@localhost:5432/db"
    )


def test_redact_headers_masks_authorization_and_cookies() -> None:
    headers = {
        "Authorization": "Bearer secret",
        "Cookie": "session=abc",
        "Accept": "application/json",
    }
    redacted = redact_headers(headers)
    assert redacted["Authorization"] == REDACTED
    assert redacted["Cookie"] == REDACTED
    assert redacted["Accept"] == "application/json"
