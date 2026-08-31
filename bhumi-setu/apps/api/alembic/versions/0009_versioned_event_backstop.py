"""Deferred event backstop for versioned entity updates.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-01

Task 3.7. A service that updates a versioned entity but forgets to append an event
must not be able to commit. The backstop is a deferred constraint trigger: after an
UPDATE to a protected table, commit checks that the same transaction wrote an
``event`` row for ``(TG_TABLE_NAME, NEW.id, txid_current())``.

Only the versioned tables that exist at this point in the migration chain are
installed here: ``acquisition_case``, ``land_parcel``, ``ownership_record``,
``statutory_notice``, and ``notice_service_record``. Later table-creating migrations
must call the same installer for their own versioned tables; the trigger coverage
test derives the expected current set from ORM models so that cannot be missed.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ASSERT_FN = """
CREATE OR REPLACE FUNCTION assert_event_in_transaction()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF current_setting('bhumisetu.skip_event_backstop', true) = 'on' THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM event
        WHERE entity_type = TG_TABLE_NAME
          AND entity_id = NEW.id
          AND txid = txid_current()
    ) THEN
        RAISE EXCEPTION
            'versioned update to %.% committed without event in transaction %',
            TG_TABLE_NAME, NEW.id, txid_current()
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    RETURN NEW;
END;
$$;
"""


INSTALL_FN = """
CREATE OR REPLACE FUNCTION install_event_backstop(table_name text)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I', table_name || '_event_backstop', table_name);
    EXECUTE format(
        'CREATE CONSTRAINT TRIGGER %I '
        'AFTER UPDATE ON %I '
        'DEFERRABLE INITIALLY DEFERRED '
        'FOR EACH ROW EXECUTE FUNCTION assert_event_in_transaction()',
        table_name || '_event_backstop',
        table_name
    );
END;
$$;
"""


CURRENT_VERSIONED_TABLES = (
    "acquisition_case",
    "land_parcel",
    "ownership_record",
    "statutory_notice",
    "notice_service_record",
)


def upgrade() -> None:
    op.execute(ASSERT_FN)
    op.execute(INSTALL_FN)
    for table in CURRENT_VERSIONED_TABLES:
        op.execute(f"SELECT install_event_backstop('{table}')")


def downgrade() -> None:
    for table in reversed(CURRENT_VERSIONED_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_event_backstop ON {table}")
    op.execute("DROP FUNCTION IF EXISTS install_event_backstop(text)")
    op.execute("DROP FUNCTION IF EXISTS assert_event_in_transaction()")
