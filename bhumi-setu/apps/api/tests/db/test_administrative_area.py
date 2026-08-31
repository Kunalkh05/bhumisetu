"""The administrative hierarchy triggers, and the two bugs they had.

R2.1 and R2.2. Every assertion here was run by hand while migration 0001 was
written; this file is what makes them permanent. Two of them failed the first
time, and both failed *silently* — no error, just a hierarchy that quietly
disagreed with itself.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text


def _tree(area_factory) -> None:
    """A hierarchy whose codes exercise transliteration rather than assuming it.

    ``MH.PUNE`` contains ltree's separator and ``HAVELI-1`` a hyphen, so a
    regression in labelling shows up as a wrong path here rather than needing its
    own test.
    """
    area_factory("MH", "state", "Maharashtra")
    area_factory("MH.PUNE", "district", "Pune", "MH")
    area_factory("MH.SATARA", "district", "Satara", "MH")
    area_factory("HAVELI-1", "tehsil", "Haveli", "MH.PUNE")
    area_factory("WAGHOLI", "village", "Wagholi", "HAVELI-1")
    area_factory("KESNAND", "village", "Kesnand", "HAVELI-1")


def _paths(connection: Connection) -> dict[str, str]:
    return {
        row.code: row.path
        for row in connection.execute(
            text("SELECT code, path::text AS path FROM administrative_area")
        )
    }


def _contained_by(connection: Connection, code: str) -> set[str]:
    """Codes inside ``code``'s subtree — the R2.2 scope test, verbatim."""
    return set(
        connection.scalars(
            text(
                """
                SELECT a.code FROM administrative_area a
                WHERE a.path <@ (
                    SELECT path FROM administrative_area WHERE code = :code
                )
                """
            ),
            {"code": code},
        )
    )


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------


def test_supplied_path_and_state_key_are_overwritten(area_factory) -> None:
    """The application must not be able to set either column.

    ``area_factory`` supplies the literal 'SUPPLIED' for both. If the trigger
    stops overwriting them, R2.2's containment starts answering against whatever a
    caller felt like storing.
    """
    row = area_factory("MH", "state", "Maharashtra")
    assert row.path == "MH"
    assert row.state_key == "MH"


def test_separator_in_a_code_becomes_one_label_not_two(area_factory) -> None:
    """``MH.PUNE`` is one district, so it must be one level.

    Untransliterated it would cast to ltree perfectly happily and become two
    levels, putting the district at the depth of a tehsil and silently corrupting
    every containment answer beneath it.
    """
    area_factory("MH", "state", "Maharashtra")
    row = area_factory("MH.PUNE", "district", "Pune", "MH")
    assert row.path == "MH.MH_PUNE"
    assert row.path.count(".") == 1


def test_state_key_is_inherited_from_the_root(area_factory) -> None:
    _tree(area_factory)
    row = area_factory("SOMEWHERE", "village", "Somewhere", "HAVELI-1")
    assert row.state_key == "MH"


def test_path_extends_the_parents_path(db_connection: Connection, area_factory) -> None:
    _tree(area_factory)
    paths = _paths(db_connection)
    assert paths["WAGHOLI"].startswith(paths["HAVELI-1"] + ".")
    assert paths["HAVELI-1"].startswith(paths["MH.PUNE"] + ".")


# ---------------------------------------------------------------------------
# R2.2 containment
# ---------------------------------------------------------------------------


def test_scope_containment_reaches_every_descendant(
    db_connection: Connection, area_factory
) -> None:
    """One district row in jurisdiction_scope must cover its whole subtree.

    This is the property the ltree path exists for: an officer scoped to Pune sees
    Wagholi without Wagholi being listed anywhere.
    """
    _tree(area_factory)
    assert _contained_by(db_connection, "MH.PUNE") == {
        "MH.PUNE",
        "HAVELI-1",
        "WAGHOLI",
        "KESNAND",
    }
    assert _contained_by(db_connection, "MH.SATARA") == {"MH.SATARA"}


def test_containment_uses_the_gist_index(
    db_connection: Connection, area_factory
) -> None:
    """A correct answer arrived at by a sequential scan is a latency bug waiting.

    Asserted with enable_seqscan off, which is how you ask "is the index usable"
    rather than "did the planner prefer it on six rows". Without a usable index
    every scoped list query degrades as the area table grows.
    """
    _tree(area_factory)
    db_connection.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        db_connection.scalars(
            text(
                "EXPLAIN SELECT code FROM administrative_area "
                "WHERE path <@ 'MH.MH_PUNE'::ltree"
            )
        )
    )
    assert "administrative_area_path_gist" in plan, plan


