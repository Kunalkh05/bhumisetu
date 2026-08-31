"""``EventLog.append_correction`` — compensating events (task 3.6).

Requirements R4.6 (and R4.2, which a correction must not violate); Correctness
Property 8.

What task 3.6 delivers, and where the rest of Property 8 lives
--------------------------------------------------------------

Property 8 has two clauses. The first — that an update or delete of a stored event is
rejected on every interface path and the row is unchanged — is enforced by the
revoked ``UPDATE, DELETE`` grant and the ``EventImmutable`` ORM guard, and is
exercised exhaustively in ``test_event_log_schema.py``. This module owns the second
clause, which is what ``append_correction`` is for: a correction exists only as a
**new appended event** that references the erroneous event's identifier, while the
erroneous event remains stored exactly as it was. ``test_property_8_...`` below is the
generative form of that clause; a single end-to-end example ties it back to the first
clause so the whole property is legible in one place.

Why this is database-backed
----------------------------

``append_correction`` is a thin specialisation of :meth:`EventLog.append`: it writes
to ``event`` (and ``personal_datum`` when a correction carries personal data), and it
reads ``event`` to check that the corrected id exists. The JSONB payload, the
``bigserial`` id the correction must differ by, and the ``corrects_event_id`` foreign
key are all PostgreSQL's, so these run against a real database through the
``db_connection`` fixture, which skips cleanly when no PostgreSQL is reachable.

Isolation across Hypothesis examples
-------------------------------------

``db_connection`` is function-scoped and shared across every example of a property
test. Each example runs on its own savepoint-joined session and closes it in a
``finally``, rolling its writes back to the savepoint before the next example, so no
example sees another's events.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.db.event_log import PD_REF_KEY, AsOfMode, EventLog
from app.models.event import ActorType, Event, EventImmutable
from app.retention.categories import OWNER_CONTACT, OWNER_IDENTITY

UTC = timezone.utc
OCCURRED = datetime(2024, 3, 4, 9, 12, 44, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Stand-ins, mirroring the append and read tests
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Actor:
    """Satisfies the ``Actor`` protocol; ``Principal`` (task 5.1) will do the same."""

    kind: str
    id: str


class _StandInEntity:
    """A table name and an id — all ``append``/``append_correction`` read off an
    entity. The versioned entity tables land in tasks 8–15 and are not needed here,
    because a correction, like any append, writes only to ``event`` and
    ``personal_datum``."""

    def __init__(self, table: str, id: int, **attributes: Any) -> None:
        self.__tablename__ = table
        self.id = id
        for name, value in attributes.items():
            setattr(self, name, value)


OFFICER = _Actor(kind=ActorType.OFFICER, id="officer:412")

#: Every column of ``event``, so a snapshot is the whole row and "byte-identical"
#: means what it says.
_EVENT_COLUMNS = (
    "id, event_type, entity_type, entity_id, case_id, actor_type, actor_id, "
    "occurrence_time, recording_time, payload, has_pd_refs, entity_version_after, "
    "provenance, import_batch_id, corrects_event_id, txid"
)


def _read_full_event(connection: Connection, event_id: int) -> dict[str, Any]:
    """Every stored column of one event, as a plain dict for equality comparison."""
    row = connection.execute(
        text(f"SELECT {_EVENT_COLUMNS} FROM event WHERE id = :id"), {"id": event_id}
    ).one()
    return dict(row._mapping)


def _count_events(connection: Connection) -> int:
    return connection.execute(text("SELECT count(*) FROM event")).scalar_one()


@pytest.fixture
def session(db_connection: Connection) -> Session:
    return Session(bind=db_connection, join_transaction_mode="create_savepoint")


# ===========================================================================
# append_correction behaviour (database-backed; skips without PostgreSQL)
# ===========================================================================


class TestAppendCorrection:
    def test_it_writes_a_new_event_referencing_the_erroneous_one(
        self, session: Session, db_connection: Connection
    ) -> None:
        """R4.6: the correction is a distinct new row whose ``corrects_event_id``
        points at the erroneous event."""
        entity = _StandInEntity("statutory_notice", 5001, case_id=900)
        erroneous = EventLog.append(
            session,
            event_type="NOTICE_ISSUED",
            entity=entity,
            actor=OFFICER,
            changes={"issued_on": (None, "2024-03-01")},
            occurrence_time=OCCURRED,
        )
        correction = EventLog.append_correction(
            session,
            corrects_event_id=erroneous.id,
            event_type="NOTICE_ISSUE_CORRECTED",
            entity=entity,
            actor=OFFICER,
            changes={"issued_on": ("2024-03-01", "2024-03-02")},
            occurrence_time=OCCURRED,
        )
        assert correction.id != erroneous.id, "a correction is a new event, not an edit"
        assert _read_full_event(db_connection, correction.id)["corrects_event_id"] == (
            erroneous.id
        )

    def test_it_records_actor_entity_changes_and_a_distinct_recording_time(
        self, session: Session, db_connection: Connection
    ) -> None:
        """A correction is an ordinary event in every other respect — routing it
        through :meth:`append` is what guarantees that."""
        entity = _StandInEntity("acquisition_case", 5002)
        erroneous = EventLog.append(
            session,
            event_type="STATE_RECORDED",
            entity=entity,
            actor=OFFICER,
            changes={"note": (None, "wrong")},
            occurrence_time=OCCURRED,
        )
        correction = EventLog.append_correction(
            session,
            corrects_event_id=erroneous.id,
            event_type="STATE_CORRECTED",
            entity=entity,
            actor=OFFICER,
            changes={"note": ("wrong", "right")},
            occurrence_time=OCCURRED,
            entity_version_after=3,
        )
        row = _read_full_event(db_connection, correction.id)
        assert row["event_type"] == "STATE_CORRECTED"
        assert row["entity_type"] == "acquisition_case"
        assert row["entity_id"] == 5002
        assert row["case_id"] == 5002, "an acquisition_case is its own case"
        assert row["actor_type"] == ActorType.OFFICER
        assert row["actor_id"] == OFFICER.id
        assert row["payload"] == {"note": {"from": "wrong", "to": "right"}}
        assert row["entity_version_after"] == 3
        assert row["recording_time"] > row["occurrence_time"]

    def test_it_externalises_personal_data_by_reference(
        self, session: Session, db_connection: Connection
    ) -> None:
        """§5.4 holds for a correction too: a personal value in a corrected attribute
        is stored by ``$pd`` reference, never inline, so it stays erasable."""
        entity = _StandInEntity("ownership_record", 5003)
        erroneous = EventLog.append(
            session,
            event_type="OWNERSHIP_RECORDED",
            entity=entity,
            actor=OFFICER,
            changes={"owner_name": (None, "Asha")},
            occurrence_time=OCCURRED,
        )
        correction = EventLog.append_correction(
            session,
            corrects_event_id=erroneous.id,
            event_type="OWNERSHIP_CORRECTED",
            entity=entity,
            actor=OFFICER,
            changes={"owner_name": ("Asha", "Asha Devi")},
            occurrence_time=OCCURRED,
        )
        row = _read_full_event(db_connection, correction.id)
        assert row["has_pd_refs"] is True
        assert set(row["payload"]["owner_name"]) == {PD_REF_KEY}
        assert row["corrects_event_id"] == erroneous.id

    def test_it_can_reference_an_event_appended_in_the_same_transaction(
        self, session: Session, db_connection: Connection
    ) -> None:
        """The corrected event need not be committed: :meth:`append` flushes, so the
        existence check sees a row appended moments earlier in this transaction."""
        entity = _StandInEntity("acquisition_case", 5004)
        erroneous = EventLog.append(
            session,
            event_type="STAGE_TRANSITIONED",
            entity=entity,
            actor=OFFICER,
            changes={"stage_key": ("SIA", "PN")},
            occurrence_time=OCCURRED,
        )
        correction = EventLog.append_correction(
            session,
            corrects_event_id=erroneous.id,
            event_type="STAGE_TRANSITION_CORRECTED",
            entity=entity,
            actor=OFFICER,
            changes={"stage_key": ("PN", "SIA")},
            occurrence_time=OCCURRED,
        )
        assert _read_full_event(db_connection, correction.id)["corrects_event_id"] == (
            erroneous.id
        )

    def test_correcting_a_missing_event_raises_and_writes_nothing(
        self, session: Session, db_connection: Connection
    ) -> None:
        """A ``corrects_event_id`` that resolves to no event is a clear ``LookupError``
        at the call site, and no event is appended — the reference is the whole point
        of the method, so a dangling one is refused before anything is written."""
        count_before = _count_events(db_connection)
        with pytest.raises(LookupError, match="no such event"):
            EventLog.append_correction(
                session,
                corrects_event_id=2_000_000_123,
                event_type="STATE_CORRECTED",
                entity=_StandInEntity("acquisition_case", 5005),
                actor=OFFICER,
                changes={"note": (None, "orphan correction")},
                occurrence_time=OCCURRED,
            )
        assert _count_events(db_connection) == count_before

    def test_the_correction_joins_the_entitys_history_carrying_the_reference(
        self, session: Session
    ) -> None:
        """Read back through :meth:`EventLog.events`, both events are in the entity's
        timeline; only the correction carries ``corrects_event_id``."""
        entity = _StandInEntity("acquisition_case", 5006)
        t1 = datetime(2020, 1, 1, tzinfo=UTC)
        t2 = datetime(2020, 2, 1, tzinfo=UTC)
        erroneous = EventLog.append(
            session,
            event_type="STATE_RECORDED",
            entity=entity,
            actor=OFFICER,
            changes={"note": (None, "typo")},
            occurrence_time=t1,
        )
        correction = EventLog.append_correction(
            session,
            corrects_event_id=erroneous.id,
            event_type="STATE_CORRECTED",
            entity=entity,
            actor=OFFICER,
            changes={"note": ("typo", "fixed")},
            occurrence_time=t2,
        )
        by_id = {
            r.id: r
            for r in EventLog.events(session, entity, as_of=t2, mode=AsOfMode.OCCURRED_BY)
        }
        assert {erroneous.id, correction.id} <= set(by_id)
        assert by_id[erroneous.id].corrects_event_id is None
        assert by_id[correction.id].corrects_event_id == erroneous.id


def test_property_8_example_end_to_end_with_immutability(
    session: Session, db_connection: Connection
) -> None:
    """Property 8 at one concrete example, spanning both clauses.

    The correction is a new event referencing the erroneous one; the erroneous row is
    byte-identical afterwards; and it remains immutable in place (R4.2). The rejection
    clause's exhaustive coverage is in ``test_event_log_schema.py`` — this ties it to a
    corrected event so the whole property reads in one test.
    """
    entity = _StandInEntity("ownership_record", 5100)
    erroneous = EventLog.append(
        session,
        event_type="OWNERSHIP_RECORDED",
        entity=entity,
        actor=OFFICER,
        changes={"owner_name": (None, "Asha")},
        occurrence_time=OCCURRED,
    )
    before = _read_full_event(db_connection, erroneous.id)

    correction = EventLog.append_correction(
        session,
        corrects_event_id=erroneous.id,
        event_type="OWNERSHIP_CORRECTED",
        entity=entity,
        actor=OFFICER,
        changes={"owner_name": ("Asha", "Asha Devi")},
        occurrence_time=OCCURRED,
    )
    assert correction.id != erroneous.id
    assert _read_full_event(db_connection, correction.id)["corrects_event_id"] == (
        erroneous.id
    )
    assert _read_full_event(db_connection, erroneous.id) == before, (
        "the erroneous event is unchanged by the correction"
    )

    # It also cannot be edited in place: recording a correction is the only route.
    stored = session.get(Event, erroneous.id)
    stored.event_type = "TAMPERED"
    with pytest.raises(EventImmutable, match="append-only"):
        session.flush()
    session.expunge_all()
    assert _read_full_event(db_connection, erroneous.id) == before


# ===========================================================================
# Property 8 (database-backed; skips without PostgreSQL)
# ===========================================================================
#
# Property 8 (correction clause): for any Event identified as erroneous, the correction
# exists as a new appended Event referencing the erroneous Event's identifier while the
# erroneous Event remains stored unchanged.

_ASCII = string.ascii_letters + string.digits
_NON_PERSONAL_NAMES = ["stage_key", "status", "note", "amount", "remarks", "count"]

#: Personal columns per entity, restricted to the plainly classified ones (every value
#: is a plain category string in CATEGORY_MAP), so a correction can carry personal data
#: without needing a row to resolve a value-dependent classification.
_PERSONAL_BY_TABLE: dict[str, dict[str, str]] = {
    "ownership_record": {
        "owner_name": OWNER_IDENTITY,
        "government_identifier": OWNER_IDENTITY,
        "contact_mobile": OWNER_CONTACT,
    },
    "objection": {"objector_name": OWNER_IDENTITY},
    "acquisition_case": {},
    "statutory_notice": {},
}

# JSON-safe scalars for inline attributes. Floats are omitted so equality after the
# jsonb round trip is exact.
_json_scalar = st.one_of(
    st.text(alphabet=_ASCII, max_size=12),
    st.integers(min_value=-10_000, max_value=10_000),
    st.booleans(),
    st.none(),
)
_personal_value = st.text(alphabet=_ASCII, min_size=1, max_size=12)

_actor_strategy = st.builds(
    _Actor,
    kind=st.sampled_from(
        [ActorType.OFFICER, ActorType.CITIZEN_SESSION, ActorType.SYSTEM, ActorType.IMPORT]
    ),
    id=st.text(alphabet=_ASCII + ":-", min_size=1, max_size=16),
)
_occurrence = st.datetimes(
    min_value=datetime(2019, 1, 1),
    max_value=datetime(2024, 1, 1),
    timezones=st.just(UTC),
)


def _draw_changes(draw: st.DrawFn, table: str) -> dict[str, tuple[Any, Any]]:
    """A non-empty change set for ``table``: at least one non-personal attribute, plus
    any subset of that table's personal columns."""
    changes: dict[str, tuple[Any, Any]] = {}
    for name in draw(
        st.lists(st.sampled_from(_NON_PERSONAL_NAMES), min_size=1, max_size=3, unique=True)
    ):
        changes[name] = (draw(_json_scalar), draw(_json_scalar))
    personal_columns = _PERSONAL_BY_TABLE[table]
    if personal_columns:
        for column in draw(
            st.lists(
                st.sampled_from(list(personal_columns)),
                min_size=0,
                max_size=len(personal_columns),
                unique=True,
            )
        ):
            changes[column] = (draw(_personal_value), draw(_personal_value))
    return changes


