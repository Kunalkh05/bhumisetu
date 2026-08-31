"""``VersionedRepository.update`` — the one write path for a versioned entity (§7).

What R29 asks for, and where it is discharged
---------------------------------------------

R29.1 requires an :class:`~app.db.versioned.Versioned` entity's version to
increase on every committed modification; R29.3/29.5 require a request presenting a
stale version to be rejected with *nothing written*; R29.6/29.7 require that of two
requests presenting the same version exactly one commits. The mechanism that makes
all four true is a single conditional compare-and-set issued here, inside the
caller's transaction, followed by the event append on that same transaction:

    UPDATE <entity>
       SET <changes>, entity_version = entity_version + 1
     WHERE id = :id AND entity_version = :expected
    RETURNING <entity>;

    -- then, only if a row came back:
    INSERT INTO event (...);

Two things about *how* this is written are load-bearing.

**The UPDATE runs first; the event append runs second.** On the rejection path the
compare-and-set matches no row, so control never reaches the append and **no event
is ever written** (R29.5). The property therefore holds *structurally* — there is
no code path that appends an event for a rejected modification — rather than by
leaning on the transaction rolling an already-written event back. Rollback would
work too, but only for as long as nobody moved the append to a second connection
where the rollback could not reach it; ordering the append after the conditional
UPDATE makes that mistake impossible to make quietly. This is the same reasoning
``app/db/event_log.py`` and ``app/db/session.py`` apply to the append itself, one
level up.

**The append is on the caller's session, not a new one.** ``update`` takes the
``session`` the caller is already holding inside its ``unit_of_work()`` and hands
that same session to :meth:`EventLog.append`, so the entity write and the event
insert are one transaction on one connection. If the append fails, the enclosing
``unit_of_work()`` rolls the whole thing back — the version bump included — and
R4.8's atomicity holds. ``update`` never opens a connection or commits; that is the
block's job (see ``app/db/session.py`` for why a service is *handed* its session
rather than reaching for one).

The compare-and-set is atomic, so the same-version race needs no lock of ours
--------------------------------------------------------------------------------

Two transactions issuing the same conditional UPDATE at ``READ COMMITTED`` serialise
on the row lock: the second blocks until the first commits, then PostgreSQL
re-evaluates the second's ``WHERE`` against the *new* row, finds ``entity_version =
:expected`` now false, and matches zero rows. Exactly one commits, every time, with
no advisory lock and no ``SERIALIZABLE`` retry loop (§7.2). This module does not
implement that arbitration — PostgreSQL does — it only issues the statement that
lets PostgreSQL do it. Task 4.4's two-connection test is what proves the belief.

The strengthened predicate for a stage transition (§7.2, R29.7)
---------------------------------------------------------------

A Case_Stage transition passes ``expected_stage``, which adds ``AND stage_key =
:expected_stage`` to the ``WHERE``. Two officers transitioning *out of the same
stage* then race on the stage as well as the version, so even if they somehow hold
the same version by different routes the second still matches zero rows once the
first has moved the case on. The version check alone already arbitrates the common
case; the stage predicate closes the gap R29.7 names explicitly.

The conflict description (task 4.3, R29.3/29.4/29.8)
----------------------------------------------------

When the compare-and-set matches no row this raises :class:`EntityVersionConflict`,
a 409 in the §9.4 envelope. R29.4 says the rejection must tell the caller *why*, in
enough detail to resubmit: every attribute whose stored value now differs from the
value the request presented as its prior value, the current stored value of each,
and the actor and occurrence time of the modification that produced the current
version. :func:`_describe_conflict` builds exactly that. The actor and time come
from ``event.entity_version_after`` — the event whose ``entity_version_after``
equals the row's current version is the winning modification, and reading it there
is what lets R29.4 attribute a version to an actor rather than guessing from
timestamps (§7.2). :func:`_describe_field_review_conflict` adds the winner's review
state and recorded value for the double-field-review case (R29.8); it is
parameterised on attribute names rather than importing ``extracted_field`` (which
task 16.1 creates), so it is the single description the review write path will pass
its column names to. The ``expected_version`` / ``If-Match`` request plumbing that
carries the presented version *in* lives in ``app/api/versioning.py`` — an API
concern, kept out of this DB-layer module.

Placement
---------

Plumbing, so it lives under ``app/db/`` beside :class:`~app.db.versioned.Versioned`
(the column it drives) and :class:`~app.db.event_log.EventLog` (the append it
orders itself before). It declares no table and imports nothing from the security
layer: ``actor`` is typed on the structural :class:`~app.db.event_log.Actor`
protocol, exactly as the event log types it, so ``app/db/`` stays independent of
``app/security/`` (which is built later and imports *this*). The one model it reads
is :class:`~app.models.event.Event`, to find the winning modification's actor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.db.versioned import Versioned
from app.errors import DomainError, ErrorCode
from app.models.event import Event

__all__ = [
    "AttrConflict",
    "ConflictDetail",
    "EntityVersionConflict",
    "ReviewConflictSpec",
    "VersionedRepository",
]

#: The attribute the strengthened stage predicate compares (§7.2). A Case_Stage
#: transition is the one modification that races on more than the version, so the
#: column name lives here as a named constant rather than a string buried in the
#: statement builder.
_STAGE_COLUMN = "stage_key"

#: Keys a caller must not put in ``changes``: the version is the repository's to
#: increment, and the identity is what the ``WHERE`` selects on. Letting either
#: through ``.values(**changes)`` would either break the compare-and-set invariant
#: (a caller setting ``entity_version`` by hand) or move the row out from under the
#: predicate (a caller setting ``id``).
_REPOSITORY_MANAGED = frozenset({"entity_version", "id"})


def _jsonable(value: Any) -> Any:
    """Render a stored or submitted value for the JSON error envelope.

    The conflict detail crosses the API boundary as ``jsonb`` (§9.4), so every value
    in it must be JSON-native. A ``datetime`` becomes its ISO-8601 string, normalised
    to UTC when it carries a timezone so the envelope reads the same regardless of the
    database session's timezone (§9.4 states the occurrence time in UTC); a
    ``Decimal``, ``date`` or any other non-native value becomes ``str(value)`` — the
    ``"0.50"`` / ``"0.34"`` shape §9.4 shows for a share conflict. Native scalars
    (``str``, ``int``, ``float``, ``bool``, ``None``) pass through unchanged, so an
    integer count stays a number and a null prior stays ``null`` rather than the
    string ``"None"``. Comparison for divergence happens on the *raw* values before
    this runs (``Decimal('0.50') != Decimal('0.34')``); this only shapes the output.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value.isoformat()
    return str(value)


