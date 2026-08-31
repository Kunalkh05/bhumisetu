"""``EventLog.append`` — one event per state change, on the caller's session (§5.2).

What this module is
-------------------

R4.1 requires that every state change appends one ``event`` recording the actor,
the affected entity, the changed attributes with their prior and new values, the
occurrence time and the recording time. This module is the single function that
writes that row. Two things about *how* it writes are load-bearing.

**It never opens a connection.** :meth:`EventLog.append` takes the session the
caller is already holding inside its ``unit_of_work()`` and does its work on that
session, ending in ``session.flush()``. The flush is deliberate: it forces the
insert to hit the database *now*, inside the caller's transaction, so a failure —
a constraint violation, a lost connection — raises here and propagates out of the
enclosing ``unit_of_work()``, which rolls the whole transaction back and takes the
state change with it. That is R4.8's atomicity, and it is the database's, not
ours (see ``app/db/session.py`` for why the session is passed rather than
acquired). Moving the append to a second connection would silently break it, which
is exactly what the boundary guards in ``session.py`` exist to prevent.

**Personal data is stored by reference, never inline (§5.4).** A payload that
would carry ``{"owner_name": "Asha"}`` instead carries ``{"owner_name":
{"$pd": 91827}}`` — a pointer to a ``personal_datum`` row that holds the value and
can later be erased without touching this event. A non-personal attribute stays
inline as ``{"share": {"from": 0.5, "to": 0.34}}``. ``has_pd_refs`` is set true
whenever any ``$pd`` reference is written, so the read-time resolver of task 3.5
can skip the ``personal_datum`` join for the large majority of events (stage
transitions, deadline sweeps, uploads) that carry no personal data at all.

Which value of a personal attribute is externalised, and R4.1's "prior and new"
-------------------------------------------------------------------------------

For a **non-personal** attribute both values are recorded, inline, as
``{"from": old, "to": new}``. For a **personal** attribute the payload carries a
single reference to the **new** value — ``{"$pd": id}`` — not a from/to pair. This
is the shape §5.4 specifies and the shape task 3.5's ``PayloadResolver`` reads: it
replaces that one leaf with ``{"$erased": {...}}`` once the datum is erased.

Recording only the new value by reference does not lose the prior one and does not
leave a personal value inline: the prior value of the attribute is the referent of
the *preceding* event that set it, itself a ``personal_datum`` row, so the whole
history of a personal attribute is a chain of erasable references and no event ever
holds a personal value in its payload. That is what lets R32.13 hold — the log can
stop returning an erased value in *any* payload — while R4.1's audit of prior and
new values is served across the ordered event sequence rather than duplicated into
every row.

Classification, and why an unmapped attribute stays inline for now
------------------------------------------------------------------

Each changed attribute is classified with :func:`app.retention.categories.category_of`
against ``(entity_type, attribute)``. An attribute whose category is one of the
personal-data categories is externalised; everything else stays inline.

``category_of`` raises ``KeyError`` on an attribute that ``CATEGORY_MAP`` does not
name, and ``CATEGORY_MAP`` is deliberately incomplete at this point in the build —
task 3.3 populated only the personal-data entries the event log needs, and task
25.2 completes it to full schema coverage *and* adds the metadata walk that turns a
missing classification into a build failure. Until then an unmapped attribute is
treated as non-personal and recorded inline. That is the only workable behaviour
while the map is partial, and it is safe in the one direction that matters: the
attributes that *are* mapped are exactly the personal ones, so a personal value is
never mistaken for a non-personal one and leaked inline. The reverse mistake — a
genuinely personal column nobody classified — is what 25.2's build failure is for.
The membership pre-check in :func:`_classify` keeps this narrow: it swallows only
"this attribute is not in the map", never a ``KeyError`` raised while resolving a
value-dependent entry (a missing discriminator column is a real error, not an
inline attribute).

The ``value_ciphertext`` encoding seam
--------------------------------------

``personal_datum.value_ciphertext`` is a ``bytea`` and §5.4 calls for it to be
encrypted with a per-category key as defence in depth. That key management is not
wired up yet — there is no key source to encrypt against — so values pass through
:func:`_encode_personal_value`, which serialises them to bytes and stamps
``key_version`` with :data:`KEY_VERSION_UNENCRYPTED`. This is the one choke point a
later task swaps for real encryption; nothing else in the append path needs to
change, because the ``$pd`` indirection that makes erasure possible does not depend
on the bytes being ciphertext. The plain columns on the entity tables hold the same
values in the clear by design (``ownership_record.owner_name`` is ``text``), so the
encoding here is genuinely a defence-in-depth layer and not the primary protection.
"""