# ---------------------------------------------------------------------------
# Re-parenting. This is the bug.
# ---------------------------------------------------------------------------


def test_reparenting_moves_the_entire_subtree(
    db_connection: Connection, area_factory
) -> None:
    """Regression: the cascade trigger did not fire on a re-parent.

    It was written ``AFTER UPDATE OF path``. PostgreSQL arms an ``UPDATE OF col``
    trigger from the columns named in the statement's SET list, not from the
    columns actually modified — and re-parenting is ``SET parent_code``, with the
    BEFORE trigger being what changes ``path``. So the tehsil moved and both
    villages kept paths under the old district.

    Nothing raised. The old district still contained a descendant it no longer
    had, the new one was missing three, and it would have surfaced as an
    authorization bug a long way from this trigger.

    A leaf-only test passes against the broken version. The node being moved has
    to have children.
    """
    _tree(area_factory)
    db_connection.execute(
        text("UPDATE administrative_area SET parent_code='MH.SATARA' WHERE code='HAVELI-1'")
    )

    assert _contained_by(db_connection, "MH.SATARA") == {
        "MH.SATARA",
        "HAVELI-1",
        "WAGHOLI",
        "KESNAND",
    }
    assert _contained_by(db_connection, "MH.PUNE") == {"MH.PUNE"}


def test_no_row_disagrees_with_its_parent_after_reparenting(
    db_connection: Connection, area_factory
) -> None:
    """The invariant, stated directly: every path extends its parent's path.

    Broader than the containment assertions above, and the thing that would have
    caught the cascade bug regardless of which subtree the test happened to move.
    """
    _tree(area_factory)
    db_connection.execute(
        text("UPDATE administrative_area SET parent_code='MH.SATARA' WHERE code='HAVELI-1'")
    )
    disagreements = db_connection.execute(
        text(
            """
            SELECT a.code, a.path::text, p.path::text
            FROM administrative_area a
            JOIN administrative_area p ON a.parent_code = p.code
            WHERE a.path <> p.path || subpath(a.path, nlevel(a.path) - 1)
               OR a.state_key <> p.state_key
            """
        )
    ).all()
    assert not disagreements, f"paths disagree with parents: {disagreements}"


def test_reparenting_across_states_moves_state_key_too(
    db_connection: Connection, area_factory
) -> None:
    """state_key is derived, so it has to follow a cross-state move.

    Otherwise the moved area keeps resolving Policy_Config against its old state,
    which means a statutory deadline computed from the wrong state's rules — wrong
    in a way that looks like a data entry error rather than a bug.
    """
    _tree(area_factory)
    area_factory("KA", "state", "Karnataka")
    db_connection.execute(
        text("UPDATE administrative_area SET parent_code='KA' WHERE code='HAVELI-1'")
    )
    states = {
        row.code: row.state_key
        for row in db_connection.execute(
            text("SELECT code, state_key FROM administrative_area")
        )
    }
    assert states["HAVELI-1"] == "KA"
    assert states["WAGHOLI"] == "KA", "descendant kept the old state_key"
    assert states["KESNAND"] == "KA"
    assert states["MH.PUNE"] == "MH", "an unrelated subtree was touched"


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def test_code_with_no_legal_characters_is_rejected(
    db_connection: Connection, area_factory
) -> None:
    area_factory("MH", "state", "Maharashtra")
    with pytest.raises(Exception, match="no ltree-legal characters"):
        area_factory("---", "village", "Nameless", "MH")


def test_a_root_area_must_be_a_state(area_factory) -> None:
    """state_key originates at the root, so a non-state root silently mis-keys
    Policy_Config for every descendant."""
    with pytest.raises(Exception, match="root_area_is_a_state"):
        area_factory("ORPHAN", "village", "Orphan", None)


def test_an_area_cannot_be_its_own_parent(db_connection: Connection, area_factory) -> None:
    area_factory("MH", "state", "Maharashtra")
    with pytest.raises(Exception, match="area_not_its_own_parent"):
        db_connection.execute(
            text("UPDATE administrative_area SET parent_code='MH' WHERE code='MH'")
        )


def test_deleting_a_parent_with_children_is_refused(
    db_connection: Connection, area_factory
) -> None:
    """RESTRICT rather than CASCADE: deleting a district should not silently take
    its villages, and any parcel referencing them, with it."""
    _tree(area_factory)
    with pytest.raises(Exception, match="violates foreign key constraint"):
        db_connection.execute(
            text("DELETE FROM administrative_area WHERE code='MH.PUNE'")
        )
