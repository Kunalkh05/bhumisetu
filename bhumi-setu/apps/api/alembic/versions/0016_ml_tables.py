"""machine learning feature, model, prediction, explanation, and monitor tables.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-02
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ml_feature_row",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("reference_t", sa.DateTime(timezone=True), nullable=False),
        sa.Column("as_of_mode", sa.Text(), nullable=False),
        sa.Column("feature_set_version", sa.Text(), nullable=False),
        sa.Column("label_definition_version", sa.Text(), nullable=True),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("consumed_event_ids", postgresql.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["acquisition_case.id"],
            name="fk_ml_feature_row_case_id_acquisition_case",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "case_id",
            "reference_t",
            "as_of_mode",
            "feature_set_version",
            "purpose",
            name="ml_feature_row_unique_reference",
        ),
    )

    op.create_table(
        "ml_training_row",
        sa.Column("feature_row_id", sa.BigInteger(), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("time_to_event_days", sa.Integer(), nullable=True),
        sa.Column("event_observed", sa.Boolean(), nullable=True),
        sa.Column("label_definition_version", sa.Text(), nullable=False),
        sa.Column("split", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["feature_row_id"],
            ["ml_feature_row.id"],
            name="fk_ml_training_row_feature_row_id_ml_feature_row",
            ondelete="RESTRICT",
        ),
    )

    op.create_table(
        "ml_model_version",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("feature_set_version", sa.Text(), nullable=False),
        sa.Column("label_definition_version", sa.Text(), nullable=False),
        sa.Column("training_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("training_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hyperparameters", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("baseline_metrics", postgresql.JSONB(), nullable=False),
        sa.Column("train_base_rate", sa.Double(), nullable=False),
        sa.Column("eval_base_rate", sa.Double(), nullable=False),
        sa.Column("censored_count", sa.Integer(), nullable=False),
        sa.Column("censoring_rate", sa.Double(), nullable=False),
        sa.Column("feature_reference_bins", postgresql.JSONB(), nullable=False),
        sa.Column("promotion_state", sa.Text(), nullable=False),
        sa.Column("promoted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("artifact_object_key", sa.Text(), nullable=False),
        sa.Column("superseded_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["promoted_by"],
            ["officer.id"],
            name="fk_ml_model_version_promoted_by_officer",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by"],
            ["ml_model_version.id"],
            name="fk_ml_model_version_superseded_by_ml_model_version",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("version", name="uq_ml_model_version_version"),
    )

    op.create_table(
        "ml_prediction",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("model_version_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_row_id", sa.BigInteger(), nullable=False),
        sa.Column("risk_probability", sa.Double(), nullable=False),
        sa.Column("risk_band", sa.Text(), nullable=False),
        sa.Column("cutoff_source", sa.Text(), nullable=False),
        sa.Column("cutoff_set_version", sa.Text(), nullable=False),
        sa.Column("reference_t", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["acquisition_case.id"],
            name="fk_ml_prediction_case_id_acquisition_case",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["ml_model_version.id"],
            name="fk_ml_prediction_model_version_id_ml_model_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["feature_row_id"],
            ["ml_feature_row.id"],
            name="fk_ml_prediction_feature_row_id_ml_feature_row",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "case_id",
            "model_version_id",
            "feature_row_id",
            name="ml_prediction_idempotency",
        ),
    )
    op.create_index(
        "ml_prediction_history",
        "ml_prediction",
        ["case_id", sa.text("generated_at DESC")],
    )

    op.create_table(
        "ml_explanation_factor",
        sa.Column("prediction_id", sa.BigInteger(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("feature_name", sa.Text(), nullable=False),
        sa.Column("label_key", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("magnitude", sa.Double(), nullable=False),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["ml_prediction.id"],
            name="fk_ml_explanation_factor_prediction_id_ml_prediction",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "prediction_id",
            "rank",
            name="pk_ml_explanation_factor",
        ),
    )

    op.create_table(
        "ml_monitor_run",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("model_version_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("withholding_reason", sa.Text(), nullable=True),
        sa.Column("evaluable_case_count", sa.Integer(), nullable=True),
        sa.Column("results", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["ml_model_version.id"],
            name="fk_ml_monitor_run_model_version_id_ml_model_version",
            ondelete="RESTRICT",
        ),
    )


def downgrade() -> None:
    op.drop_table("ml_monitor_run")
    op.drop_table("ml_explanation_factor")
    op.drop_index("ml_prediction_history", table_name="ml_prediction")
    op.drop_table("ml_prediction")
    op.drop_table("ml_model_version")
    op.drop_table("ml_training_row")
    op.drop_table("ml_feature_row")
