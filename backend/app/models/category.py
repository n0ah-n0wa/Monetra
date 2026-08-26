"""Category model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enum_column import pg_enum
from app.models.enums import CategoryStatus, CategoryType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.budget import Budget
    from app.models.recurring_transaction import RecurringTransaction
    from app.models.transaction import Transaction
    from app.models.user import User


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint(
            "(is_system = true AND user_id IS NULL) OR "
            "(is_system = false AND user_id IS NOT NULL)",
            name="ck_categories_system_owner",
        ),
        Index(
            "uq_categories_system_name_type",
            "name",
            "category_type",
            unique=True,
            postgresql_where=text("is_system = true"),
        ),
        Index(
            "uq_categories_user_name_type",
            "user_id",
            "name",
            "category_type",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index("ix_categories_user_id", "user_id"),
        Index("ix_categories_user_id_status", "user_id", "status"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category_type: Mapped[CategoryType] = mapped_column(
        pg_enum(CategoryType, "category_type"),
        nullable=False,
    )
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_system: Mapped[bool] = mapped_column(nullable=False, default=False)
    status: Mapped[CategoryStatus] = mapped_column(
        pg_enum(CategoryStatus, "category_status"),
        nullable=False,
        default=CategoryStatus.ACTIVE,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User | None] = relationship(back_populates="categories")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="category",
    )
    recurring_transactions: Mapped[list[RecurringTransaction]] = relationship(
        back_populates="category",
    )
    budgets: Mapped[list[Budget]] = relationship(
        secondary="budget_categories",
        back_populates="categories",
    )

    def __repr__(self) -> str:
        return f"Category(id={self.id!s}, name={self.name!r})"
