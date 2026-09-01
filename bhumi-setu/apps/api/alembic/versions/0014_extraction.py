"""extraction and extracted_field.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-01
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "extraction",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("extraction_model_version", sa.Text(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("detected_script", sa.Text(), nullable=False),
        sa.Column("mean_confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "mean_confidence >= 0 AND mean_confidence <= 1",
            name="ck_extraction_extraction_mean_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["document.id"],
            name="fk_extraction_document_id_document",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "document_id",
            "extraction_model_version",
            name="extraction_document_model_unique",
        ),
    )
    op.create_table(
        "extracted_field",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("extraction_id", sa.BigInteger(), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("extracted_value", sa.Text(), nullable=True),
        sa.Column("original_extracted_value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("original_confidence", sa.Float(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("bbox_x1", sa.Float(), nullable=False),
        sa.Column("bbox_y1", sa.Float(), nullable=False),
        sa.Column("bbox_x2", sa.Float(), nullable=False),
        sa.Column("bbox_y2", sa.Float(), nullable=False),
        sa.Column("review_state", sa.Text(), nullable=False),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("accuracy_report_id", sa.BigInteger(), nullable=True),
        sa.Column("entity_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_extracted_field_extracted_field_confidence_range",
        ),
        sa.CheckConstraint(
            "original_confidence >= 0 AND original_confidence <= 1",
            name="ck_extracted_field_extracted_field_original_confidence_range",
        ),
        sa.CheckConstraint("page_number >= 1", name="ck_extracted_field_extracted_field_page_positive"),
        sa.CheckConstraint(
            "bbox_x1 >= 0 AND bbox_x1 <= 1 AND bbox_y1 >= 0 AND bbox_y1 <= 1 "
            "AND bbox_x2 >= 0 AND bbox_x2 <= 1 AND bbox_y2 >= 0 AND bbox_y2 <= 1 "
            "AND bbox_x1 <= bbox_x2 AND bbox_y1 <= bbox_y2",
            name="ck_extracted_field_extracted_field_bbox_page_relative",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_id"],
            ["extraction.id"],
            name="fk_extracted_field_extraction_id_extraction",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "extracted_field_review_queue",
        "extracted_field",
        ["review_state", "extraction_id"],
    )
    op.execute("SELECT install_event_backstop('extracted_field')")


def downgrade() -> None:
    op.drop_index("extracted_field_review_queue", table_name="extracted_field")
    op.drop_table("extracted_field")
    op.drop_table("extraction")
