"""Reading a configured value (§4.1, §4.2).

Task 2.1 owns the storage and the resolution query. The :class:`PolicyResolver`
that wraps this — with its per-request cache, its :class:`PolicySnapshot`, and the
deliberate absence of a ``default=`` parameter — is task 2.2.

The one query
-------------

R28.4 asks for "the value effective on date D". Three things have to be true at
once, and :data:`RESOLVE_SQL` does all of them in one statement:

* only rows already in force on D are eligible (``effective_from <= :d``);
* a state-specific value beats the platform-wide default for the same key and
  date;
* among the remaining rows, the latest ``effective_from`` wins.

The precedence is expressed as ``ORDER BY (state_key = :state) DESC`` rather than
as two queries with a fallback. Two queries would be a correctness trap: the
natural implementation reads the state-specific row, finds nothing, then reads the
platform default — and silently returns the platform default even when a
state-specific row exists but has a *later* effective date than D. One sort gets
the answer right by construction.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

__all__ = ["PLATFORM_WIDE", "RESOLVE_SQL", "resolve_raw"]

#: Sentinel in ``state_key`` for a value applying to every state.
PLATFORM_WIDE = "*"

RESOLVE_SQL = text(
    """
    SELECT value
      FROM policy_config
     WHERE policy_key = :key
       AND state_key IN (:state, '*')
       AND coalesce(act_key, '') = coalesce(:act, '')
       AND effective_from <= :as_of
     ORDER BY (state_key = :state) DESC,
              effective_from DESC
     LIMIT 1
    """
)


def resolve_raw(
    session: Session,
    key: str,
    *,
    state: str,
    act: str | None,
    as_of: date,
) -> Any | None:
    """Return the configured value effective on ``as_of``, or ``None``.

    Returning ``None`` rather than raising is deliberate at this layer: this is the
    query, and "no row" is a fact about the data. Turning absence into a refusal is
    :class:`PolicyResolver`'s job (task 2.2, R28.5), because that is where the
    caller who needs to be told lives.

    **This function is not the public way to read policy.** Subsystems go through
    ``PolicyResolver.get()``, which caches, refuses, and has no ``default=``
    parameter. A service reaching for ``resolve_raw`` directly is how a silent
    fallback gets reintroduced.
    """
    return session.execute(
        RESOLVE_SQL,
        {"key": key, "state": state, "act": act, "as_of": as_of},
    ).scalar_one_or_none()
