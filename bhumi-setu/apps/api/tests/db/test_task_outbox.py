"""The transactional outbox: producer-side atomicity and dispatcher semantics (§5.2).

Two guarantees are under test, and they are deliberately asymmetric:

* the *insert* a producer performs is atomic with its state change and
  de-duplicated by ``idempotency_key`` — a rolled-back producer enqueues nothing,
  and a retried producer enqueues once;
* the *publish* the dispatcher performs is at-least-once — it locks a batch with
  ``FOR UPDATE SKIP LOCKED``, publishes each row, then stamps ``enqueued_at`` so a
  crash between publish and stamp costs a duplicate delivery, never a lost one.

Most tests here need the real database: the partial index, the unique constraint,
``SKIP LOCKED`` and the ``bhumisetu_app`` grants are PostgreSQL behaviours, so they
run against the migrated database and skip where none is reachable (the ``db_connection``
fixture). ``test_publish_to_broker_*`` needs neither a database nor a broker and
runs everywhere.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, event, func, select, text
from sqlalchemy.orm import Session

from app.db import outbox
from app.db.outbox import DISPATCH_BATCH, dispatch_outbox, dispatch_pending, enqueue
from app.models.task_outbox import TaskOutbox

OCR_TASK = "app.services.ocr.extract_document"


def orm_session(db_connection: Connection) -> Session:
    """A session sharing the fixture's always-rolled-back transaction."""
    return Session(bind=db_connection, join_transaction_mode="create_savepoint")


class Recorder:
    """A stand-in publisher: records (queue, task_name, kwargs) instead of Redis."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def __call__(self, queue: str, task_name: str, kwargs) -> None:
        self.calls.append((queue, task_name, dict(kwargs)))


def pending_ids(db_connection: Connection) -> list[int]:
    return list(
        db_connection.scalars(
            text(
                "SELECT id FROM task_outbox WHERE enqueued_at IS NULL "
                "ORDER BY created_at, id"
            )
        )
    )


# ---------------------------------------------------------------------------
# enqueue — the producer side
# ---------------------------------------------------------------------------


def test_enqueue_inserts_one_pending_row(db_connection: Connection) -> None:
    session = orm_session(db_connection)
    row_id = enqueue(
        session,
        queue="ocr",
        task_name=OCR_TASK,
        kwargs={"document_id": 7},
        idempotency_key="extract:7",
    )
    session.flush()
    assert row_id is not None

    stored = session.get(TaskOutbox, row_id)
    assert stored is not None
    assert stored.queue == "ocr"
    assert stored.task_name == OCR_TASK
    assert stored.kwargs == {"document_id": 7}
    assert stored.enqueued_at is None, "a freshly enqueued row is pending"


def test_enqueue_deduplicates_on_the_idempotency_key(db_connection: Connection) -> None:
    """A producer that retries its own transaction records the side effect once."""
    session = orm_session(db_connection)
    first = enqueue(
        session, queue="ocr", task_name=OCR_TASK,
        kwargs={"document_id": 7}, idempotency_key="extract:7",
    )
    second = enqueue(
        session, queue="ocr", task_name=OCR_TASK,
        kwargs={"document_id": 7}, idempotency_key="extract:7",
    )
    session.flush()

    assert first is not None
    assert second is None, "the duplicate key returns None rather than a second id"
    count = session.execute(
        select(func.count()).select_from(TaskOutbox).where(
            TaskOutbox.idempotency_key == "extract:7"
        )
    ).scalar_one()
    assert count == 1


def test_a_rolled_back_producer_transaction_enqueues_nothing(
    db_connection: Connection,
) -> None:
    """§5.2's point: the enqueue shares the caller's transaction, so an abandoned
    state change abandons the side effect too — Redis never hears about it."""
    session = orm_session(db_connection)
    savepoint = session.begin_nested()
    enqueue(
        session, queue="ocr", task_name=OCR_TASK,
        kwargs={"document_id": 7}, idempotency_key="extract:7",
    )
    session.flush()
    savepoint.rollback()

    remaining = session.execute(
        select(func.count()).select_from(TaskOutbox).where(
            TaskOutbox.idempotency_key == "extract:7"
        )
    ).scalar_one()
    assert remaining == 0


def test_enqueue_rejects_an_undeclared_queue(db_connection: Connection) -> None:
    """A row with a queue nobody declared would fail every dispatch cycle and block
    the backlog behind it (task_create_missing_queues is False). Caught at enqueue,
    so the producer's transaction aborts instead."""
    session = orm_session(db_connection)
    with pytest.raises(ValueError, match="unknown outbox queue"):
        enqueue(
            session, queue="not_a_queue", task_name=OCR_TASK,
            kwargs={}, idempotency_key="x",
        )


