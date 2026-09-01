"""The route-table guard: no endpoint reaches the wire ungated (§8.3 layer 2, task 5.4).

Task 5.3 built :class:`~app.api.gated_route.GatedRoute` and wired the four §9 routers
with it; ``tests/test_gated_route.py`` proved the gate runs over HTTP. This file is the
*build-time* half of the same guarantee — §8.3's second layer, one strength above
"the routers are constructed with ``route_class=GatedRoute``". It iterates
``create_app().routes`` and asserts that every route which is not an enumerated piece of
infrastructure is a :class:`GatedRoute` whose ``response_model`` resolves to a
:class:`~app.security.gate.GatedModel`.

That single assertion is what turns R26.7 from a convention into a build error. Each
failure mode the design names becomes a red test:

* a handler returning a **bare ``dict``** has no ``response_model`` — flagged;
* a handler returning a **``JSONResponse``** likewise declares no gated model — flagged;
* a **model without visibility annotations** is a plain ``BaseModel``, not a
  ``GatedModel`` — flagged;
* an endpoint on a **router built without ``route_class=GatedRoute``** is a bare
  ``APIRoute``, not a ``GatedRoute`` — flagged.

No domain endpoint exists yet, so against the shipped app the guard passes over the
exemptions alone (``/healthz`` and the docs routes). Its value is future-facing: the day
someone adds ``GET /cases/{id}`` returning a bare dict, or mounts a router without the
gated route class, this test goes red before the endpoint ships. The exemptions are an
explicit allowlist by path rather than a broad "skip everything that isn't obviously a
data route", so a genuinely-new non-data route is a conscious one-line entry here rather
than a silent hole the guard grows on its own.

The meta-tests at the bottom prove the guard actually bites — a positive control that a
correctly-gated route is accepted, and one deliberately-broken route per failure mode —
so a later refactor that quietly defeats the check cannot pass unnoticed. This mirrors the
"guards' own tests" section of ``tests/config_integrity/test_schema_guards.py``.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.api.gated_route import GatedRoute, _gated_item_model
from app.api.routers import ALL_ROUTERS
from app.main import create_app
from app.security.gate import GatedModel, Sensitive, Visibility
from app.settings import CoreSettings

# Infrastructure routes that are, by design, not gated data endpoints. Enumerated by
# path so the guard is precise: everything *not* on this list must be a gated data route.
# ``/healthz`` returns a fixed liveness body and discloses nothing (see ``app.main``); the
# rest are FastAPI's schema and interactive-docs routes, present only outside production.
# ``/redoc`` is disabled by ``create_app`` but listed so a fresh ``FastAPI()`` (which
# enables it by default, as the meta-tests below use) needs no special-casing.
# ``/api/officer/gis/tiles/{z}/{x}/{y}.mvt`` is a binary vector-tile endpoint:
# access is still through the officer router and authentication dependency, but
# there is no JSON response model for the redaction gate to annotate.
EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/api/officer/gis/tiles/{z}/{x}/{y}.mvt",
        "/healthz",
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
    }
)


def _core() -> CoreSettings:
    """Development settings, so the app carries its docs routes and the exemption
    allowlist is actually exercised rather than being dead entries."""
    return CoreSettings.model_validate({"APP_ENV": "development", "LOG_LEVEL": "WARNING"})


def _gating_offences(app: FastAPI) -> list[str]:
    """Every route in ``app`` that should be a gated data endpoint but is not.

    A route is exempt if its path is in :data:`EXEMPT_PATHS`. Otherwise it must be an
    :class:`APIRoute` that is a :class:`GatedRoute` (so :meth:`ResponseGate.apply` runs on
    its body) and whose ``response_model`` resolves — directly, or through ``list[...]`` /
    ``Optional[...]`` — to a :class:`GatedModel`. Anything else is a way for an attribute
    to reach the wire unredacted, so it is an offence.

    Returns a list of human-readable strings, one per offence, naming the route and why it
    failed, so a red run points straight at the endpoint to fix. An empty list means every
    route is either gated or a declared exemption.
    """
    offences: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if path in EXEMPT_PATHS:
            continue
        if not isinstance(route, APIRoute):
            # A mount, a static-files route, or a bare Starlette route nobody exempted.
            # It carries no ``response_model`` the gate can act on, so it is not a place a
            # data endpoint may legitimately hide. Fail closed rather than skip it.
            offences.append(
                f"{path!r}: {type(route).__name__} is neither a gated route nor exempt"
            )
            continue
        if not isinstance(route, GatedRoute):
            offences.append(
                f"{path!r}: {type(route).__name__}, not GatedRoute "
                "(router built without route_class=GatedRoute?)"
            )
            continue
        if _gated_item_model(route.response_model) is None:
            offences.append(
                f"{path!r}: response_model {route.response_model!r} is not a GatedModel "
                "(bare dict, JSONResponse, or a model without visibility annotations?)"
            )
    return offences


# ---------------------------------------------------------------------------
# The guarantee against the shipped app
# ---------------------------------------------------------------------------


def test_every_route_is_gated() -> None:
    """R26.7, structurally: every route ``create_app`` mounts is a gated data endpoint or
    an enumerated exemption. Passes today over the exemptions alone — its job is to go red
    the moment a later task registers an ungated endpoint."""
    app = create_app(_core())
    offences = _gating_offences(app)
    assert not offences, "ungated or unexempted routes: " + "; ".join(offences)


def test_the_exempt_routes_are_actually_present() -> None:
    """Fail closed against a vacuous pass. If ``create_app`` stopped mounting ``/healthz``
    or the docs routes, the guard above would still pass — over an empty set. Asserting the
    exemptions name real routes keeps the allowlist honest: it may only excuse routes that
    exist, not quietly cover a future data endpoint that happens to share a path."""
    app = create_app(_core())
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/healthz" in paths
    assert "/openapi.json" in paths
    assert "/docs" in paths


def test_the_four_routers_declare_the_gated_route_class() -> None:
    """§8.3 layer 1, restated as an assertion: each of the four §9 consumer surfaces is a
    ``GatedRoute`` router, so an endpoint registered on any of them is gated by
    construction. A router built without ``route_class`` would let its endpoints skip the
    gate, which is exactly what :func:`_gating_offences` catches once endpoints exist."""
    assert len(ALL_ROUTERS) == 4
    for router in ALL_ROUTERS:
        assert router.route_class is GatedRoute, (
            f"router {router.prefix!r} is not built with route_class=GatedRoute"
        )


# ---------------------------------------------------------------------------
# The guard's own tests: prove it bites, one deliberately-broken route per failure mode
# ---------------------------------------------------------------------------


class _GatedOut(GatedModel):
    """A minimal correctly-annotated response model for the positive controls."""

    id: int = Sensitive(Visibility.PUBLIC)


class _UngatedOut(BaseModel):
    """A plain model with no visibility annotations — the "model without visibility
    annotations" the design says must fail the build."""

    owner_name: str


