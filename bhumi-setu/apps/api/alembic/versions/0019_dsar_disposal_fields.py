"""DSAR disposal fields.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-03
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("data_subject_request", sa.Column("disposal_outcome", sa.Text(), nullable=True))
    op.add_column("data_subject_request", sa.Column("disposal_reasons", sa.Text(), nullable=True))
    op.add_column("data_subject_request", sa.Column("deciding_officer_id", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("data_subject_request", "deciding_officer_id")
    op.drop_column("data_subject_request", "disposal_reasons")
    op.drop_column("data_subject_request", "disposal_outcome")