# ---------------------------------------------------------------------------
# dispatch_pending — the dispatcher side
# ---------------------------------------------------------------------------


def test_dispatch_publishes_each_pending_row_then_stamps_it(
    db_connection: Connection,
) -> None:
    session = orm_session(db_connection)
    enqueue(session, queue="ocr", task_name=OCR_TASK,
            kwargs={"document_id": 1}, idempotency_key="extract:1")
    enqueue(session, queue="maintenance", task_name="app.security.otp.send_otp",
            kwargs={"case_ref": "MH-1"}, idempotency_key="otp:MH-1")
    session.flush()

    recorder = Recorder()
    dispatched = dispatch_pending(session, recorder)

    assert len(dispatched) == 2
    assert recorder.calls == [
        ("ocr", OCR_TASK, {"document_id": 1}),
        ("maintenance", "app.security.otp.send_otp", {"case_ref": "MH-1"}),
    ]
    # Every dispatched row now carries a stamp and has left the pending set.
    for row_id in dispatched:
        assert session.get(TaskOutbox, row_id).enqueued_at is not None
    assert pending_ids(db_connection) == []


def test_dispatch_is_ordered_oldest_first(db_connection: Connection) -> None:
    """Beat publishes in insertion order; the partial index is on created_at."""
    session = orm_session(db_connection)
    ids = [
        enqueue(session, queue="ocr", task_name=OCR_TASK,
                kwargs={"n": n}, idempotency_key=f"k:{n}")
        for n in range(3)
    ]
    session.flush()

    dispatched = dispatch_pending(orm_session(db_connection), Recorder())
    assert dispatched == ids


def test_dispatch_skips_already_published_rows(db_connection: Connection) -> None:
    """A redelivered dispatch must not re-publish a stamped row — that is what makes
    the task idempotent (§13.4)."""
    session = orm_session(db_connection)
    enqueue(session, queue="ocr", task_name=OCR_TASK,
            kwargs={"document_id": 1}, idempotency_key="extract:1")
    session.flush()

    first = Recorder()
    dispatch_pending(session, first)
    assert len(first.calls) == 1

    second = Recorder()
    dispatched_again = dispatch_pending(session, second)
    assert dispatched_again == []
    assert second.calls == [], "a stamped row was published a second time"


def test_dispatch_respects_the_batch_limit(db_connection: Connection) -> None:
    """A large backlog drains over several 2-second cycles, not one long run."""
    session = orm_session(db_connection)
    ids = [
        enqueue(session, queue="ocr", task_name=OCR_TASK,
                kwargs={"n": n}, idempotency_key=f"k:{n}")
        for n in range(3)
    ]
    session.flush()

    recorder = Recorder()
    dispatched = dispatch_pending(orm_session(db_connection), recorder, limit=2)
    assert dispatched == ids[:2], "only the two oldest rows were published"
    assert len(recorder.calls) == 2
    # The third stays pending for the next cycle.
    assert pending_ids(db_connection) == [ids[2]]


def test_dispatch_of_an_empty_backlog_publishes_nothing(
    db_connection: Connection,
) -> None:
    recorder = Recorder()
    assert dispatch_pending(orm_session(db_connection), recorder) == []
    assert recorder.calls == []


