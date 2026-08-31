"""Access_Control without a database: the principal, the scope clause's shape, and
the one-door authentication seam (task 5.1, §8.1).

The parts that need real ``ltree`` containment and a real officer row are in
``tests/db/test_access_scope.py``. Everything here is either pure (the frozen
principal, the fail-closed clause) or exercises :func:`principal_from_request`
against a fake :class:`AuthBackend`, which is the whole point of the backend being a
seam — the credential-to-principal wiring is testable before task 7.1's Redis store
exists.
"""

from __future__ import annotations

import dataclasses

import pytest
from sqlalchemy import BigInteger, Column, Integer, MetaData, String, Table, select
from sqlalchemy.dialects import postgresql

from starlette.requests import Request

from app.security.access import (
    CITIZEN_SESSION_COOKIE,
    OFFICER_SESSION_COOKIE,
    AuthBackendNotConfigured,
    CitizenSession,
    OfficerSession,
    Principal,
    ServiceIdentity,
    Unauthenticated,
    authenticate,
    configure_auth_backend,
    get_auth_backend,
    principal_from_request,
    scoped,
)

# A throwaway table to hang the scope clause on. A local MetaData, so it never
# reaches Base.metadata or the registry guard.
_md = MetaData()
_probe = Table(
    "access_probe",
    _md,
    Column("id", Integer, primary_key=True),
    Column("area_code", String),
    Column("case_id", BigInteger),
)


