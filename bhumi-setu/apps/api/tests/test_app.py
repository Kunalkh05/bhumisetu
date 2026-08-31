"""The application object and the §9.4 error envelope.

Every non-2xx response leaves as ``{"code", "message", "details"}``. Requirements
are specific about what a refusal must tell the caller — the per-attribute diff
for R29.3, the policy key and date for R28.5 — so the shape is asserted here,
once, before any subsystem raises through it.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import DomainError, ErrorCode
from app.main import create_app
from app.settings import CoreSettings


class _Conflict(DomainError):
    code = ErrorCode.ENTITY_VERSION_CONFLICT
    status_code = 409


def core(**overrides: str) -> CoreSettings:
    # Keyed by the committed environment names, which are the fields' validation
    # aliases: a settings group is addressed the same way in a test as in a
    # container.
    return CoreSettings.model_validate(
        {"APP_ENV": "development", "LOG_LEVEL": "WARNING"} | overrides
    )


@pytest.fixture
def app() -> FastAPI:
    application = create_app(core())

    @application.get("/_test/conflict")
    async def _conflict() -> None:
        raise _Conflict(
            "Entity was modified by another actor",
            details={
                "attributes": [
                    {"name": "share", "submitted_prior": "0.50", "current": "0.34"}
                ],
                "conflicting_actor_id": "officer:412",
                "current_entity_version": 8,
            },
        )

    @application.get("/_test/unhandled")
    async def _unhandled() -> None:
        raise ZeroDivisionError("leaked internals")

    return application


def test_healthz_answers_without_disclosing_state(app: FastAPI) -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_a_domain_refusal_returns_the_section_9_4_envelope(app: FastAPI) -> None:
    with TestClient(app) as client:
        response = client.get("/_test/conflict")

    assert response.status_code == 409
    body = response.json()
    assert set(body) == {"code", "message", "details"}
    assert body["code"] == "ENTITY_VERSION_CONFLICT"
    assert body["details"]["current_entity_version"] == 8
    assert body["details"]["conflicting_actor_id"] == "officer:412"


def test_a_framework_error_returns_the_same_envelope(app: FastAPI) -> None:
    """One shape for every failure, so a client parses one shape."""
    with TestClient(app) as client:
        response = client.get("/no-such-route")

    assert response.status_code == 404
    assert set(response.json()) == {"code", "message", "details"}


def test_an_unhandled_error_discloses_nothing(app: FastAPI) -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/unhandled")

    assert response.status_code == 500
    body = response.json()
    assert body == {"code": "INTERNAL_ERROR", "message": "Internal error", "details": {}}
    assert "leaked internals" not in response.text


def test_interactive_docs_are_off_in_production() -> None:
    """The docs page enumerates the whole surface, including internal routes."""
    production = create_app(core(APP_ENV="production"))
    assert production.docs_url is None
    assert production.openapi_url is None

    development = create_app(core())
    assert development.docs_url == "/docs"
