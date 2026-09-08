"""Localization models (§17.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["MissingTranslation"]


class MissingTranslation(Base):
    """Missing localization key recording for queryability and gap filling (R27.4)."""

    __tablename__ = "missing_translation"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    locale: Mapped[str] = mapped_column(Text, primary_key=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
