"""The transaction boundary. ``unit_of_work()`` is where R4.8 is true or false.

What the requirement asks for
-----------------------------

R4.8: *if an Event append fails, the originating subsystem shall abandon the
associated state change so that stored state and Event_Log content remain
consistent.*

§5.2 discharges it by making the append an ``INSERT`` on the caller's session,
ending in ``session.flush()`` so a failure surfaces immediately, and letting the
exception propagate out of the enclosing ``unit_of_work()``. The rollback is
PostgreSQL's, not ours. That only works if the entity write and the event append
are the same transaction on the same connection — which is a property of *this*
module, not of ``EventLog.append``.

Why the guards exist
--------------------

The failure mode this module is built against is quiet. If a service inside a
``unit_of_work()`` block acquires its own session, commits mid-block, or opens a
second connection, then the entity write and the event append land in different
transactions. R4.8 stops holding, and **no test notices**, because every test
still sees the row it wrote. There is no observable symptom until an event append
fails in production and leaves a state change behind it.

So the four ways to subvert the boundary all raise:

===========================================  ============================
Attempt                                      Raises
===========================================  ============================
``unit_of_work()`` inside a ``unit_of_work``  :class:`NestedUnitOfWork`
a second pool checkout inside the block       :class:`SecondConnectionInUnitOfWork`
``session.commit()`` / ``rollback()`` /       :class:`ManualTransactionControl`
``close()`` / ``begin()`` inside the block
reaching for an ambient session               no API exists to do it
===========================================  ============================

The last row is a design choice about the signature. There is no
``current_session()`` and no importable ``SessionLocal``: the ``ContextVar``
holding the active unit of work is private and is read only by the guards. A
service function therefore has exactly one way to obtain a session — being
handed one — which is why ``EventLog.append(session, ...)``,
``VersionedRepository.update(session, ...)`` and every service signature take it
as their first parameter. A service that cannot reach for a session cannot
accidentally put the event append on a different transaction from the state
change.

The single connection is acquired eagerly at entry. That costs a checkout on a
block that turns out to do nothing, and buys a guard with no gap: because the
block's own connection is already accounted for, *any* checkout inside the block
is a second one.

``begin_nested()`` (SAVEPOINT) is permitted. It runs on the same connection
inside the same outer transaction, so a savepoint rollback still leaves the outer
transaction to abandon everything; §16.3's chunked import path needs it.

Signature
---------

``unit_of_work(*, bind=None)`` — a keyword-only engine override, defaulting to
the engine built from ``DATABASE_URL``. Tests pass their own engine; application
and worker code never does. Both go through :func:`create_guarded_engine`, so a
test engine carries the same second-connection guard as production and cannot
pass a check that production would fail.

Usage is at the call site, not in a framework dependency::

    with unit_of_work() as session:
        case = case_service.transition(session, case_id, ...)   # state change
        EventLog.append(session, ...)                            # same session

Deliberately *not* a FastAPI dependency. A dependency-managed session hides the
transaction boundary from the code that depends on it, and FastAPI runs sync
dependencies and sync endpoints in different threadpool workers — the
``ContextVar`` set in the dependency would not be visible in the endpoint, so the
guards above would go quiet exactly where the most code is written. Route
handlers open the block themselves.
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, SessionTransaction, sessionmaker

from app.settings import get_database_settings

__all__ = [
    "ManualTransactionControl",
    "NestedUnitOfWork",
    "SecondConnectionInUnitOfWork",
    "TransactionBoundaryViolation",
    "create_guarded_engine",
    "get_engine",
    "unit_of_work",
]


class TransactionBoundaryViolation(RuntimeError):
    """The atomicity guarantee of §5.2 was about to be broken.

    A programming error, not a runtime condition: it is raised before any
    database work happens, so nothing is half-done when it propagates.
    """


class NestedUnitOfWork(TransactionBoundaryViolation):
    """A second ``unit_of_work()`` was opened inside an active one."""


class SecondConnectionInUnitOfWork(TransactionBoundaryViolation):
    """A second database connection was requested inside an active block."""


class ManualTransactionControl(TransactionBoundaryViolation):
    """The caller tried to end the transaction the block owns."""


@dataclass
class _ActiveUnitOfWork:
    """State for the one active block in this context.

    Its presence is the nesting check; the counter is the second-connection
    check. The block's own connection is acquired at entry and counted, so any
    later checkout in this context is a second one.
    """

    connections_checked_out: int = 0


# Private on purpose. Exposing an accessor would give services a way to obtain a
# session without being handed one, which is the failure mode this module is
# built to prevent (see the module docstring).
_active_unit_of_work: contextvars.ContextVar[_ActiveUnitOfWork | None] = (
    contextvars.ContextVar("bhumisetu_active_unit_of_work", default=None)
)


class _BoundarySession(Session):
    """A ``Session`` whose transaction lifecycle belongs to ``unit_of_work()``.

    ``commit``, ``rollback``, ``close`` and ``begin`` refuse while the block owns
    the session. A mid-block commit is as damaging as a second connection: it
    makes the state change durable before the event append is attempted, so a
    later failure has nothing left to roll back.

    The block itself drives the transaction through the ``SessionTransaction``
    object returned by ``begin()``, whose ``commit``/``rollback`` are separate
    methods from these, so ownership does not lock the block out of its own
    boundary. SQLAlchemy's internals do the same: a failed ``flush()`` rolls back
    through the ``SessionTransaction``, so these overrides never see it.
    """

    _boundary_owned: bool = False

    def _refuse(self, operation: str) -> None:
        if self._boundary_owned:
            raise ManualTransactionControl(
                f"session.{operation}() is not available inside unit_of_work(): "
                "the block owns the transaction. Let the exception propagate to "
                "abandon the work (R4.8), or return normally to commit it."
            )

    def commit(self) -> None:
        self._refuse("commit")
        super().commit()

    def rollback(self) -> None:
        self._refuse("rollback")
        super().rollback()

    def close(self) -> None:
        self._refuse("close")
        super().close()

    def begin(self, nested: bool = False) -> SessionTransaction:
        # begin_nested() delegates here with nested=True. SAVEPOINTs are allowed:
        # same connection, same outer transaction.
        if not nested:
            self._refuse("begin")
        return super().begin(nested=nested)


def _install_second_connection_guard(engine: Engine) -> Engine:
    """Refuse a second pool checkout while a unit of work is active."""

    @event.listens_for(engine, "checkout")
    def _guard_checkout(dbapi_connection, connection_record, connection_proxy):  # type: ignore[no-untyped-def]
        active = _active_unit_of_work.get()
        if active is None:
            return
        if active.connections_checked_out:
            # Raising out of a checkout listener leaves this connection record
            # unreturned until it is garbage-collected. Acceptable: reaching
            # here is a programming error that fails the request and the build,
            # not a runtime condition a deployed process recovers from.
            raise SecondConnectionInUnitOfWork(
                "A second database connection was requested inside "
                "unit_of_work(). The state change and its event append must "
                "share one transaction (§5.2), and two connections cannot. "
                "Pass the session you were given instead of acquiring one."
            )
        active.connections_checked_out += 1

    @event.listens_for(engine, "checkin")
    def _release_checkout(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        active = _active_unit_of_work.get()
        if active is not None and active.connections_checked_out:
            active.connections_checked_out -= 1

    return engine


def create_guarded_engine(url: str, **kwargs: Any) -> Engine:
    """Build an ``Engine`` carrying the second-connection guard.

    Every engine in the platform, including the ones tests build, is created
    here. An unguarded test engine would let a test pass while the same code
    fails in production.
    """
    kwargs.setdefault("pool_pre_ping", True)
    return _install_second_connection_guard(create_engine(url, **kwargs))


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """The process engine, built from ``DATABASE_URL``."""
    return create_guarded_engine(get_database_settings().database_url)


@lru_cache(maxsize=None)
def _session_factory(engine: Engine) -> sessionmaker[_BoundarySession]:
    return sessionmaker(
        bind=engine,
        class_=_BoundarySession,
        autoflush=True,
        # A service that returns an entity out of the block would otherwise hand
        # back an expired object attached to a closed session. Keeping loaded
        # state readable after commit is what lets `EventLog.append` return the
        # Event it wrote.
        expire_on_commit=False,
    )


@contextmanager
def unit_of_work(*, bind: Engine | None = None) -> Iterator[Session]:
    """Yield one session bound to one transaction.

    Commits on clean exit, rolls back on any exception, and closes either way.
    The rollback is the whole point: an ``EventLog.append`` that fails inside the
    block takes the state change with it (R4.8).

    :param bind: engine override for tests. Application and worker code omits it.
    :raises NestedUnitOfWork: if a unit of work is already active in this context.
    """
    if _active_unit_of_work.get() is not None:
        raise NestedUnitOfWork(
            "A unit_of_work() is already active in this context. Nesting would "
            "put the state change and its event append in different "
            "transactions and silently break R4.8. Pass the session you were "
            "given down to the code that needs it."
        )

    engine = bind if bind is not None else get_engine()
    session = _session_factory(engine)()
    token = _active_unit_of_work.set(_ActiveUnitOfWork())
    try:
        with session.begin():
            # Acquire the block's one connection now, so the guard above has no
            # gap: from here on, every checkout in this context is a second one.
            session.connection()
            session._boundary_owned = True
            try:
                yield session
            finally:
                session._boundary_owned = False
    finally:
        _active_unit_of_work.reset(token)
        session.close()
