"""``EventLog.append`` — one event per state change, with payload externalisation.

Task 3.4, requirements R4.1, R4.3, R4.8, and Correctness Property 7.

Two layers of test
------------------

The classification and planning decisions — is this attribute personal, does it go
to ``personal_datum`` or stay inline, which value is externalised — are pure and are
tested without a database. They are the part that is easy to get wrong and cheap to
check, so they run everywhere, including where there is no PostgreSQL.

The append itself writes to ``event`` and ``personal_datum`` and is exercised against
a real database through the ``db_connection`` fixture, which skips cleanly when no
PostgreSQL is reachable (the JSONB payload, the ``bytea`` ciphertext and the flush
semantics are PostgreSQL's, and SQLite cannot stand in for them). Property 7 is one
of those database-backed tests.

Isolation across Hypothesis examples
-------------------------------------

The ``db_connection`` fixture is function-scoped and is therefore shared across every
example of a property test. Each example runs on its own session bound to that
connection with ``join_transaction_mode="create_savepoint"`` and is closed at the end
of the example, rolling its writes back to the savepoint so the next example starts
from an empty log. Every assertion runs before that close, while the flushed rows are
still visible on the connection.
"""

from __future__ import annotations

import json
import string
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.db.event_log import (
    KEY_VERSION_UNENCRYPTED,
    PD_REF_KEY,
    EventLog,
    _Externalised,
    _Inline,
    _case_of,
    _classify,
    _encode_personal_value,
    _plan_externalisation,
    _row_view,
)
from app.models.event import ActorType
from app.retention.categories import (
    LAND_RECORD,
    OWNER_CONTACT,
    OWNER_IDENTITY,
    PERSONAL_DATA_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Stand-ins for the collaborators task 3.4 does not own yet
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Actor:
    """Satisfies the ``Actor`` protocol; ``Principal`` (task 5.1) will do the same."""

    kind: str
    id: str


class _StandInEntity:
    """A minimal entity: a table name and an id, plus any sibling columns a
    value-dependent classification needs.

    The versioned entity tables (``ownership_record`` and friends) land in tasks
    8–15, so they cannot be instantiated here — and they do not need to be, because
    ``append`` writes only to ``event`` and ``personal_datum`` and reads
    ``entity_type``/``entity_id`` as a bare string and number.
    """

    def __init__(self, table: str, id: int, **attributes: Any) -> None:
        self.__tablename__ = table
        self.id = id
        for name, value in attributes.items():
            setattr(self, name, value)


# ===========================================================================
# Pure classification and planning — no database
# ===========================================================================


class TestClassification:
    def test_a_mapped_personal_attribute_resolves_to_its_category(self) -> None:
        assert _classify("ownership_record", "owner_name", {}) == OWNER_IDENTITY
        assert _classify("ownership_record", "contact_mobile", {}) == OWNER_CONTACT
        assert _classify("objection", "objector_name", {}) == OWNER_IDENTITY

    def test_a_mapped_non_personal_attribute_stays_inline(self) -> None:
        """Task 25.2 completes the map; non-personal categories are explicit."""
        assert _classify("acquisition_case", "stage_key", {}) == LAND_RECORD
        assert _classify("ownership_record", "share", {}) == LAND_RECORD
        assert _classify("test_probe", "note", {}) is None

    def test_a_value_dependent_attribute_uses_the_row(self) -> None:
        """``extracted_field.extracted_value`` is personal or not depending on which
        field was extracted — the ``Discriminated`` entry resolved from the row."""
        assert (
            _classify("extracted_field", "extracted_value", {"field_name": "owner_name"})
            == OWNER_IDENTITY
        )
        assert (
            _classify("extracted_field", "extracted_value", {"field_name": "survey_number"})
            == LAND_RECORD
        )

    def test_a_missing_discriminator_is_a_real_error_not_an_inline_attribute(self) -> None:
        """The membership pre-check must not swallow this: the attribute *is* mapped,
        it simply cannot be classified without its discriminator, and turning that
        into a silent inline write is exactly the leak the design guards against."""
        with pytest.raises(KeyError):
            _classify("extracted_field", "extracted_value", {})


class TestPlanExternalisation:
    def test_non_personal_attributes_are_planned_inline_with_both_values(self) -> None:
        plan = _plan_externalisation(
            "acquisition_case", {"stage_key": ("SIA", "PN")}, {}
        )
        assert plan == [_Inline(attribute="stage_key", old="SIA", new="PN")]

    def test_personal_attributes_are_planned_for_externalisation_of_the_new_value(
        self,
    ) -> None:
        plan = _plan_externalisation(
            "ownership_record", {"owner_name": ("Asha", "Asha Devi")}, {}
        )
        assert plan == [
            _Externalised(
                attribute="owner_name", data_category=OWNER_IDENTITY, value="Asha Devi"
            )
        ]

    def test_a_mixed_change_set_splits_correctly(self) -> None:
        plan = _plan_externalisation(
            "ownership_record",
            {
                "owner_name": ("A", "B"),
                "contact_mobile": (None, "9000000000"),
                "share": (0.5, 0.34),
            },
            {},
        )
        by_attr = {item.attribute: item for item in plan}
        assert isinstance(by_attr["owner_name"], _Externalised)
        assert by_attr["owner_name"].data_category == OWNER_IDENTITY
        assert isinstance(by_attr["contact_mobile"], _Externalised)
        assert by_attr["contact_mobile"].data_category == OWNER_CONTACT
        assert isinstance(by_attr["share"], _Inline)

    def test_the_new_value_is_the_one_externalised_not_the_old(self) -> None:
        """§5.4: the payload carries a reference to the new value; the prior value is
        the referent of the preceding event, never stored inline where it could not be
        erased."""
        [item] = _plan_externalisation(
            "objection", {"objector_name": ("old name", "new name")}, {}
        )
        assert isinstance(item, _Externalised)
        assert item.value == "new name"


class TestValueEncoding:
    def test_a_value_round_trips_through_the_encoding(self) -> None:
        for value in ["Asha Devi", "नरेश", "9876543210", 42, None]:
            encoded, key_version = _encode_personal_value(value)
            assert isinstance(encoded, bytes)
            assert key_version == KEY_VERSION_UNENCRYPTED
            assert json.loads(encoded.decode("utf-8")) == value

    def test_devanagari_is_stored_as_utf8_not_ascii_escapes(self) -> None:
        """R27.5 in miniature: a name must survive as its own bytes."""
        encoded, _ = _encode_personal_value("नरेश")
        assert "नरेश".encode("utf-8") in encoded


class TestCaseOf:
    def test_an_acquisition_case_is_its_own_case(self) -> None:
        assert _case_of(_StandInEntity("acquisition_case", 77)) == 77

    def test_a_denormalised_case_id_is_used(self) -> None:
        assert _case_of(_StandInEntity("statutory_notice", 3, case_id=77)) == 77

    def test_an_entity_with_no_derivable_case_is_none(self) -> None:
        assert _case_of(_StandInEntity("ownership_record", 3)) is None


class TestRowView:
    def test_a_stand_in_entitys_attributes_are_exposed(self) -> None:
        view = _row_view(_StandInEntity("extracted_field", 1, field_name="owner_name"))
        assert view["field_name"] == "owner_name"


# ===========================================================================
# Database-backed append (skips without PostgreSQL)
# ===========================================================================


@pytest.fixture
def session(db_connection: Connection) -> Session:
    return Session(bind=db_connection, join_transaction_mode="create_savepoint")


OFFICER = _Actor(kind=ActorType.OFFICER, id="officer:412")
OCCURRED = datetime(2024, 3, 4, 9, 12, 44, tzinfo=timezone.utc)


def _read_event(connection: Connection, event_id: int):
    return connection.execute(
        text(
            "SELECT event_type, entity_type, entity_id, case_id, actor_type, actor_id, "
            "occurrence_time, recording_time, payload, has_pd_refs, entity_version_after "
            "FROM event WHERE id = :id"
        ),
        {"id": event_id},
    ).one()


def _read_datum(connection: Connection, datum_id: int):
    return connection.execute(
        text(
            "SELECT data_category, entity_type, entity_id, attribute_name, "
            "value_ciphertext, key_version, erased_at FROM personal_datum WHERE id = :id"
        ),
        {"id": datum_id},
    ).one()


class TestAppendWritesOneEvent:
    def test_a_non_personal_change_is_recorded_inline(
        self, session: Session, db_connection: Connection
    ) -> None:
        entity = _StandInEntity("acquisition_case", 1)
        event = EventLog.append(
            session,
            event_type="STAGE_TRANSITIONED",
            entity=entity,
            actor=OFFICER,
            changes={"stage_key": ("SIA", "PN")},
            occurrence_time=OCCURRED,
        )
        row = _read_event(db_connection, event.id)
        assert row.event_type == "STAGE_TRANSITIONED"
        assert row.entity_type == "acquisition_case"
        assert row.entity_id == 1
        assert row.case_id == 1, "an acquisition_case is its own case"
        assert row.actor_type == ActorType.OFFICER
        assert row.actor_id == "officer:412"
        assert row.payload == {"stage_key": {"from": "SIA", "to": "PN"}}
        assert row.has_pd_refs is False

    def test_a_personal_change_is_externalised_to_personal_datum(
        self, session: Session, db_connection: Connection
    ) -> None:
        entity = _StandInEntity("ownership_record", 5)
        event = EventLog.append(
            session,
            event_type="OWNERSHIP_UPDATED",
            entity=entity,
            actor=OFFICER,
            changes={"owner_name": ("Asha", "Asha Devi")},
            occurrence_time=OCCURRED,
        )
        row = _read_event(db_connection, event.id)
        assert row.has_pd_refs is True
        assert set(row.payload) == {"owner_name"}
        leaf = row.payload["owner_name"]
        assert set(leaf) == {PD_REF_KEY}, "a personal attribute carries a single reference"

        datum = _read_datum(db_connection, leaf[PD_REF_KEY])
        assert datum.data_category == OWNER_IDENTITY
        assert datum.entity_type == "ownership_record"
        assert datum.entity_id == 5
        assert datum.attribute_name == "owner_name"
        assert datum.key_version == KEY_VERSION_UNENCRYPTED
        assert datum.erased_at is None
        assert json.loads(bytes(datum.value_ciphertext).decode("utf-8")) == "Asha Devi", (
            "the externalised value is the new one"
        )

    def test_a_mixed_change_set_externalises_only_the_personal_attributes(
        self, session: Session, db_connection: Connection
    ) -> None:
        entity = _StandInEntity("ownership_record", 9)
        event = EventLog.append(
            session,
            event_type="OWNERSHIP_UPDATED",
            entity=entity,
            actor=OFFICER,
            changes={
                "owner_name": ("A", "B"),
                "contact_mobile": (None, "9000000000"),
                "share": (0.5, 0.34),
            },
            occurrence_time=OCCURRED,
        )
        row = _read_event(db_connection, event.id)
        assert row.has_pd_refs is True
        assert row.payload["share"] == {"from": 0.5, "to": 0.34}
        assert set(row.payload["owner_name"]) == {PD_REF_KEY}
        assert set(row.payload["contact_mobile"]) == {PD_REF_KEY}
        assert (
            _read_datum(db_connection, row.payload["contact_mobile"][PD_REF_KEY]).data_category
            == OWNER_CONTACT
        )

    def test_occurrence_and_recording_time_are_distinct(
        self, session: Session, db_connection: Connection
    ) -> None:
        """R4.3. The occurrence time is supplied and backdated; the recording time is
        the column default, so the two are genuinely different values."""
        event = EventLog.append(
            session,
            event_type="STAGE_TRANSITIONED",
            entity=_StandInEntity("acquisition_case", 2),
            actor=OFFICER,
            changes={"stage_key": ("SIA", "PN")},
            occurrence_time=OCCURRED,
        )
        row = _read_event(db_connection, event.id)
        assert row.recording_time is not None
        assert row.recording_time > row.occurrence_time
        assert row.occurrence_time == OCCURRED

    def test_entity_version_after_is_recorded_when_supplied(
        self, session: Session, db_connection: Connection
    ) -> None:
        """R29.4's hook: the version a change produced is attributable to its actor."""
        event = EventLog.append(
            session,
            event_type="OWNERSHIP_UPDATED",
            entity=_StandInEntity("ownership_record", 11),
            actor=OFFICER,
            changes={"share": (0.5, 0.34)},
            occurrence_time=OCCURRED,
            entity_version_after=7,
        )
        assert _read_event(db_connection, event.id).entity_version_after == 7

    def test_a_caller_may_override_the_derived_case_id(
        self, session: Session, db_connection: Connection
    ) -> None:
        """An ownership record's case is reached through its parcel, a relationship not
        declared until task 8.x, so the write path passes case_id explicitly."""
        event = EventLog.append(
            session,
            event_type="OWNERSHIP_UPDATED",
            entity=_StandInEntity("ownership_record", 13),
            actor=OFFICER,
            changes={"share": (0.5, 0.34)},
            occurrence_time=OCCURRED,
            case_id=321,
        )
        assert _read_event(db_connection, event.id).case_id == 321


class TestAppendAtomicity:
    def test_a_failing_append_surfaces_inside_the_transaction(
        self, session: Session
    ) -> None:
        """R4.8: the flush forces the failure to raise here, inside the caller's
        transaction, rather than after the block has committed. A NULL event_type
        violates the NOT NULL constraint and must surface at append time."""
        with pytest.raises(Exception):
            EventLog.append(
                session,
                event_type=None,  # type: ignore[arg-type]
                entity=_StandInEntity("acquisition_case", 3),
                actor=OFFICER,
                changes={"stage_key": ("SIA", "PN")},
                occurrence_time=OCCURRED,
            )


# ===========================================================================
# Property 7 (database-backed; skips without PostgreSQL)
# ===========================================================================
#
# Property 7: every state change appends exactly one event carrying the actor, the
# entity, the changed attributes with their prior and new values, the occurrence
# time, and a distinct recording time.
#
# "prior and new values" is discharged as the design specifies: inline as
# {"from": old, "to": new} for a non-personal attribute, and as a single {"$pd": id}
# reference to the new value for a personal one (whose prior value is the referent of
# the preceding event, never stored inline — §5.4).

_ASCII = string.ascii_letters + string.digits
_NON_PERSONAL_NAMES = ["stage_key", "status", "note", "amount", "remarks", "count"]

#: Personal columns per entity, restricted to the plainly classified ones so the
#: expected category is known without a row. Every value here is a plain category
#: string in CATEGORY_MAP.
_PERSONAL_BY_TABLE: dict[str, dict[str, str]] = {
    "ownership_record": {
        "owner_name": OWNER_IDENTITY,
        "government_identifier": OWNER_IDENTITY,
        "contact_mobile": OWNER_CONTACT,
    },
    "objection": {"objector_name": OWNER_IDENTITY},
    "acquisition_case": {},
    "land_parcel": {},
}

# JSON-safe scalars for inline attributes. Floats are omitted so the equality check
# after the jsonb round trip is exact rather than subject to numeric normalisation.
_json_scalar = st.one_of(
    st.text(alphabet=_ASCII, max_size=12),
    st.integers(min_value=-10_000, max_value=10_000),
    st.booleans(),
    st.none(),
)

# Personal values: names and identifiers, including Devanagari so the UTF-8 path is
# exercised. Non-empty strings, so a change always has a value to externalise.
_personal_value = st.one_of(
    st.text(alphabet=_ASCII, min_size=1, max_size=12),
    st.text(alphabet="कखगघचछजझटठडढणतथदधनपफ ािीुूेैोौंँ्", min_size=1, max_size=10),
)

_actor_strategy = st.builds(
    _Actor,
    kind=st.sampled_from(
        [ActorType.OFFICER, ActorType.CITIZEN_SESSION, ActorType.SYSTEM, ActorType.IMPORT]
    ),
    id=st.text(alphabet=_ASCII + ":-", min_size=1, max_size=16),
)


@dataclass(frozen=True)
class _AppendSpec:
    table: str
    entity_id: int
    actor: _Actor
    occurrence_time: datetime
    changes: dict[str, tuple[Any, Any]]
    #: attribute -> expected data category, for the personal attributes only.
    personal: dict[str, str]


@st.composite
def _append_specs(draw: st.DrawFn) -> _AppendSpec:
    table = draw(st.sampled_from(list(_PERSONAL_BY_TABLE)))
    changes: dict[str, tuple[Any, Any]] = {}
    personal: dict[str, str] = {}

    # At least one non-personal attribute, so there is always a change.
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
            personal[column] = personal_columns[column]

    return _AppendSpec(
        table=table,
        entity_id=draw(st.integers(min_value=1, max_value=2_000_000_000)),
        actor=draw(_actor_strategy),
        occurrence_time=draw(
            st.datetimes(
                min_value=datetime(2019, 1, 1),
                max_value=datetime(2024, 1, 1),
                timezones=st.just(timezone.utc),
            )
        ),
        changes=changes,
        personal=personal,
    )


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(spec=_append_specs())
def test_property_7_one_complete_event_per_state_change(
    db_connection: Connection, spec: _AppendSpec
) -> None:
    before_max = db_connection.execute(
        text("SELECT COALESCE(MAX(id), 0) FROM event")
    ).scalar_one()

    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        entity = _StandInEntity(spec.table, spec.entity_id)
        returned = EventLog.append(
            session,
            event_type="STATE_CHANGED",
            entity=entity,
            actor=spec.actor,
            changes=spec.changes,
            occurrence_time=spec.occurrence_time,
        )

        # Exactly one event, and it is the one returned.
        new_events = db_connection.execute(
            text(
                "SELECT id, entity_type, entity_id, actor_type, actor_id, "
                "occurrence_time, recording_time, payload, has_pd_refs "
                "FROM event WHERE id > :m ORDER BY id"
            ),
            {"m": before_max},
        ).all()
        assert len(new_events) == 1
        row = new_events[0]
        assert row.id == returned.id

        # Actor and entity.
        assert row.entity_type == spec.table
        assert row.entity_id == spec.entity_id
        assert row.actor_type == spec.actor.kind
        assert row.actor_id == spec.actor.id

        # Occurrence time recorded, recording time distinct from it.
        assert row.occurrence_time == spec.occurrence_time
        assert row.recording_time is not None
        assert row.recording_time > spec.occurrence_time

        # has_pd_refs is true exactly when a personal attribute was externalised.
        assert row.has_pd_refs == bool(spec.personal)

        # Every changed attribute is present, and nothing else.
        assert set(row.payload) == set(spec.changes)

        for attribute, (old, new) in spec.changes.items():
            leaf = row.payload[attribute]
            if attribute in spec.personal:
                assert set(leaf) == {PD_REF_KEY}
                datum = _read_datum(db_connection, leaf[PD_REF_KEY])
                assert datum.data_category == spec.personal[attribute]
                assert datum.entity_type == spec.table
                assert datum.entity_id == spec.entity_id
                assert datum.attribute_name == attribute
                assert datum.erased_at is None
                stored = json.loads(bytes(datum.value_ciphertext).decode("utf-8"))
                assert stored == new, "the externalised value is the new one"
            else:
                assert leaf == {"from": old, "to": new}
    finally:
        session.close()
