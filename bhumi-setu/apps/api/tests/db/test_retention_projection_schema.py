"""Retention projection schema contract tests (task 25.1)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import BigInteger, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import all_metadata


def _table(name: str):
    return all_metadata().tables[name]


def test_retention_projection_tables_are_declared_in_metadata() -> None:
    assert {"data_subject_request", "retention_withholding"}.issubset(
        all_metadata().tables
    )


def test_data_subject_request_materializes_due_at_for_overdue_scan() -> None:
    table = _table("data_subject_request")

    assert isinstance(table.c.id.type, BigInteger)
    assert isinstance(table.c.request_type.type, Text)
    assert isinstance(table.c.subject_key.type, Text)
    assert isinstance(table.c.current_value.type, JSONB)
    assert isinstance(table.c.asserted_value.type, JSONB)
    assert isinstance(table.c.received_at.type, DateTime)
    assert isinstance(table.c.due_at.type, DateTime)
    assert isinstance(table.c.disposal_outcome.type, Text)
    assert isinstance(table.c.disposal_reasons.type, Text)
    assert isinstance(table.c.deciding_officer_id.type, Text)
    indexes = {index.name: index for index in table.indexes if isinstance(index, Index)}
    assert "data_subject_request_overdue" in indexes
    assert str(indexes["data_subject_request_overdue"].dialect_options["postgresql"]["where"]) == (
        "completed_at IS NULL"
    )


def test_retention_withholding_records_missing_start_or_policy_reason() -> None:
    table = _table("retention_withholding")

    assert isinstance(table.c.entity_type.type, Text)
    assert isinstance(table.c.entity_id.type, BigInteger)
    assert isinstance(table.c.attribute_name.type, Text)
    assert isinstance(table.c.data_category.type, Text)
    assert isinstance(table.c.reason.type, Text)
    assert isinstance(table.c.retention_start.type, DateTime)
    assert isinstance(table.c.policy_key.type, Text)
    assert "retention_withholding_lookup" in {index.name for index in table.indexes}


def test_retention_projection_migration_extends_the_current_single_head() -> None:
    migration = Path("alembic/versions/0018_retention_projection.py").read_text(
        encoding="utf-8"
    )

    assert 'revision: str = "0018"' in migration
    assert 'down_revision: str | None = "0017"' in migration
    assert "data_subject_request_overdue" in migration
    assert "CREATE VIEW v_case_terminal" in migration


def test_dsar_disposal_migration_extends_the_current_single_head() -> None:
    migration = Path("alembic/versions/0019_dsar_disposal_fields.py").read_text(
        encoding="utf-8"
    )

    assert 'revision: str = "0019"' in migration
    assert 'down_revision: str | None = "0018"' in migration
    assert "disposal_outcome" in migration
    assert "disposal_reasons" in migration
    assert "deciding_officer_id" in migration