from __future__ import annotations

import copy
import enum
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence

from sqlalchemy import BigInteger, any_, bindparam, inspect as sa_inspect, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.personal_datum import PersonalDatum
from app.retention.categories import (
    CATEGORY_MAP,
    PERSONAL_DATA_CATEGORIES,
    category_of,
)

__all__ = [
    "Actor",
    "AsOfMode",
    "ERASED_MARKER_KEY",
    "Entity",
    "EventLog",
    "KEY_VERSION_UNENCRYPTED",
    "PD_REF_KEY",
    "PayloadResolver",
    "ResolvedEvent",
]

#: The payload key that marks a reference into ``personal_datum``. A payload leaf
#: ``{"$pd": 91827}`` means "the value lived here; read it from personal_datum row
#: 91827, or treat it as erased if that row has been". Task 3.5's ``PayloadResolver``
#: is the counterpart that turns it back into a value or an ``{"$erased": ...}``
#: marker. Kept as a named constant so the writer and the reader cannot drift.
PD_REF_KEY = "$pd"

#: The payload key that marks an *erased* referent in a resolved payload. Where the
#: stored payload held ``{"$pd": id}`` and that datum has since been erased, the
#: read-time resolver substitutes ``{"$erased": {"data_category": …, "erased_at": …}}``
#: — everything the log may still disclose about the attribute, and nothing of its
#: value (R32.13). It appears only in a *resolved* payload, never in a stored one, so
#: the writer has no counterpart to it.
ERASED_MARKER_KEY = "$erased"

#: The ``key_version`` stamped on a ``personal_datum`` row whose value is stored
#: encoded but not yet encrypted. §5.4 wants per-category encryption as defence in
#: depth; the key management does not exist yet, so this sentinel records that these
#: bytes are not ciphertext. A later task introduces real key versions starting at 1
#: and rewrites :func:`_encode_personal_value`; the value here stays reserved for
#: "unencrypted" so an old row remains identifiable.
KEY_VERSION_UNENCRYPTED = 0


class Actor(Protocol):
    """Whoever caused a state change, as the event log needs to record it.

    ``Principal`` (task 5.1) satisfies this structurally through its ``kind`` and
    ``id``; typing against a protocol rather than importing ``Principal`` keeps the
    event log independent of the security layer, which is built later and which
    imports *this* module rather than the other way round.
    """

    kind: str
    id: str


class Entity(Protocol):
    """A mapped entity undergoing a state change.

    ``__tablename__`` supplies ``event.entity_type`` so the log is self-describing,
    and ``id`` supplies ``event.entity_id``. Every entity R4.1 names carries a
    ``bigint`` primary key (see ``app/models/event.py``), so ``id`` is an ``int``.
    The table name is declared as a read-only property rather than an annotated
    attribute so the registry guard (``tests/test_metadata_registry.py``), which
    forbids a ``__tablename__`` assignment outside ``app/models/``, is not tripped
    by a structural type; a mapped class's plain ``__tablename__`` string satisfies
    it.
    """

    id: int

    @property
    def __tablename__(self) -> str: ...


@dataclass(frozen=True)
class _Externalised:
    """A personal attribute whose new value must be written to ``personal_datum``."""

    attribute: str
    data_category: str
    value: Any


@dataclass(frozen=True)
class _Inline:
    """A non-personal attribute recorded inline as ``{"from": old, "to": new}``."""

    attribute: str
    old: Any
    new: Any


