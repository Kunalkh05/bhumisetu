"""The atomicity boundary of §5.2, which is where R4.8 is true or false.

R4.8: *if an Event append fails, the originating subsystem shall abandon the
associated state change so that stored state and Event_Log content remain
consistent.*

These are deterministic tests, not property tests. The generated-input property
for R4.8 is Property 10 ("For any state-changing operation and any injected
failure of the event append, the stored state after the operation equals the
stored state before it"), which task 3.9 owns because it needs a real
``EventLog.append`` and a real entity to inject a failure into. What is testable
here is the boundary itself: one session, one transaction, commit on clean exit,
rollback on anything else, and the four ways a caller could quietly step outside
it.

``event_stub`` and ``widget`` stand in for an event row and an entity row. They
are declared on a metadata local to this module rather than on
``Base.metadata``, which stays the single registry of *platform* tables
(``app/db/base.py``).
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Engine, Integer, String, delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.db import session as session_module
from app.db.session import (
    ManualTransactionControl,
    NestedUnitOfWork,
    SecondConnectionInUnitOfWork,
    unit_of_work,
)


class _TestBase(DeclarativeBase):
    """Local declarative base. Not ``app.db.base.Base``: these are not platform tables."""


class Widget(_TestBase):
    """Stands in for a versioned entity whose state a service changes."""

    __tablename__ = "widget"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(32), nullable=False)


class EventStub(_TestBase):
    """Stands in for the ``event`` row that ``EventLog.append`` inserts and flushes."""

    __tablename__ = "event_stub"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)


@pytest.fixture
def engine(transactional_sqlite_engine: Engine) -> Engine:
    _TestBase.metadata.create_all(transactional_sqlite_engine)
    return transactional_sqlite_engine


def stored_labels(engine: Engine) -> list[str]:
    """Read committed state on a connection of its own, outside any unit of work."""
    with engine.connect() as connection:
        return list(connection.scalars(select(Widget.label).order_by(Widget.id)))


# --------------------------------------------------------------------------
# The boundary: commit on clean exit, roll back on anything else
# --------------------------------------------------------------------------


def test_clean_block_commits(engine: Engine) -> None:
    with unit_of_work(bind=engine) as session:
        session.execute(insert(Widget).values(id=1, label="kept"))

    assert stored_labels(engine) == ["kept"]


def test_exception_inside_block_leaves_no_partial_write(engine: Engine) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with unit_of_work(bind=engine) as session:
            session.execute(insert(Widget).values(id=1, label="first"))
            session.execute(insert(Widget).values(id=2, label="second"))
            raise RuntimeError("boom")

    assert stored_labels(engine) == []


def test_failed_event_append_abandons_the_state_change(engine: Engine) -> None:
    """The §5.2 shape: state change, then an append whose ``flush()`` fails.

    ``EventLog.append`` ends in ``session.flush()`` precisely so the failure
    surfaces inside the caller's transaction. Nothing here catches it, so the
    state change written a moment earlier is abandoned with it — R4.8.
    """
    with unit_of_work(bind=engine) as session:
        session.add(EventStub(id=7, event_type="CASE_CREATED"))

    with pytest.raises(IntegrityError):
        with unit_of_work(bind=engine) as session:
            session.execute(insert(Widget).values(id=1, label="state change"))
            session.add(EventStub(id=7, event_type="CASE_UPDATED"))  # duplicate id
            session.flush()

    assert stored_labels(engine) == []


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    existing=st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=16),
        min_size=0,
        max_size=8,
        unique=True,
    ),
    attempted=st.lists(
        st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=16),
        min_size=1,
        max_size=8,
        unique=True,
    ),
)
def test_property_10_injected_append_failure_leaves_state_bit_identical(
    engine: Engine, existing: list[str], attempted: list[str]
) -> None:
    """Property 10: an injected event-append failure abandons every state change.

    The initial rows commit. The attempted rows are inserted in the next unit of work,
    followed by a duplicate event row that stands in for ``EventLog.append`` failing
    during its final ``flush()``. After the exception, the stored state equals the
    pre-operation snapshot exactly: no missing original rows and no partial attempted
    rows.
    """
    with engine.begin() as connection:
        connection.execute(delete(Widget))
        connection.execute(delete(EventStub))

    with unit_of_work(bind=engine) as session:
        session.add(EventStub(id=777, event_type="CASE_CREATED"))
        for index, label in enumerate(existing, start=1):
            session.execute(insert(Widget).values(id=index, label=label))

    before = stored_labels(engine)

    with pytest.raises(IntegrityError):
        with unit_of_work(bind=engine) as session:
            for offset, label in enumerate(attempted, start=len(existing) + 1):
                session.execute(insert(Widget).values(id=offset, label=label))
            session.add(EventStub(id=777, event_type="CASE_UPDATED"))
            session.flush()

    assert stored_labels(engine) == before


def test_sequential_blocks_are_independent_after_a_failure(engine: Engine) -> None:
    """A failed block must leave the context clean, or every later write breaks."""
    with pytest.raises(RuntimeError):
        with unit_of_work(bind=engine) as session:
            session.execute(insert(Widget).values(id=1, label="discarded"))
            raise RuntimeError("boom")

    with unit_of_work(bind=engine) as session:
        session.execute(insert(Widget).values(id=2, label="committed"))

    assert stored_labels(engine) == ["committed"]


# --------------------------------------------------------------------------
# The four ways to step outside the boundary
# --------------------------------------------------------------------------


def test_nested_unit_of_work_is_refused(engine: Engine) -> None:
    with unit_of_work(bind=engine) as outer:
        outer.execute(insert(Widget).values(id=1, label="outer"))
        with pytest.raises(NestedUnitOfWork):
            with unit_of_work(bind=engine):
                pass

    # The refusal happens before any database work, so the outer block is intact.
    assert stored_labels(engine) == ["outer"]


def test_nested_unit_of_work_left_unhandled_discards_the_outer_work(
    engine: Engine,
) -> None:
    with pytest.raises(NestedUnitOfWork):
        with unit_of_work(bind=engine) as outer:
            outer.execute(insert(Widget).values(id=1, label="outer"))
            with unit_of_work(bind=engine):
                pass

    assert stored_labels(engine) == []


def test_second_connection_inside_the_block_is_refused(engine: Engine) -> None:
    with unit_of_work(bind=engine) as session:
        session.execute(insert(Widget).values(id=1, label="outer"))
        with pytest.raises(SecondConnectionInUnitOfWork):
            with engine.connect():
                pass


def test_a_second_session_on_the_same_engine_is_refused(engine: Engine) -> None:
    """The failure mode the guard exists for: a service acquiring its own session.

    Two sessions are two transactions, so a failed append on one would leave the
    other's state change behind. The refusal happens on connection checkout, so
    it does not matter how the second session was constructed.
    """
    with unit_of_work(bind=engine) as session:
        session.execute(insert(Widget).values(id=1, label="outer"))
        smuggled = Session(bind=engine)
        with pytest.raises(SecondConnectionInUnitOfWork):
            smuggled.execute(select(Widget.label)).all()


def test_a_second_connection_after_the_block_is_allowed(engine: Engine) -> None:
    with unit_of_work(bind=engine) as session:
        session.execute(insert(Widget).values(id=1, label="kept"))

    with engine.connect() as connection:
        assert connection.scalar(select(Widget.label)) == "kept"


@pytest.mark.parametrize("operation", ["commit", "rollback", "close", "begin"])
def test_manual_transaction_control_is_refused(engine: Engine, operation: str) -> None:
    """A mid-block commit is as damaging as a second connection.

    It makes the state change durable before the event append is attempted, so a
    later failure has nothing left to abandon.
    """
    with unit_of_work(bind=engine) as session:
        session.execute(insert(Widget).values(id=1, label="outer"))
        with pytest.raises(ManualTransactionControl):
            getattr(session, operation)()


def test_a_mid_block_commit_attempt_does_not_make_the_write_durable(
    engine: Engine,
) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with unit_of_work(bind=engine) as session:
            session.execute(insert(Widget).values(id=1, label="not durable"))
            with pytest.raises(ManualTransactionControl):
                session.commit()
            raise RuntimeError("boom")

    assert stored_labels(engine) == []


def test_savepoints_are_permitted_inside_the_block(engine: Engine) -> None:
    """SAVEPOINT stays on the one connection inside the one outer transaction.

    §16.3's chunked import needs it, and it does not weaken R4.8: the outer
    transaction still abandons everything, released savepoints included.
    """
    with unit_of_work(bind=engine) as session:
        session.execute(insert(Widget).values(id=1, label="outer"))
        savepoint = session.begin_nested()
        session.execute(insert(Widget).values(id=2, label="rolled back"))
        savepoint.rollback()

    assert stored_labels(engine) == ["outer"]


def test_an_outer_failure_discards_released_savepoint_work(engine: Engine) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with unit_of_work(bind=engine) as session:
            savepoint = session.begin_nested()
            session.execute(insert(Widget).values(id=1, label="released"))
            savepoint.commit()
            raise RuntimeError("boom")

    assert stored_labels(engine) == []


def test_an_outer_failure_discards_work_inside_an_open_savepoint(
    engine: Engine,
) -> None:
    """The import path (§16.3) can fail with a chunk savepoint still open."""
    with pytest.raises(RuntimeError, match="boom"):
        with unit_of_work(bind=engine) as session:
            session.execute(insert(Widget).values(id=1, label="outer"))
            session.begin_nested()
            session.execute(insert(Widget).values(id=2, label="in savepoint"))
            raise RuntimeError("boom")

    assert stored_labels(engine) == []


# --------------------------------------------------------------------------
# The seam: there is no way to reach for a session
# --------------------------------------------------------------------------


def test_no_public_accessor_for_the_active_session() -> None:
    """A service must be handed a session, never able to fetch one.

    If any public name in ``app.db.session`` returned the active session, a
    service could obtain one without being given one, put its event append on a
    different transaction from its state change, and break R4.8 with nothing
    observable to catch it.
    """
    permitted = {
        "ManualTransactionControl",
        "NestedUnitOfWork",
        "SecondConnectionInUnitOfWork",
        "TransactionBoundaryViolation",
        "create_guarded_engine",
        "get_engine",
        "unit_of_work",
    }
    assert set(session_module.__all__) == permitted

    # Everything public that this module defines is in __all__; the remaining
    # public names are imports it needs, and none of them is a session accessor.
    defined_here = {
        name
        for name, value in vars(session_module).items()
        if not name.startswith("_")
        and getattr(value, "__module__", None) == session_module.__name__
    }
    assert defined_here == permitted
