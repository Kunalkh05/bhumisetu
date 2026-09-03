"""Materialized dashboard snapshots and band history."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["DashboardBandHistory", "DashboardSnapshot"]


class DashboardSnapshot(Base):
    """One precomputed dashboard snapshot per leaf area."""

    __tablename__ = "dashboard_snapshot"

    area_code: Mapped[str] = mapped_column(
        Text,
        ForeignKey("administrative_area.code", ondelete="RESTRICT"),
        primary_key=True,
    )
    metrics: Mapped[Any] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DashboardBandHistory(Base):
    """Append-only monthly risk-band counts for the dashboard trend."""

    __tablename__ = "dashboard_band_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    area_code: Mapped[str] = mapped_column(
        Text,
        ForeignKey("administrative_area.code", ondelete="RESTRICT"),
        nullable=False,
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    band: Mapped[str] = mapped_column(Text, nullable=False)
    case_count: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "area_code",
            "month",
            "band",
            "computed_at",
            name="dashboard_band_history_unique_computation",
        ),
    )
