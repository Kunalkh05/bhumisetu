"""Internal i18n telemetry route tests (task 18.6)."""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.api.routers import internal_router
from app.api.versioning import VersionedWrite
from app.schemas.i18n import MissingI18nKeyIn, MissingI18nKeyOut


def test_internal_missing_key_route_is_registered_with_versioned_body() -> None:
    routes = [
        route
        for route in internal_router.routes
        if isinstance(route, APIRoute) and route.path == "/internal/i18n/missing"
    ]

    assert len(routes) == 1
    assert routes[0].response_model is MissingI18nKeyOut
    assert issubclass(MissingI18nKeyIn, VersionedWrite)
