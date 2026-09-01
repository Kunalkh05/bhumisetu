"""objection.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-01
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "objection",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("objector_name", sa.Text(), nullable=False),
        sa.Column("ownership_record_id", sa.BigInteger(), nullable=True),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("grounds_category", sa.Text(), nullable=False),
        sa.Column("substance", sa.Text(), nullable=False),
        sa.Column("governing_notice_id", sa.BigInteger(), nullable=True),
        sa.Column("window_state", sa.Text(), nullable=False),
        sa.Column("disposal_deadline", sa.Date(), nullable=False),
        sa.Column(
            "is_disposal_overdue",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("disposal_outcome", sa.Text(), nullable=True),
        sa.Column("disposal_date", sa.Date(), nullable=True),
        sa.Column("disposal_reasons", sa.Text(), nullable=True),
        sa.Column("deciding_officer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "entity_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["acquisition_case.id"],
            name="fk_objection_case_id_acquisition_case",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ownership_record_id"],
            ["ownership_record.id"],
            name="fk_objection_ownership_record_id_ownership_record",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["governing_notice_id"],
            ["statutory_notice.id"],
            name="fk_objection_governing_notice_id_statutory_notice",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["deciding_officer_id"],
            ["officer.id"],
            name="fk_objection_deciding_officer_id_officer",
            ondelete="RESTRICT",
        ),
        comment=(
            "Objections and their disposal state (R8). Versioned; no date defaults "
            "or period CHECKs because deadlines are supplied by Objection_Service."
        ),
    )
    op.create_index("objection_case_receipt", "objection", ["case_id", "receipt_date"])
    op.create_index(
        "objection_undisposed",
        "objection",
        ["case_id", "disposal_deadline"],
        postgresql_where=sa.text("disposal_date IS NULL"),
    )
    op.execute("SELECT install_event_backstop('objection')")


def downgrade() -> None:
    op.drop_index("objection_undisposed", table_name="objection")
    op.drop_index("objection_case_receipt", table_name="objection")
    op.drop_table("objection")
