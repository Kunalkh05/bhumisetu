"""``task_outbox`` — how a non-database side effect joins a transaction (§5.2).

The problem this table exists for
---------------------------------

R4.8 makes a state change and its event append atomic: both commit or neither
does. But a Celery enqueue, an SMS send and a presigned-URL issuance are not
database writes, and Redis and MinIO cannot be enrolled in the PostgreSQL
transaction. Publish an OCR enqueue *before* the upload transaction commits and a
rolled-back upload leaves a worker chasing a document that does not exist;
publish *after* and a crash in the gap loses the job.

The resolution is to make the *decision* to perform the side effect a row in this
table, written on the caller's session inside the same ``unit_of_work()`` as the
state change. The row is durable exactly when the state change is, and gone
exactly when it rolled back. ``app/db/outbox.py``'s ``dispatch_outbox`` then
publishes the durable rows to Redis out of band, so the broker never learns about
work that was abandoned.

Why the table is here and the logic is not
------------------------------------------

A mapped table is declared under ``app/models/`` and nowhere else, because
``Base.metadata`` is walked by the schema guards (task 2.7) and the retention
category walk (task 25.2), and a table declared in a service or plumbing module
would sit outside that walk (see ``app/db/base.py``). So the *table* lives here
while the ``enqueue`` helper and the ``dispatch_outbox`` task live in
``app/db/outbox.py`` — exactly as the ``event`` table lives here while
``EventLog.append`` lives in ``app/db/event_log.py``.

This module deliberately imports only SQLAlchemy and :class:`Base`. It must stay
free of any Celery import so that ``all_metadata()`` — called by Alembic and by
the schema-guard tests — never drags in the broker configuration, which several
processes (§3.4) do not hold.

Columns
-------

``idempotency_key`` is UNIQUE so ``enqueue`` can insert with ``ON CONFLICT DO
NOTHING`` and a producer that retries its transaction records the side effect
once. ``enqueued_at`` is NULL until the dispatcher publishes the row; it is set,
never cleared, and the row is retained rather than deleted so the table doubles
as an audit trail of what was published and when. ``kwargs`` is the task's
argument mapping, stored as JSONB so the dispatcher can hand it straight to
``send_task``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["TaskOutbox"]


class TaskOutbox(Base):
    """One durable intent to perform a non-database side effect (§5.2)."""

    __tablename__ = "task_outbox"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    queue: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "The §13.7 queue to publish to. Stored rather than re-derived at "
            "dispatch so the producer's routing intent is a property of the row."
        ),
    )
    task_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The registered Celery task name, e.g. app.services.ocr.extract_document.",
    )
    kwargs: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        comment="The task's keyword arguments, handed straight to send_task.",
    )

    idempotency_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Producer-supplied key for the work this row stands for. UNIQUE, so "
            "enqueue can ON CONFLICT DO NOTHING and a retried producer transaction "
            "records the side effect once. Publish remains at-least-once (§13.4)."
        ),
    )

    enqueued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "NULL until the dispatcher publishes the row to Redis, then set once. "
            "The partial index below covers only the NULL (pending) rows, so a "
            "published row falls out of the dispatcher's working set."
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Insert time. The dispatcher publishes in this order (oldest first).",
    )

    __table_args__ = (
        # A UNIQUE constraint rather than a plain unique index, so `\d task_outbox`
        # documents the idempotency guarantee in the schema itself.
        UniqueConstraint("idempotency_key", name="task_outbox_idempotency_key"),
        # Partial: the dispatcher reads only `enqueued_at IS NULL`, so the index
        # is the size of the backlog, not of history. A row leaves it on publish.
        Index(
            "task_outbox_pending",
            created_at,
            postgresql_where=enqueued_at.is_(None),
        ),
        {
            "comment": (
                "Transactional outbox for non-database side effects (§5.2): Celery "
                "enqueues, SMS sends, presigned-URL issuance. A producer inserts a "
                "row inside its transaction; dispatch_outbox publishes durable rows "
                "to Redis at-least-once, which is why every task is idempotent "
                "(§13.4)."
            )
        },
    )

    @property
    def is_dispatched(self) -> bool:
        return self.enqueued_at is not None

    def __repr__(self) -> str:
        state = "dispatched" if self.is_dispatched else "pending"
        return (
            f"<TaskOutbox {self.id} {self.task_name} -> {self.queue} "
            f"{state} key={self.idempotency_key!r}>"
        )
