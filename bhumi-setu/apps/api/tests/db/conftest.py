"""Fixtures for tests that need a real PostgreSQL server.

The migrated database is session scoped because ``alembic upgrade head`` is the
expensive part and it does not vary per test. Isolation between tests comes from
the outer-transaction pattern in :func:`db_connection`, not from rebuilding the
schema, which would make the suite unusably slow once there are thirty tables.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from sqlalchemy import Connection, Engine, text

from tests.postgres import skip_without_postgres, temporary_database


@pytest.fixture(scope="session")
def migrated_url() -> Iterator[str]:
    """A throwaway database with every migration applied."""
    skip_without_postgres()
    with temporary_database() as url:
        from alembic import command
        from alembic.config import Config

        config = Config("alembic.ini")
        # Passed through env.py rather than exported into os.environ, so a test
        # session cannot leave a stray DATABASE_URL affecting anything else.
        config.set_main_option("sqlalchemy.url", url)
        config.attributes["test_url"] = url
        command.upgrade(config, "head")
        yield url


@pytest.fixture(scope="session")
def migrated_engine(migrated_url: str) -> Iterator[Engine]:
    from app.db.session import create_guarded_engine

    engine = create_guarded_engine(migrated_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_connection(migrated_engine: Engine) -> Iterator[Connection]:
    """A connection inside a transaction that is always rolled back.

    Every test therefore sees the migrated schema with no rows from any other
    test, without paying for a schema rebuild. Nothing a test writes survives it,
    including the trigger side effects, which is what lets the administrative
    hierarchy tests each build their own tree from scratch.
    """
    connection = migrated_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture
def area_factory(db_connection: Connection):
    """Insert an administrative area, returning its derived path and state_key.

    Supplies deliberate rubbish for ``path`` and ``state_key`` on every call. If
    the trigger ever stops overwriting them, every test using this factory fails
    rather than one dedicated test — the derived-column guarantee is load-bearing
    for R2.2 and should be hard to lose quietly.
    """

    def insert(code: str, area_type: str, name: str, parent_code: str | None = None):
        row = db_connection.execute(
            text(
                """
                INSERT INTO administrative_area
                    (code, area_type, name, parent_code, state_key, path)
                VALUES
                    (:code, :area_type, :name, :parent_code, 'SUPPLIED', 'SUPPLIED')
                RETURNING code, path::text AS path, state_key
                """
            ),
            {
                "code": code,
                "area_type": area_type,
                "name": name,
                "parent_code": parent_code,
            },
        ).one()
        return row

    return insert
