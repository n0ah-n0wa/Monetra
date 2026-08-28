"""Redact sensitive values before logging or returning diagnostics."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|passwd|secret|token|authorization|api[_-]?key|cookie|"
    r"jwt|bearer|credential|private[_-]?key|refresh)",
    re.IGNORECASE,
)

_BEARER_PATTERN = re.compile(r"^Bearer\s+.+$", re.IGNORECASE)
_CONNECTION_URL_PATTERN = re.compile(
    r"(postgresql(?:\+\w+)?://)[^@\s]+@",
    re.IGNORECASE,
)


def is_sensitive_key(key: str) -> bool:
    """Return True when a mapping key should be redacted."""
    return bool(_SENSITIVE_KEY_PATTERN.search(key))


def redact_string(value: str) -> str:
    """Redact known secret patterns inside a string."""
    if _BEARER_PATTERN.match(value.strip()):
        return "Bearer [REDACTED]"
    return _CONNECTION_URL_PATTERN.sub(r"\1[REDACTED]@", value)


def redact_value(key: str, value: Any) -> Any:
    """Redact a single value based on its key and shape."""
    if is_sensitive_key(key):
        return REDACTED
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, list | tuple):
        return [redact_value(key, item) for item in value]
    return value


def redact_mapping(data: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a copy of ``data`` with sensitive keys and patterns redacted."""
    if data is None:
        return {}
    return {key: redact_value(key, value) for key, value in data.items()}


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Redact sensitive HTTP headers for access logs."""
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        lowered = key.lower()
        if lowered in {"authorization", "cookie", "set-cookie"}:
            redacted[key] = REDACTED
        else:
            redacted[key] = redact_string(value)
    return redacted
