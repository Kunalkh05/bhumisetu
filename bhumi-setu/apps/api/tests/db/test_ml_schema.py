"""Machine-learning table storage contract tests (task 22.1)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import BigInteger, DateTime, Double, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from app.db.base import all_metadata


def _table(name: str):
    return all_metadata().tables[name]


def test_ml_tables_are_declared_in_metadata() -> None:
    tables = all_metadata().tables
    assert {
        "ml_feature_row",
        "ml_training_row",
        "ml_model_version",
        "ml_prediction",
        "ml_explanation_factor",
        "ml_monitor_run",
    }.issubset(tables)


def test_ml_feature_row_has_replay_contract_and_unique_reference() -> None:
    table = _table("ml_feature_row")

    assert isinstance(table.c.case_id.type, BigInteger)
    assert isinstance(table.c.reference_t.type, DateTime)
    assert isinstance(table.c.as_of_mode.type, Text)
    assert isinstance(table.c.features.type, JSONB)
    assert isinstance(table.c.consumed_event_ids.type, ARRAY)
    assert isinstance(table.c.consumed_event_ids.type.item_type, BigInteger)
    assert table.c.label_definition_version.nullable

    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert uniques["ml_feature_row_unique_reference"] == (
        "case_id",
        "reference_t",
        "as_of_mode",
        "feature_set_version",
        "purpose",
    )


def test_training_row_is_one_label_per_feature_row() -> None:
    table = _table("ml_training_row")

    assert [column.name for column in table.primary_key.columns] == ["feature_row_id"]
    assert not table.c.label_definition_version.nullable
    assert table.c.time_to_event_days.nullable
    assert table.c.event_observed.nullable


def test_model_version_stores_metrics_baseline_bins_and_uuid_promoter() -> None:
    table = _table("ml_model_version")

    assert isinstance(table.c.hyperparameters.type, JSONB)
    assert isinstance(table.c.metrics.type, JSONB)
    assert isinstance(table.c.baseline_metrics.type, JSONB)
    assert isinstance(table.c.feature_reference_bins.type, JSONB)
    assert isinstance(table.c.train_base_rate.type, Double)
    assert isinstance(table.c.eval_base_rate.type, Double)
    assert isinstance(table.c.promoted_by.type, UUID)
    assert table.c.superseded_by.foreign_keys


def test_prediction_has_idempotency_unique_constraint_and_history_index() -> None:
    table = _table("ml_prediction")
    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    indexes = {index.name: tuple(column.name for column in index.columns) for index in table.indexes}

    assert uniques["ml_prediction_idempotency"] == (
        "case_id",
        "model_version_id",
        "feature_row_id",
    )
    assert indexes["ml_prediction_history"][0] == "case_id"


def test_explanation_and_monitor_tables_hold_required_shapes() -> None:
    explanation = _table("ml_explanation_factor")
    monitor = _table("ml_monitor_run")

    assert [column.name for column in explanation.primary_key.columns] == ["prediction_id", "rank"]
    assert isinstance(explanation.c.magnitude.type, Double)
    assert isinstance(monitor.c.results.type, JSONB)
    assert monitor.c.finished_at.nullable
    assert monitor.c.withholding_reason.nullable


def test_migration_extends_the_current_single_head() -> None:
    migration = Path("alembic/versions/0016_ml_tables.py").read_text(encoding="utf-8")

    assert 'revision: str = "0016"' in migration
    assert 'down_revision: str | None = "0015"' in migration
    assert "ml_prediction_idempotency" in migration
    assert "ml_prediction_history" in migration