@dataclass(frozen=True)
class AttrConflict:
    """One attribute whose stored value no longer matches the request's prior (R29.4).

    ``submitted_prior`` is what the request presented as the value it believed it was
    replacing; ``current`` is what the row actually holds now. Both are rendered
    JSON-native for the envelope.
    """

    name: str
    submitted_prior: Any
    current: Any

    def as_detail(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "submitted_prior": _jsonable(self.submitted_prior),
            "current": _jsonable(self.current),
        }


@dataclass(frozen=True)
class ConflictDetail:
    """The R29.4 description of why a modification was rejected.

    Names every diverged attribute, the entity's current version, and the actor and
    occurrence time of the modification that produced that version (read from
    ``event.entity_version_after``; ``None`` when no event attributes the current
    version, e.g. a freshly created entity with no modification yet). For a double
    field review (R29.8) ``is_field_review`` is set and ``current_review_state``
    carries the winning review's state; the value the winner recorded is the
    ``current`` of the value attribute in :attr:`attributes`.
    """

    attributes: tuple[AttrConflict, ...]
    current_entity_version: int | None
    conflicting_actor_id: str | None
    conflicting_occurrence_time: datetime | None
    current_review_state: str | None = None
    is_field_review: bool = False

    def as_details(self) -> dict[str, Any]:
        """The §9.4 ``details`` payload for this conflict."""
        details: dict[str, Any] = {
            "attributes": [attr.as_detail() for attr in self.attributes],
            "conflicting_actor_id": self.conflicting_actor_id,
            "conflicting_occurrence_time": _jsonable(self.conflicting_occurrence_time),
            "current_entity_version": self.current_entity_version,
        }
        if self.is_field_review:
            # R29.8: the rejected review is told the winning review's recorded state.
            # Emitted only for a field-review conflict, where a None state would still
            # be meaningful, so its absence elsewhere is not mistaken for "no state".
            details["current_review_state"] = self.current_review_state
        return details


