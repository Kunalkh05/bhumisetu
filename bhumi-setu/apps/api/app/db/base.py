"""``Base.metadata`` — the single registry of tables.

Why this module holds a monopoly
--------------------------------

Two later tests walk this metadata and fail the build on what they find:

* task 2.7 fails on a ``Date``/``DateTime`` column with a computed
  ``server_default`` other than ``now()``, and on a CHECK constraint containing a
  day count — a statutory period must come from ``Policy_Config`` (§4), never
  from a column default;
* task 25.2 fails on any column that ``CATEGORY_MAP`` does not classify into a
  ``Data_Category`` (R32.2).

A metadata walk is only a guard if the metadata is complete. Two ways it can be
incomplete, and what stops each:

1. **A second registry.** If any module declared its own ``MetaData`` or
   ``DeclarativeBase``, its tables would be invisible here and both guards would
   pass vacuously over them. ``tests/test_metadata_registry.py`` scans the source
   tree and fails on a second registry, so this module is the only one.

2. **A model module nobody imported.** Declarative registration is a side
   effect of import, so a table only exists in ``Base.metadata`` once its module
   has been imported. There is no hand-maintained import list to forget:
   :func:`all_metadata` calls :func:`app.models.load_all_models`, which walks
   ``app/models/`` on disk and imports every module it finds. Adding a file to
   that package is sufficient and nothing else is required.

The corollary is a placement rule, enforced by
``test_tables_are_declared_only_under_app_models``: **a mapped table is declared
in a module under ``app/models/``.** Service and plumbing modules operate on
tables, they do not declare them — ``app/db/event_log.py`` (§3.2) holds the
append logic while the ``event`` table itself is declared in ``app/models/``.
A table declared anywhere else would be outside the walk and therefore outside
both guards.

Consumers — Alembic's ``target_metadata``, the guard tests, ``create_all`` in a
test fixture — call :func:`all_metadata` rather than touching ``Base.metadata``
directly, because only the former guarantees the walk has run.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Names for constraints and indexes that are not named explicitly, so Alembic
# autogenerate produces stable DDL. Where the design names an index or
# constraint (`policy_config_unique_version`, `event_entity_asof`,
# `document_case_checksum`), the explicit name wins and this convention does not
# apply. `ck` intentionally requires a name: an anonymous CHECK constraint is
# undroppable in a later migration without looking up what the database called
# it.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """The one declarative base. Every mapped class in the platform inherits it."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def all_metadata() -> MetaData:
    """Return ``Base.metadata`` with every model module imported.

    The import walk is the point: calling this instead of reading
    ``Base.metadata`` is what makes a metadata walk a guard rather than a
    coincidence.
    """
    from app import models  # imported here: app.models imports this module

    models.load_all_models()
    return Base.metadata
