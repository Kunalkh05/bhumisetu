"""Deferred event backstop for versioned updates (task 3.7).

The trigger installed by migration 0009 catches the failure mode task 3.7 names:
a versioned entity row is updated and the transaction reaches commit without an
event for that same table/id/transaction. The check is deferred so
``VersionedRepository.update`` can update first and append second.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import Engine, text

from app.db.versioned import Versioned
from app.models import load_all_models
from app.db.base import Base


CURRENT_BACKSTOP_TABLES = {
    "acquisition_case",
    "land_parcel",
    "ownership_record",
    "statutory_notice",
    "notice_service_record",
}


def _seed_case(engine: Engine, reference: str) -> int:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO administrative_area
                    (code, area_type, name, parent_code, state_key, path)
                VALUES ('BACKSTOP', 'state', 'Backstop', NULL, 'SUPPLIED', 'SUPPLIED')
                ON CONFLICT (code) DO NOTHING
                """
            )
        )
        project_id = conn.execute(
            text(
                """
                INSERT INTO project
                    (name, implementing_authority, area_code, purpose_category,
                     sanctioned_extent, extent_unit)
                VALUES (:reference, 'PWD', 'BACKSTOP', 'INFRASTRUCTURE', 100, 'hectare')
                RETURNING id
                """
            ),
            {"reference": reference},
        ).scalar_one()
        return conn.execute(
            text(
                """
                INSERT INTO acquisition_case
                    (case_reference, project_id, state_key, act_key, area_code, stage_key,
                     stage_set_effective_from, stage_entered_on)
                VALUES
                    (:reference, :project_id, 'BACKSTOP', 'RFCTLARR_2013', 'BACKSTOP',
                     'SIA', DATE '2024-01-01', DATE '2024-01-01')
                RETURNING id
                """
            ),
            {"reference": reference, "project_id": project_id},
        ).scalar_one()


def _cleanup_case(engine: Engine, case_id: int) -> None:
    with engine.begin() as conn:
        project_id = conn.execute(
            text("SELECT project_id FROM acquisition_case WHERE id = :id"),
            {"id": case_id},
        ).scalar_one_or_none()
        conn.execute(
            text("DELETE FROM event WHERE entity_type = 'acquisition_case' AND entity_id = :id"),
            {"id": case_id},
        )
        conn.execute(text("DELETE FROM acquisition_case WHERE id = :id"), {"id": case_id})
        if project_id is not None:
            conn.execute(text("DELETE FROM project WHERE id = :id"), {"id": project_id})


def _count_events(engine: Engine, case_id: int) -> int:
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT count(*) FROM event "
                "WHERE entity_type = 'acquisition_case' AND entity_id = :id"
            ),
            {"id": case_id},
        ).scalar_one()


def test_every_current_versioned_table_has_the_deferred_backstop(
    migrated_engine: Engine,
) -> None:
    """The current ORM versioned tables are covered; later tables make this set grow."""
    load_all_models()
    versioned_tables = {
        table.name
        for table in Base.metadata.sorted_tables
        if any(issubclass(mapper.class_, Versioned) for mapper in Base.registry.mappers if mapper.local_table is table)
    }
    assert CURRENT_BACKSTOP_TABLES <= versioned_tables

    with migrated_engine.connect() as conn:
        triggers = set(
            conn.execute(
                text(
                    """
                    SELECT rel.relname
                    FROM pg_trigger trig
                    JOIN pg_class rel ON rel.oid = trig.tgrelid
                    WHERE trig.tgname = rel.relname || '_event_backstop'
                      AND NOT trig.tgisinternal
                      AND (trig.tgdeferrable AND trig.tginitdeferred)
                    """
                )
            ).scalars()
        )

    assert CURRENT_BACKSTOP_TABLES <= triggers


def test_update_without_event_fails_at_commit(migrated_engine: Engine) -> None:
    case_id = _seed_case(migrated_engine, "BACKSTOP-NO-EVENT")
    try:
        with pytest.raises(Exception, match="committed without event"):
            with migrated_engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE acquisition_case
                        SET pending_review_count = pending_review_count + 1
                        WHERE id = :id
                        """
                    ),
                    {"id": case_id},
                )
        assert _count_events(migrated_engine, case_id) == 0
    finally:
        _cleanup_case(migrated_engine, case_id)


def test_update_with_event_in_the_same_transaction_commits(migrated_engine: Engine) -> None:
    case_id = _seed_case(migrated_engine, "BACKSTOP-WITH-EVENT")
    occurred = datetime(2024, 6, 1, 12, tzinfo=timezone.utc)
    try:
        with migrated_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE acquisition_case
                    SET pending_review_count = pending_review_count + 1
                    WHERE id = :id
                    """
                ),
                {"id": case_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO event
                        (event_type, entity_type, entity_id, case_id, actor_type, actor_id,
                         occurrence_time, payload, entity_version_after)
                    VALUES
                        ('CASE_UPDATED', 'acquisition_case', :id, :id, 'OFFICER',
                         'officer:backstop', :occurred,
                         '{"pending_review_count": {"from": 0, "to": 1}}'::jsonb, 2)
                    """
                ),
                {"id": case_id, "occurred": occurred},
            )

        assert _count_events(migrated_engine, case_id) == 1
    finally:
        _cleanup_case(migrated_engine, case_id)


def test_skip_flag_allows_bulk_paths_to_disable_the_backstop(migrated_engine: Engine) -> None:
    case_id = _seed_case(migrated_engine, "BACKSTOP-SKIP")
    try:
        with migrated_engine.begin() as conn:
            conn.execute(text("SET LOCAL bhumisetu.skip_event_backstop = 'on'"))
            conn.execute(
                text(
                    """
                    UPDATE acquisition_case
                    SET pending_review_count = pending_review_count + 1
                    WHERE id = :id
                    """
                ),
                {"id": case_id},
            )
        assert _count_events(migrated_engine, case_id) == 0
    finally:
        _cleanup_case(migrated_engine, case_id)
