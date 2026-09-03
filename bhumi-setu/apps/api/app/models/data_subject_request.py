"""Data subject requests and retention withholding records."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["DataSubjectRequest", "RetentionWithholding"]


class DataSubjectRequest(Base):
    """A DSAR or correction request with its due date materialized at receipt."""

    __tablename__ = "data_subject_request"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_type: Mapped[str] = mapped_column(Text, nullable=False)
    subject_key: Mapped[str] = mapped_column(Text, nullable=False)
    case_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_case.id", ondelete="RESTRICT"),
        nullable=True,
    )
    ownership_record_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ownership_record.id", ondelete="RESTRICT"),
        nullable=True,
    )
    target_attribute: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    asserted_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'OPEN'"),
    )
    routed_area_code: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("administrative_area.code", ondelete="RESTRICT"),
        nullable=True,
    )
    created_event_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("event.id", ondelete="RESTRICT"),
        nullable=True,
    )
    disposed_event_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("event.id", ondelete="RESTRICT"),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "data_subject_request_overdue",
            due_at,
            postgresql_where=text("completed_at IS NULL"),
        ),
    )


class RetentionWithholding(Base):
    """A recorded reason a personal datum cannot yet be erased."""

    __tablename__ = "retention_withholding"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    attribute_name: Mapped[str] = mapped_column(Text, nullable=False)
    data_category: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    retention_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    policy_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "retention_withholding_lookup",
            entity_type,
            entity_id,
            attribute_name,
            data_category,
        ),
    )
