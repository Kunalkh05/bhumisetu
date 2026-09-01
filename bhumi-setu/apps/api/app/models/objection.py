"""``objection`` — representations raised against a notice or case (§6.1, R8)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.versioned import Versioned

__all__ = ["Objection"]


class Objection(Base, Versioned):
    """One objection and, once decided, its disposal."""

    __tablename__ = "objection"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_case.id", ondelete="RESTRICT"),
        nullable=False,
    )
    objector_name: Mapped[str] = mapped_column(Text, nullable=False)
    ownership_record_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ownership_record.id", ondelete="RESTRICT"),
        nullable=True,
    )
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    grounds_category: Mapped[str] = mapped_column(Text, nullable=False)
    substance: Mapped[str] = mapped_column(Text, nullable=False)
    governing_notice_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("statutory_notice.id", ondelete="RESTRICT"),
        nullable=True,
    )
    window_state: Mapped[str] = mapped_column(Text, nullable=False)
    disposal_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    is_disposal_overdue: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    disposal_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    disposal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    disposal_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    deciding_officer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("officer.id", ondelete="RESTRICT"),
        nullable=True,
    )

    __table_args__ = (
        {
            "comment": (
                "An objection raised against a case or notice (R8). Versioned "
                "(R29.1); objector_name is personal data and substance is a land "
                "record in the retention registry."
            )
        },
    )
