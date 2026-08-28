"""Password reset flow integration tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.core.security import hash_opaque_token, verify_password
from app.domain.email import normalize_email
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.notification_providers import InMemoryNotificationProvider
from app.services.password_reset_service import RESET_REQUEST_ACK_MESSAGE
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

API = "/api/v1"
VALID_PASSWORD = "SecurePass1"
NEW_PASSWORD = "NewSecure2"


def _unique_email(prefix: str = "reset") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


async def _register_user(client: AsyncClient, email: str) -> None:
    response = await client.post(
        f"{API}/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201, response.text


async def test_password_reset_request_sends_email_for_existing_user(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
) -> None:
    email = _unique_email()
    await _register_user(auth_client, email)

    response = await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    assert response.status_code == 200
    assert response.json()["message"] == RESET_REQUEST_ACK_MESSAGE

    sent = notification_provider.latest_password_reset()
    assert sent is not None
    assert sent.to_email == normalize_email(email)
    assert sent.reset_token
    assert sent.expires_at > datetime.now(UTC)


async def test_password_reset_request_same_response_for_unknown_email(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
) -> None:
    known = _unique_email("known")
    await _register_user(auth_client, known)

    existing = await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": known},
    )
    unknown = await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": _unique_email("missing")},
    )

    assert existing.status_code == 200
    assert unknown.status_code == 200
    assert existing.json() == unknown.json()
    assert existing.json()["message"] == RESET_REQUEST_ACK_MESSAGE
    assert len(notification_provider.password_resets) == 1


async def test_password_reset_request_does_not_leak_token_in_response(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
) -> None:
    email = _unique_email("leak")
    await _register_user(auth_client, email)
    response = await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    sent = notification_provider.latest_password_reset()
    assert sent is not None
    assert sent.reset_token not in response.text


async def test_password_reset_token_stored_hashed(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
    db_session: AsyncSession,
) -> None:
    email = _unique_email("hash")
    await _register_user(auth_client, email)
    await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    sent = notification_provider.latest_password_reset()
    assert sent is not None

    result = await db_session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_opaque_token(sent.reset_token),
        ),
    )
    stored = result.scalar_one()
    assert stored.token_hash == hash_opaque_token(sent.reset_token)
    assert stored.token_hash != sent.reset_token


async def test_password_reset_confirm_replaces_password(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
    db_session: AsyncSession,
) -> None:
    email = _unique_email("confirm")
    await _register_user(auth_client, email)
    await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    token = notification_provider.latest_password_reset()
    assert token is not None

    confirm = await auth_client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": token.reset_token, "new_password": NEW_PASSWORD},
    )
    assert confirm.status_code == 204

    auth_client.cookies.clear()
    old_password = await auth_client.post(
        f"{API}/auth/login",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert old_password.status_code == 401

    new_password = await auth_client.post(
        f"{API}/auth/login",
        json={"email": email, "password": NEW_PASSWORD},
    )
    assert new_password.status_code == 200

    result = await db_session.execute(
        select(User).where(User.email == normalize_email(email)),
    )
    user = result.scalar_one()
    assert verify_password(NEW_PASSWORD, user.password_hash)


async def test_password_reset_confirm_rejects_invalid_token(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": "not-a-valid-reset-token", "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_RESET_TOKEN"


async def test_password_reset_confirm_rejects_expired_token(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
    db_engine: AsyncEngine,
) -> None:
    email = _unique_email("expired")
    await _register_user(auth_client, email)
    await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    sent = notification_provider.latest_password_reset()
    assert sent is not None

    async with db_engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE password_reset_tokens "
                "SET expires_at = :expired WHERE token_hash = :token_hash",
            ),
            {
                "expired": datetime.now(UTC) - timedelta(minutes=5),
                "token_hash": hash_opaque_token(sent.reset_token),
            },
        )

    response = await auth_client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": sent.reset_token, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_RESET_TOKEN"


async def test_password_reset_confirm_rejects_reused_token(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
) -> None:
    email = _unique_email("replay")
    await _register_user(auth_client, email)
    await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    sent = notification_provider.latest_password_reset()
    assert sent is not None

    first = await auth_client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": sent.reset_token, "new_password": NEW_PASSWORD},
    )
    assert first.status_code == 204

    replay = await auth_client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": sent.reset_token, "new_password": "AnotherPass3"},
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "INVALID_RESET_TOKEN"


async def test_password_reset_confirm_rejects_weak_password(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
) -> None:
    email = _unique_email("weak")
    await _register_user(auth_client, email)
    await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    sent = notification_provider.latest_password_reset()
    assert sent is not None

    response = await auth_client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": sent.reset_token, "new_password": "short"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "WEAK_PASSWORD"


async def test_password_reset_rapid_requests_preserve_active_token(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
) -> None:
    """Reset requests within the cooldown must not invalidate the prior token."""
    email = _unique_email("cooldown")
    await _register_user(auth_client, email)
    await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    first = notification_provider.latest_password_reset()
    assert first is not None

    await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    assert notification_provider.latest_password_reset() is first

    still_valid = await auth_client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": first.reset_token, "new_password": NEW_PASSWORD},
    )
    assert still_valid.status_code == 204


async def test_password_reset_new_request_after_cooldown_supersedes_token(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
    db_engine: AsyncEngine,
) -> None:
    email = _unique_email("supersede")
    await _register_user(auth_client, email)
    await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    first = notification_provider.latest_password_reset()
    assert first is not None

    async with db_engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE password_reset_tokens "
                "SET created_at = :created_at WHERE token_hash = :token_hash",
            ),
            {
                "created_at": datetime.now(UTC) - timedelta(minutes=10),
                "token_hash": hash_opaque_token(first.reset_token),
            },
        )

    await auth_client.post(
        f"{API}/auth/password-reset/request",
        json={"email": email},
    )
    second = notification_provider.latest_password_reset()
    assert second is not None
    assert second.reset_token != first.reset_token

    superseded = await auth_client.post(
        f"{API}/auth/password-reset/confirm",
        json={"token": first.reset_token, "new_password": NEW_PASSWORD},
    )
    assert superseded.status_code == 401


async def test_password_reset_revokes_existing_refresh_sessions(
    auth_client: AsyncClient,
    notification_provider: InMemoryNotificationProvider,
) -> None:
    email = _unique_email("sessions")
    await _register_user(auth_client, email)
    assert auth_client.cookies.get("monetra_refresh_token")

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

    refresh = await auth_client.post(f"{API}/auth/refresh")
    assert refresh.status_code == 401


async def test_password_reset_request_is_rate_limited(
    rate_limited_auth_client: AsyncClient,
) -> None:
    payload = {"email": "nobody@example.com"}
    for _ in range(2):
        response = await rate_limited_auth_client.post(
            f"{API}/auth/password-reset/request",
            json=payload,
        )
        assert response.status_code == 200

    blocked = await rate_limited_auth_client.post(
        f"{API}/auth/password-reset/request",
        json=payload,
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
