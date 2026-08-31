"""Baseline: extensions, administrative hierarchy, officers, roles, scope.

Revision ID: 0001
Revises:
Create Date: 2026-08-31

Covers task 1.2. Four things land here and each has a reason to be in the
*baseline* rather than a later migration:

1. **Extensions.** ``ltree`` is needed by the very first table, and ``postgis``
   and ``pgcrypto`` are needed before any table that uses them exists. Creating
   them later would mean the first migration to need one also has to create it,
   which puts extension management in an arbitrary place.

2. **The administrative hierarchy**, because jurisdiction scope (R2.1) is the
   first thing every other table's authorization depends on.

3. **The path/state_key trigger.** ``path`` and ``state_key`` restate facts held
   in ``parent_code``, and derived state that the application writes will
   eventually disagree with its source. The trigger makes disagreement
   impossible rather than unlikely.

4. **The ``bhumisetu_app`` role**, so task 3.1 has a role to revoke
   ``UPDATE, DELETE`` on ``event`` from. R4.2's append-only guarantee is a
   revoked grant, not application code, and a grant needs a grantee that exists
   first.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# ltree label transliteration, in SQL.
#
# This mirrors app.db.column_types.to_ltree_label. Two implementations of one
# rule is a divergence risk, and it is accepted deliberately: the trigger must
# run inside the database so that *every* insert path is covered, including the
# bulk import of task 26 and any psql session, and the application must be able
# to compute a label without a round trip.
#
# The risk is contained by a test that runs both over the same generated inputs
# and asserts equality (tests/db/test_ltree_label_parity.py). Without that test
# this pair would drift, and the symptom would be a scope check that silently
# matches nothing.
# ---------------------------------------------------------------------------
LTREE_LABEL_FN = """
CREATE OR REPLACE FUNCTION bhumisetu_ltree_label(code text)
RETURNS text
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT NULLIF(btrim(regexp_replace(code, '[^A-Za-z0-9_]+', '_', 'g'), '_'), '')
$$;
"""

DERIVE_PATH_FN = """
CREATE OR REPLACE FUNCTION administrative_area_derive_path()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    self_label text;
    parent_row administrative_area;
BEGIN
    self_label := bhumisetu_ltree_label(NEW.code);
    IF self_label IS NULL THEN
        RAISE EXCEPTION
            'administrative code % has no ltree-legal characters', NEW.code
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.parent_code IS NULL THEN
        -- A root area is where state_key originates, so it names itself. The
        -- root_area_is_a_state CHECK already restricts this branch to states.
        NEW.path := self_label::ltree;
        NEW.state_key := NEW.code;
    ELSE
        SELECT * INTO parent_row
        FROM administrative_area
        WHERE code = NEW.parent_code;

        IF NOT FOUND THEN
            -- Unreachable through the FK, but a trigger that assumes its
            -- lookup succeeded would write a NULL path and fail confusingly.
            RAISE EXCEPTION 'parent area % does not exist', NEW.parent_code
                USING ERRCODE = 'foreign_key_violation';
        END IF;

        NEW.path := parent_row.path || self_label::ltree;
        NEW.state_key := parent_row.state_key;
    END IF;

    RETURN NEW;
END;
$$;
"""

# BEFORE INSERT OR UPDATE, so a supplied path or state_key is overwritten rather
# than trusted. UPDATE is included because re-parenting an area must move its
# path; the descendant cascade below handles everything beneath it.
DERIVE_PATH_TRIGGER = """
CREATE TRIGGER administrative_area_derive_path
BEFORE INSERT OR UPDATE OF code, parent_code, path, state_key
ON administrative_area
FOR EACH ROW
EXECUTE FUNCTION administrative_area_derive_path();
"""

# Re-parenting a district has to move every path beneath it. Without this, an
# area moves and its descendants keep paths claiming the old ancestry — so a
# scope check on the new parent silently misses them, which reads as a
# permissions bug rather than stale data.
CASCADE_PATH_FN = """
CREATE OR REPLACE FUNCTION administrative_area_cascade_path()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.path IS DISTINCT FROM OLD.path
       OR NEW.state_key IS DISTINCT FROM OLD.state_key THEN
        UPDATE administrative_area
        SET path = NEW.path || subpath(path, nlevel(OLD.path)),
            state_key = NEW.state_key
        WHERE path <@ OLD.path
          AND code <> NEW.code;
    END IF;
    RETURN NULL;
END;
$$;
"""

# AFTER UPDATE with **no column list**, deliberately.
#
# `AFTER UPDATE OF path` does not work here, and the way it fails is silent.
# PostgreSQL arms an `UPDATE OF col` trigger based on the columns named in the
# statement's SET list, not on the columns actually modified. Re-parenting is
# `SET parent_code = ...`, and the BEFORE trigger is what changes `path` — so an
# `UPDATE OF path` trigger never fires, descendants keep paths claiming the old
# ancestry, and a scope check on the new parent quietly misses them. That reads
# as a permissions bug, a long way from its cause.
#
# The function's own `IS DISTINCT FROM` guard makes the missing column list
# cheap: an update that leaves the path alone does no work.
CASCADE_PATH_TRIGGER = """
CREATE TRIGGER administrative_area_cascade_path
AFTER UPDATE
ON administrative_area
FOR EACH ROW
EXECUTE FUNCTION administrative_area_cascade_path();
"""

# Task 3.1 revokes UPDATE and DELETE on `event` from this role, which is how
# R4.2's append-only log is enforced by the database rather than by application
# code. NOLOGIN: it is the role the application connects *as* in a deployed
# environment, granted to the connecting user there; locally the developer's
# superuser connection is used and the revoke is exercised by the tests that
# SET ROLE to it.
CREATE_APP_ROLE = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bhumisetu_app') THEN
        CREATE ROLE bhumisetu_app NOLOGIN;
    END IF;
END
$$;
"""


