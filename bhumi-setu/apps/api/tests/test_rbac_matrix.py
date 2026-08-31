"""Permission registry and RBAC matrix guard (task 5.6).

The app has only infrastructure routes today, so the shipped matrix is empty by
design. The important thing is that the machinery exists before domain endpoints
arrive: every protected route/role/in-scope triple must have an explicit expectation,
every expected permission must come from the registry, and denied access writes an
``ACCESS_DENIED`` event while returning a detail-free 403.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.errors import ErrorCode, NotAuthorised
from app.main import create_app
from app.security.access import Principal
from app.security.permissions import (
    ACCESS_DENIED_EVENT,
    PERMISSIONS,
    permission_registered,
    require_permission,
)
from app.settings import CoreSettings


ALL_ROLES = ("OFFICER", "OWNER", "NON_OWNER", "SERVICE")
PROTECTED_ROUTE_PERMISSIONS: dict[tuple[str, str], str] = {}
RBAC_EXPECTATIONS: dict[tuple[str, str, bool], bool] = {}


def _core() -> CoreSettings:
    return CoreSettings.model_validate({"APP_ENV": "development", "LOG_LEVEL": "WARNING"})


def _route_key(route: APIRoute) -> tuple[str, str]:
    methods = sorted(method for method in (route.methods or ()) if method not in {"HEAD", "OPTIONS"})
    return ("|".join(methods), route.path)


def _protected_route_keys(
    app_routes: Iterable[object], route_permissions: Mapping[tuple[str, str], str]
) -> set[tuple[str, str]]:
    return {
        _route_key(route)
        for route in app_routes
        if isinstance(route, APIRoute) and _route_key(route) in route_permissions
    }


def _rbac_matrix_offences(
    routes: Iterable[object],
    route_permissions: Mapping[tuple[str, str], str],
    expectations: Mapping[tuple[str, str, bool], bool],
) -> list[str]:
    offences: list[str] = []
    protected = _protected_route_keys(routes, route_permissions)

    for route_key, permission in route_permissions.items():
        if permission not in PERMISSIONS:
            offences.append(f"{route_key}: permission {permission!r} is not in PERMISSIONS")
        if route_key not in protected:
            offences.append(f"{route_key}: has an RBAC permission but no matching app route")

    for route_key in protected:
        for role in ALL_ROLES:
            for in_scope in (False, True):
                if (f"{route_key[0]} {route_key[1]}", role, in_scope) not in expectations:
                    offences.append(
                        f"{route_key[0]} {route_key[1]} role={role} in_scope={in_scope} "
                        "has no declared RBAC expectation"
                    )

    for expected_route, role, in_scope in expectations:
        method, _, path = expected_route.partition(" ")
        route_key = (method, path)
        if route_key not in route_permissions:
            offences.append(f"{expected_route}: expectation exists but route has no permission")
        if role not in ALL_ROLES:
            offences.append(f"{expected_route}: unknown role {role!r}")
        if not isinstance(in_scope, bool):
            offences.append(f"{expected_route}: in_scope key must be bool")

    return offences


def test_permission_registry_is_the_task_5_6_vocabulary() -> None:
    assert PERMISSIONS == frozenset(
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
    assert all(permission_registered(permission) for permission in PERMISSIONS)
    assert not permission_registered("case.transiton")


def test_rbac_matrix_is_exhaustive_and_declared() -> None:
    offences = _rbac_matrix_offences(
        create_app(_core()).routes,
        PROTECTED_ROUTE_PERMISSIONS,
        RBAC_EXPECTATIONS,
    )
    assert not offences, "RBAC matrix is incomplete or invalid: " + "; ".join(offences)


def test_rbac_matrix_guard_bites_on_missing_expectations() -> None:
    app = FastAPI()

    @app.patch("/api/officer/cases/{case_id}/stage")
    async def _stage(case_id: int) -> dict[str, int]:
        return {"case_id": case_id}

    route_key = ("PATCH", "/api/officer/cases/{case_id}/stage")
    offences = _rbac_matrix_offences(
        app.routes,
        {route_key: "case.transition"},
        {},
    )
    assert any("role=OFFICER" in offence and "no declared" in offence for offence in offences)
    assert any("role=SERVICE" in offence and "no declared" in offence for offence in offences)


def test_rbac_matrix_guard_bites_on_unknown_permissions() -> None:
    app = FastAPI()

    @app.post("/api/officer/imports")
    async def _imports() -> dict[str, bool]:
        return {"ok": True}

    route_key = ("POST", "/api/officer/imports")
    expectation = "POST /api/officer/imports"
    expectations = {
        (expectation, role, in_scope): False
        for role in ALL_ROLES
        for in_scope in (False, True)
    }
    offences = _rbac_matrix_offences(
        app.routes,
        {route_key: "import.submt"},
        expectations,
    )
    assert any("not in PERMISSIONS" in offence for offence in offences)


def test_rbac_matrix_guard_bites_on_stale_expectations() -> None:
    offences = _rbac_matrix_offences(
        [],
        {},
        {("PATCH /api/officer/missing", "OFFICER", True): True},
    )
    assert any("expectation exists but route has no permission" in offence for offence in offences)


def test_require_permission_allows_a_registered_held_permission() -> None:
    principal = Principal(
        kind="OFFICER",
        id="officer-1",
        permissions=frozenset({"case.transition"}),
    )
    require_permission(None, principal, "case.transition")


def test_require_permission_rejects_an_unknown_permission() -> None:
    principal = Principal(kind="OFFICER", id="officer-1")
    with pytest.raises(ValueError, match="unknown permission"):
        require_permission(None, principal, "case.transiton")


def test_require_permission_denies_with_detail_free_403_without_a_session() -> None:
    principal = Principal(kind="CITIZEN", id="citizen-1")
    with pytest.raises(NotAuthorised) as caught:
        require_permission(None, principal, "case.transition")
    error = caught.value
    assert error.status_code == 403
    assert error.code == ErrorCode.NOT_AUTHORISED
    assert error.envelope().details == {}


@dataclass
class _RecordedEvent:
    event_type: str
    actor_id: str
    payload: dict


class _FakeSession:
    def __init__(self) -> None:
        self.events: list[_RecordedEvent] = []


def test_require_permission_appends_access_denied_before_raising(monkeypatch) -> None:
    session = _FakeSession()
    principal = Principal(kind="OFFICER", id="officer-1")
    occurred = datetime(2024, 5, 1, 12, tzinfo=timezone.utc)

    def _append(session_arg, *, event_type, entity, actor, changes, occurrence_time, **kw):  # type: ignore[no-untyped-def]
        assert session_arg is session
        assert entity.__tablename__ == "access_decision"
        assert occurrence_time == occurred
        session.events.append(
            _RecordedEvent(
                event_type=event_type,
                actor_id=actor.id,
                payload={name: {"from": old, "to": new} for name, (old, new) in changes.items()},
            )
        )

    monkeypatch.setattr("app.security.permissions.EventLog.append", _append)

    with pytest.raises(NotAuthorised):
        require_permission(
            session,  # type: ignore[arg-type]
            principal,
            "dsar.dispose",
            resource={"case_id": 7},
            occurrence_time=occurred,
        )

    assert session.events == [
        _RecordedEvent(
            event_type=ACCESS_DENIED_EVENT,
            actor_id="officer-1",
            payload={
                "permission": {"from": None, "to": "dsar.dispose"},
                "outcome": {"from": None, "to": "DENIED"},
                "resource": {"from": None, "to": {"case_id": 7}},
            },
        )
    ]
