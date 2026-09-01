"""holdout and extraction accuracy reports.

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-01
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "holdout_document",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("detected_script", sa.Text(), nullable=False),
        sa.Column("document_type", sa.Text(), nullable=False),
        sa.Column("manifest_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("object_key", name="uq_holdout_document_object_key"),
    )
    op.create_table(
        "holdout_label",
        sa.Column("holdout_document_id", sa.BigInteger(), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["holdout_document_id"],
            ["holdout_document.id"],
            name="fk_holdout_label_holdout_document_id_holdout_document",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "holdout_document_id",
            "field_name",
            name="pk_holdout_label",
        ),
        sa.UniqueConstraint(
            "holdout_document_id",
            "field_name",
            name="holdout_label_document_field_unique",
        ),
    )
    op.create_table(
        "extraction_accuracy_report",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("extraction_model_version", sa.Text(), nullable=False),
        sa.Column("script_set_version", sa.Text(), nullable=False),
        sa.Column("holdout_manifest_hash", sa.Text(), nullable=False),
        sa.Column("accuracy_by_field", postgresql.JSONB(), nullable=False),
        sa.Column("accuracy_by_script", postgresql.JSONB(), nullable=False),
        sa.Column("holdout_document_count", sa.Integer(), nullable=False),
        sa.Column("labelled_instance_count_by_field", postgresql.JSONB(), nullable=False),
        sa.Column("precision_at_threshold", postgresql.JSONB(), nullable=False),
        sa.Column("measurement_date", sa.Date(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "extraction_model_version",
            "script_set_version",
            "holdout_manifest_hash",
            name="extraction_accuracy_report_idempotency",
        ),
    )
    op.create_foreign_key(
        "fk_extracted_field_accuracy_report_id_extraction_accuracy_report",
        "extracted_field",
        "extraction_accuracy_report",
        ["accuracy_report_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_policy_config_justification_report_id_extraction_accuracy_report",
        "policy_config",
        "extraction_accuracy_report",
        ["justification_report_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_policy_config_justification_report_id_extraction_accuracy_report",
        "policy_config",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_extracted_field_accuracy_report_id_extraction_accuracy_report",
        "extracted_field",
        type_="foreignkey",
    )
    op.drop_table("extraction_accuracy_report")
    op.drop_table("holdout_label")
    op.drop_table("holdout_document")
