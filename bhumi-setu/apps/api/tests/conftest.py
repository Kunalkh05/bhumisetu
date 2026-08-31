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