def test_dispatch_locks_pending_rows_with_skip_locked(
    db_connection: Connection,
) -> None:
    """FOR UPDATE SKIP LOCKED is what lets two dispatchers take disjoint batches
    rather than double-publishing. Assert the clause reaches the database."""
    session = orm_session(db_connection)
    enqueue(session, queue="ocr", task_name=OCR_TASK,
            kwargs={"document_id": 1}, idempotency_key="extract:1")
    session.flush()

    statements: list[str] = []

    def _capture(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        statements.append(statement)

    event.listen(db_connection.engine, "before_cursor_execute", _capture)
    try:
        dispatch_pending(session, Recorder())
    finally:
        event.remove(db_connection.engine, "before_cursor_execute", _capture)

    locking = [s for s in statements if "FOR UPDATE" in s.upper()]
    assert locking, f"no FOR UPDATE statement was issued; saw {statements}"
    assert any("SKIP LOCKED" in s.upper() for s in locking), locking


# ---------------------------------------------------------------------------
# dispatch_outbox — the task wiring (unit_of_work + broker), driven over a session
# ---------------------------------------------------------------------------


def test_dispatch_outbox_task_publishes_the_backlog(
    db_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The task opens a unit_of_work and publishes through the broker seam. Both are
    redirected here — the transaction onto the test connection, the publish onto a
    recorder — so the wiring is exercised without a real engine or Redis."""
    from contextlib import contextmanager

    session = orm_session(db_connection)
    enqueue(session, queue="ocr", task_name=OCR_TASK,
            kwargs={"document_id": 1}, idempotency_key="extract:1")
    session.flush()

    @contextmanager
    def fake_unit_of_work(**_kwargs):
        yield session
        session.flush()

    recorder = Recorder()
    monkeypatch.setattr(outbox, "unit_of_work", fake_unit_of_work)
    monkeypatch.setattr(outbox, "_publish_to_broker", recorder)

    published = dispatch_outbox()
    assert published == 1
    assert recorder.calls == [("ocr", OCR_TASK, {"document_id": 1})]
    assert pending_ids(db_connection) == []


# ---------------------------------------------------------------------------
# The broker seam — no database, no Redis
# ---------------------------------------------------------------------------


def test_publish_to_broker_sends_to_the_stored_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stored queue overrides Celery's route resolution, so the queue the
    producer chose is the queue the task lands on."""
    sent: list[dict] = []

    def fake_send_task(name, *, kwargs, queue):
        sent.append({"name": name, "kwargs": kwargs, "queue": queue})

    monkeypatch.setattr(outbox.celery_app, "send_task", fake_send_task)

    outbox._publish_to_broker("ocr", OCR_TASK, {"document_id": 42})
    assert sent == [{"name": OCR_TASK, "kwargs": {"document_id": 42}, "queue": "ocr"}]


def test_dispatch_batch_default_is_bounded() -> None:
    """A default bound exists so one run cannot lock the whole table."""
    assert isinstance(DISPATCH_BATCH, int) and DISPATCH_BATCH > 0


# ---------------------------------------------------------------------------
# Schema: the unique key, the partial index, and the grants
# ---------------------------------------------------------------------------


def test_the_idempotency_key_is_unique_at_the_database(
    db_connection: Connection,
) -> None:
    """enqueue leans on this constraint for its ON CONFLICT. A raw double insert
    that bypasses ON CONFLICT must still be refused."""
    db_connection.execute(
        text(
            "INSERT INTO task_outbox (queue, task_name, kwargs, idempotency_key) "
            "VALUES ('ocr', :t, '{}'::jsonb, 'dup')"
        ),
        {"t": OCR_TASK},
    )
    with pytest.raises(Exception, match="duplicate key|unique constraint"):
        db_connection.execute(
            text(
                "INSERT INTO task_outbox (queue, task_name, kwargs, idempotency_key) "
                "VALUES ('ocr', :t, '{}'::jsonb, 'dup')"
            ),
            {"t": OCR_TASK},
        )


def test_the_pending_index_only_covers_undispatched_rows(
    db_connection: Connection,
) -> None:
    """Partial on `enqueued_at IS NULL`, so the dispatcher's index is the size of
    the backlog rather than of history."""
    definition = db_connection.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'task_outbox_pending'")
    ).scalar_one()
    assert "WHERE" in definition and "enqueued_at IS NULL" in definition, definition


def test_the_application_role_can_enqueue_and_stamp_but_not_delete(
    db_connection: Connection,
) -> None:
    """Producers INSERT, the dispatcher UPDATEs enqueued_at, neither DELETEs —
    mirroring event and personal_datum. Asserted as the app role, because a
    superuser is not subject to the grant."""
    db_connection.execute(text("SET LOCAL ROLE bhumisetu_app"))
    row_id = db_connection.execute(
        text(
            "INSERT INTO task_outbox (queue, task_name, kwargs, idempotency_key) "
            "VALUES ('ocr', :t, '{}'::jsonb, 'k') RETURNING id"
        ),
        {"t": OCR_TASK},
    ).scalar_one()
    db_connection.execute(
        text("UPDATE task_outbox SET enqueued_at = now() WHERE id = :id"),
        {"id": row_id},
    )
    with pytest.raises(Exception, match="permission denied"):
        db_connection.execute(
            text("DELETE FROM task_outbox WHERE id = :id"), {"id": row_id}
        )
