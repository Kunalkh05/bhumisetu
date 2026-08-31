"""Database column types PostgreSQL has and SQLAlchemy does not.

Named ``column_types`` and not ``types``: the latter shadows the standard library
``types`` module for anything that puts this directory on ``sys.path``, and the
resulting failure is a circular-import traceback out of ``functools`` that names
neither this file nor the real cause.

Only ``ltree`` so far. It lives here rather than in ``app/models/`` because the
placement rule in :mod:`app.db.base` is about *mapped tables* — a column type is
plumbing, and putting it in the models package would give the metadata walk a
module with no table in it.

Why ltree at all
----------------

Jurisdiction scope (R2.1, R2.2) is a set of administrative areas, and the check
``scoped()`` performs is "is this case's area inside any area this officer
covers" (§8.1). An officer scoped to a district must see every tehsil and village
under it without those descendants being enumerated anywhere.

Three ways to express that, and why this one:

* **Recursive CTE over ``parent_code``.** Correct, but the containment test
  becomes a join per query and cannot be indexed as a containment test. Every
  scoped list query in the platform pays it.
* **Closure table.** Fast to read, but every ancestor pair is a row to keep
  correct, and a re-parented district silently leaves stale pairs behind.
* **Materialised path in ``ltree``.** One indexed operator, ``<@``, answers
  containment directly, and GiST makes it an index scan. The cost is that the
  path is derived state which must not be allowed to disagree with
  ``parent_code`` — which is why migration 0001 derives it in a trigger rather
  than trusting callers.

The label alphabet is the sharp edge
------------------------------------

An ``ltree`` label admits ``A-Za-z0-9_`` and nothing else. Real administrative
codes contain hyphens, spaces and periods, and a period is ltree's *separator* —
so a code like ``MH.PUNE`` silently becomes two levels rather than one label, and
the hierarchy is quietly wrong rather than rejected. :func:`to_ltree_label`
therefore transliterates, and migration 0001 stores the transliterated form in
``path`` while ``code`` keeps the authoritative value. They are different columns
because they answer different questions: ``code`` is what a government record
says, ``path`` is what the index can answer containment on.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator, UserDefinedType

__all__ = ["LQuery", "Ltree", "to_ltree_label", "to_ltree_path"]

# ltree admits letters, digits and underscore in a label; '.' separates labels.
_ILLEGAL_LABEL_CHARS = re.compile(r"[^A-Za-z0-9_]+")
_LTREE_LABEL = re.compile(r"^[A-Za-z0-9_]+$")
_LTREE_PATH = re.compile(r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*$")


def to_ltree_label(value: str) -> str:
    """Transliterate one administrative code into a single legal ltree label.

    Every run of illegal characters collapses to a single underscore, so
    ``MH.PUNE`` becomes ``MH_PUNE`` — one label, not two. Collapsing rather than
    dropping matters: dropping would map ``PUNE-1`` and ``PUNE1`` onto the same
    label and merge two distinct areas into one.

    :raises ValueError: if nothing legal remains, since an empty label would
        produce ``a..b`` and corrupt the path of every descendant.
    """
    label = _ILLEGAL_LABEL_CHARS.sub("_", value).strip("_")
    if not label:
        raise ValueError(
            f"administrative code {value!r} has no ltree-legal characters; "
            "it cannot be used as a path label"
        )
    return label


def to_ltree_path(*labels: str) -> str:
    """Join already-legal labels into a path, rejecting an illegal one.

    Each label is validated **individually** against the label alphabet, not
    against the joined result. Validating only the join would accept
    ``to_ltree_path("IN", "MH.PUNE")`` — the result ``IN.MH.PUNE`` is a perfectly
    legal path, so the check passes while the caller who thought they passed two
    labels has silently produced three levels. That is the exact corruption this
    module exists to prevent, and it is invisible afterwards because the stored
    value looks correct.

    Validates rather than transliterating: a caller assembling a path from parts
    has already decided what the labels are, and silently rewriting one here
    would hide the mistake at the point it can still be diagnosed. Use
    :func:`to_ltree_label` first if the parts are raw codes.
    """
    if not labels:
        raise ValueError("an ltree path needs at least one label")
    for label in labels:
        if not _LTREE_LABEL.match(label):
            raise ValueError(
                f"{label!r} is not a legal ltree label: labels admit only "
                "[A-Za-z0-9_]. A '.' makes it two labels rather than one, so "
                "pass them separately or use to_ltree_label() to transliterate."
            )
    return ".".join(labels)


class Ltree(UserDefinedType[str]):
    """The PostgreSQL ``ltree`` type.

    Values move as strings in both directions, which is what makes the operators
    usable from the ORM: ``AdministrativeArea.path.op("<@")(scope_path)`` renders
    as ``path <@ 'IN.MH'`` and hits the GiST index.

    ``cache_ok`` is set so statements using this type participate in SQLAlchemy's
    compiled-statement cache. That is only correct because the type carries no
    parameters that change the SQL it generates.
    """

    cache_ok = True

    def get_col_spec(self, **_: Any) -> str:
        return "ltree"

    def bind_processor(self, dialect: Dialect) -> Any:
        def process(value: str | None) -> str | None:
            if value is None:
                return None
            if not _LTREE_PATH.match(value):
                # Fail here rather than let PostgreSQL reject it, so the error
                # names the offending value and the alphabet rule.
                raise ValueError(
                    f"{value!r} is not a legal ltree path: labels admit only "
                    "[A-Za-z0-9_] and are separated by '.'"
                )
            return value

        return process

    def literal_processor(self, dialect: Dialect) -> Any:
        def process(value: str) -> str:
            escaped = value.replace("'", "''")
            return f"'{escaped}'::ltree"

        return process


class _LQueryImpl(UserDefinedType[str]):
    cache_ok = True

    def get_col_spec(self, **_: Any) -> str:
        return "lquery"


class LQuery(TypeDecorator[str]):
    """An ``lquery`` pattern, for ``path ~ 'IN.MH.*'`` style matching.

    Distinct from :class:`Ltree` because the alphabets differ: an lquery admits
    ``*``, ``|``, ``!`` and ``@``, all illegal in a path. Sharing one type would
    mean either rejecting valid patterns or accepting invalid paths.

    Unused at task 1.2. Present because ``scoped()`` (§8.1) uses ``<@``
    containment, and the day someone reaches for pattern matching instead, the
    distinction should already be drawn rather than improvised under deadline.
    """

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        return dialect.type_descriptor(_LQueryImpl())
