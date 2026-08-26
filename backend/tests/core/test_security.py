"""Security utility tests."""

from datetime import timedelta

import pytest
from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    hashed = hash_password("correct-horse-battery")
    assert hashed != "correct-horse-battery"
    assert verify_password("correct-horse-battery", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip(app_settings: Settings) -> None:
    token = create_access_token("user-123", settings=app_settings)
    payload = decode_token(token, settings=app_settings)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_expired_token_raises(app_settings: Settings) -> None:
    token = create_access_token(
        "user-123",
        settings=app_settings,
        expires_delta=timedelta(seconds=-1),
    )
    with pytest.raises(UnauthorizedError) as exc_info:
        decode_token(token, settings=app_settings)
    assert exc_info.value.code == "INVALID_TOKEN"


def test_tampered_token_raises(app_settings: Settings) -> None:
    token = create_access_token("user-123", settings=app_settings)
    with pytest.raises(UnauthorizedError):
        decode_token(token + "x", settings=app_settings)


def test_decode_access_token_rejects_non_access_type(app_settings: Settings) -> None:
    token = create_access_token(
        "user-123",
        settings=app_settings,
        extra_claims={"type": "refresh"},
    )
    with pytest.raises(UnauthorizedError) as exc_info:
        decode_access_token(token, settings=app_settings)
    assert exc_info.value.code == "INVALID_TOKEN"


def test_assert_access_token_active_for_user_accepts_current_token(
    app_settings: Settings,
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.core.security import assert_access_token_active_for_user

    token = create_access_token("user-123", settings=app_settings)
    payload = decode_access_token(token, settings=app_settings)
    assert_access_token_active_for_user(
        payload,
        password_changed_at=datetime.now(UTC) - timedelta(minutes=1),
    )


def test_refresh_token_hash_is_stable() -> None:
    digest = hash_refresh_token("sample-token")
    assert digest == hash_refresh_token("sample-token")
    assert len(digest) == 64


def test_opaque_token_hash_is_stable() -> None:
    from app.core.security import hash_opaque_token

    digest = hash_opaque_token("sample-token")
    assert digest == hash_opaque_token("sample-token")
    assert len(digest) == 64