def upgrade() -> None:
    # --- extensions ------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute(CREATE_APP_ROLE)
    op.execute(LTREE_LABEL_FN)

    # --- administrative hierarchy ---------------------------------------
    op.create_table(
        "administrative_area",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("area_type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("parent_code", sa.String(64), nullable=True),
        sa.Column("state_key", sa.String(64), nullable=False),
        # `path` is added by raw ALTER below: SQLAlchemy has no ltree type, and
        # importing app.db.column_types here would couple a frozen migration to a
        # module that keeps changing.
        sa.ForeignKeyConstraint(
            ["parent_code"],
            ["administrative_area.code"],
            name="fk_administrative_area_parent_code_administrative_area",
            ondelete="RESTRICT",
        ),
        # Bare names. The `ck` naming convention in app/db/base.py is
        # ck_%(table_name)s_%(constraint_name)s, so it wraps the name given here.
        # Passing an already-prefixed name yields
        # ck_administrative_area_ck_administrative_area_root_area_c599 — prefixed
        # twice, truncated at 63 characters, with a hash suffix. That name is
        # unpredictable, so a later migration cannot DROP the constraint by name,
        # it does not match what the model declares (making every autogenerate
        # emit a spurious diff), and the error message a violation produces no
        # longer says what the rule was.
        sa.CheckConstraint(
            "parent_code IS NULL OR parent_code <> code",
            name="area_not_its_own_parent",
        ),
        sa.CheckConstraint(
            "parent_code IS NOT NULL OR area_type = 'state'",
            name="root_area_is_a_state",
        ),
        comment=(
            "Administrative hierarchy. Jurisdiction scope (R2.1) is a set of "
            "rows here; scope containment (R2.2) is path <@ scope_path."
        ),
    )
    # Added nullable, then set NOT NULL after the trigger exists. Declaring it
    # NOT NULL up front would reject every insert before the BEFORE trigger has a
    # chance to derive the value.
    op.execute("ALTER TABLE administrative_area ADD COLUMN path ltree")

    op.execute(DERIVE_PATH_FN)
    op.execute(DERIVE_PATH_TRIGGER)
    op.execute(CASCADE_PATH_FN)
    op.execute(CASCADE_PATH_TRIGGER)

    op.execute("ALTER TABLE administrative_area ALTER COLUMN path SET NOT NULL")

    op.create_index(
        "administrative_area_path_gist",
        "administrative_area",
        ["path"],
        postgresql_using="gist",
    )
    op.create_index("administrative_area_parent", "administrative_area", ["parent_code"])
    op.create_index("administrative_area_state", "administrative_area", ["state_key"])

    # --- roles and officers ---------------------------------------------
    op.create_table(
        "role",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "permissions",
            sa.dialects.postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        comment=(
            "A role carries both permissions and territory (R2.1), so the same "
            "job in two districts is two roles."
        ),
    )

    op.create_table(
        "officer",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("officer_code", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("designation", sa.String(255), nullable=True),
        sa.Column("credential_hash", sa.Text(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        comment=(
            "Officers are deactivated, not deleted, so event actors stay "
            "resolvable (R4.1)."
        ),
    )

    op.create_table(
        "officer_role",
        sa.Column(
            "officer_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True
        ),
        sa.Column(
            "role_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["officer_id"],
            ["officer.id"],
            name="fk_officer_role_officer_id_officer",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["role.id"],
            name="fk_officer_role_role_id_role",
            ondelete="CASCADE",
        ),
        comment="Officer-to-role grants. Read on every authenticated request.",
    )
    op.create_index("officer_role_by_role", "officer_role", ["role_id"])

    op.create_table(
        "jurisdiction_scope",
        sa.Column(
            "role_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True
        ),
        sa.Column("area_code", sa.String(64), primary_key=True),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["role.id"], name="fk_jurisdiction_scope_role_id_role", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["area_code"],
            ["administrative_area.code"],
            name="fk_jurisdiction_scope_area_code_administrative_area",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("role_id", "area_code", name="jurisdiction_scope_unique"),
        comment=(
            "Territory of a role (R2.1). Union across rows; containment is "
            "path <@ area.path so one district row covers its descendants."
        ),
    )
    op.create_index("jurisdiction_scope_by_area", "jurisdiction_scope", ["area_code"])


def downgrade() -> None:
    op.drop_table("jurisdiction_scope")
    op.drop_table("officer_role")
    op.drop_table("officer")
    op.drop_table("role")
    op.execute("DROP TRIGGER IF EXISTS administrative_area_cascade_path ON administrative_area")
    op.execute("DROP TRIGGER IF EXISTS administrative_area_derive_path ON administrative_area")
    op.drop_table("administrative_area")
    op.execute("DROP FUNCTION IF EXISTS administrative_area_cascade_path()")
    op.execute("DROP FUNCTION IF EXISTS administrative_area_derive_path()")
    op.execute("DROP FUNCTION IF EXISTS bhumisetu_ltree_label(text)")
    # Extensions and the bhumisetu_app role are deliberately not dropped. Both
    # are cluster or database scoped rather than schema scoped, and another
    # database in the same cluster may depend on them. `downgrade base` is for
    # rebuilding the schema, not for uninstalling PostGIS.
