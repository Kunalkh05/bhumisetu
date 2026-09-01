"""``award`` and ``award_component`` — compensation determined outside the platform."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, CHAR, Date, ForeignKey, Numeric, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.versioned import Versioned

__all__ = ["Award", "AwardComponent"]


class Award(Base, Versioned):
    """A compensation award for one ownership record."""

    __tablename__ = "award"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ownership_record_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ownership_record.id", ondelete="RESTRICT"),
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    determination_date: Mapped[date] = mapped_column(Date, nullable=False)
    determining_authority: Mapped[str] = mapped_column(Text, nullable=False)
    disbursement_state: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'UNPAID'"),
    )


class AwardComponent(Base):
    """One itemised component of an award total."""

    __tablename__ = "award_component"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    award_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("award.id", ondelete="RESTRICT"),
        nullable=False,
    )
    component_label: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
