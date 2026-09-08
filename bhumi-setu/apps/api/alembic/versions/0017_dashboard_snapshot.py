"""dashboard snapshot and band history tables.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-03
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dashboard_snapshot",
        sa.Column("area_code", sa.Text(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["area_code"],
            ["administrative_area.code"],
            name="fk_dashboard_snapshot_area_code_administrative_area",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("area_code", name="pk_dashboard_snapshot"),
    )
    op.create_table(
        "dashboard_band_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("area_code", sa.Text(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("band", sa.Text(), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["area_code"],
            ["administrative_area.code"],
            name="fk_dashboard_band_history_area_code_administrative_area",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "area_code",
            "month",
            "band",
            "computed_at",
            name="dashboard_band_history_unique_computation",
        ),
    )


def downgrade() -> None:
    op.drop_table("dashboard_band_history")
    op.drop_table("dashboard_snapshot")
