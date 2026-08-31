"""Two-connection optimistic-concurrency harness (task 4.4, R29.6/R29.7/R29.8).

The single-connection repository tests prove the compare-and-set shape. This file
proves the database behaviour that shape relies on: under PostgreSQL READ COMMITTED,
two transactions presenting the same ``entity_version`` serialize on the row lock;
after the first commits, PostgreSQL rechecks the second transaction's ``WHERE`` clause
against the new row and the second update matches zero rows.

These tests intentionally use two real connections from ``migrated_engine``. SQLite,
savepoints, and mocks cannot prove the row-lock/recheck behaviour R29.6 rests on, so
the fixture skips locally when no PostgreSQL test database is reachable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Queue
from threading import Event, Thread
from typing import Any, Mapping

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.db.versioned_repository import (
    EntityVersionConflict,
    ReviewConflictSpec,
    VersionedRepository,
)
from app.models.acquisition_case import AcquisitionCase
from app.models.event import ActorType


@dataclass(frozen=True)
class _Actor:
    kind: str
    id: str


WINNER = _Actor(kind=ActorType.OFFICER, id="officer:winner")
LOSER = _Actor(kind=ActorType.OFFICER, id="officer:loser")
OCCURRED = datetime(2024, 4, 17, 10, 0, tzinfo=timezone.utc)


def _seed_case(engine: Engine, case_reference: str, stage_key: str = "SIA") -> int:
    """Commit one case visible to two later transactions."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO administrative_area
                    (code, area_type, name, parent_code, state_key, path)
                VALUES (:area_code, 'state', :area_code, NULL, 'SUPPLIED', 'SUPPLIED')
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {"area_code": "RACE44"},
        )
        project_id = conn.execute(
            text(
                """
                INSERT INTO project
                    (name, implementing_authority, area_code, purpose_category,
                     sanctioned_extent, extent_unit)
                VALUES (:case_reference, 'PWD', 'RACE44', 'INFRASTRUCTURE', 100, 'hectare')
                RETURNING id
                """
            ),
            {"case_reference": case_reference},
        ).scalar_one()
        return conn.execute(
            text(
                """
                INSERT INTO acquisition_case
                    (case_reference, project_id, state_key, act_key, area_code, stage_key,
                     stage_set_effective_from, stage_entered_on)
                VALUES
                    (:case_reference, :project_id, 'RACE44', 'RFCTLARR_2013', 'RACE44',
                     :stage_key, DATE '2024-01-01', DATE '2024-01-01')
                RETURNING id
                """
            ),
            {
                "case_reference": case_reference,
                "project_id": project_id,
                "stage_key": stage_key,
            },
        ).scalar_one()


def _cleanup_case(engine: Engine, case_id: int) -> None:
    """Remove rows committed by this harness so later migrated-engine tests stay isolated."""
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


def _case_row(engine: Engine, case_id: int) -> dict[str, Any]:
    with engine.connect() as conn:
        return dict(
            conn.execute(
                text(
                    "SELECT id, entity_version, stage_key, pending_review_count, "
                    "risk_band FROM acquisition_case WHERE id = :id"
                ),
                {"id": case_id},
            )
            .mappings()
            .one()
        )


def _event_rows(engine: Engine, case_id: int) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        return list(
            conn.execute(
                text(
                    "SELECT event_type, actor_id, entity_version_after, payload "
                    "FROM event WHERE entity_type = 'acquisition_case' AND entity_id = :id "
                    "ORDER BY id"
                ),
                {"id": case_id},
            )
            .mappings()
            .all()
        )