@dataclass(frozen=True)
class _Scenario:
    table: str
    entity_id: int
    erroneous_actor: _Actor
    erroneous_changes: dict[str, tuple[Any, Any]]
    erroneous_time: datetime
    correction_actor: _Actor
    correction_changes: dict[str, tuple[Any, Any]]
    correction_time: datetime


@st.composite
def _correction_scenarios(draw: st.DrawFn) -> _Scenario:
    table = draw(st.sampled_from(list(_PERSONAL_BY_TABLE)))
    return _Scenario(
        table=table,
        entity_id=draw(st.integers(min_value=1, max_value=2_000_000_000)),
        erroneous_actor=draw(_actor_strategy),
        erroneous_changes=_draw_changes(draw, table),
        erroneous_time=draw(_occurrence),
        correction_actor=draw(_actor_strategy),
        correction_changes=_draw_changes(draw, table),
        correction_time=draw(_occurrence),
    )


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(scenario=_correction_scenarios())
def test_property_8_correction_is_a_new_event_and_leaves_the_erroneous_one_unchanged(
    db_connection: Connection, scenario: _Scenario
) -> None:
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        entity = _StandInEntity(scenario.table, scenario.entity_id)
        erroneous = EventLog.append(
            session,
            event_type="STATE_RECORDED",
            entity=entity,
            actor=scenario.erroneous_actor,
            changes=scenario.erroneous_changes,
            occurrence_time=scenario.erroneous_time,
        )
        before = _read_full_event(db_connection, erroneous.id)
        count_before = _count_events(db_connection)

        correction = EventLog.append_correction(
            session,
            corrects_event_id=erroneous.id,
            event_type="STATE_CORRECTED",
            entity=entity,
            actor=scenario.correction_actor,
            changes=scenario.correction_changes,
            occurrence_time=scenario.correction_time,
        )

        # Exactly one new event — the correction — and it is a distinct row.
        assert _count_events(db_connection) == count_before + 1
        assert correction.id != erroneous.id

        # It references the erroneous event's identifier (R4.6).
        assert _read_full_event(db_connection, correction.id)["corrects_event_id"] == (
            erroneous.id
        )

        # The erroneous event remains stored unchanged, every column byte-identical.
        assert _read_full_event(db_connection, erroneous.id) == before
    finally:
        session.close()