@dataclass(frozen=True)
class ReviewConflictSpec:
    """How to describe a double-field-review conflict without importing the model.

    R29.8's ``Extracted_Field`` (task 16.1) does not exist yet, and this DB-layer
    module must not depend on a domain model regardless. So the field-review write
    path passes the two column names the R29.8 description reads — the reviewed value
    and the review state — and :func:`_describe_field_review_conflict` reads them off
    the current row by name. ``VersionedRepository.update`` takes one of these as
    ``review_conflict`` to select the field-review description on the rejection path.
    """

    value_attribute: str
    review_state_attribute: str


class EntityVersionConflict(DomainError):
    """A modification presented a version the target entity is no longer at (R29.3).

    Raised when the conditional UPDATE matches no row — because the presented
    version is stale (R29.3/29.6) or, for a stage transition, because the case has
    already left the expected stage (R29.7). A 409 in the §9.4 envelope.

    ``details`` always names the entity and the presented version, and — once
    ``detail`` is supplied by :meth:`VersionedRepository.update` — carries the full
    R29.4 description: the per-attribute diff, the current version, and the winning
    modification's actor and occurrence time, plus the review state for a field
    review (R29.8). Composing the identity keys here and the description in
    :class:`ConflictDetail` keeps the two concerns separate while presenting one
    envelope.
    """

    code = ErrorCode.ENTITY_VERSION_CONFLICT
    status_code = 409

    def __init__(
        self,
        *,
        entity_type: type[Versioned],
        entity_id: int,
        expected_version: int,
        detail: ConflictDetail | None = None,
    ) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.expected_version = expected_version
        self.detail = detail
        table = getattr(entity_type, "__tablename__", entity_type.__name__)
        # Identity first, so a caller always learns which entity and which presented
        # version conflicted even before the description; the description keys are
        # merged over it (they never collide with these three).
        details: dict[str, Any] = {
            "entity_type": table,
            "entity_id": entity_id,
            "expected_version": expected_version,
        }
        if detail is not None:
            details.update(detail.as_details())
        super().__init__(
            f"{table} {entity_id} is not at version {expected_version}: a "
            "concurrent modification changed it. Re-read the entity and resubmit "
            "against its current version.",
            details=details,
        )


