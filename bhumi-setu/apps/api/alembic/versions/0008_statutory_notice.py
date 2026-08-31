"""statutory_notice, notice_parcel, and notice_service_record.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-31

Task 10.1. §6.1's ``statutory_notice``, the ``notice_parcel`` join table, and
``notice_service_record`` — a case's notices, the parcels each notice covers, and
where each notice was served. Two of the three (``statutory_notice`` and
``notice_service_record``) are R29.1 versioned entities and carry
``entity_version integer NOT NULL DEFAULT 1``; ``notice_parcel`` is a pure join
and is not versioned, exactly as ``case_parcel`` in migration 0007.

response_deadline is frozen at issue, and that is what makes R7.8 structural
-----------------------------------------------------------------------------

``response_deadline`` is a plain ``date NOT NULL`` the Notice_Service *stores* when
the notice is issued (task 10.2), computed as the issue date advanced by the
Policy_Config response period effective on that issue date. It is deliberately
**not** a computed default and carries **no** ``server_default``: a default would
have to know the state, the act and the issue date to resolve the period (R28.6),
which a column default cannot, and it would be exactly the buried statutory period
task 2.7's guard exists to catch. Freezing the resolved date in a column is what
gives R7.8 its guarantee — a later change to the period leaves already-issued
notices untouched because their deadline is stored, not recomputed — rather than
leaving "don't recompute old deadlines" as a rule someone has to remember.

``policy_snapshot_hash`` records the PolicySnapshot content hash (§4.2) of the
configuration that produced that deadline, so a stored date is attributable to the
exact policy state it came from. It is ``text NOT NULL``: a frozen deadline whose
provenance is unknown is not attributable, so there is no notice without one.

``issue_date`` and ``service_date`` are likewise plain dates the service supplies;
neither takes a ``server_default`` for the same reason. ``breach_state`` defaults
to ``'WITHIN'`` — a text state, not a date arithmetic — which the deadline sweep
(task 10.3) advances; a text default is not a statutory period and the guard
permits it.

service_location is raw SQL, mirroring geom in 0006 and 0007
------------------------------------------------------------

``notice_service_record.service_location`` is a ``geometry(Point, 4326)`` (R15.2:
point geometries for service locations, in the one platform-wide SRID, §12).
SQLAlchemy has no native PostGIS type and a frozen migration must not import
``app.db.column_types`` (which keeps changing), so the column and its GiST index
are added with raw ``ALTER TABLE`` / ``CREATE INDEX`` — exactly how migration 0006
adds ``project.geom`` and 0007 adds ``land_parcel.geom``. PostGIS is installed by
the baseline, so no ``CREATE EXTENSION`` is needed here. The model names the same
column with the :class:`~app.db.column_types.Geometry` type and a GiST ``Index`` so
``Base.metadata`` stays a faithful picture for the schema-guard walk (task 2.7).
It is nullable: a service can be recorded before its location is captured, and not
every service mode has a meaningful point (a newspaper publication has none).

Ordering and the foreign keys
-----------------------------

``statutory_notice`` is created first: both ``notice_parcel`` and
``notice_service_record`` reference it. ``notice_parcel`` also references
``land_parcel`` and ``notice_service_record`` also references ``ownership_record``,
all of which migration 0007 created. Every foreign key is ``ON DELETE RESTRICT``,
matching every other reference in the schema — nothing here is hard-deleted from
under a dependant (retention is erasure, not deletion). The downgrade drops the
two children before ``statutory_notice`` so no foreign key is ever left dangling.

No enum, no date default, no day-count CHECK
--------------------------------------------

Nothing here carries an enum type, a computed date default, or a CHECK constraint
mentioning a day count — the schema guards of task 2.7 are written to pass, and
this migration is written to pass them. ``notice_type``, ``publication_mode`` and
``service_mode`` are open ``text`` vocabularies (§4.4), not enums.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- statutory_notice ------------------------------------------------
    op.create_table(
        "statutory_notice",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("notice_type", sa.Text(), nullable=False),
        sa.Column("issuing_authority", sa.Text(), nullable=False),
        # Plain dates the service supplies; no server_default (task 2.7).
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("publication_mode", sa.Text(), nullable=False),
        # Frozen at issue (R7.8): the resolved deadline is stored, never a computed
        # default that would have to know the state, act and date to resolve.
        sa.Column("response_deadline", sa.Date(), nullable=False),
        # The PolicySnapshot content hash (§4.2) of the config that produced the
        # deadline, so a frozen date is attributable to its policy state.
        sa.Column("policy_snapshot_hash", sa.Text(), nullable=False),
        # A text state the deadline sweep advances (task 10.3); a text default is
        # not a statutory period, so the guard permits it.
        sa.Column(
            "breach_state",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'WITHIN'"),
        ),
        # R29.1: contributed by the Versioned mixin on the model.
        sa.Column(
            "entity_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["acquisition_case.id"],
            name="fk_statutory_notice_case_id_acquisition_case",
            ondelete="RESTRICT",
        ),
        comment=(
            "A statutory notice issued on a case (§6.1). Versioned (R29.1). "
            "response_deadline is frozen at issue and policy_snapshot_hash records "
            "the configuration that produced it — R7.8 is structural, not a rule."
        ),
    )

    # --- notice_parcel (join table; not a versioned entity) --------------
    op.create_table(
        "notice_parcel",
        sa.Column("notice_id", sa.BigInteger(), nullable=False),
        sa.Column("parcel_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["notice_id"],
            ["statutory_notice.id"],
            name="fk_notice_parcel_notice_id_statutory_notice",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parcel_id"],
            ["land_parcel.id"],
            name="fk_notice_parcel_parcel_id_land_parcel",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("notice_id", "parcel_id", name="pk_notice_parcel"),
        comment=(
            "Which parcels a notice covers (§6.1). A pure join, so not versioned "
            "and no entity_version; RESTRICT keeps a referenced notice or parcel "
            "from being deleted from under the link."
        ),
    )

    # --- notice_service_record -------------------------------------------
    op.create_table(
        "notice_service_record",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("notice_id", sa.BigInteger(), nullable=False),
        sa.Column("ownership_record_id", sa.BigInteger(), nullable=False),
        # Plain date the service supplies; no server_default (task 2.7).
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("service_mode", sa.Text(), nullable=False),
        # R29.1: contributed by the Versioned mixin on the model.
        sa.Column(
            "entity_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["notice_id"],
            ["statutory_notice.id"],
            name="fk_notice_service_record_notice_id_statutory_notice",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ownership_record_id"],
            ["ownership_record.id"],
            name="fk_notice_service_record_ownership_record_id_ownership_record",
            ondelete="RESTRICT",
        ),
        comment=(
            "Where and how a notice was served on an interested person (§6.1, "
            "R7.5). Versioned (R29.1)."
        ),
    )

    # service_location and its GiST index in raw SQL, mirroring project.geom in
    # 0006 and land_parcel.geom in 0007: no native PostGIS type in SQLAlchemy, and
    # a frozen migration must not import app.db.column_types. PostGIS is installed
    # by the baseline. Point geometry per R15.2; nullable because a service can be
    # recorded before its location is captured and not every mode has a point.
    op.execute(
        "ALTER TABLE notice_service_record "
        "ADD COLUMN service_location geometry(Point, 4326)"
    )
    op.execute(
        "CREATE INDEX notice_service_location_gist ON notice_service_record "
        "USING gist (service_location)"
    )


def downgrade() -> None:
    # Reverse of creation, honouring the foreign keys: notice_service_record and
    # notice_parcel both reference statutory_notice, so both drop before it. The
    # service_location column and its GiST index drop with their table.
    op.drop_table("notice_service_record")
    op.drop_table("notice_parcel")
    op.drop_table("statutory_notice")
