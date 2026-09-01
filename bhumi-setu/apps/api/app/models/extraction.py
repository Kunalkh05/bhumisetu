"""OCR extraction output for an immutable document."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.versioned import Versioned

__all__ = ["ExtractedField", "Extraction"]


class Extraction(Base):
    """One OCR run for one document and model version."""

    __tablename__ = "extraction"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document.id", ondelete="RESTRICT"),
        nullable=False,
    )
    extraction_model_version: Mapped[str] = mapped_column(Text, nullable=False)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_script: Mapped[str] = mapped_column(Text, nullable=False)
    mean_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "extraction_model_version",
            name="extraction_document_model_unique",
        ),
        CheckConstraint(
            "mean_confidence >= 0 AND mean_confidence <= 1",
            name="extraction_mean_confidence_range",
        ),
    )


class ExtractedField(Base, Versioned):
    """A single extracted field and its review state."""

    __tablename__ = "extracted_field"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    extraction_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("extraction.id", ondelete="RESTRICT"),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    original_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_x1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x2: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y2: Mapped[float] = mapped_column(Float, nullable=False)
    review_state: Mapped[str] = mapped_column(Text, nullable=False)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    accuracy_report_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("extraction_accuracy_report.id", ondelete="RESTRICT"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="extracted_field_confidence_range",
        ),
        CheckConstraint(
            "original_confidence >= 0 AND original_confidence <= 1",
            name="extracted_field_original_confidence_range",
        ),
        CheckConstraint("page_number >= 1", name="extracted_field_page_positive"),
        CheckConstraint(
            "bbox_x1 >= 0 AND bbox_x1 <= 1 AND bbox_y1 >= 0 AND bbox_y1 <= 1 "
            "AND bbox_x2 >= 0 AND bbox_x2 <= 1 AND bbox_y2 >= 0 AND bbox_y2 <= 1 "
            "AND bbox_x1 <= bbox_x2 AND bbox_y1 <= bbox_y2",
            name="extracted_field_bbox_page_relative",
        ),
        Index("extracted_field_review_queue", review_state, extraction_id),
    )
