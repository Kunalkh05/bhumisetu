"""``event`` — the append-only log (§5.1).

R4.1 requires one event per state change. R4.2 requires the log to accept appends
only. R4.7 makes it the *sole* source of both the citizen timeline and the machine
learning features, which is why this is a product feature rather than a journal:
two very different readers depend on it, and they read it differently.

Append-only is a revoked grant, not a convention
------------------------------------------------

``REVOKE UPDATE, DELETE ON event FROM bhumisetu_app`` in migration 0003 is the
guarantee. The ORM mapping additionally refuses a mutation before it reaches the
database — see :func:`_forbid_event_mutation` — but that is a developer
convenience, not the enforcement. The distinction matters: application-level
checks are bypassed by the next person who writes raw SQL, and a log whose
immutability depends on everyone remembering is not immutable.

Two timestamps, and they are not redundant
------------------------------------------

``occurrence_time`` is when the thing happened in the world; ``recording_time`` is
when the platform learned it. R4.3 requires both, and R4.4 permits an event to be
appended with an occurrence time *earlier* than one already stored — an officer
recording a notice served last week.

That backdating is why the two as-of predicates in task 3.5 cannot be collapsed
into one. A citizen timeline asks "what happened by date D" and filters on
occurrence time. A feature row asks "what was knowable at time T" and must filter
on **both**, or it uses information that did not exist yet and R17.2 is violated
silently — the model trains on the future and looks unusually accurate.

Ordering is ``(occurrence_time, id)``
-------------------------------------

The ``id`` tiebreak is not decoration. R17.5 requires the Feature_Builder to be
deterministic, and a replay fold over a sequence with ties in an unspecified order
is not. Two events with the same occurrence time — common, since officers enter
dates rather than timestamps — would otherwise fold in whatever order the planner
returned them.

``entity_id`` is ``bigint``
--------------------------

Which constrains every entity R4.1 names to a bigint primary key. That is a
deliberate constraint on tasks 8.1 onward, recorded here because it is invisible
from those tasks: ``acquisition_case``, ``land_parcel``, ``ownership_record``,
``statutory_notice``, ``objection``, ``award``, ``payout``, ``document``,
``extracted_field`` and ``validation_issue`` must all use bigint, and
``policy_config`` already does.

``officer`` and ``role`` remain uuid, which is not a conflict: an officer appears
in the log as an *actor* (``actor_id text``), never as an entity, because R4.1
does not make officer records auditable state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    event as sa_event,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.base import Base

__all__ = ["ActorType", "Event", "EventImmutable", "Provenance"]


class ActorType:
    """Who caused an event. Text rather than an enum: R30.8 adds IMPORT, and a
    future integration will add another without wanting a migration."""

    OFFICER = "OFFICER"
    CITIZEN_SESSION = "CITIZEN_SESSION"
    SYSTEM = "SYSTEM"
    IMPORT = "IMPORT"


class Provenance:
    """How a row came to exist. R30.8 requires imported rows to be distinguishable."""

    MANUAL = "MANUAL"
    IMPORTED = "IMPORTED"
    SYSTEM = "SYSTEM"


class EventImmutable(RuntimeError):
    """An attempt to change or delete a stored event (R4.2).

    Raised by the ORM before the statement is emitted. The database would refuse it
    anyway via the revoked grant; this exists so the traceback names the offending
    code rather than surfacing as a permission error from psycopg.
    """


class Event(Base):
    """One immutable record of one state change."""

    __tablename__ = "event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    event_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="CASE_CREATED, DEADLINE_BREACHED, PERSONAL_DATA_ERASED, and so on.",
    )

    entity_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The table name of the affected entity, so the log is self-describing.",
    )
    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment=(
            "bigint, which constrains every entity R4.1 names to a bigint primary "
            "key. See the module docstring."
        ),
    )

    case_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment=(
            "Denormalised so the citizen timeline (R25.4) is one indexed read "
            "rather than a walk from parcel to ownership to case. NULL for an event "
            "with no case, such as a Policy_Config change. The foreign key to "
            "acquisition_case is added by task 8.1, which creates that table."
        ),
    )

    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Text, not a foreign key to officer: an actor may be a citizen session, "
            "the scheduler, or an import batch. R4.1 needs the actor recorded, not "
            "joined."
        ),
    )

    occurrence_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When it happened in the world. May precede an existing event (R4.4).",
    )
    recording_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment=(
            "When the platform learned it. Distinct from occurrence_time (R4.3); "
            "the pair is what makes KNOWABLE_AT possible in task 3.5."
        ),
    )

    payload: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        comment=(
            "Changed attributes as {'from': ..., 'to': ...}. Personal data is held "
            "by reference as {'$pd': id} and never inline, which is what lets a "
            "value be erased later without touching a stored event (§5.4, R32.12)."
        ),
    )
    has_pd_refs: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment=(
            "True when payload holds any $pd reference, so the read-time resolver "
            "can skip the join for the majority of events."
        ),
    )

    entity_version_after: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "R29.4 needs the actor whose modification produced the current version. "
            "Without this, attributing a version to an actor means guessing from "
            "timestamps."
        ),
    )

    provenance: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'MANUAL'")
    )
    import_batch_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="R30.8. Foreign key to import_batch added by task 26.1.",
    )

    corrects_event_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("event.id", ondelete="RESTRICT"),
        nullable=True,
        comment=(
            "R4.6 and R32.12: a correction and an erasure are both new events "
            "referencing the erroneous one, never an update to it."
        ),
    )

    txid: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("txid_current()"),
        comment=(
            "The transaction that wrote this event. Task 3.7's deferred constraint "
            "trigger uses it to assert that a mutated row got an event in the same "
            "transaction."
        ),
    )

    __table_args__ = (
        # As-of reads for one entity (§5.3). Ordering columns are in the index so
        # the fold in task 22.2 is an index scan, not a sort.
        Index("event_entity_asof", entity_type, entity_id, occurrence_time, id),
        # The citizen timeline (R25.4) and the officer case timeline (R23.4).
        Index("event_case_asof", case_id, occurrence_time, id),
        # KNOWABLE_AT filters on recording_time as well (task 3.5).
        Index("event_knowable", entity_type, entity_id, recording_time),
        # Task 3.7's trigger looks up by transaction.
        Index("event_txid", txid),
        {
            "comment": (
                "Append-only event log (§5.1). R4.2 is enforced by REVOKE UPDATE, "
                "DELETE from bhumisetu_app, not by application code."
            )
        },
    )

    def __repr__(self) -> str:
        return (
            f"<Event {self.id} {self.event_type} {self.entity_type}:{self.entity_id} "
            f"occurred={self.occurrence_time}>"
        )


def _forbid_event_mutation(session: Session, flush_context: Any, instances: Any) -> None:
    """Refuse an update or delete of a stored event before the statement is emitted.

    A convenience, not the guarantee — the revoked grant is. It exists because a
    permission error from psycopg names the connection, not the line of code that
    tried to mutate the log, and that is a poor first clue.

    Deliberately checks ``session.dirty`` and ``session.deleted`` rather than
    overriding ``__setattr__``: an in-memory attribute change on an event that is
    never flushed harms nothing, and a setter guard would also block SQLAlchemy
    populating the object on load.
    """
    for instance in session.deleted:
        if isinstance(instance, Event):
            raise EventImmutable(
                f"cannot delete event {instance.id}: the log is append-only (R4.2). "
                "Record a compensating event instead (R4.6)."
            )
    for instance in session.dirty:
        if isinstance(instance, Event) and session.is_modified(instance):
            raise EventImmutable(
                f"cannot modify event {instance.id}: the log is append-only (R4.2). "
                "Record a compensating event referencing it instead (R4.6)."
            )


sa_event.listen(Session, "before_flush", _forbid_event_mutation)
