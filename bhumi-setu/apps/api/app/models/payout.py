"""``payout`` — disbursements made against an award."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.versioned import Versioned

__all__ = ["Payout"]


class Payout(Base, Versioned):
    """One payout against one award."""

    __tablename__ = "payout"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    award_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("award.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payout_date: Mapped[date] = mapped_column(Date, nullable=False)
    instrument_reference: Mapped[str] = mapped_column(Text, nullable=False)
    beneficiary: Mapped[str] = mapped_column(Text, nullable=False)
