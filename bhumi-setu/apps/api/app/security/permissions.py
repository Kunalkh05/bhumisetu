"""Permission registry and route authorization helpers (task 5.6).

The access layer reduces a request to a :class:`~app.security.access.Principal`;
this module is the small, explicit vocabulary of things a principal may be allowed
to do. Keeping permissions in code rather than in a CHECK constraint means adding a
permission does not require a migration, while the registry tests still fail the
build on a misspelled role permission or route expectation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.errors import NotAuthorised
from app.security.access import Principal

__all__ = [
    "ACCESS_DENIED_EVENT",
    "PERMISSIONS",
    "permission_registered",
    "require_permission",
]

PERMISSIONS: frozenset[str] = frozenset(
    {
        "case.transition",
        "config.write",
        "import.submit",
        "validation.waive.BLOCKING",
        "validation.waive.MAJOR",
        "model.administer",
        "dsar.dispose",
    }
)

ACCESS_DENIED_EVENT = "ACCESS_DENIED"


def permission_registered(permission: str) -> bool:
    """Whether ``permission`` is part of the declared vocabulary."""
    return permission in PERMISSIONS


class _AccessDecision:
    """Synthetic entity for an access-denied event.

    Event rows need an entity type and id. A refusal may happen before a concrete
    domain row is loaded, so the default entity is the principal itself: stable id 0
    with the requested permission and optional target carried in the payload.
    """

    def __init__(self, entity_id: int = 0) -> None:
        self.__tablename__ = "access_decision"
        self.id = entity_id


def _event_changes(
    permission: str, resource: Mapping[str, Any] | None
) -> dict[str, tuple[Any, Any]]:
    changes: dict[str, tuple[Any, Any]] = {
        "permission": (None, permission),
        "outcome": (None, "DENIED"),
    }
    if resource:
        changes["resource"] = (None, dict(resource))
    return changes


def require_permission(
    session: Session | None,
    principal: Principal,
    permission: str,
    *,
    resource: Mapping[str, Any] | None = None,
    occurrence_time: datetime | None = None,
) -> None:
    """Require ``principal`` to hold ``permission``, else log and raise 403.

    The 403 has no body details (R2.3); the audit trail gets the useful detail in an
    ``ACCESS_DENIED`` event. ``session`` may be ``None`` in pure checks and tests; in
    a route handler, pass the request's unit-of-work session so the refusal event is
    written on the same transaction as the attempted operation's audit context.
    """
    if permission not in PERMISSIONS:
        raise ValueError(f"unknown permission {permission!r}; add it to PERMISSIONS")
    if principal.has_permission(permission):
        return

    if session is not None:
        EventLog.append(
            session,
            event_type=ACCESS_DENIED_EVENT,
            entity=_AccessDecision(),
            actor=principal,  # Principal is structurally an EventLog actor.
            changes=_event_changes(permission, resource),
            occurrence_time=occurrence_time or datetime.now(timezone.utc),
        )
    raise NotAuthorised()