def _app_with(router: APIRouter) -> FastAPI:
    """A throwaway app carrying only ``router``. A bare ``FastAPI()`` still mounts the docs
    routes, but those are exempt, so any offence comes from ``router`` alone. The shipped
    routers in :data:`ALL_ROUTERS` are never touched, so no test pollutes another."""
    app = FastAPI()
    app.include_router(router)
    return app


def test_a_gated_route_with_a_gated_model_is_accepted() -> None:
    """Positive control: a ``GatedRoute`` carrying a ``GatedModel`` is exactly what the
    guard permits, so it must produce no offence — otherwise the guard would reject the
    real endpoints as they land."""
    router = APIRouter(prefix="/api/officer", route_class=GatedRoute)

    @router.get("/probe", response_model=_GatedOut)
    async def _probe() -> _GatedOut:
        return _GatedOut(id=1)

    assert _gating_offences(_app_with(router)) == []


def test_list_and_optional_gated_models_are_accepted() -> None:
    """``list[GatedModel]`` and ``Optional[GatedModel]`` resolve to the element model, so
    a collection or nullable response is accepted — the shapes real endpoints use."""
    router = APIRouter(route_class=GatedRoute)

    @router.get("/list", response_model=list[_GatedOut])
    async def _list() -> list[_GatedOut]:
        return [_GatedOut(id=1)]

    @router.get("/opt", response_model=Optional[_GatedOut])
    async def _opt() -> Optional[_GatedOut]:
        return _GatedOut(id=2)

    assert _gating_offences(_app_with(router)) == []


def test_an_endpoint_on_an_ungated_router_is_flagged() -> None:
    """A router built without ``route_class=GatedRoute`` produces bare ``APIRoute`` s, so
    its endpoints skip the gate. The guard must flag them even though the response model is
    a perfectly good ``GatedModel`` — being gated is about the route, not just the model."""
    router = APIRouter()  # no route_class -> plain APIRoute

    @router.get("/leak", response_model=_GatedOut)
    async def _leak() -> _GatedOut:
        return _GatedOut(id=1)

    offences = _gating_offences(_app_with(router))
    assert any("/leak" in offence and "not GatedRoute" in offence for offence in offences)


def test_an_endpoint_returning_a_bare_dict_is_flagged() -> None:
    """A handler with no ``response_model`` returning a raw dict has nothing for the gate
    to redact by field name — every key it returns reaches the wire. Flagged."""
    router = APIRouter(route_class=GatedRoute)

    @router.get("/raw")
    async def _raw() -> dict:
        return {"owner_name": "would leak"}

    offences = _gating_offences(_app_with(router))
    assert any("/raw" in offence and "not a GatedModel" in offence for offence in offences)


def test_an_endpoint_returning_a_jsonresponse_is_flagged() -> None:
    """Returning a ``JSONResponse`` bypasses ``response_model`` serialization entirely, so
    there is no gated model on the route. Flagged for the same reason as a bare dict."""
    router = APIRouter(route_class=GatedRoute)

    @router.get("/json")
    async def _json() -> JSONResponse:
        return JSONResponse({"owner_name": "would leak"})

    offences = _gating_offences(_app_with(router))
    assert any("/json" in offence and "not a GatedModel" in offence for offence in offences)


def test_a_non_gated_response_model_is_flagged() -> None:
    """A ``response_model`` that is a plain ``BaseModel`` carries no ``Sensitive``
    visibility annotations, so the gate cannot decide what to omit. The route-table test
    rejects it before it can ship an unredacted field."""
    router = APIRouter(route_class=GatedRoute)

    @router.get("/plain", response_model=_UngatedOut)
    async def _plain() -> _UngatedOut:
        return _UngatedOut(owner_name="would leak")

    offences = _gating_offences(_app_with(router))
    assert any("/plain" in offence and "not a GatedModel" in offence for offence in offences)


def test_a_non_exempt_mount_is_flagged() -> None:
    """A mount is not an ``APIRoute`` and carries no ``response_model``. One that nobody
    added to the allowlist is flagged rather than skipped, so a sub-application serving data
    cannot slip past the guard by not being an ``APIRoute`` at all."""
    app = FastAPI()
    app.mount("/files", FastAPI())

    offences = _gating_offences(app)
    assert any("/files" in offence and "neither a gated route nor exempt" in offence for offence in offences)
