"""One principal, one decision, one scope clause (§8.1).

Access_Control's whole surface at this point is three things that every later
endpoint leans on: the :class:`Principal` an authenticated request is reduced to,
the :func:`authenticate` dependency that produces it, and :func:`scoped`, the one
``WHERE`` clause that confines a query to what a principal may see. R2.7 — the
same decision "regardless of whether the request originates from the Officer
Portal, the Citizen Portal, or a direct interface call" — is not enforced by a
check somewhere; it is a consequence of this shape. There is exactly one place
that looks at cookies and headers (this module), it produces a :class:`Principal`,
and **everything downstream reads the Principal and never the request**. A branch
on request origin cannot creep in later because the origin is not in scope later:
it was consumed here.

Why permissions and scope are read from the database on every request
---------------------------------------------------------------------

R2.6 requires a role's changed permission set or jurisdiction scope to apply on
the *next* request against an existing session, with no re-authentication. The
mechanism is deliberately dull: the session record (task 7.1's Redis entry) holds
only *which officer* this is, and :func:`resolve_officer_principal` reads that
officer's live roles, permissions and scope paths from the database every time
:func:`authenticate` runs. Nothing authorization-bearing is cached in the session,
so there is nothing to invalidate — a permission revoked a second ago is simply
absent from the row the next request reads. Caching the permission set into the
session would be faster and would reintroduce exactly the staleness R2.6 forbids.

The session lookup is a seam, not an import
-------------------------------------------

Turning an opaque session token into an officer id (and a citizen token into its
one case, and a service token into a service identity) is task 7.1's Redis-backed
:mod:`app.security.auth`, which does not exist yet. This module does not wait on
it and does not import it: it declares the :class:`AuthBackend` protocol that 7.1
must satisfy and reads it through :func:`get_auth_backend`. The dependency wiring,
the freshness rule, and the scope clause are all testable now against a fake
backend; task 7.1 registers the real one with :func:`configure_auth_backend` at
startup and nothing here changes.

Why ``scoped`` takes the column rather than importing the case model
--------------------------------------------------------------------

The design writes the citizen branch as ``AcquisitionCase.id == principal.case_id``
and the officer branch as an ``ltree`` disjunction joined through
``AdministrativeArea``. ``AcquisitionCase`` lands in task 8.1; this module predates
it. So :func:`scoped` composes against a *passed* column — ``case_col`` for the
citizen's single case, ``area_col`` for the officer's administrative join — rather
than importing a model that is not here. The clause is identical either way; the
call site names the column, which it must anyway because the same clause guards a
case list, a parcel query and an issue queue, each with the area on a different
table.

Fail closed
-----------

An officer with no jurisdiction scope, or a citizen session with no case, restricts
to *nothing*, never to everything: :func:`scoped` returns a ``WHERE false`` rather
than an unfiltered query. An unauthenticated or unresolvable request raises
:class:`Unauthenticated` (R1.6) rather than yielding an anonymous principal that
some downstream check might read generously. The safe direction for a mistake here
is empty, not open.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Literal, Mapping, Protocol, runtime_checkable

from fastapi import Request
from sqlalchemy import Select, false, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.errors import DomainError, ErrorCode
from app.models.jurisdiction import AdministrativeArea
from app.models.officer import JurisdictionScope, Officer, OfficerRole, Role

__all__ = [
    "AUTHORIZATION_HEADER",
    "CITIZEN_SESSION_COOKIE",
    "OFFICER_SESSION_COOKIE",
    "AuthBackend",
    "AuthBackendNotConfigured",
    "CitizenSession",
    "OfficerSession",
    "Principal",
    "ServiceIdentity",
    "Unauthenticated",
    "authenticate",
    "configure_auth_backend",
    "get_auth_backend",
    "principal_from_request",
    "resolve_officer_principal",
    "scoped",
]

PrincipalKind = Literal["OFFICER", "CITIZEN", "SERVICE"]

#: Cookie carrying the officer's opaque session token (task 7.1 sets it
#: ``HttpOnly; Secure; SameSite=Strict``, §19.1). Named here so the writer in 7.1
#: and the reader in :func:`authenticate` cannot drift onto two different cookies.
OFFICER_SESSION_COOKIE = "bhumisetu_officer_session"
#: Cookie carrying the citizen's opaque, single-case session token (task 7.5).
CITIZEN_SESSION_COOKIE = "bhumisetu_citizen_session"
#: Header carrying the ``/internal/*`` service token (§9.3), ``Bearer <token>``.
AUTHORIZATION_HEADER = "authorization"


@dataclass(frozen=True)
class Principal:
    """What an authenticated request is reduced to, and the only thing authorization
    reads (R2.7).

    Frozen because it is the request's identity for the whole of that request: a
    handler that could rewrite its own permissions is not an access control. Frozen
    also makes it hashable, which lets it key a per-request memo without surprises.

    ``id`` and ``kind`` are ``str`` so a :class:`Principal` doubles as the event
    log's actor (``app/db/event_log.py`` types its actor structurally on those two
    fields), which is how an appended event records who acted without the log
    importing this module.

    ``role_ids`` is a tuple of :class:`uuid.UUID` rather than the design's ``int``:
    ``role.id`` and ``officer.id`` are ``uuid`` in the schema (see
    ``app/models/officer.py``), while ``case_id`` and ``owner_record_ids`` stay
    ``int`` because every R4.1 entity carries a ``bigint`` key (see
    ``app/models/event.py``). The fields are split by principal kind:

    * an **officer** carries ``role_ids``, ``permissions`` (the union across its
      roles) and ``scope_paths`` (one ``ltree`` path per jurisdiction area);
    * a **citizen** carries ``case_id`` (its single case, R3.7) and
      ``owner_record_ids`` (the ownership records it may see), and no permissions;
    * a **service** carries ``permissions`` and neither scope nor case — it is
      confined by the internal network and its token, not by jurisdiction.
    """

    kind: PrincipalKind
    id: str
    role_ids: tuple[uuid.UUID, ...] = ()
    permissions: frozenset[str] = frozenset()
    scope_paths: tuple[str, ...] = ()
    case_id: int | None = None
    owner_record_ids: tuple[int, ...] = ()

    def has_permission(self, permission: str) -> bool:
        """True when this principal holds ``permission``.

        The decision reads the principal and nothing else, which is the whole of
        Property 5's "depends only on principal and resource": the same principal
        yields the same answer whether it arrived by officer cookie, citizen cookie
        or service token. Route-level enforcement of a *named* permission is the
        gate's job (task 5.6); this is the predicate it will consult.
        """
        return permission in self.permissions


# ===========================================================================
# The authentication seam (task 7.1 provides the implementation)
# ===========================================================================


@dataclass(frozen=True)
class OfficerSession:
    """What the backend resolves an officer session token to: an officer id, and
    nothing that authorization depends on.

    Deliberately just the id. If this carried the permission set, R2.6 would break
    the moment a role changed, because the request would read the permissions the
    session was minted with rather than the ones the officer holds now. The
    freshness rule is enforced structurally by there being nothing else to read
    here — :func:`resolve_officer_principal` goes to the database for the rest.
    """

    officer_id: uuid.UUID


@dataclass(frozen=True)
class CitizenSession:
    """What the backend resolves a citizen session token to: the one case the
    session is scoped to (R3.7) and the ownership records it may see."""

    subject_id: str
    case_id: int
    owner_record_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ServiceIdentity:
    """What the backend resolves a verified service token to (§9.3): an identity and
    the permissions the token grants."""

    service_id: str
    permissions: frozenset[str] = frozenset()


@runtime_checkable
class AuthBackend(Protocol):
    """The credential-resolution seam task 7.1 fills.

    Three narrow lookups, one per credential kind. Each returns ``None`` for a
    token that is absent, expired, revoked or malformed — :func:`authenticate` turns
    that ``None`` into an :class:`Unauthenticated` response and never into a partial
    principal. The protocol is intentionally free of any Redis or JWT detail: this
    module knows only that a token resolves to an identity or does not.
    """

    def officer_session(self, token: str) -> OfficerSession | None:
        """Resolve an officer session token, or ``None`` if it is not valid."""
        ...

    def citizen_session(self, token: str) -> CitizenSession | None:
        """Resolve a citizen session token, or ``None`` if it is not valid."""
        ...

    def service_identity(self, token: str) -> ServiceIdentity | None:
        """Verify a service token, or ``None`` if it does not verify."""
        ...


class AuthBackendNotConfigured(RuntimeError):
    """No :class:`AuthBackend` has been registered.

    A programming/deployment error, not a runtime condition: the process cannot
    authenticate anyone until task 7.1's backend is wired at startup. Raised loudly
    rather than defaulted to a permissive stub, in the spirit of ``app/settings.py``
    — a missing piece that changes who gets in refuses rather than guesses.
    """


_auth_backend: AuthBackend | None = None


def configure_auth_backend(backend: AuthBackend | None) -> AuthBackend | None:
    """Register the process-wide :class:`AuthBackend`, returning the previous one.

    Called once at startup by task 7.1. It is module-global on purpose — the
    backend is process infrastructure, not per-request state — and returns the prior
    value so a test can install a fake and restore what was there.
    """
    global _auth_backend
    previous = _auth_backend
    _auth_backend = backend
    return previous


def get_auth_backend() -> AuthBackend:
    """Return the registered backend, or refuse.

    :raises AuthBackendNotConfigured: if no backend has been registered yet.
    """
    if _auth_backend is None:
        raise AuthBackendNotConfigured(
            "no AuthBackend is configured; task 7.1 registers the Redis-backed "
            "session store with configure_auth_backend() at startup"
        )
    return _auth_backend


class Unauthenticated(DomainError):
    """R1.6: no valid session, so the response is unauthenticated and carries no
    case data.

    A 401 with an empty ``details`` — distinct from :class:`~app.errors.NotAuthorised`
    (403), which is for a principal that authenticated but may not do the thing.
    :func:`authenticate` raises this; the gate (task 5.6) raises the other. The empty
    body is the point: a refusal to authenticate discloses nothing about why.
    """

    code = ErrorCode.UNAUTHENTICATED
    status_code = 401

    def __init__(self) -> None:
        super().__init__("Unauthenticated", details={})


# ===========================================================================
# Resolving a principal
# ===========================================================================


def resolve_officer_principal(
    session: Session, officer_id: uuid.UUID
) -> Principal | None:
    """Read an officer's live permissions and scope from the database (R2.6).

    This is the freshness guarantee in one function: called on every request by
    :func:`authenticate`, it reads the officer's *current* roles, the union of those
    roles' permissions, and one ``ltree`` path per jurisdiction area. A role change
    committed a moment ago is visible here on the next request because nothing is
    cached between requests — the session held only ``officer_id``.

    Returns ``None`` for an officer that does not exist or is not active, so a
    deactivated officer's still-valid-looking session resolves to no principal and
    the request is unauthenticated. That is the same fail-closed direction as an
    empty scope: absence denies.

    :param session: a session to read on. A read only — nothing is written or
        flushed — so it is deliberately *not* a ``unit_of_work()``; a dependency
        must not open the write transaction the handler owns (``app/db/session.py``).
    :param officer_id: the officer the session identified.
    :returns: the officer's :class:`Principal`, or ``None`` if there is no active
        officer with that id.
    """
    is_active = session.execute(
        select(Officer.id).where(
            Officer.id == officer_id, Officer.is_active.is_(True)
        )
    ).scalar_one_or_none()
    if is_active is None:
        return None

    role_rows = session.execute(
        select(Role.id, Role.permissions)
        .join(OfficerRole, OfficerRole.role_id == Role.id)
        .where(OfficerRole.officer_id == officer_id)
    ).all()
    role_ids = tuple(row.id for row in role_rows)
    permissions: set[str] = set()
    for row in role_rows:
        permissions.update(row.permissions or ())

    # One ltree path per area any of the officer's roles covers. distinct() collapses
    # the case where two roles name the same area; the paths feed scoped()'s <@
    # disjunction directly.
    scope_paths = tuple(
        session.execute(
            select(AdministrativeArea.path)
            .select_from(OfficerRole)
            .join(
                JurisdictionScope,
                JurisdictionScope.role_id == OfficerRole.role_id,
            )
            .join(
                AdministrativeArea,
                AdministrativeArea.code == JurisdictionScope.area_code,
            )
            .where(OfficerRole.officer_id == officer_id)
            .distinct()
        ).scalars()
    )

    return Principal(
        kind="OFFICER",
        id=str(officer_id),
        role_ids=role_ids,
        permissions=frozenset(permissions),
        scope_paths=scope_paths,
    )


@runtime_checkable
class _Credentials(Protocol):
    """The slice of the request :func:`principal_from_request` reads: cookies and
    headers, nothing else. Starlette's ``Request`` satisfies it, and so does a plain
    stand-in in a test, which keeps the resolution logic testable without a live
    ASGI request."""

    @property
    def cookies(self) -> Mapping[str, str]:
        ...

    @property
    def headers(self) -> Mapping[str, str]:
        ...


def _bearer_token(header_value: str | None) -> str | None:
    """Extract the token from an ``Authorization: Bearer <token>`` header.

    Returns ``None`` for an absent header, a non-Bearer scheme, or an empty token,
    so a malformed header is simply "no service credential" rather than an error.
    """
    if not header_value:
        return None
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def principal_from_request(
    credentials: _Credentials,
    *,
    backend: AuthBackend,
    session: Session,
) -> Principal:
    """Reduce a request's credentials to a :class:`Principal`, or refuse.

    This is the one place origin is examined (R2.7): an officer cookie, a citizen
    cookie, or a service token, checked in that order, each resolved through
    ``backend`` and — for an officer — enriched from the database. The result is a
    :class:`Principal`; the caller reads it and never the request again.

    A credential that is *present but does not resolve* raises
    :class:`Unauthenticated` rather than falling through to try the next kind: a
    stale officer cookie is a failed officer, not a candidate citizen. Only the
    genuine absence of a credential falls through, and a request with none is
    unauthenticated.

    :param credentials: the request's cookies and headers.
    :param backend: the resolution seam (task 7.1's store, or a fake in a test).
    :param session: a read session, used only to resolve an officer's live
        permissions and scope; the citizen and service paths never touch it.
    :raises Unauthenticated: if no credential is present, or the presented one does
        not resolve to a live identity.
    """
    officer_token = credentials.cookies.get(OFFICER_SESSION_COOKIE)
    if officer_token is not None:
        officer = backend.officer_session(officer_token)
        if officer is None:
            raise Unauthenticated()
        principal = resolve_officer_principal(session, officer.officer_id)
        if principal is None:
            raise Unauthenticated()
        return principal

    citizen_token = credentials.cookies.get(CITIZEN_SESSION_COOKIE)
    if citizen_token is not None:
        citizen = backend.citizen_session(citizen_token)
        if citizen is None:
            raise Unauthenticated()
        return Principal(
            kind="CITIZEN",
            id=citizen.subject_id,
            case_id=citizen.case_id,
            owner_record_ids=tuple(citizen.owner_record_ids),
        )

    service_token = _bearer_token(credentials.headers.get(AUTHORIZATION_HEADER))
    if service_token is not None:
        service = backend.service_identity(service_token)
        if service is None:
            raise Unauthenticated()
        return Principal(
            kind="SERVICE",
            id=service.service_id,
            permissions=frozenset(service.permissions),
        )

    raise Unauthenticated()


@contextmanager
def _read_session() -> Iterator[Session]:
    """A short-lived read session for principal resolution.

    Not a ``unit_of_work()``: authentication is a read, and a dependency must not
    open the write transaction the route handler owns (``app/db/session.py`` explains
    why the boundary is opened at the call site). It runs before that boundary
    exists, checks out one connection, and returns it on exit, so it never collides
    with the handler's later transaction.
    """
    session = Session(bind=get_engine())
    try:
        yield session
    finally:
        session.close()


def authenticate(request: Request) -> Principal:
    """FastAPI dependency: resolve the request to a :class:`Principal` (R2.6, R2.7).

    The single authentication entry point for every router — officer, citizen and
    internal alike — so the same principal model guards them all. It reads the
    registered :class:`AuthBackend`, opens a read session, resolves the principal,
    and records it on ``request.state.principal`` for the response gate (task 5.3) to
    read on the way out.

    :raises Unauthenticated: if the request presents no valid credential (R1.6).
    :raises AuthBackendNotConfigured: if startup has not registered a backend.
    """
    backend = get_auth_backend()
    with _read_session() as session:
        principal = principal_from_request(request, backend=backend, session=session)
    request.state.principal = principal
    return principal


# ===========================================================================
# Scope confinement (§8.1)
# ===========================================================================


def scoped(
    stmt: Select,
    principal: Principal,
    area_col: Any = None,
    *,
    case_col: Any = None,
) -> Select:
    """Confine ``stmt`` to what ``principal`` may see — the one clause every
    scope-restricted query wears (R2.2, R3.7).

    A citizen is confined to its single case: the statement gains
    ``case_col == principal.case_id``. An officer is confined to its jurisdiction:
    the statement joins ``AdministrativeArea`` on ``area_col`` and keeps rows whose
    ``path`` is a descendant of any of the officer's scope paths — one ``<@`` per
    path, OR'd, which is why one district row in ``jurisdiction_scope`` reaches every
    village beneath it without those villages being enumerated.

    The column is passed rather than assumed because the same clause guards
    different tables — a case list scopes on the case's area, a parcel query on the
    parcel's — and because ``AcquisitionCase`` (the citizen branch's table in the
    design) does not exist until task 8.1. The caller names ``area_col`` for an
    officer query and ``case_col`` for a citizen one.

    Fails closed. An officer with no scope paths, or a citizen with no case, matches
    nothing (``WHERE false``) rather than everything — the safe direction for a
    missing scope.

    :param stmt: the ``SELECT`` to constrain.
    :param principal: the requesting principal.
    :param area_col: the column joining the queried row to ``administrative_area.code``;
        required for an officer (and any non-citizen) query.
    :param case_col: the column holding the row's case id; required for a citizen query.
    :returns: ``stmt`` with the confining clause applied.
    :raises ValueError: if the column the principal's kind needs was not supplied.
    """
    if principal.kind == "CITIZEN":
        if case_col is None:
            raise ValueError(
                "a citizen-scoped query must pass case_col: the citizen sees exactly "
                "its one case (R3.7), and the case-id column differs per table"
            )
        if principal.case_id is None:
            return stmt.where(false())
        return stmt.where(case_col == principal.case_id)

    # Officer (and any non-citizen principal): confine to the jurisdiction subtree.
    if area_col is None:
        raise ValueError(
            "an officer-scoped query must pass area_col: the column joining the row "
            "to administrative_area.code, over which the ltree containment is tested"
        )
    if not principal.scope_paths:
        # No scope means see nothing, never see everything (R2.2 fail-closed).
        return stmt.where(false())
    return stmt.join(
        AdministrativeArea, area_col == AdministrativeArea.code
    ).where(
        or_(
            *[
                AdministrativeArea.path.descendant_of(path)
                for path in principal.scope_paths
            ]
        )
    )
