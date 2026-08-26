"""Historical exchange rate snapshots for multi-currency analytics."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import ExchangeRateNumeric
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ExchangeRate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable daily rate used for reporting conversions.

    Storing rates by date prevents historical analytics from changing when a
    provider publishes newer values.
    """

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint(
            "base_currency",
            "quote_currency",
            "rate_date",
            name="uq_exchange_rates_pair_date",
        ),
        CheckConstraint(
            "base_currency <> quote_currency",
            name="ck_exchange_rates_distinct_currencies",
        ),
        CheckConstraint("rate > 0", name="ck_exchange_rates_rate_positive"),
        Index("ix_exchange_rates_rate_date", "rate_date"),
        Index(
            "ix_exchange_rates_pair_rate_date",
            "base_currency",
            "quote_currency",
            "rate_date",
        ),
    )

    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(ExchangeRateNumeric(), nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return (
            f"ExchangeRate({self.base_currency}/{self.quote_currency}="
            f"{self.rate}@{self.rate_date})"
        )
