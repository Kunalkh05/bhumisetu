"""Redaction is structural: every gated route redacts its body for the request's
principal, over HTTP, through the real routers and ``create_app`` (task 5.3, §8.2).

Task 5.2 proved the gate as a pure function (``tests/test_gate.py``). This file proves
the *wiring*: that :class:`~app.api.gated_route.GatedRoute` runs that gate on the way
out of an actual endpoint, that the four §9 routers are built with it, and that
``create_app`` mounts them. The load-bearing claim is R26.7 — a redacted attribute is
absent from the response *body*, not hidden in a view — asserted here against a live
:class:`~fastapi.testclient.TestClient` rather than against the gate in isolation.

R2.7 rides along: the same principal produces the same redaction whichever surface it
arrives on, because nothing between the router and the gate looks at the request's
origin. The probe endpoints below are test-only. They are registered on the shipped
routers so the assertions run through the real construction, and removed again when the
test finishes; the domain endpoints that will live here permanently arrive in later
tasks.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.gated_route import GatedRoute, _gated_item_model
from app.api.routers import (
    ALL_ROUTERS,
    citizen_html,
    citizen_router,
    internal_router,
    officer_router,
)
from app.citizen.templating import render_gated
from app.main import create_app
from app.retention.categories import OWNER_CONTACT, OWNER_IDENTITY
from app.security.access import Principal, authenticate
from app.security.gate import GatedModel, Mask, Sensitive, Visibility
from app.settings import CoreSettings

_BULLET = "\u2022"


# ---------------------------------------------------------------------------
# Test response models (the domain models do not exist yet)
# ---------------------------------------------------------------------------


class NoteOut(GatedModel):
    """A nested officer-only note (R23.5)."""

    __owner_record_id_field__ = None
    body: str = Sensitive(Visibility.OFFICER_ONLY)


class OwnershipOut(GatedModel):
    """The design's canonical carrier (§8.2): public parcel facts, owner-only personal
    data, a masked identifier, and officer-only internals."""

    id: int = Sensitive(Visibility.PUBLIC)
    share: Decimal = Sensitive(Visibility.PUBLIC)
    owner_name: str | None = Sensitive(Visibility.OWNER_ONLY, data_category=OWNER_IDENTITY)
    government_identifier: str | None = Sensitive(
        Visibility.OWNER_ONLY, mask=Mask.TRAILING_4, data_category=OWNER_IDENTITY
    )
    contact_mobile: str | None = Sensitive(Visibility.OWNER_ONLY, data_category=OWNER_CONTACT)
    priority_score: float | None = Sensitive(Visibility.OFFICER_ONLY)
    internal_notes: list[NoteOut] = Sensitive(Visibility.OFFICER_ONLY)


_RECORD_ID = 42
_FULL_IDENTIFIER = "AADHAAR1234567890"
_OWNER_NAME = "Asha Kumari"


def _sample(record_id: int = _RECORD_ID) -> OwnershipOut:
    return OwnershipOut(
        id=record_id,
        share=Decimal("0.5"),
        owner_name=_OWNER_NAME,
        government_identifier=_FULL_IDENTIFIER,
        contact_mobile="9876543210",
        priority_score=0.91,
        internal_notes=[NoteOut(body="verify survey number")],
    )


# ---------------------------------------------------------------------------
# Principals
# ---------------------------------------------------------------------------


def _officer() -> Principal:
    return Principal(kind="OFFICER", id="officer-1", scope_paths=("MH",))


def _owner(record_id: int = _RECORD_ID) -> Principal:
    return Principal(kind="CITIZEN", id="owner", case_id=1, owner_record_ids=(record_id,))


def _non_owner(record_id: int = _RECORD_ID) -> Principal:
    return Principal(
        kind="CITIZEN", id="stranger", case_id=2, owner_record_ids=(record_id + 1,)
    )


def _service() -> Principal:
    return Principal(kind="SERVICE", id="prediction")


# ---------------------------------------------------------------------------
# App and client wiring
# ---------------------------------------------------------------------------


def _core() -> CoreSettings:
    return CoreSettings.model_validate({"APP_ENV": "development", "LOG_LEVEL": "WARNING"})


@pytest.fixture
def gated_app() -> Iterator[FastAPI]:
    """An app built by ``create_app``, with probe endpoints on the real routers.

    The probes are added to the shipped routers before ``create_app`` copies them in,
    so the assertions exercise the genuine ``route_class=GatedRoute`` construction and
    the genuine wiring. They are stripped again afterwards, restoring the routers to the
    endpoint-less state every other test expects.
    """
    routers = (officer_router, citizen_router, citizen_html, internal_router)
    baseline = [len(router.routes) for router in routers]

    @officer_router.get("/probe", response_model=OwnershipOut, include_in_schema=False)
    async def _officer_probe(principal: Principal = Depends(authenticate)) -> OwnershipOut:
        return _sample()

    @officer_router.get(
        "/probe-list", response_model=list[OwnershipOut], include_in_schema=False
    )
    async def _officer_probe_list(
        principal: Principal = Depends(authenticate),
    ) -> list[OwnershipOut]:
        return [_sample(1), _sample(2)]

    @citizen_router.get("/probe", response_model=OwnershipOut, include_in_schema=False)
    async def _citizen_probe(principal: Principal = Depends(authenticate)) -> OwnershipOut:
        return _sample()

    @internal_router.get("/probe", response_model=OwnershipOut, include_in_schema=False)
    async def _internal_probe(principal: Principal = Depends(authenticate)) -> OwnershipOut:
        return _sample()

    @citizen_html.get("/probe", include_in_schema=False)
    async def _citizen_html_probe(
        request: Request, principal: Principal = Depends(authenticate)
    ):
        return render_gated(request, "ownership.html", _sample(), principal)

    app = create_app(_core())
    try:
        yield app
    finally:
        for router, count in zip(routers, baseline):
            del router.routes[count:]


def _client_as(app: FastAPI, principal: Principal) -> TestClient:
    """A client whose requests resolve to ``principal``.

    The override stands in for task 7.1's session resolution and, crucially, records the
    principal on ``request.state`` exactly as the real :func:`authenticate` does — that
    is where :class:`GatedRoute` reads it on the way out.
    """

    def _dep(request: Request) -> Principal:
        request.state.principal = principal
        return principal

    app.dependency_overrides[authenticate] = _dep
    return TestClient(app)


def _client_without_principal(app: FastAPI) -> TestClient:
    """A client whose dependency resolves but never sets ``request.state.principal`` —
    the misconfiguration the gate must fail closed on."""

    def _dep(request: Request) -> None:
        return None

    app.dependency_overrides[authenticate] = _dep
    return TestClient(app)


# ---------------------------------------------------------------------------
# Router construction and wiring
# ---------------------------------------------------------------------------


def test_the_four_routers_are_gated_with_the_section_9_prefixes() -> None:
    """§9's four consumer surfaces, each a GatedRoute router at its declared prefix."""
    assert [router.prefix for router in ALL_ROUTERS] == [
        "/api/officer",
        "/api/citizen",
        "/c",
        "/internal",
    ]
    for router in ALL_ROUTERS:
        assert router.route_class is GatedRoute


