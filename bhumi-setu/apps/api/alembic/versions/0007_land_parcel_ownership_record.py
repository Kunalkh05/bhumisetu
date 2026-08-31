"""land_parcel, case_parcel, and ownership_record.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-31

Task 9.1. §6.1's ``land_parcel``, the ``case_parcel`` join table, and
``ownership_record`` — the parcel identity and its owners over time. Two of the
three (``land_parcel`` and ``ownership_record``) are R29.1 versioned entities and
carry ``entity_version integer NOT NULL DEFAULT 1``; ``case_parcel`` is a pure
join and is not versioned.

Generated columns, geom and the GiST indexes are raw SQL
--------------------------------------------------------

Exactly as migration 0006 adds ``project.geom`` and migration 0001 adds
``administrative_area.path`` as ``ltree``: SQLAlchemy has no native spelling for a
PostGIS ``geometry`` column, for ``normalize(village, NFC)`` or for a ``daterange``
generation expression, and a frozen migration must not import
``app.db.column_types`` (which keeps changing). So the plain columns are created
with ``op.create_table`` and everything the ORM cannot express is added with raw
``ALTER TABLE`` / ``CREATE INDEX``. The models under ``app/models/`` name the same
columns with the :class:`~app.db.column_types.Geometry` type and ``Computed`` so
``Base.metadata`` stays a faithful picture for the schema-guard walk (task 2.7).

Ordering matters twice
----------------------

``village_norm`` is added before ``parcel_dup_scan`` because that index is over it;
``validity`` is added before ``ownership_validity_gist`` for the same reason. And
``ownership_record``/``case_parcel`` reference ``land_parcel``, so the parcel table
is created first and the downgrade drops it last.

Why btree_gist
--------------

``ownership_validity_gist`` is a *composite* GiST index over
``(parcel_id, validity)``. A range type carries a GiST operator class in core
PostgreSQL, but a scalar like ``bigint`` does not — ``btree_gist`` supplies
``gist_int8_ops``, and without it ``CREATE INDEX ... USING gist (parcel_id,
validity)`` fails with "data type bigint has no default operator class for access
method gist". The extension is created ``IF NOT EXISTS`` and, like ``postgis`` and
``ltree`` in the baseline, is **not** dropped on downgrade: an extension is
database-scoped and dropping it could break anything else sharing the database
(the round-trip test asserts on leftover *tables and functions*, not extensions).

village_norm is for matching only
---------------------------------

``village_norm`` NFC-folds ``village`` so the duplicate scan (R30.9) and the R13.5
detection query compare canonical forms rather than tripping over two byte
sequences that render identically. It is never displayed or exported — the
authoritative ``village`` column is what a record shows. It is nullable in DDL (no
``NOT NULL``), which is what a generated column defaults to.

parcel_identity is one unique index for R6.2, R6.3 and R30.9
------------------------------------------------------------

The six-column identity is unique over ``coalesce(sub_division, '')`` rather than
``sub_division`` directly: two parcels differing only in that one has a NULL
sub-division and the other has ``''`` would otherwise both be admitted, because a
plain unique index treats every NULL as distinct. Folding NULL to ``''`` makes the
"same identity" test total. The rejection message and the matching identifier are
the write path's job (task 9.2); this index is the mechanism it relies on.

No exclusion constraint on ownership overlap (§6.1's explicit rejection)
------------------------------------------------------------------------

The GiST index over ``(parcel_id, validity)`` makes an exclusion constraint on
``(parcel_id, owner_identity_key, validity)`` *available*, and it is deliberately
not created. R13.5 requires an overlapping same-owner validity period to raise a
``BLOCKING`` Validation_Issue, not to be rejected by the database; an exclusion
constraint would reject the write instead, contradicting the requirement and
breaking the bulk import's partial-commit semantics (a batch must commit the good
rows and report the bad, not abort on the first overlap). The range column and its
index exist purely for the as-of query (task 9.3) and for the detection rule.

No date column carries a computed default
-----------------------------------------

``valid_from`` and ``valid_to`` are plain dates the service supplies; neither takes
a ``server_default``, because a computed default on a date column is exactly the
buried period task 2.7's guard exists to catch. ``validity`` is derived from them
by the generation expression, which is data transformation, not a statutory
period.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The composite GiST index below is over (parcel_id, validity); parcel_id is
    # bigint, which has no core GiST opclass. btree_gist supplies it. IF NOT EXISTS
    # and never dropped in downgrade, exactly as the baseline treats postgis/ltree.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # --- land_parcel -----------------------------------------------------
    op.create_table(
        "land_parcel",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("state_key", sa.Text(), nullable=False),
        sa.Column("district", sa.Text(), nullable=False),
        sa.Column("tehsil", sa.Text(), nullable=False),
        sa.Column("village", sa.Text(), nullable=False),
        sa.Column("survey_number", sa.Text(), nullable=False),
        sa.Column("sub_division", sa.Text(), nullable=True),
        sa.Column("classification", sa.Text(), nullable=False),
        sa.Column("extent", sa.Numeric(14, 4), nullable=False),
        sa.Column("extent_unit", sa.Text(), nullable=False),
        sa.Column("area_code", sa.Text(), nullable=False),
        sa.Column("geodesic_area_sqm", sa.Numeric(16, 4), nullable=True),
        # R29.1: contributed by the Versioned mixin on the model.
        sa.Column(
            "entity_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["area_code"],
            ["administrative_area.code"],
            name="fk_land_parcel_area_code_administrative_area",
            ondelete="RESTRICT",
        ),
        comment=(
            "A cadastral parcel: the six-column identity, extent and geometry "
            "(§6.1). Versioned (R29.1)."
        ),
    )

    # village_norm: raw generated column. normalize(village, NFC) has no SQLAlchemy
    # spelling, and a frozen migration must not import app.db.column_types. For
    # matching only (R30.9), never displayed or exported. Added before the
    # dup-scan index that references it.
    op.execute(
        "ALTER TABLE land_parcel ADD COLUMN village_norm text "
        "GENERATED ALWAYS AS (normalize(village, NFC)) STORED"
    )
    # geom and its GiST index in raw SQL, mirroring 0006 and 0001's ltree. PostGIS
    # is installed by the baseline, so no CREATE EXTENSION postgis here.
    op.execute("ALTER TABLE land_parcel ADD COLUMN geom geometry(MultiPolygon, 4326)")

    # One unique index serving R6.2, R6.3 and R30.9. coalesce(sub_division, '') so
    # a NULL sub-division still collides with an empty one and the identity test is
    # total. Expression index → raw SQL.
    op.execute(
        "CREATE UNIQUE INDEX parcel_identity ON land_parcel "
        "(state_key, district, tehsil, village, survey_number, "
        "coalesce(sub_division, ''))"
    )
    op.execute("CREATE INDEX parcel_geom_gist ON land_parcel USING gist (geom)")
    # Indexes the generated village_norm, so it lands after that column exists.
    op.execute(
        "CREATE INDEX parcel_dup_scan ON land_parcel "
        "(state_key, district, tehsil, village_norm, survey_number)"
    )

    # --- case_parcel (join table; not a versioned entity) ----------------
    op.create_table(
        "case_parcel",
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("parcel_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["acquisition_case.id"],
            name="fk_case_parcel_case_id_acquisition_case",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parcel_id"],
            ["land_parcel.id"],
            name="fk_case_parcel_parcel_id_land_parcel",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("case_id", "parcel_id", name="pk_case_parcel"),
        comment=(
            "Which parcels a case acquires (§6.1). A pure join, so not versioned "
            "and no entity_version; RESTRICT keeps a referenced case or parcel from "
            "being deleted from under the link."
        ),
    )

    # --- ownership_record ------------------------------------------------
    op.create_table(
        "ownership_record",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("parcel_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_name", sa.Text(), nullable=True),
        sa.Column("owner_identity_key", sa.Text(), nullable=True),
        sa.Column("government_identifier", sa.Text(), nullable=True),
        sa.Column("contact_mobile", sa.Text(), nullable=True),
        sa.Column("contact_mobile_hash", sa.LargeBinary(), nullable=True),
        sa.Column("interest_type", sa.Text(), nullable=False),
        sa.Column("share", sa.Numeric(12, 6), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        # R29.1: contributed by the Versioned mixin on the model.
        sa.Column(
            "entity_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["parcel_id"],
            ["land_parcel.id"],
            name="fk_ownership_record_parcel_id_land_parcel",
            ondelete="RESTRICT",
        ),
        comment=(
            "An owner's interest in a parcel over a validity period (§6.1). "
            "Versioned (R29.1); owner_name, government_identifier and "
            "contact_mobile are erasable personal data."
        ),
    )

    # validity: raw generated daterange with inclusive '[]' bounds. An open
    # valid_to becomes an unbounded upper bound, so the as-of query (task 9.3) is a
    # plain validity @> :d with no COALESCE or OR. Generated → raw SQL, and added
    # before the index over it.
    op.execute(
        "ALTER TABLE ownership_record ADD COLUMN validity daterange "
        "GENERATED ALWAYS AS (daterange(valid_from, valid_to, '[]')) STORED"
    )
    # GiST over (parcel_id, validity): the as-of query and the R13.5 overlap scan.
    # Deliberately NOT an exclusion constraint (§6.1): R13.5 wants an overlapping
    # same-owner period to raise a Validation_Issue, not to be rejected by the
    # database, and an exclusion constraint would also break the import's
    # partial-commit semantics. Composite over a bigint, hence btree_gist above.
    op.execute(
        "CREATE INDEX ownership_validity_gist ON ownership_record "
        "USING gist (parcel_id, validity)"
    )
    # Plain btree on the retained hash for OTP lookup after contact erasure.
    op.create_index(
        "ownership_mobile_hash", "ownership_record", ["contact_mobile_hash"]
    )


def downgrade() -> None:
    # Reverse of creation, honouring the foreign keys: ownership_record and
    # case_parcel both reference land_parcel, so both drop before it. Generated
    # columns, geom and every index drop with their tables. btree_gist is left
    # installed (see upgrade) — an extension is database-scoped.
    op.drop_table("ownership_record")
    op.drop_table("case_parcel")
    op.drop_table("land_parcel")
