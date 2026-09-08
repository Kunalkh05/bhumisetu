"""Retention sweep tests (task 25.3)."""

from __future__ import annotations

import uuid
import json
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.db.event_log import EventLog
from app.models.ownership_record import OwnershipRecord
from app.retention.categories import OWNER_CONTACT, OWNER_IDENTITY
from app.retention.sweep import (
    ErasableAttributeTarget,
    due_for_erasure,
    run_retention_sweep,
    sweep_enabled,
)


class _Resolver:
    def __init__(self, values: dict[str, object] | None = None) -> None:
        self.values = values or {}
        self.calls = []

    def try_get(self, key: str, *, state: str, act: str | None, as_of: date):
        self.calls.append((key, state, act, as_of))
        return self.values.get(key)


def test_sweep_is_disabled_unless_policy_explicitly_enables_it() -> None:
    resolver = _Resolver()

    assert sweep_enabled(resolver, today=date(2035, 1, 1)) is False
    assert resolver.calls == [("retention.sweep_enabled", "*", None, date(2035, 1, 1))]


def test_due_for_erasure_is_generated_from_category_map() -> None:
    targets = set(due_for_erasure())

    assert ErasableAttributeTarget("ownership_record", "owner_name", OWNER_IDENTITY) in targets
    assert ErasableAttributeTarget("ownership_record", "government_identifier", OWNER_IDENTITY) in targets
    assert ErasableAttributeTarget("ownership_record", "owner_identity_key", OWNER_IDENTITY) in targets
    assert ErasableAttributeTarget("ownership_record", "contact_mobile", OWNER_CONTACT) in targets
    assert ErasableAttributeTarget("ownership_record", "contact_mobile_hash", OWNER_CONTACT) in targets
    assert all(target.table_name != "personal_datum" for target in targets)


def test_disabled_sweep_returns_before_scanning(db_connection: Connection, seeded_owner) -> None:
    session = Session(bind=db_connection)
    try:
        result = run_retention_sweep(
            session,
            today=date(2035, 1, 1),
            resolver=_Resolver(),
        )
    finally:
        session.close()

    assert result.enabled is False
    assert result.scanned == 0
    assert result.erased == 0
    assert db_connection.execute(
        text("SELECT owner_name FROM ownership_record WHERE id = :id"),
        {"id": seeded_owner},
    ).scalar_one() == "Asha Patil"


def test_enabled_sweep_erases_entity_column_and_personal_datum(
    db_connection: Connection,
    seeded_owner,
) -> None:
    session = Session(bind=db_connection)
    try:
        owner = session.get(OwnershipRecord, seeded_owner)
        assert owner is not None
        EventLog.append(
            session,
            event_type="OWNERSHIP_UPDATED",
            entity=owner,
            actor=_Actor(),
            changes={"owner_name": (None, "Asha Patil")},
            occurrence_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            case_id=1,
        )
        session.flush()

        result = run_retention_sweep(
            session,
            today=date(2035, 1, 1),
            resolver=_Resolver(
                {
                    "retention.sweep_enabled": True,
                    "retention.period.OWNER_IDENTITY": 1,
                    "retention.period.OWNER_CONTACT": 1,
                }
            ),
            targets=(
                ErasableAttributeTarget(
                    "ownership_record",
                    "owner_name",
                    OWNER_IDENTITY,
                ),
            ),
        )
        session.flush()
    finally:
        session.close()

    assert result.enabled is True
    assert result.erased == 1
    assert db_connection.execute(
        text("SELECT owner_name FROM ownership_record WHERE id = :id"),
        {"id": seeded_owner},
    ).scalar_one() is None
    datum = db_connection.execute(
        text(
            """
            SELECT value_ciphertext, erased_at, erasure_event_id
              FROM personal_datum
             WHERE entity_type = 'ownership_record'
               AND entity_id = :id
               AND attribute_name = 'owner_name'
            """
        ),
        {"id": seeded_owner},
    ).one()
    assert datum.value_ciphertext is None
    assert datum.erased_at is not None
    assert datum.erasure_event_id is not None
    event_payload = db_connection.execute(
        text("SELECT payload FROM event WHERE id = :id"),
        {"id": datum.erasure_event_id},
    ).scalar_one()
    assert event_payload["attribute_name"]["to"] == "owner_name"
    assert event_payload["data_category"]["to"] == OWNER_IDENTITY


