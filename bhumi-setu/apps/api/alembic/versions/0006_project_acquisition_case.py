"""project and acquisition_case.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-31

Task 8.1. §6.1's ``project`` and ``acquisition_case`` tables, the project geometry
column and its GiST index, and the two partial indexes that drive the queue and
the rescore sweep.

Why the two tables land together
--------------------------------

``acquisition_case.project_id`` references ``project``, so the parent has to exist
first and the natural home for both is one migration. ``project`` is created, then
``acquisition_case`` referencing it; the downgrade drops them in the opposite
order so the foreign key is never left dangling.

The stage column is text, and that is the point (§4.3)
------------------------------------------------------

``stage_key`` is created as plain ``text`` with **no enum type and no CHECK
constraint**. The legal stage set and its successor graph are a ``Policy_Config``
value validated in the service layer, so onboarding a state with a different
lifecycle is an INSERT rather than a migration (§4.4). The schema guards of task
2.7 (``tests/config_integrity/test_schema_guards.py``) actively fail the build on
a ``case_stage`` enum or any constraint mentioning ``stage_key`` — this migration
is written to pass them, and deliberately adds neither.

No date column carries a computed default
-----------------------------------------

``stage_set_effective_from``, ``stage_entered_on`` and ``stage_deadline`` are
dates the service supplies from resolved ``Policy_Config`` (R28.6), never derived
in DDL; ``risk_generated_at`` and ``priority_computed_at`` record when something
happened. None of them takes a ``server_default``, because a computed default on a
date column is exactly the buried statutory period task 2.7's guard exists to
catch.

geom is raw SQL, mirroring ltree in the baseline
------------------------------------------------

SQLAlchemy has no native PostGIS type and a frozen migration must not import
``app.db.column_types`` (which keeps changing), so ``geom`` is added with a raw
``ALTER TABLE`` and its GiST index with raw ``CREATE INDEX`` — exactly how
migration 0001 adds ``administrative_area.path`` as ``ltree``. PostGIS is already
installed by the baseline, so no ``CREATE EXTENSION`` is needed here.

The two partial indexes
-----------------------

``case_queue`` and ``case_rescore`` are both partial on ``WHERE is_terminal =
false``: a closed case is neither queued for attention (R21.7/21.10) nor rescored
(R19.2), so excluding terminal rows keeps each index the size of the active
caseload. Written as raw SQL to keep the ``priority_score DESC`` ordering and the
partial predicate verbatim from §6.1, as 0003 and 0005 do for their expression and
partial indexes.

The deferred event.case_id foreign key is *not* added here
----------------------------------------------------------

``event.case_id`` is left without its foreign key to ``acquisition_case`` on
purpose. The event-log schema tests append events carrying an arbitrary
``case_id`` (and ``entity_type = 'acquisition_case'`` with a synthetic
``entity_id``) to exercise the timeline indexes against rows that intentionally
have no backing case; a foreign key here would break those tests. Wiring that
constraint up — and adapting those tests — is left to the case-service work rather
than folded into the table-creation task.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- project ---------------------------------------------------------
    op.create_table(
        "project",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("implementing_authority", sa.Text(), nullable=False),
        sa.Column("area_code", sa.Text(), nullable=False),
        sa.Column("purpose_category", sa.Text(), nullable=False),
        sa.Column("sanctioned_extent", sa.Numeric(14, 4), nullable=False),
        sa.Column("extent_unit", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["area_code"],
            ["administrative_area.code"],
            name="fk_project_area_code_administrative_area",
            ondelete="RESTRICT",
        ),
        comment=(
            "A government undertaking land is acquired for (§6.1). Its cases hold "
            "the acquisition lifecycle; it holds the sanctioned extent and boundary."
        ),
    )

    # geom and its GiST index in raw SQL: no native PostGIS type in SQLAlchemy, and
    # a frozen migration must not import app.db.column_types. Mirrors the ltree
    # handling in migration 0001. PostGIS is installed by the baseline.
    op.execute("ALTER TABLE project ADD COLUMN geom geometry(MultiPolygon, 4326)")
    op.execute("CREATE INDEX project_geom_gist ON project USING gist (geom)")

    # --- acquisition_case ------------------------------------------------
    op.create_table(
        "acquisition_case",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("case_reference", sa.Text(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("state_key", sa.Text(), nullable=False),
        sa.Column("act_key", sa.Text(), nullable=False),
        sa.Column("area_code", sa.Text(), nullable=False),
        # No enum, no CHECK: the stage set is Policy_Config (§4.3). Task 2.7 guards
        # this.
        sa.Column("stage_key", sa.Text(), nullable=False),
        # Dates the service supplies from resolved policy; never a computed default.
        sa.Column("stage_set_effective_from", sa.Date(), nullable=False),
        sa.Column("stage_entered_on", sa.Date(), nullable=False),
        sa.Column("stage_deadline", sa.Date(), nullable=True),
        sa.Column(
            "deadline_breached",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_terminal",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("terminal_event_id", sa.BigInteger(), nullable=True),
        # Denormalised counters, maintained transactionally by their owning
        # subsystems (tasks 11, 12, 13, 16).
        sa.Column(
            "open_blocking_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "undisposed_objection_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "pending_review_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "aggregate_awarded",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "aggregate_disbursed",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        # Current prediction, denormalised from the newest ml_prediction. NULL until
        # scored — omitted from the API rather than sent as zero (§14.7).
        sa.Column("risk_probability", sa.Double(), nullable=True),
        sa.Column("risk_band", sa.Text(), nullable=True),
        sa.Column("risk_model_version", sa.Text(), nullable=True),
        sa.Column("risk_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "risk_is_stale",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("risk_cutoff_source", sa.Text(), nullable=True),
        # Current priority, denormalised for ordering.
        sa.Column("priority_score", sa.Numeric(6, 3), nullable=True),
        sa.Column("priority_weight_version", sa.Text(), nullable=True),
        sa.Column("priority_computed_at", sa.DateTime(timezone=True), nullable=True),
        # R29.1: the version column the Versioned mixin contributes to the model.
        sa.Column(
            "entity_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.UniqueConstraint(
            "case_reference", name="uq_acquisition_case_case_reference"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name="fk_acquisition_case_project_id_project",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["area_code"],
            ["administrative_area.code"],
            name="fk_acquisition_case_area_code_administrative_area",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["terminal_event_id"],
            ["event.id"],
            name="fk_acquisition_case_terminal_event_id_event",
            ondelete="RESTRICT",
        ),
        comment=(
            "The unit of work for one acquisition (§6.1). Versioned (R29.1); "
            "stage_key is text with no enum and no CHECK — the stage set is "
            "Policy_Config (§4.3)."
        ),
    )

    # Live cases by priority within an area (R21.7/21.10) and live cases due for
    # rescoring (R19.2). Both partial on not-terminal so a closed case falls out of
    # each. Raw SQL to keep the DESC ordering and the partial predicate verbatim
    # from §6.1.
    op.execute(
        "CREATE INDEX case_queue ON acquisition_case (area_code, priority_score DESC) "
        "WHERE is_terminal = false"
    )
    op.execute(
        "CREATE INDEX case_rescore ON acquisition_case (risk_generated_at) "
        "WHERE is_terminal = false"
    )


def downgrade() -> None:
    # acquisition_case first: it references project, and its own indexes and the
    # terminal_event_id foreign key to the (retained) event table go with it.
    op.drop_table("acquisition_case")
    # project's geom column and project_geom_gist index are dropped with the table.
    op.drop_table("project")
