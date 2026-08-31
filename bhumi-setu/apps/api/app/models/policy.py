"""``policy_config`` — the configuration substrate (§4.1).

Every statutory period, notice window, stage deadline, OCR threshold, risk band
cutoff, priority weight and retention period in the platform is a row here. R7.2
forbids any of them appearing as a literal in code, a column default, or a CHECK
constraint, so this table is not a convenience: it is where the numbers live.

Append-only by convention, not by grant
---------------------------------------

No row is ever updated or deleted. A change is a **new row with a later
``effective_from``**, which is what gives R28.3 its change history without a
separate audit table, and what makes R7.8 structural — a deadline computed from
the period effective on the notice's issue date keeps resolving to the same
answer forever, because the row it read is still there.

The event log gets this enforced by a revoked grant (task 3.1). This table does
not, yet, and the distinction is worth stating rather than leaving a reader to
assume: nothing at the database level currently stops an ``UPDATE`` here. Task 2.5
routes all writes through ``PolicyService.set``, and the same revoke belongs on
this table when the application role is in use.

Resolution
----------

``state_key`` carries ``'*'`` for a platform-wide default rather than NULL. NULL
would make the resolution predicate ``state_key = :state OR state_key IS NULL``
and the ordering ``state_key IS NOT NULL DESC``, both of which read worse and the
second of which is easy to get backwards. A sentinel keeps the query in §4.1 to
one ``IN`` and one boolean sort.

``act_key`` *is* nullable, because "not act-specific" is a real state rather than
a default — a retention period is not act-scoped at all. The cost is that
uniqueness and the resolve index both key on ``coalesce(act_key, '')``, since NULL
is not equal to NULL and a plain unique constraint would let two NULL-act rows
coexist for the same key, state and date.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["PolicyConfig"]

#: Sentinel in ``state_key`` for a value that applies to every state.
PLATFORM_WIDE = "*"


class PolicyConfig(Base):
    """One version of one configured value, effective from a date."""

    __tablename__ = "policy_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    policy_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Dotted key, e.g. period.pn.to_declaration, policy.stage_set, "
            "ocr.threshold.auto_accept. Validators in task 2.4 key on a pattern "
            "over this column."
        ),
    )

    state_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text(f"'{PLATFORM_WIDE}'"),
        comment=(
            "'IN-MH' etc., or '*' for platform-wide. A sentinel rather than NULL "
            "so the resolve query stays one IN plus one boolean sort (§4.1)."
        ),
    )

    act_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "NULL where the value is not act-specific, which is a real state and "
            "not a default. Uniqueness keys on coalesce(act_key, '') because NULL "
            "is not equal to NULL."
        ),
    )

    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment=(
            "R28.6: resolution is against the relevant statutory event date, not "
            "the current date, so a period change never rewrites a deadline "
            "already computed."
        ),
    )

    value: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        comment=(
            "jsonb so one column holds a day count, a threshold, a weight map and "
            "the whole stage graph. A typed column per shape would make every new "
            "kind of policy value a migration."
        ),
    )

    justification_report_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment=(
            "R28.9: an OCR threshold change must cite the Extraction_Accuracy_"
            "Report stating the precision observed at the new threshold. The "
            "foreign key to extraction_accuracy_report is added by task 16.7, "
            "which creates that table; the CHECK below already requires the "
            "reference to be present."
        ),
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("officer.id", ondelete="RESTRICT"),
        nullable=False,
        comment=(
            "R28.3: who made the change. RESTRICT because an officer who set a "
            "statutory period must stay resolvable for as long as the row does."
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Expression uniqueness, so it must be a unique INDEX rather than a UNIQUE
        # table constraint: PostgreSQL constraints take column names only, and the
        # coalesce() is not optional here — without it two rows with a NULL
        # act_key for the same key, state and date would both be accepted, and the
        # resolve query would return whichever the planner reached first.
        Index(
            "policy_config_unique_version",
            policy_key,
            state_key,
            text("coalesce(act_key, '')"),
            effective_from,
            unique=True,
        ),
        Index(
            "policy_config_resolve",
            policy_key,
            state_key,
            text("coalesce(act_key, '')"),
            effective_from.desc(),
        ),
        CheckConstraint(
            "policy_key NOT LIKE 'ocr.threshold.%' "
            "OR justification_report_id IS NOT NULL",
            name="ocr_threshold_requires_report",
        ),
        {
            "comment": (
                "Effective-dated configuration (§4.1). Append-only: a change is a "
                "new row with a later effective_from, which is what gives R28.3 "
                "its history and R7.8 its frozen deadlines."
            )
        },
    )

    def __repr__(self) -> str:
        return (
            f"<PolicyConfig {self.policy_key} state={self.state_key} "
            f"act={self.act_key} from={self.effective_from}>"
        )
