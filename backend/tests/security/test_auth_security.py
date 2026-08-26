"""Authentication and session security tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import Settings
from app.core.csrf import validate_cookie_auth_origin
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import (
    assert_access_token_active_for_user,
    create_access_token,
    decode_access_token,
)
from app.services.notification_providers import InMemoryNotificationProvider
from httpx import AsyncClient

API = "/api/v1"
VALID_PASSWORD = "SecurePass1"
NEW_PASSWORD = "NewSecure2"


def _unique_email(prefix: str = "sec") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


async def _register(client: AsyncClient, email: str | None = None) -> tuple[str, str]:
    address = email or _unique_email()
    response = await client.post(
        f"{API}/auth/register",
        json={"email": address, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return address, response.json()["access_token"]


async def test_invalid_bearer_token_rejected(auth_client: AsyncClient) -> None:
    response = await auth_client.get(
        f"{API}/users/me",
        headers={"Authorization": "Bearer invalid-token-value"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_expired_access_token_rejected(
    auth_client: AsyncClient,
    app_settings: Settings,
) -> None:
    _, access_token = await _register(auth_client)
    profile = await auth_client.get(
        f"{API}/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_id = profile.json()["id"]
    expired = create_access_token(
        user_id,
        settings=app_settings,
        expires_delta=timedelta(seconds=-30),
    )
    response = await auth_client.get(
        f"{API}/users/me",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_refresh_token_reuse_revokes_family(auth_client: AsyncClient) -> None:
    await _register(auth_client)
    first_cookie = auth_client.cookies.get("monetra_refresh_token")
    assert first_cookie

    rotated = await auth_client.post(f"{API}/auth/refresh")
    assert rotated.status_code == 200
    second_cookie = auth_client.cookies.get("monetra_refresh_token")
    assert second_cookie

    auth_client.cookies.set("monetra_refresh_token", first_cookie)
    reuse = await auth_client.post(f"{API}/auth/refresh")
    assert reuse.status_code == 401

    auth_client.cookies.set("monetra_refresh_token", second_cookie)
    sibling = await auth_client.post(f"{API}/auth/refresh")
    assert sibling.status_code == 401


async def test_password_reset_invalidates_existing_access_token(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
) -> None:
    email, access_token = await _register(auth_client)
    await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    sent = notification_provider.latest_password_reset()
    assert sent is not None

    confirm = await auth_client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": sent.reset_token, "new_password": NEW_PASSWORD},
    )
    assert confirm.status_code == 204

    stale = await auth_client.get(
        f"{API}/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "INVALID_TOKEN"


async def test_refresh_rejects_untrusted_origin(auth_client: AsyncClient) -> None:
    await _register(auth_client)
    response = await auth_client.post(
        f"{API}/auth/refresh",
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_logout_rejects_untrusted_origin(auth_client: AsyncClient) -> None:
    await _register(auth_client)
    response = await auth_client.post(
        f"{API}/auth/logout",
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403


async def test_refresh_cookie_not_returned_in_response_body(
    auth_client: AsyncClient,
) -> None:
    await _register(auth_client)
    response = await auth_client.post(f"{API}/auth/refresh")
    assert response.status_code == 200
    body = response.json()
    assert "refresh_token" not in body
    assert set(body.keys()) == {"access_token", "token_type", "expires_in"}


def test_assert_access_token_active_for_user_rejects_stale_token(
    app_settings: Settings,
) -> None:
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, settings=app_settings)
    payload = decode_access_token(token, settings=app_settings)

    with pytest.raises(UnauthorizedError) as exc_info:
        assert_access_token_active_for_user(
            payload,
            password_changed_at=datetime.now(UTC) + timedelta(seconds=2),
        )
    assert exc_info.value.code == "INVALID_TOKEN"


def test_production_cookie_settings_force_secure_flag() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret_key="production-secret-key-with-enough-length",
        debug=False,
        cors_origins=["https://app.example.com"],
    )
    assert settings.refresh_token_cookie_secure is True


def test_csrf_allows_trusted_origin(app_settings: Settings) -> None:
    class _Request:
        def __init__(self, origin: str) -> None:
            self.headers = {"origin": origin}

    validate_cookie_auth_origin(_Request(app_settings.cors_origins[0]), app_settings)


def test_csrf_rejects_untrusted_origin(app_settings: Settings) -> None:
    class _Request:
        def __init__(self) -> None:
            self.headers = {"origin": "https://attacker.example"}

    with pytest.raises(ForbiddenError):
        validate_cookie_auth_origin(_Request(), app_settings)
