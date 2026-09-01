"""award, award_component, and payout.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-01
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "award",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ownership_record_id", sa.BigInteger(), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("determination_date", sa.Date(), nullable=False),
        sa.Column("determining_authority", sa.Text(), nullable=False),
        sa.Column(
            "disbursement_state",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'UNPAID'"),
        ),
        sa.Column(
            "entity_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["ownership_record_id"],
            ["ownership_record.id"],
            name="fk_award_ownership_record_id_ownership_record",
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "award_component",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("award_id", sa.BigInteger(), nullable=False),
        sa.Column("component_label", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["award_id"],
            ["award.id"],
            name="fk_award_component_award_id_award",
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "payout",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("award_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payout_date", sa.Date(), nullable=False),
        sa.Column("instrument_reference", sa.Text(), nullable=False),
        sa.Column("beneficiary", sa.Text(), nullable=False),
        sa.Column(
            "entity_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["award_id"],
            ["award.id"],
            name="fk_payout_award_id_award",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("award_owner", "award", ["ownership_record_id"])
    op.create_index("payout_award", "payout", ["award_id", "payout_date"])
    op.execute("SELECT install_event_backstop('award')")
    op.execute("SELECT install_event_backstop('payout')")


def downgrade() -> None:
    op.drop_index("payout_award", table_name="payout")
    op.drop_index("award_owner", table_name="award")
    op.drop_table("payout")
    op.drop_table("award_component")
    op.drop_table("award")
