"""Authentication endpoint integration tests."""

from __future__ import annotations

import uuid
from datetime import timedelta

from app.core.config import Settings
from app.core.security import create_access_token
from app.domain.email import normalize_email
from app.models.category import Category
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

API = "/api/v1"
VALID_PASSWORD = "SecurePass1"


def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


async def _register(
    client: AsyncClient,
    *,
    email: str | None = None,
    password: str = VALID_PASSWORD,
) -> tuple[str, str]:
    address = email or _unique_email()
    response = await client.post(
        f"{API}/auth/register",
        json={"email": address, "password": password},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return address, body["access_token"]


async def test_register_success(auth_client: AsyncClient) -> None:
    email = _unique_email()
    response = await auth_client.post(
        f"{API}/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]
    assert body["expires_in"] > 0
    assert auth_client.cookies.get("monetra_refresh_token")


async def test_register_normalizes_email(auth_client: AsyncClient) -> None:
    local = uuid.uuid4().hex[:12]
    mixed = f"Mixed.Case+Tag@{local}.Example.COM"
    response = await auth_client.post(
        f"{API}/auth/register",
        json={"email": mixed, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201

    login = await auth_client.post(
        f"{API}/auth/login",
        json={"email": normalize_email(mixed), "password": VALID_PASSWORD},
    )
    assert login.status_code == 200


async def test_register_duplicate_email(auth_client: AsyncClient) -> None:
    email = _unique_email("dup")
    first = await auth_client.post(
        f"{API}/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert first.status_code == 201

    second = await auth_client.post(
        f"{API}/auth/register",
        json={"email": email.upper(), "password": VALID_PASSWORD},
    )
    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_register_weak_password(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        f"{API}/auth/register",
        json={"email": _unique_email(), "password": "short"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "WEAK_PASSWORD"


async def test_password_stored_as_argon2_hash(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    email = _unique_email("hash")
    response = await auth_client.post(
        f"{API}/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201

    result = await db_session.execute(
        select(User).where(User.email == normalize_email(email)),
    )
    user = result.scalar_one()
    assert user.password_hash.startswith("$argon2")
    assert user.password_hash != VALID_PASSWORD


async def test_register_seeds_default_categories(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    email = _unique_email("cats")
    await auth_client.post(
        f"{API}/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    result = await db_session.execute(
        select(User).where(User.email == normalize_email(email)),
    )
    user = result.scalar_one()
    categories = await db_session.execute(
        select(Category).where(Category.user_id == user.id),
    )
    rows = categories.scalars().all()
    assert len(rows) >= 10


async def test_login_success(auth_client: AsyncClient) -> None:
    email, _ = await _register(auth_client)
    auth_client.cookies.clear()
    response = await auth_client.post(
        f"{API}/auth/login",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert auth_client.cookies.get("monetra_refresh_token")


async def test_login_invalid_credentials(auth_client: AsyncClient) -> None:
    email, _ = await _register(auth_client)
    auth_client.cookies.clear()

    wrong_password = await auth_client.post(
        f"{API}/auth/login",
        json={"email": email, "password": "WrongPass9"},
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"

    unknown_user = await auth_client.post(
        f"{API}/auth/login",
        json={"email": _unique_email("missing"), "password": VALID_PASSWORD},
    )
    assert unknown_user.status_code == 401
    assert unknown_user.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_me_requires_authentication(auth_client: AsyncClient) -> None:
    response = await auth_client.get(f"{API}/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_me_returns_current_user(auth_client: AsyncClient) -> None:
    email, access_token = await _register(auth_client)
    response = await auth_client.get(
        f"{API}/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == normalize_email(email)
    assert body["reporting_currency"] == "USD"
    assert body["id"]


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


async def test_invalid_access_token_rejected(auth_client: AsyncClient) -> None:
    response = await auth_client.get(
        f"{API}/users/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_refresh_rotates_cookie(auth_client: AsyncClient) -> None:
    await _register(auth_client)
    old_cookie = auth_client.cookies.get("monetra_refresh_token")
    assert old_cookie

    refresh = await auth_client.post(f"{API}/auth/refresh")
    assert refresh.status_code == 200
    new_cookie = auth_client.cookies.get("monetra_refresh_token")
    assert new_cookie
    assert new_cookie != old_cookie

    auth_client.cookies.set("monetra_refresh_token", old_cookie)
    reuse = await auth_client.post(f"{API}/auth/refresh")
    assert reuse.status_code == 401


async def test_refresh_reuse_revokes_token_family(auth_client: AsyncClient) -> None:
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


async def test_invalid_refresh_token(auth_client: AsyncClient) -> None:
    auth_client.cookies.set("monetra_refresh_token", "invalid-refresh-token")
    response = await auth_client.post(f"{API}/auth/refresh")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


async def test_logout_revokes_refresh_token(auth_client: AsyncClient) -> None:
    await _register(auth_client)
    logout = await auth_client.post(f"{API}/auth/logout")
    assert logout.status_code == 204

    refresh = await auth_client.post(f"{API}/auth/refresh")
    assert refresh.status_code == 401


async def test_refresh_cookie_security_attributes(
    auth_client: AsyncClient,
    app_settings: Settings,
) -> None:
    email = _unique_email("cookie")
    response = await auth_client.post(
        f"{API}/auth/register",
        json={"email": email, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201
    header = response.headers.get("set-cookie", "").lower()
    assert "httponly" in header
    assert f"path={app_settings.refresh_token_cookie_path.lower()}" in header
    assert "samesite=lax" in header


async def test_auth_rate_limit(rate_limited_auth_client: AsyncClient) -> None:
    for _ in range(2):
        response = await rate_limited_auth_client.post(
            f"{API}/auth/login",
            json={"email": "nobody@example.com", "password": "WrongPass9"},
        )
        assert response.status_code in {401, 422}

    blocked = await rate_limited_auth_client.post(
        f"{API}/auth/login",
        json={"email": "nobody@example.com", "password": "WrongPass9"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


async def test_access_token_for_unknown_user_rejected(
    auth_client: AsyncClient,
    app_settings: Settings,
) -> None:
    unknown_user_id = str(uuid.uuid4())
    token = create_access_token(unknown_user_id, settings=app_settings)
    response = await auth_client.get(
        f"{API}/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
