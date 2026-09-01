"""Holdout OCR documents and hand-labelled field values."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["HoldoutDocument", "HoldoutLabel"]


class HoldoutDocument(Base):
    __tablename__ = "holdout_document"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    object_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    detected_script: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class HoldoutLabel(Base):
    __tablename__ = "holdout_label"

    holdout_document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("holdout_document.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    field_name: Mapped[str] = mapped_column(Text, primary_key=True)
    expected_value: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "holdout_document_id",
            "field_name",
            name="holdout_label_document_field_unique",
        ),
    )
