"""``validation_issue`` and history — rule violations retained after resolution."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.versioned import Versioned

__all__ = ["ValidationIssue", "ValidationIssueHistory"]


class ValidationIssue(Base, Versioned):
    __tablename__ = "validation_issue"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_case.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rule_id: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    offending_entities: Mapped[dict] = mapped_column(JSONB, nullable=False)
    observed_values: Mapped[dict] = mapped_column(JSONB, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolution_state: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'OPEN'"),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "validation_issue_open_unique",
            case_id,
            rule_id,
            fingerprint,
            unique=True,
            postgresql_where=text("resolution_state = 'OPEN'"),
        ),
        Index(
            "validation_issue_queue",
            case_id,
            severity,
            detected_at,
            postgresql_where=text("resolution_state = 'OPEN'"),
        ),
    )


class ValidationIssueHistory(Base):
    __tablename__ = "validation_issue_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("validation_issue.id", ondelete="RESTRICT"),
        nullable=False,
    )
    prior_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_state: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurrence_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
