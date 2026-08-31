"""The SQL and Python ltree label functions must agree (§20.9).

``bhumisetu_ltree_label(text)`` in migration 0001 and
:func:`app.db.column_types.to_ltree_label` implement one rule twice. Neither can
be deleted:

* the trigger has to run inside the database, because it is the only way to cover
  *every* insert path — the bulk import of task 26, a psql session, a future
  service nobody has written yet;
* the application has to compute a label without a database round trip, or
  building a scope query means a query first.

So the duplication is accepted and this test is what makes it safe. Without it the
pair drifts, and the symptom is not an error: a scope check compares a path built
by one implementation against a path stored by the other, matches nothing, and
reads as an authorization bug.
"""

from __future__ import annotations

from hypothesis import given, settings
from sqlalchemy import Connection, text

from app.db.column_types import to_ltree_label
from tests.strategies import st_administrative_code


def _sql_label(connection: Connection, code: str) -> str | None:
    return connection.execute(
        text("SELECT bhumisetu_ltree_label(:code)"), {"code": code}
    ).scalar_one()


@given(code=st_administrative_code())
@settings(max_examples=200)
def test_sql_and_python_labels_agree(db_connection: Connection, code: str) -> None:
    assert _sql_label(db_connection, code) == to_ltree_label(code), (
        f"bhumisetu_ltree_label() and to_ltree_label() disagree on {code!r}. "
        "A path built by one and stored by the other will silently fail every "
        "containment check."
    )


def test_both_reject_a_code_with_no_legal_characters(db_connection: Connection) -> None:
    """SQL returns NULL, Python raises. Different shapes, same verdict.

    They differ on purpose: the trigger turns the NULL into a check_violation with
    the offending code, while the Python side has a caller who can be told
    directly. What matters is that neither invents a label.
    """
    assert _sql_label(db_connection, "---") is None

    import pytest

    with pytest.raises(ValueError, match="no ltree-legal characters"):
        to_ltree_label("---")


def test_underscore_only_code_is_rejected_by_both(db_connection: Connection) -> None:
    """Found by st_administrative_code on its first run.

    ``"_"`` survives a naive "is it alphanumeric or underscore" filter but
    transliterates to the empty string, because both implementations strip leading
    and trailing underscores. Rejecting it is correct — the code carries no
    information — and both must reject it the same way.
    """
    assert _sql_label(db_connection, "_") is None

    import pytest

    with pytest.raises(ValueError):
        to_ltree_label("_")


@given(code=st_administrative_code())
@settings(max_examples=100)
def test_label_is_a_legal_single_ltree_label(
    db_connection: Connection, code: str
) -> None:
    """Whatever comes out must be storable as exactly one level.

    Asserted against PostgreSQL rather than a regex: the authority on what ltree
    accepts is ltree. ``nlevel`` of the result must be 1 — if a separator survived
    transliteration the value would still cast successfully and quietly become two
    levels, which is the failure this whole mechanism exists to prevent.
    """
    label = to_ltree_label(code)
    depth = db_connection.execute(
        # CAST(... AS ltree) rather than `:label::ltree`: the parameter parser
        # reads the leading colon of `::` as the start of another bind name.
        text("SELECT nlevel(CAST(:label AS ltree))"),
        {"label": label},
    ).scalar_one()
    assert depth == 1, f"{code!r} produced {label!r}, which is {depth} levels"