def test_missing_retention_period_records_withholding(
    db_connection: Connection,
    seeded_owner,
) -> None:
    session = Session(bind=db_connection)
    try:
        result = run_retention_sweep(
            session,
            today=date(2035, 1, 1),
            resolver=_Resolver({"retention.sweep_enabled": True}),
            targets=(
                ErasableAttributeTarget(
                    "ownership_record",
                    "owner_name",
                    OWNER_IDENTITY,
                ),
            ),
        )
        session.flush()
    finally:
        session.close()

    assert result.withheld == 1
    assert db_connection.execute(
        text(
            """
            SELECT reason
              FROM retention_withholding
             WHERE entity_type = 'ownership_record'
               AND entity_id = :id
               AND attribute_name = 'owner_name'
            """
        ),
        {"id": seeded_owner},
    ).scalar_one() == "RETENTION_PERIOD_MISSING"


class _Actor:
    kind = "OFFICER"
    id = "test-officer"


def _insert_policy_officer(connection: Connection) -> uuid.UUID:
    officer_id = uuid.uuid4()
    connection.execute(
        text(
            """
            INSERT INTO officer (id, officer_code, display_name, credential_hash)
            VALUES (:id, 'retention-officer', 'Retention Officer', 'hash')
            """
        ),
        {"id": officer_id},
    )
    return officer_id


def _insert_terminal_event(connection: Connection, case_id: int) -> int:
    return connection.execute(
        text(
            """
            INSERT INTO event
                (event_type, entity_type, entity_id, case_id, actor_type, actor_id,
                 occurrence_time, payload)
            VALUES
                ('CASE_STAGE_TRANSITIONED', 'acquisition_case', :case_id, :case_id,
                 'OFFICER', 'retention-officer', TIMESTAMPTZ '2026-01-01 00:00:00+00',
                 '{"stage_key": {"from": "AWARD", "to": "POSSESSION"}}'::jsonb)
            RETURNING id
            """
        ),
        {"case_id": case_id},
    ).scalar_one()


def _insert_policy(connection: Connection, officer_id: uuid.UUID, key: str, value: object) -> None:
    connection.execute(
        text(
            """
            INSERT INTO policy_config
                (policy_key, state_key, act_key, effective_from, value, created_by)
            VALUES (:key, '*', NULL, DATE '2026-01-01', CAST(:value AS jsonb), :officer)
            """
        ),
        {"key": key, "value": json.dumps(value), "officer": officer_id},
    )


@pytest.fixture
def seeded_owner(db_connection: Connection, area_factory) -> int:
    area_factory("RET", "state", "Retention")
    officer_id = _insert_policy_officer(db_connection)
    _insert_policy(db_connection, officer_id, "retention.sweep_enabled", True)
    _insert_policy(db_connection, officer_id, "retention.period.OWNER_IDENTITY", 1)
    _insert_policy(db_connection, officer_id, "retention.period.OWNER_CONTACT", 1)
    project_id = db_connection.execute(
        text(
            """
            INSERT INTO project
                (name, implementing_authority, area_code, purpose_category,
                 sanctioned_extent, extent_unit)
            VALUES ('Retention Project', 'PWD', 'RET', 'INFRASTRUCTURE', 10, 'hectare')
            RETURNING id
            """
        )
    ).scalar_one()
    case_id = db_connection.execute(
        text(
            """
            INSERT INTO acquisition_case
                (id, case_reference, project_id, state_key, act_key, area_code, stage_key,
                 stage_set_effective_from, stage_entered_on, is_terminal)
            VALUES
                (1, 'RET-1', :project_id, 'RET', 'RFCTLARR_2013', 'RET', 'POSSESSION',
                 DATE '2026-01-01', DATE '2026-01-01', true)
            RETURNING id
            """
        ),
        {"project_id": project_id},
    ).scalar_one()
    terminal_event_id = _insert_terminal_event(db_connection, case_id)
    db_connection.execute(
        text("UPDATE acquisition_case SET terminal_event_id = :event_id WHERE id = :case_id"),
        {"event_id": terminal_event_id, "case_id": case_id},
    )
    parcel_id = db_connection.execute(
        text(
            """
            INSERT INTO land_parcel
                (state_key, district, tehsil, village, survey_number, classification,
                 extent, extent_unit, area_code)
            VALUES ('RET', 'D', 'T', 'V', '42', 'AGRI', 1, 'hectare', 'RET')
            RETURNING id
            """
        )
    ).scalar_one()
    db_connection.execute(
        text("INSERT INTO case_parcel (case_id, parcel_id) VALUES (:case_id, :parcel_id)"),
        {"case_id": case_id, "parcel_id": parcel_id},
    )
    return db_connection.execute(
        text(
            """
            INSERT INTO ownership_record
                (parcel_id, owner_name, owner_identity_key, government_identifier,
                 contact_mobile, contact_mobile_hash, interest_type, share, valid_from)
            VALUES
                (:parcel_id, 'Asha Patil', 'asha-patil', 'GOV123', '9999999999',
                 decode('abcd', 'hex'), 'OWNER', 1, DATE '2024-01-01')
            RETURNING id
            """
        ),
        {"parcel_id": parcel_id},
    ).scalar_one()
