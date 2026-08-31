"""Shared fixtures.

The environment is set before any ``app`` module is imported, because
``app.main`` and ``app.workers.celery_app`` build their objects at import time
(compose runs ``uvicorn app.main:app`` and ``celery -A app.workers.celery_app``,
both of which need a module-level object). The values mirror the names committed
in ``docker-compose.yml``; nothing here connects to them.

PostgreSQL, Redis and MinIO are not available in this environment, so the
transaction-boundary tests run against a file-backed SQLite database. That is
sound for what they assert — commit on clean exit, rollback on exception, one
session, one transaction, one connection — because those are properties of
``app/db/session.py`` and of SQLAlchemy's session lifecycle, not of PostgreSQL.
A file rather than ``:memory:`` on purpose: in-memory SQLite uses
``SingletonThreadPool``, which hands the same connection back on a second
``connect()`` and would make the second-connection guard untestable, and would
also let two sequential units of work share one connection and so weaken the
rollback assertions.

What SQLite cannot stand in for, and is therefore *not* claimed here: the
deferred constraint trigger of §5.2, ``REVOKE UPDATE, DELETE ON event``, PostGIS,
and the two-connection concurrency harness of §20.8. Those need the real
database and arrive with the tasks that introduce them.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Iterator

import pytest

if TYPE_CHECKING:
    from sqlalchemy import Engine

COMPOSE_ENV: dict[str, str] = {
    "APP_ENV": "development",
    "LOG_LEVEL": "WARNING",
    "DATABASE_URL": "postgresql+psycopg://bhumisetu:pw@localhost:5432/bhumisetu_test",
    "REDIS_URL": "redis://localhost:6379/0",
    "OBJECT_STORAGE_ENDPOINT": "http://localhost:9000",
    "OBJECT_STORAGE_ACCESS_KEY": "minioadmin",
    "OBJECT_STORAGE_SECRET_KEY": "minioadmin",
    "OBJECT_STORAGE_BUCKET": "bhumisetu-documents",
    "JWT_SECRET": "test-internal-service-token-secret",
}

for _name, _value in COMPOSE_ENV.items():
    os.environ.setdefault(_name, _value)


@pytest.fixture
def transactional_sqlite_engine(tmp_path) -> Iterator["Engine"]:
    """A throwaway SQLite engine with genuine BEGIN/COMMIT/ROLLBACK semantics.

    Built through ``create_guarded_engine`` so it carries the same
    second-connection guard as the process engine — an unguarded test engine
    would let a test pass where production fails.

    The two listeners are the workaround SQLAlchemy's pysqlite dialect notes
    prescribe. Left alone, the ``sqlite3`` driver manages transactions itself and
    emits no BEGIN, which silently breaks SAVEPOINT: a released savepoint becomes
    durable and survives the enclosing rollback. Disabling the driver's implicit
    handling and emitting BEGIN explicitly means the boundary under test is
    exercised against real transaction control rather than the driver's
    approximation of it.
    """
    from sqlalchemy import event

    from app.db.session import create_guarded_engine

    engine = create_guarded_engine(f"sqlite+pysqlite:///{tmp_path / 'boundary.db'}")

    @event.listens_for(engine, "connect")
    def _disable_driver_transaction_handling(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _emit_begin(connection):  # type: ignore[no-untyped-def]
        connection.exec_driver_sql("BEGIN")

    yield engine
    engine.dispose()


@pytest.fixture
def clean_settings_cache() -> Iterator[None]:
    """Drop every cached settings group around a test that changes the environment."""
    from app.settings import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()

# ---------------------------------------------------------------------------
# Hypothesis profiles (§20.8)
# ---------------------------------------------------------------------------

from hypothesis import HealthCheck, Verbosity, settings as hypothesis_settings  # noqa: E402

# The `.hypothesis/examples` directory is what makes a found counterexample
# permanent. Hypothesis writes every failing example there and replays it first
# on the next run, so a bug found once by a random draw becomes a deterministic
# regression test without anyone writing it down. In CI the directory must be
# cached between runs or this is lost — the point of the database is that it
# outlives the session that found the failure.

hypothesis_settings.register_profile(
    "dev",
    max_examples=100,
    deadline=None,          # PostgreSQL round trips vary too much for a deadline
    print_blob=True,        # print a reproducible blob on failure
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)

hypothesis_settings.register_profile(
    "ci",
    max_examples=300,
    deadline=None,
    print_blob=True,
    derandomize=False,      # CI should keep finding new counterexamples
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)

# For reproducing one reported failure without the rest of the suite in the way.
hypothesis_settings.register_profile(
    "debug",
    max_examples=1000,
    deadline=None,
    verbosity=Verbosity.verbose,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)

hypothesis_settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


# ---------------------------------------------------------------------------
# PostgreSQL fixtures (§20.9)
# ---------------------------------------------------------------------------
#
# Declared here rather than in tests/db/ because more than one test package needs
# them: tests/config_integrity/ reads the live catalogue to catch a constraint a
# migration created with raw SQL, which a walk over Base.metadata cannot see.
#
# The migrated database is session scoped because `alembic upgrade head` is the
# expensive part and does not vary per test. Isolation comes from the
# outer-transaction pattern in db_connection, not from rebuilding the schema, which
# would make the suite unusable once there are thirty tables.

from typing import Iterator as _Iterator  # noqa: E402

from sqlalchemy import Connection as _Connection, Engine as _Engine, text as _text  # noqa: E402

from tests.postgres import skip_without_postgres, temporary_database  # noqa: E402


@pytest.fixture(scope="session")
def migrated_url() -> _Iterator[str]:
    """A throwaway database with every migration applied."""
    skip_without_postgres()
    with temporary_database() as url:
        from alembic import command
        from alembic.config import Config

        config = Config("alembic.ini")
        # Passed through env.py rather than exported into os.environ, so a test
        # session cannot leave a stray DATABASE_URL affecting anything else.
        config.attributes["test_url"] = url
        command.upgrade(config, "head")
        yield url


@pytest.fixture(scope="session")
def migrated_engine(migrated_url: str) -> _Iterator[_Engine]:
    from app.db.session import create_guarded_engine

    engine = create_guarded_engine(migrated_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_connection(migrated_engine: _Engine) -> _Iterator[_Connection]:
    """A connection inside a transaction that is always rolled back.

    Every test sees the migrated schema with no rows from any other test, without
    paying for a schema rebuild. Nothing a test writes survives it, including
    trigger side effects, which is what lets the hierarchy tests each build their
    own tree.
    """
    connection = migrated_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture
def area_factory(db_connection: _Connection):
    """Insert an administrative area, returning its derived path and state_key.

    Supplies deliberate rubbish for path and state_key on every call. If the trigger
    ever stops overwriting them, every test using this factory fails rather than one
    dedicated test — the derived-column guarantee is load-bearing for R2.2 and
    should be hard to lose quietly.
    """

    def insert(code: str, area_type: str, name: str, parent_code: str | None = None):
        return db_connection.execute(
            _text(
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

    return insert
