"""``upgrade head`` then ``downgrade base`` must both run clean (§20.9).

A downgrade nobody runs is a downgrade that does not work, and it is discovered
during an incident rather than in CI. This is cheap insurance: the round trip
catches a migration that creates something its downgrade forgets to drop, which is
the most common way a downgrade rots.
"""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from tests.postgres import skip_without_postgres, temporary_database

# Objects migration 0001 creates that are not tables, so `drop_table` will not
# remove them and only an explicit DROP in downgrade() will.
_FUNCTIONS = ("bhumisetu_ltree_label", "administrative_area_derive_path",
              "administrative_area_cascade_path")


def _config(url: str) -> Config:
    config = Config("alembic.ini")
    config.attributes["test_url"] = url
    return config


def test_upgrade_then_downgrade_leaves_no_tables_or_functions() -> None:
    skip_without_postgres()
    with temporary_database("bhumisetu_roundtrip") as url:
        config = _config(url)
        command.upgrade(config, "head")

        engine = create_engine(url)
        with engine.connect() as conn:
            tables = set(
                conn.scalars(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                    )
                )
            )
        assert "administrative_area" in tables
        assert "jurisdiction_scope" in tables

        command.downgrade(config, "base")

        with engine.connect() as conn:
            remaining = set(
                conn.scalars(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                    )
                )
            )
            functions = set(
                conn.scalars(
                    text(
                        """
                        SELECT proname FROM pg_proc p
                        JOIN pg_namespace n ON n.oid = p.pronamespace
                        WHERE n.nspname = 'public' AND proname = ANY(:names)
                        """
                    ),
                    {"names": list(_FUNCTIONS)},
                )
            )
        engine.dispose()

        # spatial_ref_sys belongs to PostGIS and downgrade deliberately leaves the
        # extension installed: it is database scoped and dropping it would break
        # anything else in the same database. alembic_version is Alembic's own.
        leftovers = remaining - {"spatial_ref_sys", "alembic_version"}
        assert not leftovers, (
            f"downgrade base left tables behind: {sorted(leftovers)}. A migration "
            "created something its downgrade does not drop."
        )
        assert not functions, (
            f"downgrade base left functions behind: {sorted(functions)}"
        )


def test_upgrade_is_idempotent_against_an_existing_extension() -> None:
    """A database that already has PostGIS must still migrate.

    Real deployments hand over a database with extensions pre-installed by an
    administrator, because CREATE EXTENSION needs privileges the application role
    does not have. If the baseline used a bare CREATE EXTENSION rather than IF NOT
    EXISTS, it would work locally and fail exactly there.
    """
    skip_without_postgres()
    with temporary_database("bhumisetu_preext") as url:
        engine = create_engine(url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))
        engine.dispose()

        command.upgrade(_config(url), "head")
