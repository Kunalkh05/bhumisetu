"""Locating and creating a throwaway PostgreSQL database for tests.

Separate from ``conftest.py`` because ``tests/db/conftest.py`` and the migration
round-trip both need it, and because the discovery rules below are worth reading
once rather than being buried among fixtures.

Discovery order for the server
------------------------------

1. ``BHUMISETU_TEST_DATABASE_URL`` if set. CI sets this at the service container.
2. A local server on the default socket, reached with the current user. This is
   what Postgres.app gives on a developer machine, and it needs no password
   because ``initdb`` ran with trust auth for local connections.

If neither answers, the PostgreSQL-backed tests **skip** rather than fail. They
are not optional in CI — a skip there would let a broken migration merge — so
:envvar:`BHUMISETU_REQUIRE_POSTGRES` turns the skip into a hard failure, and the
CI pipeline sets it. Locally, a contributor without a server should still be able
to run the rest of the suite.

Why a separate database rather than a transaction on the main one
-----------------------------------------------------------------

The migration round-trip runs ``upgrade head`` then ``downgrade base``, which is
DDL against every table. Doing that inside a transaction on the development
database would work right up until a test failed and left it half-migrated, and
``CREATE EXTENSION`` is not something to roll back under a developer's feet. A
database created and dropped per session cannot damage anything.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

__all__ = [
    "POSTGRES_REQUIRED",
    "admin_url",
    "postgres_available",
    "skip_without_postgres",
    "temporary_database",
]

POSTGRES_REQUIRED = os.environ.get("BHUMISETU_REQUIRE_POSTGRES") == "1"

# Postgres.app keeps its binaries outside the shell PATH a test runner inherits.
# `latest` is a symlink, so this survives an upgrade.
_POSTGRES_APP_BIN = Path(
    "/Applications/Postgres.app/Contents/Versions/latest/bin"
)


def _psql_env() -> dict[str, str]:
    env = dict(os.environ)
    if _POSTGRES_APP_BIN.is_dir():
        env["PATH"] = f"{_POSTGRES_APP_BIN}:{env.get('PATH', '')}"
    return env


def admin_url() -> str:
    """A URL for a database that certainly exists, used to CREATE and DROP others."""
    explicit = os.environ.get("BHUMISETU_TEST_DATABASE_URL")
    if explicit:
        return explicit
    user = os.environ.get("PGUSER") or os.environ.get("USER") or "postgres"
    return f"postgresql+psycopg://{user}@localhost:5432/postgres"


def postgres_available() -> bool:
    """True when a server answers. Cached per process; connection attempt is cheap."""
    global _available
    if _available is None:
        from sqlalchemy import create_engine, text

        try:
            engine = create_engine(admin_url(), connect_args={"connect_timeout": 3})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            _available = True
        except Exception:
            _available = False
    return _available


_available: bool | None = None


def skip_without_postgres() -> None:
    """Skip, or fail if CI has declared a server mandatory."""
    if postgres_available():
        return
    message = (
        "no PostgreSQL server reachable. Start Postgres.app, or set "
        "BHUMISETU_TEST_DATABASE_URL. See docs/postgres-app-setup.md."
    )
    if POSTGRES_REQUIRED:
        pytest.fail(f"BHUMISETU_REQUIRE_POSTGRES=1 but {message}")
    pytest.skip(message)


@contextmanager
def temporary_database(prefix: str = "bhumisetu_test") -> Iterator[str]:
    """Create a uniquely named database, yield its URL, drop it afterwards.

    The name carries a uuid fragment so two test sessions in parallel — a local
    run and a watcher, or two CI shards — cannot collide on it. Dropping happens
    in a ``finally`` with ``WITH (FORCE)`` so a leaked connection from a failed
    test does not leave the database behind for the next run to trip over.
    """
    from sqlalchemy import create_engine, text

    name = f"{prefix}_{uuid.uuid4().hex[:12]}"
    admin = create_engine(admin_url(), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        yield admin_url().rsplit("/", 1)[0] + f"/{name}"
    finally:
        with admin.connect() as conn:
            conn.execute(
                text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
            )
        admin.dispose()
