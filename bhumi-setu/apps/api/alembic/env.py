"""Alembic environment.

``target_metadata`` is :func:`app.db.base.all_metadata`, not ``Base.metadata``.
The difference is the import walk: ``all_metadata()`` imports every module under
``app/models/`` before returning, so a newly added model is present. Reading
``Base.metadata`` directly would autogenerate a migration that silently omits any
table whose module happened not to be imported yet — and the omission looks like
"no changes detected", which is indistinguishable from being up to date.

The URL comes from ``app.settings.get_database_settings()`` rather than from
``alembic.ini``. One source per value; a url in the ini file would be a second
source that wins without saying so.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app.db.base import all_metadata
from app.db.session import create_guarded_engine
from app.settings import get_database_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = all_metadata()


def _url() -> str:
    return get_database_settings().database_url


def include_object(obj, name, type_, reflected, compare_to) -> bool:  # type: ignore[no-untyped-def]
    """Keep PostGIS's own tables out of autogenerate.

    ``CREATE EXTENSION postgis`` creates ``spatial_ref_sys`` and a few views the
    extension owns. They are not in ``Base.metadata``, so without this filter
    every autogenerate produces a migration that drops them — which succeeds, and
    breaks every coordinate transformation afterwards.
    """
    if type_ == "table" and name in {"spatial_ref_sys", "geography_columns", "geometry_columns"}:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # NullPool: a migration process makes one connection and exits, so a pool
    # would only keep the process alive holding an idle connection.
    connectable = create_guarded_engine(_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            # Both on: a type or default that drifts from the models is exactly
            # the kind of divergence that is invisible until it corrupts data.
            compare_type=True,
            compare_server_default=True,
            # One transaction for the whole upgrade. A migration that fails
            # halfway must not leave a partially-migrated schema behind.
            transaction_per_migration=False,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