class VersionedRepository:
    """The only writer permitted to modify a versioned entity (§7.3).

    Stateless, like :class:`~app.db.event_log.EventLog`: reach it through
    :meth:`update` as ``VersionedRepository.update(session, ...)``. Every mutation
    of a versioned entity — from the officer API, the citizen API, the
    Import_Service, or a direct call — goes through this one method, which is what
    lets R29.10's uniformity be checked statically (task 4.5) rather than hoped for.
    """

    @staticmethod
    def update(
        session: Session,
        *,
        entity_type: type[Versioned],
        entity_id: int,
        expected_version: int,
        changes: Mapping[str, Any],
        submitted_prior: Mapping[str, Any],
        actor: Actor,
        occurrence_time: datetime,
        event_type: str,
        expected_stage: str | None = None,
        review_conflict: ReviewConflictSpec | None = None,
    ) -> Versioned:
        """Modify a versioned entity under an optimistic version check (R29.1/29.3).

        Issues the conditional compare-and-set of §7.1 and, only if it matches a
        row, appends one event on the *same* session (§5.2). The order is the point:
        a rejected modification never reaches the append, so no event is written for
        it (R29.5), and the same-session append keeps the state change and the event
        in one transaction (R4.8).

        :param session: the session the caller holds inside its ``unit_of_work()``.
            No connection is opened and nothing is committed here; the block owns the
            transaction.
        :param entity_type: the mapped :class:`~app.db.versioned.Versioned` class to
            modify, e.g. :class:`~app.models.acquisition_case.AcquisitionCase`.
        :param entity_id: the ``id`` of the row to modify.
        :param expected_version: the ``entity_version`` the request believes the row
            is at — the version the officer observed when the entity was opened
            (R29.2). The modification commits only if the row is still at it.
        :param changes: attribute name to new value, applied by the UPDATE. Must not
            contain ``entity_version`` or ``id`` (both repository-managed).
        :param submitted_prior: attribute name to the value the request presented as
            the prior value. Supplies the "from" side of the event's recorded change
            (R4.1), and the "submitted prior" side of a conflict description (R29.4).
        :param actor: who is making the change; recorded on the event. Any
            :class:`~app.db.event_log.Actor` — a ``Principal`` satisfies it.
        :param occurrence_time: when the change happened in the world (R4.3).
        :param event_type: the domain event name to append, e.g.
            ``STAGE_TRANSITIONED`` or ``OWNERSHIP_UPDATED``.
        :param expected_stage: for a Case_Stage transition, the stage the case must
            still be in. When given, ``AND stage_key = :expected_stage`` strengthens
            the predicate so exactly one of two racing transitions out of that stage
            commits (§7.2, R29.7). Omitted for a non-stage modification.
        :param review_conflict: for a double field review, the value and review-state
            column names to include in the rejection description (R29.8). When given,
            a rejection is described by :func:`_describe_field_review_conflict`
            instead of :func:`_describe_conflict`. Omitted for any other modification.
        :returns: the modified entity, freshly loaded from the ``RETURNING`` row with
            its incremented ``entity_version``.
        :raises EntityVersionConflict: if the compare-and-set matches no row — the
            presented version is stale, or the case has left ``expected_stage``. On
            this path nothing is written and no event is appended (R29.5); the raised
            error carries the R29.4 conflict description.
        :raises ValueError: if ``changes`` contains a repository-managed key.
        """
        managed = _REPOSITORY_MANAGED.intersection(changes)
        if managed:
            raise ValueError(
                f"changes may not set repository-managed attribute(s) {sorted(managed)}: "
                "entity_version is incremented by the compare-and-set and id selects "
                "the row."
            )

        version_col = entity_type.entity_version
        # id is not part of the Versioned contract — it is declared on each mapped
        # entity, not on the mixin — so it is read dynamically. Every R29.1 entity
        # carries a bigint id (see app/models/event.py).
        predicates = [getattr(entity_type, "id") == entity_id, version_col == expected_version]
        if expected_stage is not None:
            predicates.append(getattr(entity_type, _STAGE_COLUMN) == expected_stage)

        stmt = (
            update(entity_type)
            .where(*predicates)
            .values(entity_version=version_col + 1, **changes)
            .returning(entity_type)
            # populate_existing so the returned object reflects the RETURNING row
            # even if a stale copy is already in the session's identity map.
            .execution_options(populate_existing=True)
        )
        row = session.execute(stmt).scalars().one_or_none()

        if row is None:
            # R29.5: the compare-and-set matched no row, so nothing was written and
            # there is no event to remove. Raising before the append is what makes
            # "no event for a rejected modification" structural. The description is
            # built here, in the same transaction, so it reads the state the losing
            # request actually lost to (R29.4) rather than a later one.
            if review_conflict is not None:
                detail = _describe_field_review_conflict(
                    session,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    submitted_prior=submitted_prior,
                    spec=review_conflict,
                )
            else:
                detail = _describe_conflict(
                    session,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    submitted_prior=submitted_prior,
                )
            raise EntityVersionConflict(
                entity_type=entity_type,
                entity_id=entity_id,
                expected_version=expected_version,
                detail=detail,
            )

        # Same session, same transaction, and only now that a row committed (§5.2).
        # entity_version_after is the incremented version, so R29.4 can attribute
        # this version to this actor without guessing from timestamps.
        EventLog.append(
            session,
            event_type=event_type,
            entity=row,
            actor=actor,
            changes=_diff(submitted_prior, changes),
            occurrence_time=occurrence_time,
            entity_version_after=row.entity_version,
        )
        return row


def _diff(
    submitted_prior: Mapping[str, Any], changes: Mapping[str, Any]
) -> dict[str, tuple[Any, Any]]:
    """Pair each changed attribute's prior and new value for the event (R4.1).

    :meth:`EventLog.append` records a change as ``attribute -> (prior, new)``. The
    repository is handed the two halves separately — ``changes`` is what the write
    sets, ``submitted_prior`` is what the request presented as the value it was
    replacing — so this joins them on attribute name. An attribute changed without a
    presented prior takes ``None`` on the "from" side.
    """
    return {attribute: (submitted_prior.get(attribute), new) for attribute, new in changes.items()}


def _describe_conflict(
    session: Session,
    *,
    entity_type: type[Versioned],
    entity_id: int,
    submitted_prior: Mapping[str, Any],
) -> ConflictDetail:
    """Build the R29.4 description of a rejected modification.

    Reads the current row (forcing a reload past any stale identity-map copy, so the
    values reported are the ones the losing request lost to), lists every attribute
    the request named whose stored value now differs from the prior it presented, and
    attributes the current version to the actor and occurrence time of the winning
    modification. See :func:`_winning_modification` for how that actor is found.
    """
    current = session.get(entity_type, entity_id, populate_existing=True)
    attributes, current_version = _attribute_conflicts(current, submitted_prior)
    actor_id, occurrence_time = _winning_modification(
        session, entity_type, entity_id, current_version
    )
    return ConflictDetail(
        attributes=attributes,
        current_entity_version=current_version,
        conflicting_actor_id=actor_id,
        conflicting_occurrence_time=occurrence_time,
    )


