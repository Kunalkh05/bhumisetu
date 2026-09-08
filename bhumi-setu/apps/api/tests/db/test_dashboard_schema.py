"""Dashboard snapshot table storage contract tests (task 24.3)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import BigInteger, Date, DateTime, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import all_metadata


def _table(name: str):
    return all_metadata().tables[name]


def test_dashboard_tables_are_declared_in_metadata() -> None:
    assert {"dashboard_snapshot", "dashboard_band_history"}.issubset(
        all_metadata().tables
    )


def test_dashboard_snapshot_is_one_row_per_area_with_json_metrics() -> None:
    table = _table("dashboard_snapshot")

    assert [column.name for column in table.primary_key.columns] == ["area_code"]
    assert isinstance(table.c.area_code.type, Text)
    assert isinstance(table.c.metrics.type, JSONB)
    assert isinstance(table.c.computed_at.type, DateTime)
    assert table.c.area_code.foreign_keys


def test_dashboard_band_history_is_append_only_by_computation_time() -> None:
    table = _table("dashboard_band_history")

    assert isinstance(table.c.id.type, BigInteger)
    assert isinstance(table.c.area_code.type, Text)
    assert isinstance(table.c.month.type, Date)
    assert isinstance(table.c.band.type, Text)
    assert isinstance(table.c.case_count.type, Integer)
    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert uniques["dashboard_band_history_unique_computation"] == (
        "area_code",
        "month",
        "band",
        "computed_at",
    )


def test_dashboard_migration_extends_the_current_single_head() -> None:
    migration = Path("alembic/versions/0017_dashboard_snapshot.py").read_text(
        encoding="utf-8"
    )

    assert 'revision: str = "0017"' in migration
    assert 'down_revision: str | None = "0016"' in migration
    assert "dashboard_snapshot" in migration
    assert "dashboard_band_history" in migration
