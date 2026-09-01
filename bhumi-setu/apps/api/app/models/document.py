"""``document`` — immutable uploaded bytes and extraction state."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.versioned import Versioned

__all__ = ["Document"]


class Document(Base, Versioned):
    """A document object stored outside PostgreSQL, with immutable bytes."""

    __tablename__ = "document"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_case.id", ondelete="RESTRICT"),
        nullable=True,
    )
    parcel_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("land_parcel.id", ondelete="RESTRICT"),
        nullable=True,
    )
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("officer.id", ondelete="RESTRICT"),
        nullable=False,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    processing_state: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'QUEUED'"),
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_script: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "case_id IS NOT NULL OR parcel_id IS NOT NULL",
            name="document_has_scope",
        ),
        Index(
            "document_case_checksum",
            case_id,
            checksum_sha256,
            unique=True,
            postgresql_where=case_id.is_not(None),
        ),
        {
            "comment": (
                "Immutable uploaded document bytes; extraction writes separate rows "
                "and never rewrites the object."
            )
        },
    )
