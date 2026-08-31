"""event: the append-only log.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-31

Task 3.1. §5.1's table, its four indexes, a BRIN on recording_time, and the revoked
grant that makes R4.2 true.

The revoke is the substance of this migration
---------------------------------------------

``REVOKE UPDATE, DELETE ON event FROM bhumisetu_app`` is what makes the log
append-only. Not a trigger, which a superuser connection bypasses without noticing;
not application code, which the next person writing raw SQL bypasses. A revoked
grant fails the statement regardless of how it was issued.

It is granted-then-revoked rather than simply never granted, because the
application role needs INSERT and SELECT. The explicit REVOKE also documents the
intent in the schema itself: ``\\dp event`` shows the log has no UPDATE or DELETE
for the application role, which is discoverable in a way that an absent GRANT is
not.

**Local development does not exercise it.** Postgres.app connects as a superuser,
and a superuser is not subject to table privileges — so the revoke is inert on a
developer machine. That is why ``test_append_only_is_enforced_by_the_database``
does ``SET ROLE bhumisetu_app`` before trying to mutate: without that, the test
passes for the wrong reason and the guarantee is untested everywhere except
production.

Deferred foreign keys
---------------------

``case_id`` and ``import_batch_id`` reference tables that do not exist yet
(``acquisition_case`` in task 8.1, ``import_batch`` in task 26.1), so the columns
are created without their constraints and those tasks add them. ``corrects_event_id``
is self-referential and lands now.

Not partitioned
---------------

§5.1 rejects partitioning by ``recording_time`` on day one: it prunes well for the
``KNOWABLE_AT`` feature read but forces an all-partition scan for the citizen
timeline, which filters on ``occurrence_time`` alone. A BRIN on ``recording_time``
gives most of the range-scan benefit at a fraction of the cost, and partitioning
stays available once the read mix is measured rather than guessed.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("case_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("occurrence_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recording_time",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "has_pd_refs",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("entity_version_after", sa.Integer(), nullable=True),
        sa.Column(
            "provenance", sa.Text(), nullable=False, server_default=sa.text("'MANUAL'")
        ),
        sa.Column("import_batch_id", sa.BigInteger(), nullable=True),
        sa.Column("corrects_event_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "txid", sa.BigInteger(), nullable=False, server_default=sa.text("txid_current()")
        ),
        sa.ForeignKeyConstraint(
            ["corrects_event_id"],
            ["event.id"],
            name="fk_event_corrects_event_id_event",
            ondelete="RESTRICT",
        ),
        comment=(
            "Append-only event log (§5.1). R4.2 is enforced by REVOKE UPDATE, DELETE "
            "from bhumisetu_app, not by application code."
        ),
    )

    # (occurrence_time, id): the id tiebreak makes the order total, which R17.5's
    # deterministic replay depends on. Two events routinely share an occurrence
    # time because officers enter dates, not timestamps.
    op.create_index(
        "event_entity_asof",
        "event",
        ["entity_type", "entity_id", "occurrence_time", "id"],
    )
    op.create_index("event_case_asof", "event", ["case_id", "occurrence_time", "id"])
    op.create_index(
        "event_knowable", "event", ["entity_type", "entity_id", "recording_time"]
    )
    op.create_index("event_txid", "event", ["txid"])

    # BRIN rather than btree: recording_time is append-ordered, so a BRIN summarises
    # it in a fraction of the space and answers the range scans that a partition
    # would have served. See the module docstring on why we are not partitioned.
    op.execute(
        "CREATE INDEX event_recording_time_brin ON event USING brin (recording_time)"
    )

    # R4.2. The application role gets what it needs and nothing that could rewrite
    # history. See the module docstring: a superuser is not subject to this, which is
    # why the test SET ROLEs before asserting.
    op.execute("GRANT SELECT, INSERT ON event TO bhumisetu_app")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE event_id_seq TO bhumisetu_app")
    op.execute("REVOKE UPDATE, DELETE ON event FROM bhumisetu_app")


def downgrade() -> None:
    op.drop_table("event")
