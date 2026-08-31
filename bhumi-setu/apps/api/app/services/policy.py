"""Reading a configured value (§4.1, §4.2).

:class:`PolicyResolver` is the only way any subsystem reads a policy value. Its
shape is a set of refusals as much as a set of features, and each refusal exists
because of a specific way this goes wrong.

``get()`` has no ``default=`` parameter
--------------------------------------

Not an oversight, and not stylistic. A ``default=`` is precisely how a statutory
period ends up hardcoded: the call site that writes
``resolver.get("period.objection.window", default=30)`` has put a legal deadline in
Python, and it will keep working, silently, in a state whose window is 60 days.
R7.2 forbids that, and the AST lint in task 2.6 catches ``timedelta(days=30)`` but
cannot catch a plausible keyword argument.

So absence raises. Where a caller genuinely branches on absence — the retention
sweep withholding erasure under R32.14 — :meth:`PolicyResolver.try_get` says so at
the call site, which is reviewable in a way that a default value is not.

The single ORDER BY
-------------------

R28.4's three rules interact: only rows in force on the date are eligible, a
state-specific value beats the platform default, and among the rest the latest
wins. The obvious implementation — read the state row, fall back to the platform
row — gets one case wrong. A state override with an ``effective_from`` *later* than
the requested date must lose to the platform default, and the fallback returns the
right answer there only by accident, because its state query found nothing. One
sort is correct in both directions by construction.

The cache is per resolver, and a resolver is per unit of work
-------------------------------------------------------------

A request resolves the same key repeatedly — a stage deadline, then the same period
again while computing priority. The cache makes that one query. It is deliberately
*not* process-wide: a long-lived cache would keep serving a period that an officer
changed through :class:`PolicyService` moments earlier, and R28.3's history would
be correct while the running system disagreed with it. Bound to the session's
lifetime, staleness cannot outlive the transaction that observed it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.errors import DomainError, ErrorCode

__all__ = [
    "PLATFORM_WIDE",
    "RESOLVE_SQL",
    "PolicyResolver",
    "PolicySnapshot",
    "PolicyValueMissing",
    "resolve_raw",
]

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


class PolicyValueMissing(DomainError):
    """R28.5: the dependent operation refuses, and says which key and date.

    A 409 rather than a 500, because it is not a fault. Until Q8 is confirmed no
    statutory period is seeded at all (§1.2), so this is the platform's *expected*
    answer for a period lookup, and the remedy is configuration rather than a
    retry. ``details`` carries the key, state, act and date because a message
    saying "policy value missing" sends an operator hunting.
    """

    code = ErrorCode.POLICY_VALUE_MISSING
    status_code = 409

    def __init__(
        self, *, key: str, state: str, act: str | None, as_of: date
    ) -> None:
        super().__init__(
            f"no value for {key!r} effective on {as_of.isoformat()} "
            f"(state={state!r}, act={act!r})",
            details={
                "policy_key": key,
                "state_key": state,
                "act_key": act,
                "as_of": as_of.isoformat(),
            },
        )
        self.policy_key = key
        self.state_key = state
        self.act_key = act
        self.as_of = as_of


@dataclass(frozen=True)
class PolicySnapshot:
    """A frozen bundle of resolved values, with a hash identifying it.

    Several outputs have to stay attributable to the configuration that produced
    them: a notice deadline (R7.8) must keep resolving to the same date after the
    period changes, a Priority_Score records its weight-set version (R21.3), a
    training run records its label definition version.

    Storing the hash rather than the values keeps the audit trail small while
    leaving "which configuration produced this" answerable. The hash is over
    canonical JSON with sorted keys, so it is stable across processes and Python
    versions — a hash built from ``repr()`` or from ``hash()`` would differ between
    runs and be useless for exactly the comparison it exists for.
    """

    values: Mapping[str, Any]
    resolved_at: date
    content_hash: str

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def __contains__(self, key: str) -> bool:
        return key in self.values


def _canonical_hash(values: Mapping[str, Any], resolved_at: date) -> str:
    payload = json.dumps(
        {"values": values, "resolved_at": resolved_at.isoformat()},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_raw(
    session: Session,
    key: str,
    *,
    state: str,
    act: str | None,
    as_of: date,
) -> Any | None:
    """Run the R28.4 query. Returns ``None`` when no row is in force.

    **Not the public way to read policy.** Subsystems go through
    :class:`PolicyResolver`, which caches and refuses. A service reaching for this
    directly is how a silent fallback gets reintroduced; it is exported for the
    resolver and for tests that assert on the query itself.
    """
    return session.execute(
        RESOLVE_SQL,
        {"key": key, "state": state, "act": act, "as_of": as_of},
    ).scalar_one_or_none()


class PolicyResolver:
    """The only way any subsystem reads a policy value (§4.2)."""

    __slots__ = ("_session", "_cache")

    def __init__(self, session: Session) -> None:
        self._session = session
        self._cache: dict[tuple[str, str, str | None, date], Any] = {}

    def get(self, key: str, *, state: str, act: str | None, as_of: date) -> Any:
        """Return the value effective on ``as_of``, or refuse.

        There is no ``default`` parameter and there must not be one. See the module
        docstring.

        :raises PolicyValueMissing: when no value is in force (R28.5).
        """
        cache_key = (key, state, act, as_of)
        if cache_key not in self._cache:
            value = resolve_raw(
                self._session, key, state=state, act=act, as_of=as_of
            )
            if value is None:
                raise PolicyValueMissing(key=key, state=state, act=act, as_of=as_of)
            self._cache[cache_key] = value
        return self._cache[cache_key]

    def try_get(
        self, key: str, *, state: str, act: str | None, as_of: date
    ) -> Any | None:
        """Return the value, or ``None`` where absence is a legitimate branch.

        Used where a requirement says to *withhold* rather than fail — R32.14's
        retention sweep records the missing key and moves on. Spelled as its own
        method so that tolerating absence is visible at the call site and in review,
        which a ``default=`` argument on :meth:`get` would not be.

        Caches a hit; does not cache a miss, because the caller's next action is
        usually to have someone configure the value.
        """
        cache_key = (key, state, act, as_of)
        if cache_key in self._cache:
            return self._cache[cache_key]
        value = resolve_raw(self._session, key, state=state, act=act, as_of=as_of)
        if value is not None:
            self._cache[cache_key] = value
        return value

    def snapshot(
        self,
        keys: Iterable[str],
        *,
        state: str,
        act: str | None,
        as_of: date,
    ) -> PolicySnapshot:
        """Resolve several keys into a frozen, hashable bundle.

        Every key must resolve: a snapshot with a hole in it would hash to
        something that looks authoritative while describing configuration that was
        never complete. So this refuses on the first missing key rather than
        recording a partial result.
        """
        values = {
            key: self.get(key, state=state, act=act, as_of=as_of) for key in sorted(keys)
        }
        return PolicySnapshot(
            values=MappingProxyType(dict(values)),
            resolved_at=as_of,
            content_hash=_canonical_hash(values, as_of),
        )

    def invalidate(self) -> None:
        """Drop the cache. Called after a policy write inside the same unit of work.

        Without this, :class:`PolicyService` could set a value and the resolver in
        the same request would keep serving the old one — the write would be correct
        and the behaviour that followed it wrong.
        """
        self._cache.clear()
