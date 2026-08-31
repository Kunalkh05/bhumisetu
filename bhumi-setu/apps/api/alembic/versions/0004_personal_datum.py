"""personal_datum: erasable references from event payloads.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-31

Task 3.2. §5.4's table, its two indexes, and the trigger that makes "mutable in
exactly one way" a guarantee rather than a comment.

The trigger permits exactly one transition
------------------------------------------

``value_ciphertext`` to NULL with ``erased_at`` set, once. Everything else is
rejected:

* changing ``data_category``, ``entity_type``, ``entity_id``, ``attribute_name``,
  ``key_version`` or ``created_at`` — the row identifies what it holds, and moving
  that identity would silently re-point an event payload at a different value;
* setting ``value_ciphertext`` to a new non-NULL value — that is a rewrite of
  history through the back door, since event payloads reference this row;
* un-erasing, by clearing ``erased_at`` or restoring the ciphertext — erasure is
  irreversible under R32.10 and a reversible erasure is not an erasure;
* erasing twice with a different timestamp, which would make the ``$erased`` marker
  in R32.13's read path disagree with the compensating event.

DELETE is refused outright. A deleted row leaves every event payload referencing it
resolving to nothing, which is indistinguishable from a bug and loses the
``data_category`` and ``erased_at`` that R32.13 requires the resolver to return.

Enforced by trigger rather than by grant, unlike ``event``
---------------------------------------------------------

``event`` uses ``REVOKE UPDATE, DELETE`` because it needs *no* updates. This table
needs exactly one, so a grant cannot express the rule and a trigger is the only
mechanism that can distinguish the permitted transition from every other. The
tradeoff is that a superuser bypasses it — which is why the tests here assert the
trigger fires for the owner as well, since a trigger, unlike a privilege, applies to
everyone by default.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SINGLE_TRANSITION_FN = """
CREATE OR REPLACE FUNCTION personal_datum_single_transition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'personal_datum rows cannot be deleted: event payloads reference them '
            '(R32.13). Erase the value instead.'
            USING ERRCODE = 'restrict_violation';
    END IF;

    -- Identity is immutable. Changing it would re-point existing event payloads
    -- at a different value without touching a single event row.
    IF NEW.id            IS DISTINCT FROM OLD.id
    OR NEW.data_category IS DISTINCT FROM OLD.data_category
    OR NEW.entity_type   IS DISTINCT FROM OLD.entity_type
    OR NEW.entity_id     IS DISTINCT FROM OLD.entity_id
    OR NEW.attribute_name IS DISTINCT FROM OLD.attribute_name
    OR NEW.key_version   IS DISTINCT FROM OLD.key_version
    OR NEW.created_at    IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION
            'personal_datum identity is immutable; only erasure may change a row'
            USING ERRCODE = 'restrict_violation';
    END IF;

    -- Un-erasure. Erasure is irreversible (R32.10); a reversible one is not an
    -- erasure at all.
    IF OLD.erased_at IS NOT NULL THEN
        IF NEW.erased_at IS DISTINCT FROM OLD.erased_at THEN
            RAISE EXCEPTION 'erased_at is set once and cannot change'
                USING ERRCODE = 'restrict_violation';
        END IF;
        IF NEW.value_ciphertext IS NOT NULL THEN
            RAISE EXCEPTION 'an erased value cannot be restored'
                USING ERRCODE = 'restrict_violation';
        END IF;
        IF NEW.erasure_event_id IS DISTINCT FROM OLD.erasure_event_id
           AND OLD.erasure_event_id IS NOT NULL THEN
            RAISE EXCEPTION 'erasure_event_id is set once and cannot change'
                USING ERRCODE = 'restrict_violation';
        END IF;
        RETURN NEW;
    END IF;

    -- The one permitted transition: ciphertext to NULL, erased_at set.
    IF NEW.value_ciphertext IS NULL AND NEW.erased_at IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- Anything else. Note this also rejects setting a *new* non-NULL ciphertext,
    -- which would be a rewrite of history through the back door.
    RAISE EXCEPTION
        'the only permitted update sets value_ciphertext to NULL and erased_at to '
        'a timestamp; got value_ciphertext % and erased_at %',
        CASE WHEN NEW.value_ciphertext IS NULL THEN 'NULL' ELSE 'non-NULL' END,
        CASE WHEN NEW.erased_at IS NULL THEN 'NULL' ELSE 'set' END
        USING ERRCODE = 'restrict_violation';
END;
$$;
"""

SINGLE_TRANSITION_TRIGGER = """
CREATE TRIGGER personal_datum_single_transition
BEFORE UPDATE OR DELETE
ON personal_datum
FOR EACH ROW
EXECUTE FUNCTION personal_datum_single_transition();
"""


def upgrade() -> None:
    op.create_table(
        "personal_datum",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("data_category", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("attribute_name", sa.Text(), nullable=False),
        sa.Column("value_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("erased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("erasure_event_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["erasure_event_id"],
            ["event.id"],
            name="fk_personal_datum_erasure_event_id_event",
            ondelete="RESTRICT",
        ),
        comment=(
            "Personal-data values referenced from event payloads (§5.4). The only "
            "mutable thing in the log's read path, with exactly one permitted "
            "transition, enforced by trigger."
        ),
    )

    op.create_index(
        "personal_datum_target",
        "personal_datum",
        ["entity_type", "entity_id", "attribute_name"],
    )
    # Partial, so the sweep's index shrinks as data ages out rather than growing.
    op.execute(
        "CREATE INDEX personal_datum_category ON personal_datum (data_category) "
        "WHERE erased_at IS NULL"
    )

    op.execute(SINGLE_TRANSITION_FN)
    op.execute(SINGLE_TRANSITION_TRIGGER)

    # The application role reads and writes these rows and erases them, but must
    # never delete one. The trigger refuses DELETE for everyone; revoking it as well
    # means the attempt fails at the privilege check rather than reaching plpgsql.
    op.execute("GRANT SELECT, INSERT, UPDATE ON personal_datum TO bhumisetu_app")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE personal_datum_id_seq TO bhumisetu_app")
    op.execute("REVOKE DELETE ON personal_datum FROM bhumisetu_app")


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS personal_datum_single_transition ON personal_datum"
    )
    op.drop_table("personal_datum")
    op.execute("DROP FUNCTION IF EXISTS personal_datum_single_transition()")