class AsOfMode(enum.StrEnum):
    """Which of the two as-of predicates a read applies (§5.3).

    The distinction is load-bearing, not a convenience. R4.4 permits an event to be
    appended with an occurrence time *earlier* than one already stored — an officer
    recording a notice served last week. R17.2 forbids a feature row from using an
    attribute whose value *first became knowable* after T. A read filtering on
    occurrence time alone satisfies the first and silently violates the second: a
    notice that occurred on 1 March but was recorded on 20 March would fold into a
    feature row for 5 March, and the model would train on information nobody held yet.
    Only a both-times filter reconciles them, which is why there are two modes and not
    one.

    ``OCCURRED_BY`` — ``occurrence_time <= T``. The world's facts as of T, regardless
        of when the platform learned them. The citizen timeline (R25.4), the officer
        timeline (R23.4) and label evaluation read this way, because a late-recorded
        fact does not change whether the thing actually happened by T.
    ``KNOWABLE_AT`` — ``occurrence_time <= T AND recording_time <= T``. Only what was
        both true *and* known by T. The Feature_Builder reads this way (R17.2), so an
        inference row at T equals the training row for the same T.

    A :class:`~enum.StrEnum`, so a member *is* its wire string: it can be written
    verbatim to a consumer that must record which predicate produced it —
    ``ml_feature_row.as_of_mode`` is ``text`` (§14) — and compared against a stored
    string without conversion. Every :class:`ResolvedEvent` carries it, so a row
    lifted out of a result can never be misread as the other mode.
    """

    OCCURRED_BY = "OCCURRED_BY"
    KNOWABLE_AT = "KNOWABLE_AT"


@dataclass(frozen=True)
class ResolvedEvent:
    """One event as a reader sees it: the stored columns, the payload with personal
    references resolved, and the as-of mode that produced it.

    Distinct from :class:`~app.models.event.Event` for two reasons. The mapped
    object's ``payload`` is the stored jsonb, byte-identical to insert time and still
    holding ``{"$pd": id}`` references; this object's ``payload`` has those resolved
    to values or to ``{"$erased": …}`` markers, without the stored row ever being
    touched (§5.4). And the mapped object is read-only and must not be handed to a
    caller who might mutate it, whereas this is a frozen snapshot safe to pass around
    and to store.

    ``mode`` rides on every row deliberately (§5.3): a :class:`ResolvedEvent` pulled
    out of a result and compared or persisted elsewhere still records whether it was
    read ``OCCURRED_BY`` or ``KNOWABLE_AT``, so it can never be mistaken for the other.
    """

    id: int
    event_type: str
    entity_type: str
    entity_id: int
    case_id: int | None
    actor_type: str
    actor_id: str
    occurrence_time: datetime
    recording_time: datetime
    payload: Mapping[str, Any]
    has_pd_refs: bool
    entity_version_after: int | None
    provenance: str
    import_batch_id: int | None
    corrects_event_id: int | None
    mode: AsOfMode


class EventLog:
    """The one door to the append-only log. :meth:`append` writes one event per state
    change (task 3.4); :meth:`events` reads an entity's history as of a timestamp
    under one of two as-of modes (task 3.5), resolving personal references through
    :class:`PayloadResolver`. Compensating appends (task 3.6) join them here, all
    sharing this namespace so a caller reaches the log through one name."""

    @staticmethod
    def append(
        session: Session,
        *,
        event_type: str,
        entity: Entity,
        actor: Actor,
        changes: Mapping[str, tuple[Any, Any]],
        occurrence_time: datetime,
        entity_version_after: int | None = None,
        **kw: Any,
    ) -> Event:
        """Append one event for one state change, on the caller's transaction (R4.1).

        :param session: the session the caller already holds inside its
            ``unit_of_work()``. No connection is opened here; the append lives in the
            caller's transaction so a failure abandons the state change (R4.8, §5.2).
        :param event_type: the domain event name, e.g. ``OWNERSHIP_UPDATED``.
        :param entity: the mapped entity that changed; supplies ``entity_type`` and
            ``entity_id``.
        :param actor: who caused it; supplies ``actor_type`` and ``actor_id``.
        :param changes: a mapping of attribute name to ``(prior, new)``. Personal
            attributes are externalised to ``personal_datum`` and referenced;
            non-personal attributes are recorded inline. Inline values must be
            JSON-serialisable, since the payload is stored as ``jsonb``.
        :param occurrence_time: when the change happened in the world. May precede an
            existing event for the same entity (R4.4); the distinct ``recording_time``
            is filled by the column default.
        :param entity_version_after: the entity's version after the change, so a
            version can be attributed to an actor (R29.4). ``VersionedRepository``
            (task 4.2) passes it; a plain create leaves it ``None``.
        :param kw: passed through to :class:`~app.models.event.Event` for the
            columns a caller may need to set explicitly — ``provenance``,
            ``import_batch_id``, ``corrects_event_id``, ``recording_time``, and
            ``case_id`` to override the derived value.
        :returns: the flushed :class:`~app.models.event.Event`.
        """
        payload, has_pd_refs = _externalise_personal_data(session, entity, changes)

        # case_id is derived from the entity for the citizen/officer timelines, but a
        # caller may override it: an ownership record's owning case is reached through
        # its parcel, a relationship that does not exist until task 8.x, so the write
        # path passes case_id explicitly until _case_of can derive it.
        case_id = kw.pop("case_id") if "case_id" in kw else _case_of(entity)

        event = Event(
            event_type=event_type,
            entity_type=entity.__tablename__,
            entity_id=entity.id,
            case_id=case_id,
            actor_type=actor.kind,
            actor_id=actor.id,
            occurrence_time=occurrence_time,
            payload=payload,
            has_pd_refs=has_pd_refs,
            entity_version_after=entity_version_after,
            **kw,
        )
        session.add(event)
        # Surface a failure now, inside the caller's transaction, so it can be rolled
        # back with the state change rather than after the block has committed.
        session.flush()
        return event

    @staticmethod
    def events(
        session: Session,
        entity: Entity,
        *,
        as_of: datetime,
        mode: AsOfMode,
    ) -> list[ResolvedEvent]:
        """Return one entity's history as of ``as_of`` under ``mode`` (R4.5, R4.7).

        The read counterpart to :meth:`append`: the ordered set of events for
        ``entity`` up to ``as_of``, with the personal references in each payload
        resolved (§5.4). It is the single source both the citizen timeline and the
        Feature_Builder read through (R4.7), which is why ``mode`` is required rather
        than defaulted — the two readers need different predicates and a returned row
        must record which it got.

        :param session: the caller's session. A read, so nothing is flushed; events
            already appended in this transaction are visible, since they live in the
            session's identity map.
        :param entity: the entity whose history is wanted; ``__tablename__`` and
            ``id`` select it, matching :meth:`append`.
        :param as_of: the timestamp T the history is reconstructed as of.
        :param mode: which as-of predicate to apply (:class:`AsOfMode`); a bare string
            is accepted and normalised. Recorded on every returned row.
        :returns: the events with ``occurrence_time <= T`` — and, for
            :attr:`AsOfMode.KNOWABLE_AT`, ``recording_time <= T`` as well — ordered by
            ``(occurrence_time, id)``, the total deterministic order R17.5 depends on,
            each with its payload resolved and ``mode`` stamped on it.
        """
        mode = AsOfMode(mode)
        stmt = select(Event).where(
            Event.entity_type == entity.__tablename__,
            Event.entity_id == entity.id,
            Event.occurrence_time <= as_of,
        )
        if mode == AsOfMode.KNOWABLE_AT:
            # R17.2: exclude an attribute not yet knowable at T, even where its
            # occurrence time precedes T because it was appended late (R4.4).
            stmt = stmt.where(Event.recording_time <= as_of)
        # The (occurrence_time, id) order matches the event_entity_asof index, so this
        # is an index scan rather than a sort, and the id tiebreak makes it total.
        stmt = stmt.order_by(Event.occurrence_time, Event.id)

        rows = list(session.execute(stmt).scalars())
        payloads = PayloadResolver(session).resolve(rows)
        return [
            _to_resolved_event(row, payload, mode)
            for row, payload in zip(rows, payloads)
        ]

    @staticmethod
    def append_correction(
        session: Session,
        *,
        corrects_event_id: int,
        event_type: str,
        entity: Entity,
        actor: Actor,
        changes: Mapping[str, tuple[Any, Any]],
        occurrence_time: datetime,
        entity_version_after: int | None = None,
        **kw: Any,
    ) -> Event:
        """Append a compensating event that references an erroneous one (R4.6).

        The log is append-only: R4.2 forbids updating or deleting a stored event, and
        the revoked ``UPDATE, DELETE`` grant of task 3.1 enforces that in the database.
        So a correction is never an edit of the erroneous row — it is a *new* event
        carrying ``corrects_event_id`` that points at the erroneous one, and the
        erroneous row is left exactly as it was stored. That is the whole of R4.6: the
        history gains a compensating entry rather than losing the mistake, and the
        ordering, actor, and both timestamps of the erroneous event stay untouched.

        Deliberately a thin specialisation of :meth:`append`. A correction is an
        ordinary state-change event in every respect — it records an actor, an entity,
        changed attributes with their prior and new values, an occurrence time and a
        distinct recording time, and it externalises personal data by reference exactly
        as any other append does (§5.4) — plus the one reference that makes it a
        correction. Routing it through :meth:`append` is what keeps it from drifting
        from that path: the same atomicity (the flush inside the caller's transaction,
        R4.8), the same externalisation, the same ``(occurrence_time, id)`` ordering.

        Two callers share it. An R4.6 correction supplies the corrected entity and the
        attributes whose recorded history was wrong. The erasure path (task 25.3)
        appends its single ``PERSONAL_DATA_ERASED`` event this way, so Property 83's
        "the erasure is represented solely by one newly appended compensating Event"
        holds by construction rather than by convention.

        :param corrects_event_id: the id of the erroneous event this one compensates.
            It must identify a stored event — one already committed, or one appended
            earlier in this same transaction, since :meth:`append` flushes and the row
            is then visible on the session. An id that resolves to no event raises
            :class:`LookupError` here, rather than surfacing as an opaque foreign-key
            violation at commit; the ``corrects_event_id`` column's ``ondelete
            RESTRICT`` foreign key to ``event(id)`` is the durable guarantee and this
            check is the legible error. The erroneous event is only read, never
            modified.
        :param event_type: the correction's own event name, e.g. ``OWNERSHIP_CORRECTED``
            or ``PERSONAL_DATA_ERASED``.
        :param entity: the entity the correction concerns; as in :meth:`append` it
            supplies ``entity_type`` and ``entity_id``.
        :param actor: who recorded the correction — an officer for an R4.6 correction,
            the scheduler for an erasure.
        :param changes: the corrected attributes as ``{attr: (prior, new)}``, recorded
            and externalised exactly as :meth:`append` records any change.
        :param occurrence_time: when the correction happened. Typically later than the
            erroneous event but not required to be — R4.4 permits any ordering, and the
            distinct ``recording_time`` is filled by the column default.
        :param entity_version_after: forwarded to :meth:`append` unchanged.
        :param kw: forwarded to :meth:`append` (``provenance``, ``case_id``,
            ``recording_time``, …). ``corrects_event_id`` is set here, so it must not be
            passed again through ``kw``.
        :returns: the flushed compensating :class:`~app.models.event.Event`, whose
            ``corrects_event_id`` is ``corrects_event_id``.
        """
        if not _event_exists(session, corrects_event_id):
            raise LookupError(
                f"cannot correct event {corrects_event_id}: no such event is stored. "
                "A compensating event must reference an existing erroneous event (R4.6)."
            )
        return EventLog.append(
            session,
            event_type=event_type,
            entity=entity,
            actor=actor,
            changes=changes,
            occurrence_time=occurrence_time,
            entity_version_after=entity_version_after,
            corrects_event_id=corrects_event_id,
            **kw,
        )


def _event_exists(session: Session, event_id: int) -> bool:
    """True when ``event_id`` identifies a stored event.

    A read — it never mutates the log — that sees a row appended earlier in the same
    transaction as well as a committed one, since :meth:`EventLog.append` flushes.
    :meth:`EventLog.append_correction` uses it to turn a dangling ``corrects_event_id``
    into a clear :class:`LookupError` at the call site rather than a foreign-key
    violation at commit.
    """
    return session.execute(
        select(select(Event.id).where(Event.id == event_id).exists())
    ).scalar_one()


def _externalise_personal_data(
    session: Session,
    entity: Entity,
    changes: Mapping[str, tuple[Any, Any]],
) -> tuple[dict[str, Any], bool]:
    """Build the event payload, moving personal-data values out to ``personal_datum``.

    Returns the payload and whether any ``$pd`` reference was written (the value for
    ``event.has_pd_refs``). Personal attributes each become one ``personal_datum``
    row and a ``{"$pd": id}`` leaf; non-personal attributes stay inline as
    ``{"from": old, "to": new}``. See the module docstring for why only the new value
    of a personal attribute is externalised.
    """
    plan = _plan_externalisation(entity.__tablename__, changes, _row_view(entity))

    payload: dict[str, Any] = {}
    pending: list[tuple[str, PersonalDatum]] = []
    for item in plan:
        if isinstance(item, _Inline):
            payload[item.attribute] = {"from": item.old, "to": item.new}
            continue
        ciphertext, key_version = _encode_personal_value(item.value)
        datum = PersonalDatum(
            data_category=item.data_category,
            entity_type=entity.__tablename__,
            entity_id=entity.id,
            attribute_name=item.attribute,
            value_ciphertext=ciphertext,
            key_version=key_version,
        )
        session.add(datum)
        pending.append((item.attribute, datum))

    if pending:
        # One flush assigns every personal_datum id, so the references below point at
        # durable rows in the same transaction as the event that carries them.
        session.flush()
        for attribute, datum in pending:
            payload[attribute] = {PD_REF_KEY: datum.id}

    return payload, bool(pending)


def _plan_externalisation(
    entity_type: str,
    changes: Mapping[str, tuple[Any, Any]],
    row: Mapping[str, Any],
) -> list[_Externalised | _Inline]:
    """Decide, per changed attribute, whether it is externalised or recorded inline.

    Pure: no session, no database. Separated from :func:`_externalise_personal_data`
    so the classification decision — the part that is easy to get wrong and cheap to
    test — can be exercised without a database. ``row`` supplies the other column
    values a value-dependent classification (a ``Discriminated`` entry) resolves
    against.
    """
    plan: list[_Externalised | _Inline] = []
    for attribute, (old, new) in changes.items():
        category = _classify(entity_type, attribute, row)
        if category in PERSONAL_DATA_CATEGORIES:
            plan.append(_Externalised(attribute=attribute, data_category=category, value=new))
        else:
            plan.append(_Inline(attribute=attribute, old=old, new=new))
    return plan


def _classify(entity_type: str, column: str, row: Mapping[str, Any]) -> str | None:
    """Return the data category of ``entity_type.column``, or ``None`` if unmapped.

    The membership pre-check is deliberate. ``category_of`` raises ``KeyError`` both
    for an attribute that is not in ``CATEGORY_MAP`` *and* — for a value-dependent
    entry — if the discriminator column is missing from ``row``. Only the first is an
    "unmapped, treat as inline" case; the second is a real error that must not be
    silently turned into an inline attribute. Checking the map key first separates
    the two: a genuine resolution error still propagates.
    """
    if (entity_type, column) not in CATEGORY_MAP:
        return None
    return category_of(entity_type, column, row)


def _encode_personal_value(value: Any) -> tuple[bytes, int]:
    """Encode a personal value to the bytes stored in ``value_ciphertext``.

    The single seam where per-category encryption (§5.4) will plug in. Today it
    JSON-encodes the value — ``ensure_ascii=False`` so Devanagari names survive as
    UTF-8 rather than escapes (R27.5), ``default=str`` so a stray non-JSON value does
    not abort an append — and stamps :data:`KEY_VERSION_UNENCRYPTED`. A ``None`` value
    encodes to ``b"null"`` rather than a NULL column, so a present-but-null datum
    stays distinguishable from an erased one, which is marked by ``erased_at`` alone.
    """
    encoded = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
    return encoded, KEY_VERSION_UNENCRYPTED


def _row_view(entity: Any) -> Mapping[str, Any]:
    """A read-only view of the entity's column values, for value-dependent classes.

    ``category_of`` needs the sibling column values to resolve a ``Discriminated`` or
    ``Reference`` entry (for example ``extracted_field.extracted_value``'s category
    depends on ``field_name``). A mapped instance is read through its mapper; a plain
    stand-in through its ``__dict__``. The common case — a change to a plainly
    classified attribute — never touches ``row`` at all.
    """
    inspected = sa_inspect(entity, raiseerr=False)
    if inspected is not None and hasattr(inspected, "mapper"):
        return {attr.key: getattr(entity, attr.key) for attr in inspected.mapper.column_attrs}
    if hasattr(entity, "__dict__"):
        return dict(vars(entity))
    return {}


def _case_of(entity: Any) -> int | None:
    """Derive ``event.case_id`` from the entity, for the timeline reads (R23.4, R25.4).

    An ``acquisition_case`` is its own case; anything carrying a denormalised
    ``case_id`` uses it; everything else — a ``policy_config`` change, an entity whose
    case is reachable only through a relationship not yet declared — is ``None`` here
    and set explicitly by the caller. Later tasks that add those relationships extend
    this, but the append path never has to guess.
    """
    if getattr(entity, "__tablename__", None) == "acquisition_case":
        return entity.id
    return getattr(entity, "case_id", None)


# ===========================================================================
# Read-time resolution of personal references (§5.4, R32.13)
# ===========================================================================


@dataclass(frozen=True)
class _ResolvedDatum:
    """The ``personal_datum`` columns the resolver needs to produce either the value
    or the ``{"$erased": …}`` marker without a second query."""

    value_ciphertext: bytes | None
    key_version: int
    erased_at: datetime | None
    data_category: str


class PayloadResolver:
    """Turns stored event payloads into the payloads a reader sees (§5.4).

    A stored payload holds personal-data values by reference — ``{"$pd": 91827}`` —
    never inline. This resolver replaces each reference with either the value, read
    from ``personal_datum``, or, once that datum is erased, the marker
    ``{"$erased": {"data_category": …, "erased_at": …}}``. It never touches an
    ``event`` row, which is what lets R32.13's "stop returning the value" and R4.2's
    "the log is append-only" hold at the same time.

    Two cost decisions, both from §5.4:

    * **Rows without personal references skip the join entirely.** ``has_pd_refs`` is
      false for the large majority of events — stage transitions, deadline sweeps,
      uploads — and those payloads are returned without collecting an id or reading
      ``personal_datum`` at all.
    * **One fetch per batch, not per event.** Every ``$pd`` id across the whole batch
      is gathered and fetched in a single ``= ANY(…)``, so resolving a hundred-event
      timeline that references personal data is two queries, not a hundred and one.

    Statelessly usable: construct one around the caller's session and call
    :meth:`resolve`. It holds no state between calls.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve(self, events: Sequence[Event]) -> list[dict[str, Any]]:
        """Return the resolved payload for each event, in the order given.

        Each returned payload is an independent structure; the mapped ``Event.payload``
        is never mutated, so the stored row stays byte-identical to insert time.
        """
        ids: set[int] = set()
        for event in events:
            if event.has_pd_refs:
                _collect_pd_ids(event.payload, ids)

        data = self._fetch(ids) if ids else {}

        resolved: list[dict[str, Any]] = []
        for event in events:
            if not event.has_pd_refs:
                # Nothing to resolve. Hand back an independent copy so a caller that
                # mutates it cannot reach into the mapped row's in-memory payload.
                resolved.append(copy.deepcopy(event.payload))
            else:
                resolved.append(_resolve_payload_node(event.payload, data))
        return resolved

    def _fetch(self, ids: set[int]) -> dict[int, _ResolvedDatum]:
        """Fetch every referenced datum in one ``= ANY(…)`` (§5.4).

        A single bound array parameter, not an ``IN`` list whose length varies per
        call — one query plan regardless of how many references the batch holds.
        """
        stmt = select(
            PersonalDatum.id,
            PersonalDatum.value_ciphertext,
            PersonalDatum.erased_at,
            PersonalDatum.data_category,
            PersonalDatum.key_version,
        ).where(PersonalDatum.id == any_(bindparam("pd_ids", type_=ARRAY(BigInteger))))
        rows = self._session.execute(stmt, {"pd_ids": list(ids)}).all()
        return {
            row.id: _ResolvedDatum(
                value_ciphertext=(
                    bytes(row.value_ciphertext)
                    if row.value_ciphertext is not None
                    else None
                ),
                key_version=row.key_version,
                erased_at=row.erased_at,
                data_category=row.data_category,
            )
            for row in rows
        }


def _as_pd_ref(node: dict[str, Any]) -> int | None:
    """Return the referenced id if ``node`` is exactly a ``{"$pd": id}`` leaf.

    The writer produces this shape and only this shape for a personal attribute: a
    one-key dict whose key is :data:`PD_REF_KEY` and whose value is a
    ``personal_datum`` id. A ``bool`` is rejected explicitly — it is an ``int``
    subclass in Python, and a payload carrying ``{"$pd": true}`` is malformed, not a
    reference to row 1.
    """
    if len(node) == 1 and PD_REF_KEY in node:
        ref = node[PD_REF_KEY]
        if isinstance(ref, int) and not isinstance(ref, bool):
            return ref
    return None


def _collect_pd_ids(node: Any, ids: set[int]) -> None:
    """Gather every ``$pd`` id reachable in ``node`` into ``ids``.

    Recursive over dicts and lists, so a future event type with a nested payload is
    resolved rather than leaking an unresolved reference; the current writer keeps
    references one level deep, which this handles as the simple case. A ``$pd`` leaf
    is not descended into — its single value is an id, not a container.
    """
    if isinstance(node, dict):
        if _as_pd_ref(node) is not None:
            ids.add(node[PD_REF_KEY])
            return
        for value in node.values():
            _collect_pd_ids(value, ids)
    elif isinstance(node, list):
        for value in node:
            _collect_pd_ids(value, ids)


def _resolve_payload_node(node: Any, data: Mapping[int, _ResolvedDatum]) -> Any:
    """Return ``node`` with every ``$pd`` leaf replaced, as a fresh structure.

    A reference to a live datum resolves to its value; a reference to an erased datum
    resolves to the ``{"$erased": …}`` marker (§5.4, R32.13). Every container is
    rebuilt rather than mutated, so the stored payload is left untouched.
    """
    if isinstance(node, dict):
        ref = _as_pd_ref(node)
        if ref is not None:
            return _resolve_reference(ref, data)
        return {key: _resolve_payload_node(value, data) for key, value in node.items()}
    if isinstance(node, list):
        return [_resolve_payload_node(value, data) for value in node]
    return node


def _resolve_reference(ref: int, data: Mapping[int, _ResolvedDatum]) -> Any:
    """Resolve one ``$pd`` id to a value or an ``{"$erased": …}`` marker.

    A dangling reference — an id with no ``personal_datum`` row — raises rather than
    resolving to nothing: it means the log and its referents have diverged, which is
    corruption, not a normal read. The row is permanent by design (the trigger and
    the revoked ``DELETE`` grant of task 3.2 make a ``personal_datum`` row
    undeletable), so a missing one is a real inconsistency.

    For an erased datum only the ``data_category`` and ``erased_at`` are disclosed —
    the two columns erasure deliberately preserves — and never the value, which is
    what R32.13 requires the log to stop returning.
    """
    datum = data.get(ref)
    if datum is None:
        raise LookupError(
            f"event payload references personal_datum {ref}, which does not exist; "
            "the event log and its personal_datum referents have diverged"
        )
    if datum.erased_at is not None:
        return {
            ERASED_MARKER_KEY: {
                "data_category": datum.data_category,
                "erased_at": datum.erased_at,
            }
        }
    return _decode_personal_value(datum.value_ciphertext, datum.key_version)


def _decode_personal_value(ciphertext: bytes | None, key_version: int) -> Any:
    """Invert :func:`_encode_personal_value` for a non-erased datum.

    The read-side counterpart to the write-time encoding seam. Today the bytes are
    JSON, not ciphertext, and ``key_version`` is :data:`KEY_VERSION_UNENCRYPTED`; when
    per-category encryption (§5.4) is wired up, this is where decryption keyed on
    ``key_version`` plugs in, and an unknown version fails loudly rather than handing
    back wrong bytes.

    A non-erased datum always carries a value — the ciphertext is NULL only once
    erased, which the caller has already handled — so a NULL reaching here is a real
    inconsistency, not a present-but-null value (``None`` was encoded as ``b"null"``).
    """
    if key_version != KEY_VERSION_UNENCRYPTED:
        raise NotImplementedError(
            f"cannot decode personal_datum with key_version {key_version}: "
            "per-category decryption is not wired up yet (§5.4)"
        )
    if ciphertext is None:
        raise ValueError(
            "a non-erased personal_datum has a NULL value_ciphertext; the "
            "single-transition trigger should make this state unreachable"
        )
    return json.loads(bytes(ciphertext).decode("utf-8"))


def _to_resolved_event(
    event: Event, payload: dict[str, Any], mode: AsOfMode
) -> ResolvedEvent:
    """Project a stored :class:`Event` and its resolved payload into a frozen row."""
    return ResolvedEvent(
        id=event.id,
        event_type=event.event_type,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        case_id=event.case_id,
        actor_type=event.actor_type,
        actor_id=event.actor_id,
        occurrence_time=event.occurrence_time,
        recording_time=event.recording_time,
        payload=payload,
        has_pd_refs=event.has_pd_refs,
        entity_version_after=event.entity_version_after,
        provenance=event.provenance,
        import_batch_id=event.import_batch_id,
        corrects_event_id=event.corrects_event_id,
        mode=mode,
    )
