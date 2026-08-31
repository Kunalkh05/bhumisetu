"""task_outbox: the transactional outbox for non-database side effects.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-31

Task 3.8. §5.2's table, its unique idempotency key, and the partial index the
dispatcher polls.

Why the table exists
--------------------

A Celery enqueue, an SMS send and a presigned-URL issuance are side effects that
Redis and an object store cannot enrol in the PostgreSQL transaction that decides
whether the state change they belong to actually happened. Publish the enqueue
before the transaction commits and a rolled-back upload leaves an OCR job in
flight against a document that never existed; publish after and a crash between
commit and publish loses the job. Neither ordering is safe on its own.

The outbox makes the *intent* to perform the side effect part of the same
transaction as the state change: a producer inserts a row here inside its
``unit_of_work()`` (§5.2), so the row is durable exactly when the state change is
and absent exactly when the state change rolled back. ``dispatch_outbox``
(``app/db/outbox.py``) then publishes the durable rows to Redis on the
``maintenance`` queue, out of band, every two seconds.

``idempotency_key`` is UNIQUE, not decorative
---------------------------------------------

The producer supplies a key derived from the work it stands for — a document id,
a case reference plus a passcode nonce. The unique constraint lets
``enqueue`` insert with ``ON CONFLICT DO NOTHING``, so a producer that retries its
own transaction records the side effect once rather than twice. That is the
*insert* side of the guarantee; the *publish* side is at-least-once, because the
dispatcher may publish to Redis and then fail to commit ``enqueued_at``. The two
together are why every task must be idempotent (§13.4): the outbox de-duplicates
what it can and leans on idempotent consumers for what it cannot.

The partial index is the dispatcher's whole working set
------------------------------------------------------

``dispatch_outbox`` reads only rows with ``enqueued_at IS NULL``. A partial index
on exactly that predicate keeps the index the size of the backlog rather than the
size of history — dispatched rows fall out of it — so polling stays cheap as the
table grows. Rows are kept after dispatch (``enqueued_at`` set, not deleted) so
the table is an audit trail of what was published and when, and so a redelivered
dispatch cannot resurrect a already-published row into the pending set.

Grants
------

The application role inserts rows (producers) and updates ``enqueued_at`` (the
dispatcher). It never deletes: pruning dispatched rows is a maintenance concern
for a later task, and a producer or dispatcher has no reason to remove one. This
mirrors ``event`` and ``personal_datum`` — the role gets exactly the verbs its
code paths use.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_outbox",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("queue", sa.Text(), nullable=False),
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column("kwargs", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("idempotency_key", name="task_outbox_idempotency_key"),
        comment=(
            "Transactional outbox for non-database side effects (§5.2): Celery "
            "enqueues, SMS sends, presigned-URL issuance. A producer inserts a row "
            "inside its transaction; dispatch_outbox publishes durable rows to "
            "Redis at-least-once, which is why every task is idempotent (§13.4)."
        ),
    )

    # The dispatcher's entire working set is the unpublished backlog. A partial
    # index on that predicate stays the size of the backlog rather than of
    # history, because a row leaves the index the moment enqueued_at is set.
    op.execute(
        "CREATE INDEX task_outbox_pending ON task_outbox (created_at) "
        "WHERE enqueued_at IS NULL"
    )

    # Producers INSERT, the dispatcher UPDATEs enqueued_at. Neither deletes.
    op.execute("GRANT SELECT, INSERT, UPDATE ON task_outbox TO bhumisetu_app")
    op.execute(
        "GRANT USAGE, SELECT ON SEQUENCE task_outbox_id_seq TO bhumisetu_app"
    )
    op.execute("REVOKE DELETE ON task_outbox FROM bhumisetu_app")


def downgrade() -> None:
    op.drop_table("task_outbox")