def _describe_field_review_conflict(
    session: Session,
    *,
    entity_type: type[Versioned],
    entity_id: int,
    submitted_prior: Mapping[str, Any],
    spec: ReviewConflictSpec,
) -> ConflictDetail:
    """Build the R29.8 description of a rejected second field review.

    The same description as :func:`_describe_conflict` plus the winning review's
    recorded state, and with the reviewed-value attribute always present in the diff
    — even where the losing review presented no prior for it — so R29.8's "the value
    the first review recorded" is always surfaced as that attribute's ``current``.
    Parameterised on ``spec`` rather than importing ``extracted_field``: this module
    stays free of a domain model, and the review write path (task 16.x) supplies its
    own column names.
    """
    current = session.get(entity_type, entity_id, populate_existing=True)
    attributes, current_version = _attribute_conflicts(current, submitted_prior)
    attributes = _ensure_attribute_present(
        attributes, current, spec.value_attribute, submitted_prior
    )
    actor_id, occurrence_time = _winning_modification(
        session, entity_type, entity_id, current_version
    )
    review_state = (
        getattr(current, spec.review_state_attribute, None) if current is not None else None
    )
    return ConflictDetail(
        attributes=attributes,
        current_entity_version=current_version,
        conflicting_actor_id=actor_id,
        conflicting_occurrence_time=occurrence_time,
        current_review_state=review_state,
        is_field_review=True,
    )


def _attribute_conflicts(
    current: Any, submitted_prior: Mapping[str, Any]
) -> tuple[tuple[AttrConflict, ...], int | None]:
    """List the attributes whose stored value diverges from the presented prior.

    Returns the divergent attributes and the entity's current version. An attribute
    whose stored value equals the presented prior is *not* a conflict and is omitted:
    R29.4 asks only for the attributes that actually differ. Comparison is on the raw
    stored and presented values, before :func:`_jsonable` shapes them for output, so
    typed values compare correctly. A missing row (the entity is gone) yields no
    attributes and no version.
    """
    if current is None:
        return (), None
    conflicts = [
        AttrConflict(name=name, submitted_prior=prior, current=getattr(current, name, None))
        for name, prior in submitted_prior.items()
        if getattr(current, name, None) != prior
    ]
    return tuple(conflicts), current.entity_version


def _ensure_attribute_present(
    attributes: tuple[AttrConflict, ...],
    current: Any,
    name: str,
    submitted_prior: Mapping[str, Any],
) -> tuple[AttrConflict, ...]:
    """Guarantee ``name`` appears in ``attributes``, appending it if it does not.

    A field review's rejection must always disclose the value the winner recorded
    (R29.8), whether or not it diverges from the loser's presented prior — the loser
    may have presented no prior at all. If :func:`_attribute_conflicts` already
    flagged it as divergent it is left alone; otherwise it is appended reading the
    stored value as ``current``.
    """
    if current is None or any(attr.name == name for attr in attributes):
        return attributes
    return attributes + (
        AttrConflict(
            name=name,
            submitted_prior=submitted_prior.get(name),
            current=getattr(current, name, None),
        ),
    )


def _winning_modification(
    session: Session,
    entity_type: type[Versioned],
    entity_id: int,
    current_version: int | None,
) -> tuple[str | None, datetime | None]:
    """Find the actor and occurrence time of the modification that produced the
    current version (R29.4).

    The winning modification is the event whose ``entity_version_after`` equals the
    row's current version — that is what ``event.entity_version_after`` exists for
    (§7.2): without it, attributing a version to an actor means guessing from
    timestamps. The most recent such event (``id`` descending) is taken, so a version
    reached, corrected and re-reached still names the modification that last set it.
    ``(None, None)`` when no event attributes the current version — a freshly created
    entity that has never been modified through the repository, for instance — which
    is a truthful "no prior modifier" rather than a fabricated one.
    """
    if current_version is None:
        return None, None
    row = session.execute(
        select(Event.actor_id, Event.occurrence_time)
        .where(
            Event.entity_type == entity_type.__tablename__,
            Event.entity_id == entity_id,
            Event.entity_version_after == current_version,
        )
        .order_by(Event.id.desc())
        .limit(1)
    ).first()
    if row is None:
        return None, None
    return row.actor_id, row.occurrence_time
