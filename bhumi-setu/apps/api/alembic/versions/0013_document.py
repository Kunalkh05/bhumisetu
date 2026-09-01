"""document.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-01
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.BigInteger(), nullable=True),
        sa.Column("parcel_id", sa.BigInteger(), nullable=True),
        sa.Column("document_type", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.LargeBinary(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processing_state", sa.Text(), nullable=False, server_default=sa.text("'QUEUED'")),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("detected_script", sa.Text(), nullable=True),
        sa.Column("entity_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.CheckConstraint(
            "case_id IS NOT NULL OR parcel_id IS NOT NULL",
            name="ck_document_document_has_scope",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["acquisition_case.id"],
            name="fk_document_case_id_acquisition_case",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parcel_id"],
            ["land_parcel.id"],
            name="fk_document_parcel_id_land_parcel",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["officer.id"],
            name="fk_document_uploaded_by_officer",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "document_case_checksum",
        "document",
        ["case_id", "checksum_sha256"],
        unique=True,
        postgresql_where=sa.text("case_id IS NOT NULL"),
    )
    op.execute("SELECT install_event_backstop('document')")


def downgrade() -> None:
    op.drop_index("document_case_checksum", table_name="document")
    op.drop_table("document")
