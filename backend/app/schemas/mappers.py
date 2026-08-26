"""Serialize ORM datetimes for API responses."""

from datetime import datetime


def format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
