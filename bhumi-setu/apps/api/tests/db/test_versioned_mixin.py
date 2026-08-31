"""The ``Versioned`` mixin and Property 67, at the level task 4.1 can reach.

Feature: bhumisetu. Property 67 (§7; R29.1).

Task 4.1 owns the version *column* and its semantics, not the write path
(:class:`VersionedRepository`, task 4.2) and not the eleven entity tables (tasks
8–16). So there are two things testable now, and one that is not:

* **Testable — the mixin contributes the column.** ``entity_version integer NOT
  NULL DEFAULT 1`` appears on any class that inherits :class:`Versioned`, a fresh
  one per table, so "a new entity type cannot be added without a version column"
  holds structurally. These are static checks over a throwaway model's mapped
  table; no database needed.

* **Testable — the increment semantics the column exists for.** Property 67 says
  the version *increases by exactly one when and only when a modification commits,
  and is unchanged when it is rejected*. The mechanism that makes that true is the
  conditional compare-and-set of §7.1 —
  ``UPDATE ... SET entity_version = entity_version + 1 WHERE id = :id AND
  entity_version = :expected`` — and it is exercisable now against a real table
  the mixin built, without the repository that will wrap it in task 4.2. A request
  presenting the current version matches one row and increments; a request
  presenting any other version matches zero rows and changes nothing. That
  biconditional *is* Property 67, and it is a property of the column plus the
  compare-and-set, which is what this task delivers.

* **Not yet — the full write path.** The event-append-second ordering (R29.5), the
  conflict description (R29.4), and the two-connection race (R29.6) belong to tasks
  4.2–4.4 with the real :class:`VersionedRepository`; they are out of scope here.

Isolation follows ``test_policy_resolution_properties.py``: the model lives on a
declarative base local to this module, *not* ``app.db.base.Base``, so it never
enters the platform's single table registry (``app/db/base.py``); the table is
created once on the function-scoped ``db_connection`` (inside its always-rolled-
back outer transaction, so nothing survives the test); and each Hypothesis example
runs on a session with ``join_transaction_mode="create_savepoint"`` that is closed
— and so rolled back to the savepoint — before the next example, leaving the table
in place but empty.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import BigInteger, Connection, Integer, String, insert, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.db.versioned import Versioned


class _MixinTestBase(DeclarativeBase):
    """Local base. Not ``app.db.base.Base``: these are not platform tables, so they
    stay out of the metadata walk the schema guards depend on."""


class _VersionedThing(_MixinTestBase, Versioned):
    """A stand-in for a versioned entity: a bigint id, a mutable attribute, and the
    ``entity_version`` the mixin supplies."""

    __tablename__ = "versioned_thing_probe"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)


class _AnotherVersionedThing(_MixinTestBase, Versioned):
    """A second inheritor, to show each table gets its own version column rather than
    sharing one — the guarantee that makes the mixin safe to spread across eleven
    tables."""

    __tablename__ = "another_versioned_thing_probe"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)


# ---------------------------------------------------------------------------
# The mixin contributes the column (static — no database)
# ---------------------------------------------------------------------------


def test_mixin_contributes_entity_version_column() -> None:
    """``entity_version integer NOT NULL DEFAULT 1`` on any class that inherits it."""
    column = _VersionedThing.__table__.c.entity_version

    assert isinstance(column.type, Integer), "entity_version must be an integer column"
    assert column.nullable is False, "a versioned entity is never without a version"
    assert column.server_default is not None, "the column must default, so a create "
    assert str(column.server_default.arg) == "1", (
        "a freshly created entity is at version 1 (Property 67 counts from there)"
    )


def test_every_inheritor_gets_its_own_version_column() -> None:
    """The column is per-table, not shared. Two entities inheriting the mixin each
    carry an independent ``entity_version``; a race on one cannot touch the other."""
    for table in (_VersionedThing.__table__, _AnotherVersionedThing.__table__):
        assert "entity_version" in table.c, f"{table.name} lost its version column"

    assert (
        _VersionedThing.__table__.c.entity_version
        is not _AnotherVersionedThing.__table__.c.entity_version
    ), "inheritors must not share one column object"


def test_initial_version_constant_matches_the_column_default() -> None:
    """The DDL default and the value callers reason about have a single source."""
    assert Versioned.INITIAL_VERSION == 1
    assert str(_VersionedThing.__table__.c.entity_version.server_default.arg) == str(
        Versioned.INITIAL_VERSION
    )


# ---------------------------------------------------------------------------
# The column, and the compare-and-set it exists for, on a real table (Postgres)
# ---------------------------------------------------------------------------


@pytest.fixture
def versioned_probe_table(db_connection: Connection) -> None:
    """Create the probe table on the outer (rolled-back) transaction.

    Created here, before any per-example savepoint, so it survives every example's
    rollback and is dropped only when ``db_connection`` tears its transaction down.
    """
    _MixinTestBase.metadata.create_all(
        bind=db_connection, tables=[_VersionedThing.__table__]
    )


def test_a_new_row_defaults_to_version_one(
    db_connection: Connection, versioned_probe_table: None
) -> None:
    """The DDL ``DEFAULT 1`` is real: an insert that omits the version gets 1."""
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        session.execute(insert(_VersionedThing).values(id=1, label="created"))
        version = session.execute(
            select(_VersionedThing.entity_version).where(_VersionedThing.id == 1)
        ).scalar_one()
        assert version == Versioned.INITIAL_VERSION
    finally:
        session.close()


@dataclass(frozen=True)
class _Attempt:
    """One modification presenting a prior version. ``delta`` is that version minus
    the entity's *current* version, so ``delta == 0`` is a well-formed request that
    should commit and anything else is a stale one that should be rejected."""

    delta: int


@st.composite
def st_attempt_sequence(draw) -> tuple[_Attempt, ...]:
    """A run of modification attempts against one entity, mixing well-formed and
    stale versions.

    ``delta`` is drawn small and centred on zero so both branches of Property 67's
    biconditional are exercised densely: ``0`` presents the live version (commit),
    a non-zero value presents a stale one (reject). The mix and length are left to
    Hypothesis, which will also shrink a failure to the shortest offending run.
    """
    return tuple(
        _Attempt(delta=d)
        for d in draw(
            st.lists(st.integers(min_value=-4, max_value=4), min_size=1, max_size=20)
        )
    )


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(attempts=st_attempt_sequence())
def test_entity_version_increases_exactly_on_commit(
    db_connection: Connection,
    versioned_probe_table: None,
    attempts: tuple[_Attempt, ...],
) -> None:
    """Feature: bhumisetu, Property 67: for any versioned entity and any modification,
    the entity version increases by one when and only when the modification commits,
    and is unchanged when the modification is rejected.

    **Validates: Requirements 29.1**

    Modelled with the §7.1 compare-and-set the mixin's column exists for. Each
    attempt presents ``current + delta`` as its prior version: ``delta == 0`` matches
    the row and is the *commit* case, any other delta matches nothing and is the
    *reject* case. The assertions are the biconditional itself — increment iff
    matched — plus the running invariant that the version equals its start plus the
    number of commits so far, and that a rejected write leaves the row bit-identical.
    """
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        session.execute(insert(_VersionedThing).values(id=1, label="v1"))

        current = Versioned.INITIAL_VERSION
        commits = 0
        for index, attempt in enumerate(attempts):
            presented = current + attempt.delta
            new_label = f"edit-{index}"

            result = session.execute(
                update(_VersionedThing)
                .where(
                    _VersionedThing.id == 1,
                    _VersionedThing.entity_version == presented,
                )
                .values(
                    label=new_label,
                    entity_version=_VersionedThing.entity_version + 1,
                )
            )
            committed = attempt.delta == 0

            # The compare-and-set matches exactly when the presented version is the
            # current one — one row on commit, zero on reject. Nothing in between.
            assert result.rowcount == (1 if committed else 0)

            stored_version, stored_label = session.execute(
                select(_VersionedThing.entity_version, _VersionedThing.label).where(
                    _VersionedThing.id == 1
                )
            ).one()

            if committed:
                commits += 1
                current += 1
                assert stored_version == current, "a commit increases the version by one"
                assert stored_label == new_label, "a commit applies the change"
            else:
                assert stored_version == current, "a rejected write leaves the version"
                assert stored_label != new_label, "a rejected write changes nothing"

            # The version is the initial version plus the number of commits — the
            # count of committed modifications is exactly entity_version - 1.
            assert stored_version == Versioned.INITIAL_VERSION + commits
    finally:
        session.close()
