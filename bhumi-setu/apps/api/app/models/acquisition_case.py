"""``acquisition_case`` — the unit of work for one acquisition (§6.1, §4.3).

An Acquisition_Case acquires one set of Land_Parcels for one Project. It is the
spine of the domain: notices, objections, awards, payouts, validation issues,
predictions and priority all hang off a case, and the citizen timeline is the
case's slice of the event log.

Versioned, because a stage transition is raced
----------------------------------------------

``acquisition_case`` is first on R29.1's list, so it inherits
:class:`~app.db.versioned.Versioned` and carries ``entity_version integer NOT
NULL DEFAULT 1``. The version is not decoration here: two officers acting on the
same case must not both advance its stage, and §7.2 strengthens the write
predicate to ``WHERE id = :id AND entity_version = :expected AND stage_key =
:expected_stage`` so exactly one transition commits. That machinery is task 8.2's;
this model owns the columns it reads and writes.

The stage set is data, not an enum (§4.3)
-----------------------------------------

``stage_key`` is plain ``text`` with **no enum type and no CHECK constraint**. The
legal stage vocabulary and its successor graph are a ``Policy_Config`` value
(``policy.stage_set``), validated in the service layer against the resolved set,
because a state may run a different lifecycle and onboarding it must not be a
migration (§4.4). The schema guards of task 2.7 actively fail the build on a
``case_stage`` enum or any constraint mentioning ``stage_key`` — so the absence of
a CHECK here is enforced, not merely intended.

``stage_set_effective_from`` pins the graph the case runs under, resolved at
creation, so a state changing its stage set later does not strand an in-flight
case in a stage that no longer exists (§1.2). ``stage_entered_on`` is the date the
current stage was entered, and ``stage_deadline`` is computed from the period
resolved *as of that date* (R28.6) — never from today, and never from a literal,
which is why none of these date columns carries a computed default (task 2.7 fails
the build on one that does).

Denormalised counters and current scores
-----------------------------------------

``open_blocking_count``, ``undisposed_objection_count``, ``pending_review_count``,
``aggregate_awarded`` and ``aggregate_disbursed`` are maintained transactionally
by the subsystems that own those facts (validation in task 13, objections in 11,
compensation in 12), so the case card and the queue read one row rather than
aggregating on every request. They are a cache of truths held elsewhere; the
event log remains the source.

The ``risk_*`` and ``priority_*`` columns are a denormalised copy of the newest
``ml_prediction`` and priority computation (§6.1, §14.8), kept on the case so the
intervention queue and the map can order and shade without a join.
``risk_is_stale`` records that scoring failed and the shown band is the previous
one (R19.12); ``risk_cutoff_source`` records whether the band came from a
district-specific or the platform-wide cutoff set (R19.11). Omission, not a
sentinel, marks "never scored": these columns are simply NULL until a prediction
lands, and the API omits them rather than sending a zero the portal could
misread (§14.7).

The two partial indexes both exclude terminal cases
----------------------------------------------------

``case_queue`` orders live cases by priority within an area (R21.7/21.10) and
``case_rescore`` finds live cases due for rescoring (R19.2). Both are partial on
``WHERE is_terminal = false`` because a closed case is neither queued for
attention nor rescored, and keeping the terminal rows out keeps each index the
size of the active caseload.

``terminal_event_id`` references the event that closed the case, which R32.3 uses
as the retention-clock start once the case is terminal.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.versioned import Versioned

__all__ = ["AcquisitionCase"]


class AcquisitionCase(Base, Versioned):
    """One acquisition of a set of parcels for one project."""

    __tablename__ = "acquisition_case"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    case_reference: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        comment=(
            "The human-quotable identifier a citizen presents for access (R3.1). "
            "UNIQUE: it names exactly one case."
        ),
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("project.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The undertaking this case acquires land for. RESTRICT: a project "
        "with cases cannot be deleted from under them.",
    )

    state_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Policy_Config state key (§4.1). Every deadline, threshold and cutoff "
            "for this case resolves against it. Pinned on the case so policy "
            "resolution never has to walk the hierarchy in the hot path."
        ),
    )
    act_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "The governing act, e.g. RFCTLARR_2013 (§1.2). A case keeps resolving "
            "against the act it began under even if the platform later onboards "
            "another."
        ),
    )

    area_code: Mapped[str] = mapped_column(
        Text,
        ForeignKey("administrative_area.code", ondelete="RESTRICT"),
        nullable=False,
        comment=(
            "The case's administrative seat. R2.2 scope restriction is "
            "path <@ scope over this area's ltree path (§8.1)."
        ),
    )

    stage_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Current Case_Stage. Plain text with NO enum and NO CHECK: the stage "
            "set is a Policy_Config value validated in the service layer (§4.3). "
            "Task 2.7 fails the build on a stage enum or a stage_key CHECK."
        ),
    )
    stage_set_effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment=(
            "Pins the stage graph this case runs under, resolved at creation, so a "
            "later change to the state's stage set cannot strand an in-flight case "
            "(§1.2). No default: supplied at creation, never derived in DDL."
        ),
    )
    stage_entered_on: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment=(
            "Date the current stage was entered. The deadline period resolves as "
            "of this date, not today (R28.6). No computed default (task 2.7)."
        ),
    )
    stage_deadline: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment=(
            "The date the case must leave the current stage, computed from the "
            "period effective on stage_entered_on. NULL for a terminal stage with "
            "no successor. A stored date, not a period — no arithmetic default."
        ),
    )
    deadline_breached: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="Set by the deadline sweep (task 10.3) when stage_deadline passes "
        "while the case is still in the stage.",
    )

    is_terminal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment=(
            "True once the case reaches a terminal stage. Both partial indexes "
            "below exclude terminal cases, so closing a case drops it from the "
            "queue and the rescore set."
        ),
    )
    terminal_event_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("event.id", ondelete="RESTRICT"),
        nullable=True,
        comment=(
            "The event that closed the case. R32.3 starts the retention clock "
            "from it. RESTRICT: the closing event must stay resolvable."
        ),
    )

    # --- denormalised counters, maintained transactionally by their owners -----
    open_blocking_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        comment="Open BLOCKING validation issues; a stage transition is refused "
        "while this is above zero (task 8.2, maintained in task 13.3).",
    )
    undisposed_objection_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        comment="Objections not yet disposed (maintained in task 11.2).",
    )
    pending_review_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        comment="Extracted fields awaiting human review (maintained in task 16).",
    )
    aggregate_awarded: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
        comment="Sum of award totals on the case (maintained in task 12).",
    )
    aggregate_disbursed: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
        comment="Sum of payouts on the case (maintained in task 12.3).",
    )

    # --- current prediction, denormalised from the newest ml_prediction --------
    risk_probability: Mapped[float | None] = mapped_column(
        Double,
        nullable=True,
        comment=(
            "Newest calibrated delay probability. NULL, and omitted from the API, "
            "until a model version is promoted and the case is scored (§14.7): "
            "omission rather than zero, which the portal could misread."
        ),
    )
    risk_band: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="LOW | MEDIUM | HIGH | CRITICAL. Text, banded from the probability "
        "against the resolved cutoff set (§14.8).",
    )
    risk_model_version: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="The model version that produced the score (R31.11)."
    )
    risk_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the current score was generated. Drives case_rescore. No "
        "computed default: it records an event, not a period.",
    )
    risk_is_stale: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment=(
            "Set when scoring failed and the shown band is the previous one "
            "(R19.12); the portal marks it stale rather than hiding it."
        ),
    )
    risk_cutoff_source: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="DISTRICT | PLATFORM: which cutoff set banded the probability "
        "(R19.11).",
    )

    # --- current priority, denormalised for ordering ---------------------------
    priority_score: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3),
        nullable=True,
        comment="Bounded priority ranking. Orders case_queue. NULL until computed.",
    )
    priority_weight_version: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="The weight-set version the score was computed under (R21.3), so a "
        "score is attributable to its configuration.",
    )
    priority_computed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When priority_score was computed. No computed default.",
    )

    __table_args__ = (
        # Live cases by priority within an area (R21.7/21.10). Partial on
        # not-terminal so a closed case leaves the queue; priority_score DESC so
        # the highest-priority case is first without a per-query sort.
        Index(
            "case_queue",
            area_code,
            priority_score.desc(),
            postgresql_where=text("is_terminal = false"),
        ),
        # Live cases due for rescoring (R19.2), oldest score first. Same partial
        # predicate: a terminal case is not rescored.
        Index(
            "case_rescore",
            risk_generated_at,
            postgresql_where=text("is_terminal = false"),
        ),
        {
            "comment": (
                "The unit of work for one acquisition (§6.1). Versioned (R29.1); "
                "stage_key is text with no enum and no CHECK — the stage set is "
                "Policy_Config (§4.3)."
            )
        },
    )

    def __repr__(self) -> str:
        return (
            f"<AcquisitionCase {self.id} {self.case_reference!r} "
            f"stage={self.stage_key} v={self.entity_version}>"
        )
