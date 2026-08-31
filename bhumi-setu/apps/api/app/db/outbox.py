"""The transactional outbox: enqueue inside a transaction, publish out of band.

This module holds the two halves of §5.2's outbox. The table itself is declared
in ``app/models/task_outbox.py`` (a mapped table lives under ``app/models/`` so
the metadata-walk guards see it); the *behaviour* lives here, next to
``session.py`` whose ``unit_of_work()`` it depends on.

The producer side — :func:`enqueue`
-----------------------------------

A caller records a non-database side effect by calling :func:`enqueue` on the
session it is already holding, inside its ``unit_of_work()``::

    with unit_of_work() as session:
        document = document_service.store(session, ...)   # state change + event
        enqueue(session, queue="ocr",
                task_name="app.services.ocr.extract_document",
                kwargs={"document_id": document.id},
                idempotency_key=f"extract:{document.id}")

The insert shares the caller's transaction, so the row is durable exactly when
the upload is and absent exactly when the upload rolled back. Redis never learns
about an abandoned upload, because nothing was published — only a row was written,
and it went away with everything else. Wiring specific producers (OCR, SMS,
presigned URLs) belongs to their own tasks; this module provides only the seam.

The dispatcher side — :func:`dispatch_outbox`
--------------------------------------------

``dispatch_outbox`` runs on the ``maintenance`` queue every two seconds
(§13.7 beat schedule). It locks a batch of unpublished rows with ``FOR UPDATE
SKIP LOCKED`` — so two dispatchers running concurrently take disjoint batches
rather than double-publishing — publishes each to Redis, and stamps
``enqueued_at`` so the row leaves the pending set.

At-least-once, deliberately
---------------------------

The insert is de-duplicated by the unique ``idempotency_key``. The *publish* is
not: if the dispatcher publishes to Redis and then fails to commit ``enqueued_at``
(a crash, a lost connection), the row stays pending and is published again on the
next cycle. That is why §13.4 requires every task to be idempotent. Publishing
before stamping — rather than after — is the safe order: a duplicate delivery is
recoverable by an idempotent consumer, a lost delivery is not.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.session import unit_of_work
from app.models.task_outbox import TaskOutbox
from app.workers.celery_app import QUEUE_NAMES, celery_app

__all__ = ["dispatch_outbox", "dispatch_pending", "enqueue"]

#: How many pending rows one dispatch run locks, publishes and stamps. A bound so
#: a large backlog drains over several 2-second cycles instead of one run holding
#: locks over thousands of rows. Not a statutory period — a batch size.
DISPATCH_BATCH: int = 100

#: The signature of the side effect that actually reaches Redis. Injected into
#: :func:`dispatch_pending` so the transactional and locking logic can be tested
#: against a real database without a broker.
Publisher = Callable[[str, str, Mapping[str, Any]], None]


def enqueue(
    session: Session,
    *,
    queue: str,
    task_name: str,
    kwargs: Mapping[str, Any],
    idempotency_key: str,
) -> int | None:
    """Record a non-database side effect on the caller's transaction (§5.2).

    Inserts one ``task_outbox`` row using the session the caller already holds, so
    the side effect becomes durable atomically with the state change it belongs to.
    The dispatcher publishes it later; nothing reaches Redis here.

    De-duplicates on ``idempotency_key`` with ``ON CONFLICT DO NOTHING``, so a
    producer that retries its own transaction, or two producers racing on the same
    logical work, record the side effect exactly once.

    :param queue: one of the §13.7 queue names. Validated here so a typo aborts the
        producer's transaction rather than becoming a row that fails every dispatch
        cycle and blocks the backlog behind it.
    :param idempotency_key: a key derived from the work this stands for (a document
        id, a case reference plus nonce), stable across the producer's retries.
    :returns: the new row id, or ``None`` when an identical key was already present.
    """
    if queue not in QUEUE_NAMES:
        raise ValueError(
            f"unknown outbox queue {queue!r}; must be one of {sorted(QUEUE_NAMES)}. "
            "A row with an undeclared queue would fail every dispatch cycle "
            "(task_create_missing_queues is False)."
        )

    result = session.execute(
        pg_insert(TaskOutbox)
        .values(
            queue=queue,
            task_name=task_name,
            kwargs=dict(kwargs),
            idempotency_key=idempotency_key,
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
        .returning(TaskOutbox.id)
    )
    return result.scalar_one_or_none()


def dispatch_pending(
    session: Session,
    publish: Publisher,
    *,
    limit: int = DISPATCH_BATCH,
) -> list[int]:
    """Publish a batch of pending rows and stamp them, on the caller's transaction.

    The core of :func:`dispatch_outbox`, separated so it can be exercised against a
    real database with an injected ``publish`` and no broker.

    Locks up to ``limit`` unpublished rows oldest-first with ``FOR UPDATE SKIP
    LOCKED`` — concurrent dispatchers therefore take disjoint batches — calls
    ``publish(queue, task_name, kwargs)`` for each, then sets ``enqueued_at`` so the
    rows leave the pending set. Publishing precedes stamping so a failure between
    them leaves the row pending for a retry (at-least-once) rather than marking it
    published without having published it.

    :returns: the ids published, in dispatch order.
    """
    rows = session.execute(
        select(
            TaskOutbox.id,
            TaskOutbox.queue,
            TaskOutbox.task_name,
            TaskOutbox.kwargs,
        )
        .where(TaskOutbox.enqueued_at.is_(None))
        .order_by(TaskOutbox.created_at, TaskOutbox.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()

    if not rows:
        return []

    for row in rows:
        publish(row.queue, row.task_name, row.kwargs)

    dispatched = [row.id for row in rows]
    session.execute(
        update(TaskOutbox)
        .where(TaskOutbox.id.in_(dispatched))
        .values(enqueued_at=func.now())
    )
    session.flush()
    return dispatched


def _publish_to_broker(queue: str, task_name: str, kwargs: Mapping[str, Any]) -> None:
    """Hand one row to Celery. The explicit ``queue`` overrides route resolution,
    so the queue the producer chose is the queue the task lands on."""
    celery_app.send_task(task_name, kwargs=dict(kwargs), queue=queue)


@celery_app.task(name="app.db.outbox.dispatch_outbox")
def dispatch_outbox() -> int:
    """Publish the pending outbox to Redis (§5.2, ``maintenance`` queue, every 2s).

    Opens one ``unit_of_work()`` and dispatches a bounded batch. On any error —
    Redis unreachable, a connection lost mid-batch — the transaction rolls back,
    ``enqueued_at`` is not stamped, and the next beat tick retries. Idempotent by
    construction: an already-published row has ``enqueued_at`` set and is not in the
    pending set the next run reads.

    :returns: the number of rows published this run.
    """
    with unit_of_work() as session:
        dispatched = dispatch_pending(session, _publish_to_broker)
    return len(dispatched)