def _losing_update(
    engine: Engine,
    *,
    case_id: int,
    ready: Event,
    result: Queue[EntityVersionConflict | BaseException | str],
    changes: Mapping[str, Any],
    submitted_prior: Mapping[str, Any],
    event_type: str,
    expected_stage: str | None = None,
    review_conflict: ReviewConflictSpec | None = None,
) -> None:
    """Run the contender on its own connection and report its outcome."""
    try:
        with engine.connect() as conn:
            tx = conn.begin()
            session = Session(bind=conn)
            try:
                ready.set()
                VersionedRepository.update(
                    session,
                    entity_type=AcquisitionCase,
                    entity_id=case_id,
                    expected_version=1,
                    changes=changes,
                    submitted_prior=submitted_prior,
                    actor=LOSER,
                    occurrence_time=OCCURRED,
                    event_type=event_type,
                    expected_stage=expected_stage,
                    review_conflict=review_conflict,
                )
                tx.commit()
                result.put("committed")
            except EntityVersionConflict as exc:
                tx.rollback()
                result.put(exc)
            finally:
                session.close()
    except BaseException as exc:  # pragma: no cover - surfaced by the main thread
        result.put(exc)


def _commit_winner_while_loser_waits(
    engine: Engine,
    *,
    case_id: int,
    winner_changes: Mapping[str, Any],
    winner_prior: Mapping[str, Any],
    loser_changes: Mapping[str, Any],
    loser_prior: Mapping[str, Any],
    event_type: str = "CASE_UPDATED",
    winner_expected_stage: str | None = None,
    loser_expected_stage: str | None = None,
    loser_review_conflict: ReviewConflictSpec | None = None,
) -> EntityVersionConflict:
    """Hold a row lock with the winner, then let the loser finish after commit."""
    with engine.connect() as winner_conn:
        winner_tx = winner_conn.begin()
        winner_session = Session(bind=winner_conn)
        try:
            VersionedRepository.update(
                winner_session,
                entity_type=AcquisitionCase,
                entity_id=case_id,
                expected_version=1,
                changes=winner_changes,
                submitted_prior=winner_prior,
                actor=WINNER,
                occurrence_time=OCCURRED,
                event_type=event_type,
                expected_stage=winner_expected_stage,
            )

            ready = Event()
            result: Queue[EntityVersionConflict | BaseException | str] = Queue()
            thread = Thread(
                target=_losing_update,
                kwargs={
                    "engine": engine,
                    "case_id": case_id,
                    "ready": ready,
                    "result": result,
                    "changes": loser_changes,
                    "submitted_prior": loser_prior,
                    "event_type": event_type,
                    "expected_stage": loser_expected_stage,
                    "review_conflict": loser_review_conflict,
                },
                daemon=True,
            )
            thread.start()
            assert ready.wait(3), "the losing transaction never reached its UPDATE"

            winner_tx.commit()
            thread.join(5)
            assert not thread.is_alive(), "the losing transaction stayed blocked after commit"
            outcome = result.get_nowait()
            if isinstance(outcome, BaseException) and not isinstance(outcome, EntityVersionConflict):
                raise outcome
            assert isinstance(outcome, EntityVersionConflict), f"loser unexpectedly {outcome!r}"
            return outcome
        finally:
            if winner_tx.is_active:
                winner_tx.rollback()
            winner_session.close()


def test_same_version_race_commits_exactly_one_and_appends_no_loser_event(
    migrated_engine: Engine,
) -> None:
    """R29.6/R29.5: of two same-version updates on two connections, exactly one lands."""
    case_id = _seed_case(migrated_engine, "RACE-44-ONE")
    try:
        conflict = _commit_winner_while_loser_waits(
            migrated_engine,
            case_id=case_id,
            winner_changes={"pending_review_count": 1},
            winner_prior={"pending_review_count": 0},
            loser_changes={"pending_review_count": 2},
            loser_prior={"pending_review_count": 0},
        )

        stored = _case_row(migrated_engine, case_id)
        assert stored["entity_version"] == 2
        assert stored["pending_review_count"] == 1
        assert conflict.envelope().details["current_entity_version"] == 2
        assert conflict.envelope().details["conflicting_actor_id"] == WINNER.id

        events = _event_rows(migrated_engine, case_id)
        assert len(events) == 1
        assert events[0]["actor_id"] == WINNER.id
        assert events[0]["entity_version_after"] == 2
    finally:
        _cleanup_case(migrated_engine, case_id)


