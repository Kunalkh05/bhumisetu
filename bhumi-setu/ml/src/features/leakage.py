"""Runtime guard against database access during feature extraction."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

__all__ = ["LeakageGuardViolation", "no_database_access"]


class LeakageGuardViolation(RuntimeError):
    """Raised when feature extraction tries to issue SQL after replay."""


@contextmanager
def no_database_access(session: Session) -> Iterator[None]:
    """Raise on the first SQL statement issued through ``session``'s bind.

    Feature building is allowed to hit the database while constructing the
    ``AsOfView``. Once extractors are running, any lazy load or ad hoc query is a
    leakage risk, so this guard is production code rather than a test monkeypatch.
    """
    bind = session.get_bind()

    def _deny_sql(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        snippet = " ".join(statement.split())[:200]
        raise LeakageGuardViolation(
            "database access is forbidden during feature extraction"
            f" (attempted SQL: {snippet})"
        )

    event.listen(bind, "before_cursor_execute", _deny_sql)
    try:
        yield
    finally:
        event.remove(bind, "before_cursor_execute", _deny_sql)