def test_create_app_mounts_every_surface_as_a_gated_route(gated_app: FastAPI) -> None:
    """The wiring: each probe path is present on the app and is a GatedRoute, so an
    endpoint registered on a §9 router is gated by construction."""
    by_path = {
        route.path: route for route in gated_app.routes if hasattr(route, "path")
    }
    for path in (
        "/api/officer/probe",
        "/api/citizen/probe",
        "/c/probe",
        "/internal/probe",
    ):
        assert path in by_path, f"{path} was not mounted"
        assert isinstance(by_path[path], GatedRoute), f"{path} is not gated"


# ---------------------------------------------------------------------------
# R26.7: redaction at the boundary, by principal
# ---------------------------------------------------------------------------


def test_officer_receives_every_field(gated_app: FastAPI) -> None:
    body = _client_as(gated_app, _officer()).get("/api/officer/probe").json()
    assert set(body) == {
        "id",
        "share",
        "owner_name",
        "government_identifier",
        "contact_mobile",
        "priority_score",
        "internal_notes",
    }
    # An officer serves the notice, so the identifier is unmasked for them.
    assert body["government_identifier"] == _FULL_IDENTIFIER
    assert body["internal_notes"] == [{"body": "verify survey number"}]


def test_owning_citizen_sees_their_data_with_the_identifier_masked(
    gated_app: FastAPI,
) -> None:
    body = _client_as(gated_app, _owner()).get("/api/citizen/probe").json()
    assert set(body) == {
        "id",
        "share",
        "owner_name",
        "government_identifier",
        "contact_mobile",
    }
    assert body["owner_name"] == _OWNER_NAME
    # R26.5: at most the trailing four characters, the rest masked.
    assert body["government_identifier"].endswith(_FULL_IDENTIFIER[-4:])
    assert set(body["government_identifier"][:-4]) == {_BULLET}