def test_stage_transition_race_records_exactly_one_transition(migrated_engine: Engine) -> None:
    """R29.7: two transitions out of the same observed stage cannot both record."""
    case_id = _seed_case(migrated_engine, "RACE-44-STAGE", stage_key="SIA")
    try:
        conflict = _commit_winner_while_loser_waits(
            migrated_engine,
            case_id=case_id,
            winner_changes={"stage_key": "PRELIMINARY_NOTIFICATION"},
            winner_prior={"stage_key": "SIA"},
            loser_changes={"stage_key": "AWARD"},
            loser_prior={"stage_key": "SIA"},
            event_type="STAGE_TRANSITIONED",
            winner_expected_stage="SIA",
            loser_expected_stage="SIA",
        )

        stored = _case_row(migrated_engine, case_id)
        assert stored["entity_version"] == 2
        assert stored["stage_key"] == "PRELIMINARY_NOTIFICATION"
        assert conflict.envelope().details["attributes"] == [
            {
                "name": "stage_key",
                "submitted_prior": "SIA",
                "current": "PRELIMINARY_NOTIFICATION",
            }
        ]

        events = _event_rows(migrated_engine, case_id)
        assert len(events) == 1
        assert events[0]["event_type"] == "STAGE_TRANSITIONED"
        assert events[0]["payload"] == {
            "stage_key": {"from": "SIA", "to": "PRELIMINARY_NOTIFICATION"}
        }
    finally:
        _cleanup_case(migrated_engine, case_id)


def test_field_review_race_reports_the_winning_state_and_value(
    migrated_engine: Engine,
) -> None:
    """R29.8 shape: a rejected second review sees the first review's state and value."""
    case_id = _seed_case(migrated_engine, "RACE-44-REVIEW")
    try:
        conflict = _commit_winner_while_loser_waits(
            migrated_engine,
            case_id=case_id,
            winner_changes={"risk_band": "HIGH"},
            winner_prior={"risk_band": None},
            loser_changes={"risk_band": "LOW"},
            loser_prior={"risk_band": None},
            loser_review_conflict=ReviewConflictSpec(
                value_attribute="risk_band",
                review_state_attribute="stage_key",
            ),
        )

        details = conflict.envelope().details
        assert details["current_review_state"] == "SIA"
        assert details["attributes"] == [
            {"name": "risk_band", "submitted_prior": None, "current": "HIGH"}
        ]
        assert _case_row(migrated_engine, case_id)["risk_band"] == "HIGH"
        assert len(_event_rows(migrated_engine, case_id)) == 1
    finally:
        _cleanup_case(migrated_engine, case_id)


@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    winner_count=st.integers(min_value=1, max_value=10_000),
    loser_count=st.integers(min_value=1, max_value=10_000),
)
def test_property_69_same_version_race_has_one_winner_and_one_unchanged_loser(
    migrated_engine: Engine, winner_count: int, loser_count: int
) -> None:
    """Property 69 over a real two-connection race: the loser leaves no trace."""
    case_id = _seed_case(migrated_engine, f"RACE-44-PROP-{winner_count}-{loser_count}")
    try:
        before_loser = {"pending_review_count": 0}
        _commit_winner_while_loser_waits(
            migrated_engine,
            case_id=case_id,
            winner_changes={"pending_review_count": winner_count},
            winner_prior=before_loser,
            loser_changes={"pending_review_count": loser_count},
            loser_prior=before_loser,
        )

        stored = _case_row(migrated_engine, case_id)
        assert stored["entity_version"] == 2
        assert stored["pending_review_count"] == winner_count
        events = _event_rows(migrated_engine, case_id)
        assert len(events) == 1
        assert events[0]["payload"] == {
            "pending_review_count": {"from": 0, "to": winner_count}
        }
    finally:
        _cleanup_case(migrated_engine, case_id)
