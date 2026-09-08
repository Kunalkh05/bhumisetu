"""Bulk import schema contract tests (task 26.1)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import BigInteger, Index, Integer, LargeBinary, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import all_metadata


def _table(name: str):
    return all_metadata().tables[name]


def test_import_tables_are_declared_in_metadata() -> None:
    assert {"import_batch", "import_row"}.issubset(all_metadata().tables)


def test_import_batch_records_submission_and_resume_state() -> None:
    table = _table("import_batch")

    assert isinstance(table.c.id.type, BigInteger)
    assert isinstance(table.c.submitted_by.type, Text)
    assert isinstance(table.c.submitted_count.type, Integer)
    assert isinstance(table.c.content_checksum.type, LargeBinary)
    assert isinstance(table.c.state.type, Text)
    assert isinstance(table.c.last_processed_ordinal.type, Integer)


def test_import_row_has_composite_key_rejection_and_pending_index() -> None:
    table = _table("import_row")

    assert [column.name for column in table.primary_key.columns] == ["batch_id", "ordinal"]
    assert isinstance(table.c.entity_type.type, Text)
    assert isinstance(table.c.payload.type, JSONB)
    assert isinstance(table.c.state.type, Text)
    assert isinstance(table.c.committed_entity_id.type, BigInteger)
    assert isinstance(table.c.rejection.type, JSONB)
    indexes = {index.name: index for index in table.indexes if isinstance(index, Index)}
    assert "import_row_pending" in indexes
    assert str(indexes["import_row_pending"].dialect_options["postgresql"]["where"]) == (
        "state = 'PENDING'"
    )


def test_import_migration_extends_the_current_single_head() -> None:
    migration = Path("alembic/versions/0020_import_batch_rows.py").read_text(
        encoding="utf-8"
    )

    assert 'revision: str = "0020"' in migration
    assert 'down_revision: str | None = "0019"' in migration
    assert "import_row_pending" in migration
    assert "fk_event_import_batch_id_import_batch" in migration