def test_a_redacted_attribute_is_absent_from_the_body_not_null(
    gated_app: FastAPI,
) -> None:
    """R26.7 in its sharpest form: a non-owner's body has no ``owner_name`` key at all."""
    response = _client_as(gated_app, _non_owner()).get("/api/citizen/probe")
    body = response.json()
    assert set(body) == {"id", "share"}
    for hidden in ("owner_name", "government_identifier", "contact_mobile", "priority_score"):
        assert hidden not in body
    # Not present-and-null, and the personal values are nowhere in the raw bytes.
    assert _OWNER_NAME not in response.text
    assert _FULL_IDENTIFIER not in response.text


def test_service_principal_sees_only_public_fields(gated_app: FastAPI) -> None:
    body = _client_as(gated_app, _service()).get("/internal/probe").json()
    assert set(body) == {"id", "share"}


def test_the_full_identifier_never_reaches_a_citizen(gated_app: FastAPI) -> None:
    response = _client_as(gated_app, _owner()).get("/api/citizen/probe")
    assert _FULL_IDENTIFIER not in response.text
    assert _BULLET in response.json()["government_identifier"]


def test_a_list_response_is_gated_element_by_element(gated_app: FastAPI) -> None:
    """A ``list[OwnershipOut]`` route redacts each element for the principal — the item
    model is unwrapped from the generic so the gate coerces each decoded row."""
    body = _client_as(gated_app, _non_owner()).get("/api/officer/probe-list").json()
    assert body == [{"id": 1, "share": "0.5"}, {"id": 2, "share": "0.5"}]


def test_a_missing_principal_fails_closed(gated_app: FastAPI) -> None:
    """A route wired without setting ``request.state.principal`` redacts everything —
    the safe direction for a mistake (§8.2)."""
    body = _client_without_principal(gated_app).get("/api/officer/probe").json()
    assert body == {}


def test_same_principal_same_redaction_regardless_of_surface(gated_app: FastAPI) -> None:
    """R2.7: the redaction depends on the principal, not on which router the request
    reached — the same non-owner gets the same body on the officer, citizen and internal
    surfaces alike."""
    client = _client_as(gated_app, _non_owner())
    bodies = [
        client.get(path).json()
        for path in ("/api/officer/probe", "/api/citizen/probe", "/internal/probe")
    ]
    assert bodies == [{"id": _RECORD_ID, "share": "0.5"}] * 3


# ---------------------------------------------------------------------------
# The citizen HTML surface: the gated dict is the template's whole context
# ---------------------------------------------------------------------------


def test_citizen_html_cannot_print_a_co_owners_name(gated_app: FastAPI) -> None:
    """The template is handed the gated dict, so for a non-owner ``owner_name`` is not in
    its context and cannot be rendered — R26.7 for the server-rendered surface."""
    response = _client_as(gated_app, _non_owner()).get("/c/probe")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert _OWNER_NAME not in response.text
    assert _FULL_IDENTIFIER not in response.text
    assert 'class="owner-name"' not in response.text
    # A PUBLIC field still renders, so this is redaction and not a blank page.
    assert 'class="share"' in response.text


def test_citizen_html_renders_the_owners_masked_identifier(gated_app: FastAPI) -> None:
    response = _client_as(gated_app, _owner()).get("/c/probe")
    assert response.status_code == 200
    assert _OWNER_NAME in response.text
    # The identifier is present only in masked form.
    assert _FULL_IDENTIFIER not in response.text
    assert _FULL_IDENTIFIER[-4:] in response.text
    assert _BULLET in response.text


def test_citizen_html_fails_closed_without_a_principal(gated_app: FastAPI) -> None:
    response = _client_without_principal(gated_app).get("/c/probe")
    assert response.status_code == 200
    assert _OWNER_NAME not in response.text
    assert _FULL_IDENTIFIER not in response.text


# ---------------------------------------------------------------------------
# _gated_item_model: unwrapping the response model the gate coerces through
# ---------------------------------------------------------------------------


def test_gated_item_model_resolves_the_carrier_model() -> None:
    from typing import List, Optional

    assert _gated_item_model(OwnershipOut) is OwnershipOut
    assert _gated_item_model(list[OwnershipOut]) is OwnershipOut
    assert _gated_item_model(List[OwnershipOut]) is OwnershipOut
    assert _gated_item_model(Optional[OwnershipOut]) is OwnershipOut


def test_gated_item_model_is_none_for_a_non_gated_response() -> None:
    """No model, or a model that is not a GatedModel, is nothing for the gate to act on —
    the route passes such a response (e.g. the citizen HTML) straight through."""
    assert _gated_item_model(None) is None
    assert _gated_item_model(dict) is None
    assert _gated_item_model(str) is None
