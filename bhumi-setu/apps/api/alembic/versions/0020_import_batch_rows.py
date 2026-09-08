"""Import batch and row state.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-03
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_batch",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("submitted_by", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("submitted_count", sa.Integer(), nullable=False),
        sa.Column("content_checksum", sa.LargeBinary(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("last_processed_ordinal", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_table(
        "import_row",
        sa.Column("batch_id", sa.BigInteger(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("committed_entity_id", sa.BigInteger(), nullable=True),
        sa.Column("rejection", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batch.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("batch_id", "ordinal"),
    )
    op.create_index(
        "import_row_pending",
        "import_row",
        ["batch_id", "ordinal"],
        postgresql_where=sa.text("state = 'PENDING'"),
    )
    op.create_foreign_key(
        "fk_event_import_batch_id_import_batch",
        "event",
        "import_batch",
        ["import_batch_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_event_import_batch_id_import_batch", "event", type_="foreignkey")
    op.drop_index("import_row_pending", table_name="import_row")
    op.drop_table("import_row")
    op.drop_table("import_batch")

