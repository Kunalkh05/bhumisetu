"""Bulk import batch and row state (task 26.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, LargeBinary, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["ImportBatch", "ImportRow"]


class ImportBatch(Base):
    __tablename__ = "import_batch"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    submitted_by: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    submitted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_checksum: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'PENDING'"))
    last_processed_ordinal: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )


class ImportRow(Base):
    __tablename__ = "import_row"

    batch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("import_batch.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'PENDING'"))
    committed_entity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    rejection: Mapped[Any | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index(
            "import_row_pending",
            batch_id,
            ordinal,
            postgresql_where=text("state = 'PENDING'"),
        ),
    )

