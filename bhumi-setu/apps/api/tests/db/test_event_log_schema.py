"""The event log's append-only guarantee and its ordering (§5.1).

R4.2 is enforced by a revoked grant, and that has a consequence for testing which
is easy to get wrong: **a superuser is not subject to table privileges.** Local
development connects as a superuser, so a test that simply tries to UPDATE an event
succeeds, the assertion is written to expect success, and the guarantee is verified
nowhere except production.

Every test here that claims to exercise the revoke therefore does ``SET LOCAL ROLE
bhumisetu_app`` first. ``test_the_revoke_is_not_exercised_as_superuser`` exists to
prove the distinction is real rather than theoretical.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.models.event import Event, EventImmutable

NOW = datetime(2025, 3, 4, 9, 12, 44, tzinfo=timezone.utc)


def insert_event(
    connection: Connection,
    *,
    event_type: str = "CASE_CREATED",
    entity_type: str = "acquisition_case",
    entity_id: int = 1,
    occurrence_time: datetime = NOW,
    payload: str = '{"stage_key": {"from": null, "to": "SIA"}}',
    **extra,
) -> int:
    columns = {
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "actor_type": "OFFICER",
        "actor_id": "officer:412",
        "occurrence_time": occurrence_time,
        **extra,
    }
    names = ", ".join(columns)
    placeholders = ", ".join(f":{name}" for name in columns)
    return connection.execute(
        text(
            f"INSERT INTO event ({names}, payload) "
            f"VALUES ({placeholders}, CAST(:payload AS jsonb)) RETURNING id"
        ),
        {**columns, "payload": payload},
    ).scalar_one()


def as_app_role(connection: Connection) -> None:
    """Drop to the application role for the rest of the transaction.

    Without this every privilege assertion below passes for the wrong reason.
    """
    connection.execute(text("SET LOCAL ROLE bhumisetu_app"))


# ---------------------------------------------------------------------------
# R4.2 — append-only, enforced by the database
# ---------------------------------------------------------------------------


def test_the_application_role_can_append(db_connection: Connection) -> None:
    as_app_role(db_connection)
    assert insert_event(db_connection) > 0


def test_the_application_role_cannot_update_a_stored_event(
    db_connection: Connection,
) -> None:
    event_id = insert_event(db_connection)
    as_app_role(db_connection)
    with pytest.raises(Exception, match="permission denied"):
        db_connection.execute(
            text("UPDATE event SET event_type = 'TAMPERED' WHERE id = :id"),
            {"id": event_id},
        )


def test_the_application_role_cannot_delete_a_stored_event(
    db_connection: Connection,
) -> None:
    event_id = insert_event(db_connection)
    as_app_role(db_connection)
    with pytest.raises(Exception, match="permission denied"):
        db_connection.execute(text("DELETE FROM event WHERE id = :id"), {"id": event_id})


def test_the_application_role_cannot_truncate_the_log(
    db_connection: Connection,
) -> None:
    """TRUNCATE is not covered by REVOKE UPDATE, DELETE — it needs its own check.

    Worth asserting explicitly: someone reading the migration could reasonably
    assume the revoke covers every destructive statement, and it does not.
    """
    insert_event(db_connection)
    as_app_role(db_connection)
    with pytest.raises(Exception, match="permission denied|must be owner"):
        db_connection.execute(text("TRUNCATE event"))


def test_the_revoke_is_not_exercised_as_superuser(db_connection: Connection) -> None:
    """Proves the SET ROLE in every test above is load-bearing.

    A superuser bypasses table privileges entirely. If this test ever fails —
    meaning a superuser UPDATE was refused — then something other than the grant is
    doing the enforcing, and the other tests are no longer testing what they claim.
    """
    event_id = insert_event(db_connection)
    db_connection.execute(
        text("UPDATE event SET event_type = 'SUPERUSER_CAN' WHERE id = :id"),
        {"id": event_id},
    )
    assert db_connection.execute(
        text("SELECT event_type FROM event WHERE id = :id"), {"id": event_id}
    ).scalar_one() == "SUPERUSER_CAN"


# ---------------------------------------------------------------------------
# The ORM guard — a convenience, not the guarantee
# ---------------------------------------------------------------------------


def test_the_orm_refuses_a_mutation_before_it_reaches_the_database(
    db_connection: Connection,
) -> None:
    """So the traceback names the offending code rather than surfacing as a psycopg
    permission error naming only the connection."""
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    event_id = insert_event(db_connection)
    stored = session.get(Event, event_id)
    assert stored is not None

    stored.event_type = "TAMPERED"
    with pytest.raises(EventImmutable, match="append-only"):
        session.flush()


def test_the_orm_refuses_a_delete(db_connection: Connection) -> None:
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    stored = session.get(Event, insert_event(db_connection))
    session.delete(stored)
    with pytest.raises(EventImmutable, match="append-only"):
        session.flush()


def test_reading_an_event_does_not_trip_the_guard(db_connection: Connection) -> None:
    """SQLAlchemy populates attributes on load, so a naive __setattr__ guard would
    make the log unreadable. Loading many events must stay clean."""
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    for index in range(5):
        insert_event(db_connection, entity_id=index)
    session.flush()
    assert len(session.query(Event).all()) >= 5


# ---------------------------------------------------------------------------
# R4.3, R4.4 — two timestamps, and backdated appends
# ---------------------------------------------------------------------------


def test_occurrence_and_recording_time_are_independent(
    db_connection: Connection,
) -> None:
    """R4.3. A notice served last week, recorded today."""
    event_id = insert_event(db_connection, occurrence_time=NOW - timedelta(days=7))
    row = db_connection.execute(
        text("SELECT occurrence_time, recording_time FROM event WHERE id = :id"),
        {"id": event_id},
    ).one()
    assert row.occurrence_time < row.recording_time


def test_an_event_may_be_backdated_before_an_existing_one(
    db_connection: Connection,
) -> None:
    """R4.4 permits it, which is exactly why KNOWABLE_AT and OCCURRED_BY must differ
    (task 3.5). A single-predicate implementation cannot express both."""
    later = insert_event(db_connection, occurrence_time=NOW)
    earlier = insert_event(db_connection, occurrence_time=NOW - timedelta(days=30))

    ordered = db_connection.scalars(
        text(
            "SELECT id FROM event WHERE entity_type = 'acquisition_case' "
            "AND entity_id = 1 ORDER BY occurrence_time, id"
        )
    ).all()
    assert ordered == [earlier, later], "backdated event did not sort first"
    assert earlier > later, "the backdated event has the higher id, as expected"


def test_ordering_is_total_when_occurrence_times_tie(
    db_connection: Connection,
) -> None:
    """The id tiebreak. R17.5 needs a deterministic fold, and officers enter dates
    rather than timestamps, so ties are routine rather than exotic."""
    ids = [insert_event(db_connection, occurrence_time=NOW) for _ in range(6)]
    for _ in range(4):
        ordered = db_connection.scalars(
            text(
                "SELECT id FROM event WHERE entity_type = 'acquisition_case' "
                "AND entity_id = 1 ORDER BY occurrence_time, id"
            )
        ).all()
        assert ordered == sorted(ids), "tied occurrence times did not order stably"


# ---------------------------------------------------------------------------
# R4.6 — corrections reference, never overwrite
# ---------------------------------------------------------------------------


def test_a_correction_references_the_event_it_corrects(
    db_connection: Connection,
) -> None:
    original = insert_event(db_connection, event_type="NOTICE_ISSUED")
    correction = insert_event(
        db_connection, event_type="NOTICE_ISSUE_CORRECTED", corrects_event_id=original
    )
    row = db_connection.execute(
        text("SELECT corrects_event_id FROM event WHERE id = :id"), {"id": correction}
    ).scalar_one()
    assert row == original

    still_there = db_connection.execute(
        text("SELECT event_type FROM event WHERE id = :id"), {"id": original}
    ).scalar_one()
    assert still_there == "NOTICE_ISSUED", "the corrected event was altered"


def test_a_corrected_event_cannot_be_deleted_out_from_under_its_correction(
    db_connection: Connection,
) -> None:
    """RESTRICT on corrects_event_id. Even as superuser, removing the original would
    leave a correction referencing nothing."""
    original = insert_event(db_connection)
    insert_event(db_connection, corrects_event_id=original)
    with pytest.raises(Exception, match="violates foreign key constraint"):
        db_connection.execute(text("DELETE FROM event WHERE id = :id"), {"id": original})


# ---------------------------------------------------------------------------
# txid and indexes
# ---------------------------------------------------------------------------


def test_txid_records_the_writing_transaction(db_connection: Connection) -> None:
    """Task 3.7's deferred trigger asserts a mutated row got an event in the *same*
    transaction, so this has to be the real transaction id."""
    first = insert_event(db_connection, entity_id=1)
    second = insert_event(db_connection, entity_id=2)
    txids = db_connection.scalars(
        text("SELECT DISTINCT txid FROM event WHERE id IN (:a, :b)"),
        {"a": first, "b": second},
    ).all()
    assert len(txids) == 1, "events in one transaction recorded different txids"
    assert txids[0] == db_connection.execute(
        text("SELECT txid_current()")
    ).scalar_one()


def test_the_entity_as_of_read_uses_its_index(db_connection: Connection) -> None:
    insert_event(db_connection)
    db_connection.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        db_connection.scalars(
            text(
                """
                EXPLAIN SELECT * FROM event
                 WHERE entity_type = 'acquisition_case' AND entity_id = 1
                   AND occurrence_time <= now()
                 ORDER BY occurrence_time, id
                """
            )
        )
    )
    assert "event_entity_asof" in plan, plan


def test_the_case_timeline_read_uses_its_index(db_connection: Connection) -> None:
    insert_event(db_connection, case_id=99)
    db_connection.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        db_connection.scalars(
            text(
                "EXPLAIN SELECT * FROM event WHERE case_id = 99 "
                "ORDER BY occurrence_time, id"
            )
        )
    )
    assert "event_case_asof" in plan, plan
