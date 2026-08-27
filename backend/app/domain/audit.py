"""Safe audit metadata helpers."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "token",
    "secret",
    "authorization",
    "cookie",
    "credential",
    "api_key",
    "apikey",
    "refresh",
    "hash",
    "private_key",
    "access_key",
)


def is_sensitive_audit_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return sanitize_audit_metadata(value)
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    return str(value)


def sanitize_audit_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return JSON-safe metadata with secrets stripped.

    Never persists passwords, tokens, or other authentication material.
    """
    if metadata is None:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if is_sensitive_audit_key(str(key)):
            continue
        cleaned[str(key)] = _serialize_value(value)
    return cleaned
