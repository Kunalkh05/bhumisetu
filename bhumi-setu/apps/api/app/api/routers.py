"""The four consumer surfaces, each gated by construction (§8.2, §9, task 5.3).

§9 organises the API by *consumer* rather than by domain, because the authentication
mechanism and the performance budget differ by consumer, not by subsystem. Those
consumers are the four routers here:

* :data:`officer_router` — ``/api/officer/*``, the officer portal's JSON API (§9.1).
* :data:`citizen_router` — ``/api/citizen/*``, the citizen JSON API (§9.2).
* :data:`citizen_html` — ``/c/*``, the server-rendered citizen surface (§9.2, §10).
* :data:`internal_router` — ``/internal/*``, service-to-service calls (§9.3).

Every one is constructed with ``route_class=GatedRoute``. That single argument is what
makes R26.7 hold uniformly: an endpoint registered on any of these routers has its
response passed through the redaction gate whether or not its author thought about
redaction, and a new router added without it fails the route-table test of task 5.4.
The routers carry no endpoints yet — the domain tasks that follow register on them —
so including an empty router adds nothing to the application until then. What this task
fixes is the *shape*: the prefixes, and that the gate is not optional.

:data:`ALL_ROUTERS` is the tuple :func:`app.main.create_app` iterates to wire them, so
adding a fifth surface is a one-line change in one place rather than a second list to
keep in sync.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.gated_route import GatedRoute

__all__ = [
    "ALL_ROUTERS",
    "citizen_html",
    "citizen_router",
    "internal_router",
    "officer_router",
]

#: Officer portal JSON API (§9.1). Opaque session cookie plus CSRF on mutations,
#: resolved to a :class:`~app.security.access.Principal` by ``authenticate``.
officer_router = APIRouter(prefix="/api/officer", route_class=GatedRoute)

#: Citizen JSON API (§9.2). Single-case citizen session; the gate omits every other
#: owner's personal data by field visibility rather than by a handler remembering to.
citizen_router = APIRouter(prefix="/api/citizen", route_class=GatedRoute)

#: Server-rendered citizen surface (§9.2, §10). Its endpoints return HTML rendered from
#: the gated dict (:func:`app.citizen.templating.render_gated`), so a template cannot
#: print a co-owner's ``owner_name`` — the key is absent from its context.
citizen_html = APIRouter(prefix="/c", route_class=GatedRoute)

#: Internal service-to-service surface (§9.3). Bearer service token, no jurisdiction
#: scope; still gated, so a service sees only ``PUBLIC`` and permitted fields.
internal_router = APIRouter(prefix="/internal", route_class=GatedRoute)

#: The routers ``create_app`` includes. One place to register a surface.
ALL_ROUTERS: tuple[APIRouter, ...] = (
    officer_router,
    citizen_router,
    citizen_html,
    internal_router,
)

# Import endpoint modules after the routers exist; decorators register onto the
# router instances above, while create_app imports only ALL_ROUTERS.
from app.api import cases  # noqa: E402,F401
from app.api import documents  # noqa: E402,F401
from app.api import gis  # noqa: E402,F401
from app.api import i18n  # noqa: E402,F401
from app.api import intervention  # noqa: E402,F401
from app.api import issues  # noqa: E402,F401
from app.api import notices  # noqa: E402,F401
from app.api import parcels  # noqa: E402,F401
from app.api import predictions  # noqa: E402,F401
from app.citizen import routes  # noqa: E402,F401
