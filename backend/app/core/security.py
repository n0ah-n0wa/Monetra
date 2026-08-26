"""Security primitives: password hashing and JWT helpers."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True when the password matches the Argon2id hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(
    subject: str,
    *,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token."""
    cfg = settings or get_settings()
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=cfg.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return str(jwt.encode(payload, cfg.jwt_secret_key, algorithm=cfg.jwt_algorithm))


def decode_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    """Decode and validate a JWT. Raises UnauthorizedError on failure."""
    cfg = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            cfg.jwt_secret_key,
            algorithms=[cfg.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError(
            code="INVALID_TOKEN",
            message="Token is invalid or expired.",
        ) from exc
    if not isinstance(payload, dict):
        raise UnauthorizedError(
            code="INVALID_TOKEN",
            message="Token is invalid or expired.",
        )
    return payload


def decode_access_token(
    token: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Decode a JWT and ensure it is an access token."""
    payload = decode_token(token, settings=settings)
    if payload.get("type") != "access":
        raise UnauthorizedError(
            code="INVALID_TOKEN",
            message="Token is invalid or expired.",
        )
    return payload


def assert_access_token_active_for_user(
    payload: dict[str, Any],
    *,
    password_changed_at: datetime,
) -> None:
    """Reject access tokens issued before the user's latest password change."""
    issued_at = payload.get("iat")
    if not isinstance(issued_at, (int, float)):
        raise UnauthorizedError(
            code="INVALID_TOKEN",
            message="Token is invalid or expired.",
        )
    if int(issued_at) < int(password_changed_at.timestamp()):
        raise UnauthorizedError(
            code="INVALID_TOKEN",
            message="Token is invalid or expired.",
        )


def generate_refresh_token() -> str:
    """Create a cryptographically secure opaque refresh token."""
    return secrets.token_urlsafe(32)


def generate_password_reset_token() -> str:
    """Create a cryptographically secure opaque password reset token."""
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    """Return a stable SHA-256 hex digest for opaque token storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_refresh_token(token: str) -> str:
    """Return a stable SHA-256 hex digest for refresh-token storage."""
    return hash_opaque_token(token)