def _sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect())).replace("\n", " ")


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class FakeCredentials:
    """The cookies/headers slice :func:`principal_from_request` reads."""

    def __init__(
        self,
        cookies: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.cookies = cookies or {}
        self.headers = headers or {}


class FakeBackend:
    """A dict-driven :class:`AuthBackend`: a token resolves iff it was registered."""

    def __init__(
        self,
        officers: dict[str, OfficerSession] | None = None,
        citizens: dict[str, CitizenSession] | None = None,
        services: dict[str, ServiceIdentity] | None = None,
    ) -> None:
        self._officers = officers or {}
        self._citizens = citizens or {}
        self._services = services or {}

    def officer_session(self, token: str) -> OfficerSession | None:
        return self._officers.get(token)

    def citizen_session(self, token: str) -> CitizenSession | None:
        return self._citizens.get(token)

    def service_identity(self, token: str) -> ServiceIdentity | None:
        return self._services.get(token)


@pytest.fixture
def restore_auth_backend():
    """Restore whatever backend was registered before the test."""
    previous = configure_auth_backend(None)
    yield
    configure_auth_backend(previous)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------


def test_principal_is_frozen() -> None:
    """A handler must not be able to rewrite its own identity mid-request."""
    principal = Principal(kind="OFFICER", id="o1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        principal.permissions = frozenset({"config.write"})  # type: ignore[misc]


def test_principal_is_hashable() -> None:
    a = Principal(kind="OFFICER", id="o1", permissions=frozenset({"x"}), scope_paths=("MH",))
    b = Principal(kind="OFFICER", id="o1", permissions=frozenset({"x"}), scope_paths=("MH",))
    assert a == b
    assert hash(a) == hash(b)
    assert {a, b} == {a}


def test_principal_serves_as_an_event_actor() -> None:
    """``kind`` and ``id`` are the two fields the event log types its actor on, so a
    Principal is usable as the actor of an appended event without the log importing
    this module."""
    principal = Principal(kind="OFFICER", id="officer-1")
    assert isinstance(principal.kind, str)
    assert isinstance(principal.id, str)


def test_has_permission_reads_only_the_principal() -> None:
    principal = Principal(kind="SERVICE", id="svc", permissions=frozenset({"model.administer"}))
    assert principal.has_permission("model.administer") is True
    assert principal.has_permission("config.write") is False


# ---------------------------------------------------------------------------
# scoped(): shape and fail-closed behaviour (no database needed)
# ---------------------------------------------------------------------------


def test_officer_scope_joins_area_and_ors_the_paths() -> None:
    officer = Principal(kind="OFFICER", id="o", scope_paths=("MH.MH_PUNE", "MH.MH_SATARA"))
    sql = _sql(scoped(select(_probe.c.id), officer, _probe.c.area_code))
    assert "JOIN administrative_area ON access_probe.area_code = administrative_area.code" in sql
    assert sql.count("administrative_area.path <@") == 2
    assert " OR " in sql


def test_officer_with_no_scope_matches_nothing() -> None:
    """Fail closed: no jurisdiction is *nothing*, not everything (R2.2)."""
    officer = Principal(kind="OFFICER", id="o")
    sql = _sql(scoped(select(_probe.c.id), officer, _probe.c.area_code))
    assert "WHERE false" in sql
    assert "administrative_area" not in sql


def test_citizen_scope_restricts_to_the_single_case() -> None:
    citizen = Principal(kind="CITIZEN", id="c", case_id=42)
    sql = _sql(scoped(select(_probe.c.id), citizen, case_col=_probe.c.case_id))
    assert "access_probe.case_id = " in sql
    assert "administrative_area" not in sql


def test_citizen_with_no_case_matches_nothing() -> None:
    citizen = Principal(kind="CITIZEN", id="c", case_id=None)
    sql = _sql(scoped(select(_probe.c.id), citizen, case_col=_probe.c.case_id))
    assert "WHERE false" in sql


def test_citizen_query_without_case_col_is_a_programming_error() -> None:
    citizen = Principal(kind="CITIZEN", id="c", case_id=42)
    with pytest.raises(ValueError, match="case_col"):
        scoped(select(_probe.c.id), citizen)


def test_officer_query_without_area_col_is_a_programming_error() -> None:
    officer = Principal(kind="OFFICER", id="o", scope_paths=("MH",))
    with pytest.raises(ValueError, match="area_col"):
        scoped(select(_probe.c.id), officer)


# ---------------------------------------------------------------------------
# principal_from_request: one door, three credential kinds
# ---------------------------------------------------------------------------


def test_service_token_yields_a_service_principal() -> None:
    backend = FakeBackend(
        services={"svc-tok": ServiceIdentity("prediction", frozenset({"model.administer"}))}
    )
    creds = FakeCredentials(headers={"authorization": "Bearer svc-tok"})
    principal = principal_from_request(creds, backend=backend, session=None)  # type: ignore[arg-type]
    assert principal.kind == "SERVICE"
    assert principal.id == "prediction"
    assert principal.has_permission("model.administer")


def test_citizen_cookie_yields_a_case_scoped_principal() -> None:
    backend = FakeBackend(citizens={"c-tok": CitizenSession("subject-9", 77, (5, 6))})
    creds = FakeCredentials(cookies={CITIZEN_SESSION_COOKIE: "c-tok"})
    principal = principal_from_request(creds, backend=backend, session=None)  # type: ignore[arg-type]
    assert principal.kind == "CITIZEN"
    assert principal.case_id == 77
    assert principal.owner_record_ids == (5, 6)
    assert principal.permissions == frozenset()


def test_no_credential_is_unauthenticated() -> None:
    with pytest.raises(Unauthenticated):
        principal_from_request(FakeCredentials(), backend=FakeBackend(), session=None)  # type: ignore[arg-type]


def test_present_but_invalid_officer_cookie_does_not_fall_through() -> None:
    """A stale officer cookie is a failed officer, not a candidate citizen: the
    request is unauthenticated rather than silently retried as another kind."""
    backend = FakeBackend(citizens={"c-tok": CitizenSession("s", 1)})
    creds = FakeCredentials(
        cookies={OFFICER_SESSION_COOKIE: "stale", CITIZEN_SESSION_COOKIE: "c-tok"}
    )
    with pytest.raises(Unauthenticated):
        principal_from_request(creds, backend=backend, session=None)  # type: ignore[arg-type]


def test_malformed_authorization_header_is_not_a_credential() -> None:
    backend = FakeBackend(services={"": ServiceIdentity("x")})
    for header in ["", "Basic abc", "Bearer", "Bearer   "]:
        creds = FakeCredentials(headers={"authorization": header})
        with pytest.raises(Unauthenticated):
            principal_from_request(creds, backend=backend, session=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# The backend registration seam
# ---------------------------------------------------------------------------


def test_get_auth_backend_refuses_when_unconfigured(restore_auth_backend) -> None:
    configure_auth_backend(None)
    with pytest.raises(AuthBackendNotConfigured):
        get_auth_backend()


def test_configure_auth_backend_returns_the_previous_one(restore_auth_backend) -> None:
    first, second = FakeBackend(), FakeBackend()
    configure_auth_backend(first)
    assert get_auth_backend() is first
    previous = configure_auth_backend(second)
    assert previous is first
    assert get_auth_backend() is second


# ---------------------------------------------------------------------------
# authenticate(): the FastAPI dependency wiring (DB-free credential kinds)
# ---------------------------------------------------------------------------


def _request(cookies: dict[str, str] | None = None, headers: dict[str, str] | None = None) -> Request:
    """A minimal Starlette request carrying the given cookies and headers."""
    raw: list[tuple[bytes, bytes]] = []
    if cookies:
        raw.append((b"cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()).encode()))
    for key, value in (headers or {}).items():
        raw.append((key.encode(), value.encode()))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw})


def test_authenticate_returns_principal_and_records_it_on_the_request(
    restore_auth_backend,
) -> None:
    """The dependency resolves the principal and stashes it on request.state for the
    response gate (task 5.3) to read. The service path touches no database."""
    configure_auth_backend(
        FakeBackend(services={"tok": ServiceIdentity("prediction", frozenset({"model.administer"}))})
    )
    request = _request(headers={"authorization": "Bearer tok"})
    principal = authenticate(request)
    assert principal.kind == "SERVICE"
    assert request.state.principal is principal


def test_authenticate_raises_unauthenticated_without_a_credential(
    restore_auth_backend,
) -> None:
    configure_auth_backend(FakeBackend())
    with pytest.raises(Unauthenticated):
        authenticate(_request())
