"""policy_config: effective-dated configuration.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-31

Task 2.1. §4.1's table, its expression-keyed uniqueness, the resolve index, and
R28.9's CHECK.

Two departures from the DDL as printed in §4.1, both forced:

1. **Uniqueness is a unique INDEX, not a UNIQUE constraint.** The design writes
   ``CONSTRAINT policy_config_unique_version UNIQUE (policy_key, state_key,
   coalesce(act_key, ''), effective_from)``. PostgreSQL does not accept an
   expression in a UNIQUE table constraint — only column names — so that statement
   fails to parse. The coalesce cannot simply be dropped either: NULL is not equal
   to NULL, so a plain unique constraint would happily accept two rows with a NULL
   ``act_key`` for the same key, state and date, and the resolve query would then
   return whichever the planner reached first. A unique index over the expression
   is the only form that enforces what was meant.

2. **``created_by`` is uuid, not bigint.** ``officer.id`` is a uuid in migration
   0001; the design's ``bigint`` predates that choice.

``justification_report_id`` is created without its foreign key, because
``extraction_accuracy_report`` does not exist until task 16.7. The CHECK that
requires the reference to be *present* for an OCR threshold key is in force from
now, so the ordering costs nothing: what R28.9 actually demands is that a threshold
change cite a report, and that is enforced here. Task 16.7 adds referential
integrity on top.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_config",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("policy_key", sa.Text(), nullable=False),
        sa.Column(
            "state_key", sa.Text(), nullable=False, server_default=sa.text("'*'")
        ),
        sa.Column("act_key", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("value", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("justification_report_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["officer.id"],
            name="fk_policy_config_created_by_officer",
            ondelete="RESTRICT",
        ),
        # Bare name: the ck convention wraps it (see migration 0001's note).
        sa.CheckConstraint(
            "policy_key NOT LIKE 'ocr.threshold.%' "
            "OR justification_report_id IS NOT NULL",
            name="ocr_threshold_requires_report",
        ),
        comment=(
            "Effective-dated configuration (§4.1). Append-only: a change is a new "
            "row with a later effective_from, which is what gives R28.3 its "
            "history and R7.8 its frozen deadlines."
        ),
    )

    # Expression-keyed, so index rather than constraint. See the module docstring.
    op.execute(
        """
        CREATE UNIQUE INDEX policy_config_unique_version
            ON policy_config (policy_key, state_key, coalesce(act_key, ''), effective_from)
        """
    )
    op.execute(
        """
        CREATE INDEX policy_config_resolve
            ON policy_config (policy_key, state_key, coalesce(act_key, ''), effective_from DESC)
        """
    )


def downgrade() -> None:
    op.drop_table("policy_config")
