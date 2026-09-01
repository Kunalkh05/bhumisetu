"""Extraction accuracy reports measured against the holdout set."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["ExtractionAccuracyReport"]


class ExtractionAccuracyReport(Base):
    __tablename__ = "extraction_accuracy_report"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    extraction_model_version: Mapped[str] = mapped_column(Text, nullable=False)
    script_set_version: Mapped[str] = mapped_column(Text, nullable=False)
    holdout_manifest_hash: Mapped[str] = mapped_column(Text, nullable=False)
    accuracy_by_field: Mapped[dict] = mapped_column(JSONB, nullable=False)
    accuracy_by_script: Mapped[dict] = mapped_column(JSONB, nullable=False)
    holdout_document_count: Mapped[int] = mapped_column(Integer, nullable=False)
    labelled_instance_count_by_field: Mapped[dict] = mapped_column(JSONB, nullable=False)
    precision_at_threshold: Mapped[dict] = mapped_column(JSONB, nullable=False)
    measurement_date: Mapped[date] = mapped_column(Date, nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "extraction_model_version",
            "script_set_version",
            "holdout_manifest_hash",
            name="extraction_accuracy_report_idempotency",
        ),
    )
