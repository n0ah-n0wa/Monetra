"""Helpers for PostgreSQL enum columns."""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def pg_enum[E: StrEnum](enum_class: type[E], name: str) -> SAEnum:
    """Persist StrEnum values (lowercase strings) in PostgreSQL."""
    return SAEnum(
        enum_class,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )
