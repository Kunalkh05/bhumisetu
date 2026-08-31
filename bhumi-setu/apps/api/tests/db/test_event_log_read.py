"""Event log read paths and ``$erased`` resolution (task 3.5).

Requirements R4.5, R4.7, R32.13; Correctness Properties 9 and 84.

Two layers, as in the append tests
----------------------------------

The resolver's decisions — which leaves are ``$pd`` references, what an erased datum
becomes, that a row without references is never joined — are pure and are exercised
without a database, since :class:`~app.db.event_log.PayloadResolver` reads only
``has_pd_refs`` and ``payload`` off each row and only touches the session when there
is an id to fetch. Those tests run everywhere.

The read path itself (:meth:`EventLog.events`) selects from ``event``, joins
``personal_datum``, and depends on ``timestamptz`` comparison and ``jsonb`` payloads
that SQLite cannot stand in for, so it is exercised against a real database through
the ``db_connection`` fixture, which skips cleanly when no PostgreSQL is reachable.
Properties 9 and 84 are database-backed.

Isolation across Hypothesis examples
-------------------------------------

``db_connection`` is function-scoped and shared across every example of a property
test. Each example runs on its own savepoint-joined session drawing a fresh
``entity_id``, and closes the session in a ``finally`` so its writes roll back to the
savepoint before the next example. ``events()`` filters by entity, so even without
the rollback one example could not see another's rows.
"""

from __future__ import annotations

import json
import string
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.db.event_log import (
    ERASED_MARKER_KEY,
    PD_REF_KEY,
    AsOfMode,
    EventLog,
    PayloadResolver,
    ResolvedEvent,
    _as_pd_ref,
    _collect_pd_ids,
    _decode_personal_value,
    _resolve_payload_node,
    _resolve_reference,
    _ResolvedDatum,
)
from app.models.event import ActorType
from app.retention.categories import OWNER_CONTACT, OWNER_IDENTITY

UTC = timezone.utc
ERASED_AT = datetime(2031, 2, 1, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Stand-ins, mirroring the append tests
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Actor:
    kind: str
    id: str


class _StandInEntity:
    """A table name and an id — all ``append`` and ``events`` read off an entity."""

    def __init__(self, table: str, id: int, **attributes: Any) -> None:
        self.__tablename__ = table
        self.id = id
        for name, value in attributes.items():
            setattr(self, name, value)


@dataclass
class _FakeRow:
    """The two attributes :meth:`PayloadResolver.resolve` reads off an event row."""

    has_pd_refs: bool
    payload: dict[str, Any]


OFFICER = _Actor(kind=ActorType.OFFICER, id="officer:412")


# ===========================================================================
# Pure resolution logic — no database
# ===========================================================================


class TestPdReferenceDetection:
    def test_a_single_key_pd_dict_is_a_reference(self) -> None:
        assert _as_pd_ref({PD_REF_KEY: 91827}) == 91827

    def test_an_inline_change_is_not_a_reference(self) -> None:
        assert _as_pd_ref({"from": 1, "to": 2}) is None

    def test_a_pd_key_alongside_others_is_not_a_reference(self) -> None:
        """The writer only ever emits ``{"$pd": id}`` alone; a two-key dict is an
        ordinary payload node to walk into, not a reference to resolve."""
        assert _as_pd_ref({PD_REF_KEY: 1, "extra": 2}) is None

    def test_a_bool_is_not_an_id(self) -> None:
        """``bool`` is an ``int`` subclass; ``{"$pd": true}`` is malformed, not row 1."""
        assert _as_pd_ref({PD_REF_KEY: True}) is None
        assert _as_pd_ref({PD_REF_KEY: False}) is None

    def test_an_empty_dict_is_not_a_reference(self) -> None:
        assert _as_pd_ref({}) is None


class TestCollectPdIds:
    def test_flat_references_are_collected(self) -> None:
        ids: set[int] = set()
        _collect_pd_ids(
            {"a": {PD_REF_KEY: 1}, "b": {"from": 0, "to": 1}, "c": {PD_REF_KEY: 2}}, ids
        )
        assert ids == {1, 2}

    def test_nested_references_are_collected(self) -> None:
        """Recursive over dicts and lists, so a future nested payload cannot leak an
        unresolved reference."""
        ids: set[int] = set()
        _collect_pd_ids({"outer": [{PD_REF_KEY: 3}, {"k": {PD_REF_KEY: 4}}]}, ids)
        assert ids == {3, 4}

    def test_no_references_collects_nothing(self) -> None:
        ids: set[int] = set()
        _collect_pd_ids({"stage_key": {"from": "SIA", "to": "PN"}}, ids)
        assert ids == set()


class TestResolveReference:
    def test_a_live_datum_resolves_to_its_value(self) -> None:
        data = {
            1: _ResolvedDatum(
                value_ciphertext=b'"Asha Devi"',
                key_version=0,
                erased_at=None,
                data_category=OWNER_IDENTITY,
            )
        }
        assert _resolve_reference(1, data) == "Asha Devi"

    def test_an_erased_datum_resolves_to_the_marker(self) -> None:
        data = {
            2: _ResolvedDatum(
                value_ciphertext=None,
                key_version=0,
                erased_at=ERASED_AT,
                data_category=OWNER_CONTACT,
            )
        }
        assert _resolve_reference(2, data) == {
            ERASED_MARKER_KEY: {
                "data_category": OWNER_CONTACT,
                "erased_at": ERASED_AT,
            }
        }

    def test_a_dangling_reference_raises(self) -> None:
        """An id with no row means the log and its referents diverged — corruption,
        not a value of ``None``."""
        with pytest.raises(LookupError):
            _resolve_reference(404, {})


class TestDecodePersonalValue:
    def test_a_value_round_trips(self) -> None:
        assert _decode_personal_value(b'"Asha Devi"', 0) == "Asha Devi"
        assert _decode_personal_value(b"null", 0) is None
        assert _decode_personal_value(b'"\\u0928\\u0930\\u0947\\u0936"', 0) == "नरेश"

    def test_devanagari_utf8_bytes_round_trip(self) -> None:
        assert _decode_personal_value("नरेश".encode("utf-8").join([b'"', b'"']), 0) == "नरेश"

    def test_an_unknown_key_version_fails_loudly(self) -> None:
        """The seam where real decryption plugs in; an unknown version must not hand
        back wrong bytes."""
        with pytest.raises(NotImplementedError):
            _decode_personal_value(b'"x"', 1)

    def test_a_null_ciphertext_on_a_non_erased_datum_is_an_error(self) -> None:
        with pytest.raises(ValueError):
            _decode_personal_value(None, 0)


class TestResolvePayloadNode:
    def test_inline_nodes_pass_through(self) -> None:
        node = {"share": {"from": 0.5, "to": 0.34}}
        assert _resolve_payload_node(node, {}) == node

    def test_a_reference_is_replaced_in_place_in_the_tree(self) -> None:
        data = {
            7: _ResolvedDatum(
                value_ciphertext=b'"Asha"', key_version=0, erased_at=None,
                data_category=OWNER_IDENTITY,
            )
        }
        node = {"owner_name": {PD_REF_KEY: 7}, "share": {"from": 1, "to": 2}}
        assert _resolve_payload_node(node, data) == {
            "owner_name": "Asha",
            "share": {"from": 1, "to": 2},
        }


class TestResolverSkipsRowsWithoutReferences:
    def test_a_row_without_pd_refs_never_touches_the_session(self) -> None:
        """The has_pd_refs=false fast path. Session is ``None`` here, so any attempt
        to fetch would raise; the payload is returned untouched, proving the join is
        skipped entirely (§5.4)."""
        payload = {"stage_key": {"from": "SIA", "to": "PN"}}
        [out] = PayloadResolver(None).resolve([_FakeRow(has_pd_refs=False, payload=payload)])
        assert out == payload

    def test_the_flag_is_authoritative_even_over_a_pd_shaped_leaf(self) -> None:
        """A row flagged false is returned verbatim even if a leaf looks like a
        reference: the writer sets the flag, and the resolver trusts it and skips."""
        payload = {"owner_name": {PD_REF_KEY: 123}}
        [out] = PayloadResolver(None).resolve([_FakeRow(has_pd_refs=False, payload=payload)])
        assert out == payload

    def test_the_returned_payload_is_an_independent_copy(self) -> None:
        payload = {"a": {"from": 1, "to": 2}}
        [out] = PayloadResolver(None).resolve([_FakeRow(has_pd_refs=False, payload=payload)])
        out["a"]["to"] = 999
        assert payload["a"]["to"] == 2, "the caller's mutation must not reach the row"


# ===========================================================================
# Database-backed read path (skips without PostgreSQL)
# ===========================================================================


@pytest.fixture
def session(db_connection: Connection) -> Session:
    return Session(bind=db_connection, join_transaction_mode="create_savepoint")


def _append(session: Session, entity: _StandInEntity, *, occurrence_time: datetime,
            changes: dict[str, tuple[Any, Any]], event_type: str = "STATE_CHANGED",
            **kw: Any):
    return EventLog.append(
        session,
        event_type=event_type,
        entity=entity,
        actor=OFFICER,
        changes=changes,
        occurrence_time=occurrence_time,
        **kw,
    )


class TestOccurredByReadPath:
    def test_returns_events_up_to_t_ordered_by_occurrence_then_id(self, session: Session) -> None:
        entity = _StandInEntity("acquisition_case", 10001)
        t1 = datetime(2020, 1, 1, tzinfo=UTC)
        t2 = datetime(2020, 2, 1, tzinfo=UTC)
        t3 = datetime(2020, 3, 1, tzinfo=UTC)
        e1 = _append(session, entity, occurrence_time=t1, changes={"note": (None, "1")})
        e2 = _append(session, entity, occurrence_time=t2, changes={"note": (None, "2")})
        e3 = _append(session, entity, occurrence_time=t3, changes={"note": (None, "3")})

        got = EventLog.events(session, entity, as_of=t2, mode=AsOfMode.OCCURRED_BY)
        assert [r.id for r in got] == [e1.id, e2.id], "T excludes the event after it"

        got_all = EventLog.events(session, entity, as_of=t3, mode=AsOfMode.OCCURRED_BY)
        assert [r.id for r in got_all] == [e1.id, e2.id, e3.id]

    def test_equal_occurrence_times_break_ties_by_id(self, session: Session) -> None:
        """R17.5's determinism rests on the ``id`` tiebreak: same-instant events fold
        in a total, stable order rather than the planner's whim."""
        entity = _StandInEntity("acquisition_case", 10002)
        t = datetime(2020, 1, 1, tzinfo=UTC)
        ids = [
            _append(session, entity, occurrence_time=t, changes={"note": (None, str(i))}).id
            for i in range(5)
        ]
        got = EventLog.events(session, entity, as_of=t, mode=AsOfMode.OCCURRED_BY)
        assert [r.id for r in got] == sorted(ids)

    def test_the_mode_is_recorded_on_every_row(self, session: Session) -> None:
        entity = _StandInEntity("acquisition_case", 10009)
        t = datetime(2020, 1, 1, tzinfo=UTC)
        _append(session, entity, occurrence_time=t, changes={"note": (None, "v")})
        got = EventLog.events(session, entity, as_of=t, mode=AsOfMode.OCCURRED_BY)
        assert [r.mode for r in got] == [AsOfMode.OCCURRED_BY]

    def test_a_bare_string_mode_is_accepted(self, session: Session) -> None:
        entity = _StandInEntity("acquisition_case", 10010)
        t = datetime(2020, 1, 1, tzinfo=UTC)
        _append(session, entity, occurrence_time=t, changes={"note": (None, "v")})
        got = EventLog.events(session, entity, as_of=t, mode="OCCURRED_BY")
        assert [r.mode for r in got] == [AsOfMode.OCCURRED_BY]


class TestKnowableAtVersusOccurredBy:
    def test_knowable_at_excludes_a_backdated_recording_that_occurred_by_includes(
        self, session: Session
    ) -> None:
        """The load-bearing distinction (§5.3). R4.4 lets an officer record on 20 March
        a notice that occurred on 1 March; R17.2 forbids a feature row for 5 March from
        using it, since nobody knew it on 5 March. Only filtering on both times does
        both: the event is present ``OCCURRED_BY`` 5 March and absent ``KNOWABLE_AT``
        5 March.
        """
        entity = _StandInEntity("acquisition_case", 10003)
        march_1 = datetime(2024, 3, 1, tzinfo=UTC)
        march_2 = datetime(2024, 3, 2, tzinfo=UTC)
        march_5 = datetime(2024, 3, 5, tzinfo=UTC)
        march_20 = datetime(2024, 3, 20, tzinfo=UTC)

        on_time = _append(
            session, entity, occurrence_time=march_1, recording_time=march_2,
            changes={"note": (None, "recorded on time")},
        )
        backdated = _append(
            session, entity, occurrence_time=march_1, recording_time=march_20,
            changes={"note": (None, "recorded late")},
        )

        occurred = EventLog.events(session, entity, as_of=march_5, mode=AsOfMode.OCCURRED_BY)
        assert {r.id for r in occurred} == {on_time.id, backdated.id}

        knowable = EventLog.events(session, entity, as_of=march_5, mode=AsOfMode.KNOWABLE_AT)
        assert {r.id for r in knowable} == {on_time.id}
        assert all(r.mode == AsOfMode.KNOWABLE_AT for r in knowable)


class TestPayloadResolutionAgainstTheDatabase:
    def test_a_non_personal_payload_resolves_unchanged(self, session: Session) -> None:
        entity = _StandInEntity("acquisition_case", 10004)
        t = datetime(2020, 1, 1, tzinfo=UTC)
        _append(session, entity, occurrence_time=t, changes={"stage_key": ("SIA", "PN")})
        [got] = EventLog.events(session, entity, as_of=t, mode=AsOfMode.OCCURRED_BY)
        assert got.payload == {"stage_key": {"from": "SIA", "to": "PN"}}
        assert got.has_pd_refs is False

    def test_a_personal_payload_resolves_to_the_value_when_not_erased(
        self, session: Session
    ) -> None:
        entity = _StandInEntity("ownership_record", 10005)
        t = datetime(2020, 1, 1, tzinfo=UTC)
        _append(session, entity, occurrence_time=t, changes={"owner_name": ("Asha", "Asha Devi")})
        [got] = EventLog.events(session, entity, as_of=t, mode=AsOfMode.OCCURRED_BY)
        assert got.payload == {"owner_name": "Asha Devi"}
        assert got.has_pd_refs is True

    def test_an_erased_datum_resolves_to_the_marker_and_hides_the_value(
        self, session: Session
    ) -> None:
        entity = _StandInEntity("ownership_record", 10006)
        t = datetime(2020, 1, 1, tzinfo=UTC)
        _append(
            session, entity, occurrence_time=t,
            changes={"owner_name": ("Asha", "Asha Devi"), "contact_mobile": (None, "9000000000")},
        )
        [before] = EventLog.events(session, entity, as_of=t, mode=AsOfMode.OCCURRED_BY)
        assert before.payload["owner_name"] == "Asha Devi"

        raw = session.execute(
            text("SELECT payload FROM event WHERE entity_id = :eid"), {"eid": 10006}
        ).scalar_one()
        datum_id = raw["owner_name"][PD_REF_KEY]
        session.execute(
            text(
                "UPDATE personal_datum SET value_ciphertext = NULL, erased_at = :at "
                "WHERE id = :id"
            ),
            {"at": ERASED_AT, "id": datum_id},
        )

        [after] = EventLog.events(session, entity, as_of=t, mode=AsOfMode.OCCURRED_BY)
        assert after.payload["owner_name"] == {
            ERASED_MARKER_KEY: {"data_category": OWNER_IDENTITY, "erased_at": ERASED_AT}
        }
        assert "Asha Devi" not in json.dumps(after.payload, default=str)
        # The un-erased sibling attribute is untouched.
        assert after.payload["contact_mobile"] == "9000000000"
        # Actor, entity and both timestamps come straight from the untouched row.
        assert (after.id, after.actor_id, after.entity_id) == (
            before.id, before.actor_id, before.entity_id
        )
        assert after.occurrence_time == before.occurrence_time
        assert after.recording_time == before.recording_time

    def test_resolving_does_not_mutate_the_stored_payload(
        self, session: Session, db_connection: Connection
    ) -> None:
        entity = _StandInEntity("ownership_record", 10007)
        t = datetime(2020, 1, 1, tzinfo=UTC)
        ev = _append(session, entity, occurrence_time=t, changes={"owner_name": ("A", "B")})
        [got] = EventLog.events(session, entity, as_of=t, mode=AsOfMode.OCCURRED_BY)
        got.payload["owner_name"] = "MUTATED"
        stored = session.execute(
            text("SELECT payload FROM event WHERE id = :id"), {"id": ev.id}
        ).scalar_one()
        assert set(stored["owner_name"]) == {PD_REF_KEY}, "the stored $pd reference is intact"

    def test_a_dangling_reference_in_a_stored_event_raises(self, session: Session) -> None:
        entity = _StandInEntity("ownership_record", 10008)
        session.execute(
            text(
                "INSERT INTO event (event_type, entity_type, entity_id, actor_type, "
                "actor_id, occurrence_time, payload, has_pd_refs) VALUES "
                "('OWNERSHIP_UPDATED', 'ownership_record', :eid, 'OFFICER', 'o:1', "
                "now(), '{\"owner_name\": {\"$pd\": 987654321}}'::jsonb, true)"
            ),
            {"eid": 10008},
        )
        with pytest.raises(LookupError):
            EventLog.events(
                session, entity, as_of=datetime(2099, 1, 1, tzinfo=UTC),
                mode=AsOfMode.OCCURRED_BY,
            )


# ===========================================================================
# Property 9 (database-backed; skips without PostgreSQL)
# ===========================================================================
#
# Property 9: for any entity and any sequence of appends — including appends whose
# occurrence time precedes an already-stored event — the returned history is ordered
# by occurrence time with a deterministic tiebreak, and the returned set for T equals
# exactly the entity's events with occurrence time at or before T.

_POOL = [
    datetime(2020, 1, 1, tzinfo=UTC),
    datetime(2020, 6, 1, tzinfo=UTC),
    datetime(2021, 1, 1, tzinfo=UTC),
    datetime(2021, 6, 1, tzinfo=UTC),
    datetime(2022, 1, 1, tzinfo=UTC),
]
_BEFORE_ALL = datetime(2019, 1, 1, tzinfo=UTC)
_AFTER_ALL = datetime(2023, 1, 1, tzinfo=UTC)


@st.composite
def _occurred_by_plan(draw: st.DrawFn) -> tuple[int, list[datetime], datetime]:
    entity_id = draw(st.integers(min_value=1, max_value=2_000_000_000))
    # Sampling occurrence times from a small pool forces ties and, because appends
    # happen in draw order, backdated appends (a later append with an earlier time).
    occurrences = draw(st.lists(st.sampled_from(_POOL), min_size=1, max_size=8))
    # T often lands exactly on an occurrence time — the <= boundary where an off-by-one
    # would hide — and sometimes strictly outside the whole range.
    as_of = draw(st.sampled_from(_POOL + [_BEFORE_ALL, _AFTER_ALL]))
    return entity_id, occurrences, as_of


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(plan=_occurred_by_plan())
def test_property_9_history_is_ordered_and_as_of_is_exact(
    db_connection: Connection, plan: tuple[int, list[datetime], datetime]
) -> None:
    entity_id, occurrences, as_of = plan
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        entity = _StandInEntity("acquisition_case", entity_id)
        appended: list[tuple[int, datetime]] = []
        for occurrence in occurrences:
            event = EventLog.append(
                session, event_type="STATE_CHANGED", entity=entity, actor=OFFICER,
                changes={"note": (None, "x")}, occurrence_time=occurrence,
            )
            appended.append((event.id, occurrence))

        got = EventLog.events(session, entity, as_of=as_of, mode=AsOfMode.OCCURRED_BY)

        # The returned set is exactly the events at or before T, and it is ordered by
        # (occurrence_time, id) — asserted by equality with the independently sorted
        # expectation.
        expected = sorted((occ, eid) for eid, occ in appended if occ <= as_of)
        assert [(r.occurrence_time, r.id) for r in got] == expected

        # The ordering is total: no two returned rows share (occurrence_time, id).
        keys = [(r.occurrence_time, r.id) for r in got]
        assert keys == sorted(keys)
        assert len(set(keys)) == len(keys)
        assert all(r.mode == AsOfMode.OCCURRED_BY for r in got)
    finally:
        session.close()


# ===========================================================================
# Property 84 (database-backed; skips without PostgreSQL)
# ===========================================================================
#
# Property 84: for any erased attribute, the value is absent from every event payload
# the log returns; and for every event of the affected entity, the actor, the entity
# identifier, the occurrence time, the recording time, and the position in the
# returned ordering are identical to what was returned before the erasure.

_ASCII = string.ascii_letters + string.digits
_PERSONAL_CATEGORY = {"owner_name": OWNER_IDENTITY, "contact_mobile": OWNER_CONTACT}
_BASE = datetime(2020, 1, 1, tzinfo=UTC)
_FUTURE = datetime(2099, 1, 1, tzinfo=UTC)


@st.composite
def _erasure_plan(draw: st.DrawFn) -> tuple[int, list[str], list[str], list[int]]:
    entity_id = draw(st.integers(min_value=1, max_value=2_000_000_000))
    kinds = draw(
        st.lists(
            st.sampled_from(["owner_name", "contact_mobile", "share"]),
            min_size=1, max_size=6,
        )
    )
    # At least one personal attribute, so there is a datum to erase.
    if not any(kind in _PERSONAL_CATEGORY for kind in kinds):
        kinds[draw(st.integers(min_value=0, max_value=len(kinds) - 1))] = "owner_name"
    size = len(kinds)
    suffixes = draw(
        st.lists(st.text(alphabet=_ASCII, min_size=1, max_size=6), min_size=size, max_size=size)
    )
    shares = draw(
        st.lists(st.integers(min_value=-1000, max_value=1000), min_size=size, max_size=size)
    )
    return entity_id, kinds, suffixes, shares


@settings(max_examples=40, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(plan=_erasure_plan())
def test_property_84_erasure_hides_the_value_and_changes_nothing_else(
    db_connection: Connection, plan: tuple[int, list[str], list[str], list[int]]
) -> None:
    entity_id, kinds, suffixes, shares = plan
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        entity = _StandInEntity("ownership_record", entity_id)
        # (event_id, attribute, value, is_personal). Personal values carry their event
        # index so each is unique, which makes "the value is absent" unambiguous.
        created: list[tuple[int, str, Any, bool]] = []
        for index, attribute in enumerate(kinds):
            occurrence = _BASE + timedelta(days=index)
            if attribute in _PERSONAL_CATEGORY:
                value: Any = f"{attribute}-{index}-{suffixes[index]}"
                changes = {attribute: (None, value)}
            else:
                value = shares[index]
                changes = {"share": (0, value)}
            event = EventLog.append(
                session, event_type="OWNERSHIP_UPDATED", entity=entity, actor=OFFICER,
                changes=changes, occurrence_time=occurrence,
            )
            created.append((event.id, attribute, value, attribute in _PERSONAL_CATEGORY))

        before = EventLog.events(session, entity, as_of=_FUTURE, mode=AsOfMode.OCCURRED_BY)
        assert len(before) == len(created)

        # Erase the first personal datum. Its id is the referent in its event's payload.
        target_index = next(i for i, (_e, _a, _v, personal) in enumerate(created) if personal)
        target_event_id, target_attribute, target_value, _ = created[target_index]
        raw_payload = session.execute(
            text("SELECT payload FROM event WHERE id = :id"), {"id": target_event_id}
        ).scalar_one()
        datum_id = raw_payload[target_attribute][PD_REF_KEY]
        session.execute(
            text(
                "UPDATE personal_datum SET value_ciphertext = NULL, erased_at = :at "
                "WHERE id = :id"
            ),
            {"at": ERASED_AT, "id": datum_id},
        )

        after = EventLog.events(session, entity, as_of=_FUTURE, mode=AsOfMode.OCCURRED_BY)

        # The ordering is identical, position for position.
        assert [r.id for r in after] == [r.id for r in before]
        # Everything the property protects is identical on each event.
        for was, now in zip(before, after):
            assert now.id == was.id
            assert now.actor_type == was.actor_type
            assert now.actor_id == was.actor_id
            assert now.entity_type == was.entity_type
            assert now.entity_id == was.entity_id
            assert now.occurrence_time == was.occurrence_time
            assert now.recording_time == was.recording_time

        # The erased value is gone from every payload the log returns.
        for row in after:
            assert target_value not in json.dumps(row.payload, default=str)
        # It was there before, and is now the marker on its own event.
        before_target = next(r for r in before if r.id == target_event_id)
        assert before_target.payload[target_attribute] == target_value
        after_target = next(r for r in after if r.id == target_event_id)
        assert after_target.payload[target_attribute] == {
            ERASED_MARKER_KEY: {
                "data_category": _PERSONAL_CATEGORY[target_attribute],
                "erased_at": ERASED_AT,
            }
        }
        # Every other personal value still resolves to its value — one erasure erases
        # one datum, not an attribute across history.
        for event_id, attribute, value, personal in created:
            if personal and event_id != target_event_id:
                row = next(r for r in after if r.id == event_id)
                assert row.payload[attribute] == value
    finally:
        session.close()
