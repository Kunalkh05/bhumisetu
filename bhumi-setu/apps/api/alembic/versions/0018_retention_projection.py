"""retention projection and data subject request tables.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-03
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_subject_request",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("request_type", sa.Text(), nullable=False),
        sa.Column("subject_key", sa.Text(), nullable=False),
        sa.Column("case_id", sa.BigInteger(), nullable=True),
        sa.Column("ownership_record_id", sa.BigInteger(), nullable=True),
        sa.Column("target_attribute", sa.Text(), nullable=True),
        sa.Column("current_value", postgresql.JSONB(), nullable=True),
        sa.Column("asserted_value", postgresql.JSONB(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("routed_area_code", sa.Text(), nullable=True),
        sa.Column("created_event_id", sa.BigInteger(), nullable=True),
        sa.Column("disposed_event_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["acquisition_case.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ownership_record_id"], ["ownership_record.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["routed_area_code"], ["administrative_area.code"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_event_id"], ["event.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["disposed_event_id"], ["event.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "data_subject_request_overdue",
        "data_subject_request",
        ["due_at"],
        postgresql_where=sa.text("completed_at IS NULL"),
    )
    op.create_table(
        "retention_withholding",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("attribute_name", sa.Text(), nullable=False),
        sa.Column("data_category", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("retention_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_key", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "retention_withholding_lookup",
        "retention_withholding",
        ["entity_type", "entity_id", "attribute_name", "data_category"],
    )
    op.execute(
        """
        CREATE VIEW v_case_terminal AS
        SELECT ac.id AS case_id,
               MIN(e.occurrence_time) AS retention_start
          FROM acquisition_case ac
          LEFT JOIN event e
            ON e.case_id = ac.id
           AND e.entity_type = 'acquisition_case'
           AND e.entity_id = ac.id
           AND e.payload ? 'stage_key'
         WHERE ac.is_terminal = true
         GROUP BY ac.id
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_case_terminal")
    op.drop_index("retention_withholding_lookup", table_name="retention_withholding")
    op.drop_table("retention_withholding")
    op.drop_index("data_subject_request_overdue", table_name="data_subject_request")
    op.drop_table("data_subject_request")
