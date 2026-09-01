"""validation_issue and validation_issue_history.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-01
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "validation_issue",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_id", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("offending_entities", postgresql.JSONB(), nullable=False),
        sa.Column("observed_values", postgresql.JSONB(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolution_state", sa.Text(), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entity_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["acquisition_case.id"],
            name="fk_validation_issue_case_id_acquisition_case",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "validation_issue_open_unique",
        "validation_issue",
        ["case_id", "rule_id", "fingerprint"],
        unique=True,
        postgresql_where=sa.text("resolution_state = 'OPEN'"),
    )
    op.create_index(
        "validation_issue_queue",
        "validation_issue",
        ["case_id", "severity", "detected_at"],
        postgresql_where=sa.text("resolution_state = 'OPEN'"),
    )
    op.create_table(
        "validation_issue_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("issue_id", sa.BigInteger(), nullable=False),
        sa.Column("prior_state", sa.Text(), nullable=True),
        sa.Column("new_state", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("occurrence_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["validation_issue.id"],
            name="fk_validation_issue_history_issue_id_validation_issue",
            ondelete="RESTRICT",
        ),
    )
    op.execute("SELECT install_event_backstop('validation_issue')")


def downgrade() -> None:
    op.drop_table("validation_issue_history")
    op.drop_index("validation_issue_queue", table_name="validation_issue")
    op.drop_index("validation_issue_open_unique", table_name="validation_issue")
    op.drop_table("validation_issue")
