"""The route class that makes redaction structural, not optional (§8.2, task 5.3).

:mod:`app.security.gate` decides *which attributes* of a response a principal may
see; this module makes that decision happen on *every* response without an endpoint
author having to remember. :class:`GatedRoute` is a FastAPI :class:`APIRoute`
subclass, and the four routers in :mod:`app.api.routers` are built with
``route_class=GatedRoute``. The consequence R26.7 leans on: an endpoint registered on
one of those routers has its body passed through :meth:`ResponseGate.apply` whether or
not the author thought about redaction. There is no "gate this response" call for an
author to forget, because the gate is the route.

Where the gate runs, and why it reads the serialized body
---------------------------------------------------------

FastAPI's :meth:`APIRoute.get_route_handler` returns a handler that already does the
whole of request → endpoint → ``response_model`` serialization → :class:`Response`.
By the time control returns to us the handler's model instance is gone and what we
hold is a :class:`~starlette.responses.JSONResponse` whose ``body`` is the fully
serialized JSON — every field present, nothing redacted yet, because redaction is
*our* job and has not happened. So :meth:`GatedRoute.get_route_handler` wraps that
handler, decodes the JSON body, and hands it to :meth:`ResponseGate.apply` together
with the request's principal and the route's declared ``response_model``. The gate's
dict-coercion path (it validates a bare ``dict`` back through the declared
:class:`~app.security.gate.GatedModel`) is exactly what this needs — the designers of
§8.2 anticipated the gate receiving a dict, and this is where that dict comes from.
Pydantic serializes a ``Decimal`` to a JSON *string*, so decoding the body loses no
numeric precision; the round trip through the model is faithful.

What is *not* gated, and why that is correct
--------------------------------------------

* **A response with no gated ``response_model``.** The citizen HTML surface returns an
  :class:`~starlette.responses.HTMLResponse` (its ``response_model`` is ``None``): its
  redaction already happened *before* rendering, because the Jinja2 template was handed
  the gated dict, not the model (see :func:`app.citizen.templating.render_gated`). Once
  the sensitive value is baked into an HTML string there is nothing to omit by field
  name, which is precisely why the gate must run first for HTML. So a non-JSON response,
  or one with no gated response model, is passed straight through — trying to "gate" it
  would be too late to help and could only corrupt it.
* **An empty body** (a ``204``, say) has nothing to redact and is returned unchanged.

The principal is read as ``request.state.principal``, where
:func:`app.security.access.authenticate` puts it. If it is absent — a route wired
without the authentication dependency — the gate is handed ``None`` and, per §8.2,
fails closed: every field is excluded and the body is empty. A missing identity
withholds everything rather than guessing generously.

Why the item model is unwrapped
-------------------------------

A route may declare ``list[OwnershipOut]`` (or ``Optional[...]``) rather than a bare
model. :meth:`ResponseGate.apply` gates each element of a list, but only coerces a
``dict`` when handed the element's model. So :func:`_gated_item_model` unwraps the
generic to the underlying :class:`GatedModel` subclass, and the gate is given that —
one model for both the single-object and the list-of-objects shapes.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Coroutine, get_args

from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response

from app.security.gate import GatedModel, ResponseGate

__all__ = ["GatedRoute"]

#: Response headers the re-serialized response must own itself: the body changed, so
#: the length changed, and the content type is fixed by :class:`JSONResponse`. Any
#: other header the handler set (a cache directive, a cookie) is carried across.
_MANAGED_HEADERS: frozenset[str] = frozenset({"content-length", "content-type"})


def _gated_item_model(response_model: Any) -> type[GatedModel] | None:
    """Resolve the :class:`GatedModel` the response is built from, or ``None``.

    Returns the model itself for a bare ``GatedModel`` subclass, and unwraps one level
    of generics (``list[X]``, ``Optional[X]``, ``X | None``) to find it — so both a
    single-object and a list-of-objects response yield the element model the gate
    coerces a decoded ``dict`` through. Returns ``None`` for a response the gate cannot
    act on (no model, or a model that is not a ``GatedModel``), which the caller treats
    as "pass through unchanged".
    """
    if response_model is None:
        return None
    if isinstance(response_model, type) and issubclass(response_model, GatedModel):
        return response_model
    for argument in get_args(response_model):
        found = _gated_item_model(argument)
        if found is not None:
            return found
    return None


def _reserialise(original: JSONResponse, body: Any) -> JSONResponse:
    """Rebuild a :class:`JSONResponse` around the gated ``body``.

    Preserves the status code, background task, and every header the handler set
    except the two that the new body invalidates: ``content-length`` (the body is
    smaller after redaction) and ``content-type`` (owned by :class:`JSONResponse`).
    ``append`` rather than ``setdefault`` so a handler that set several values of one
    header — multiple ``Set-Cookie`` lines, say — keeps all of them.
    """
    rebuilt = JSONResponse(
        content=body,
        status_code=original.status_code,
        background=original.background,
    )
    for name, value in original.headers.items():
        if name.lower() in _MANAGED_HEADERS:
            continue
        rebuilt.headers.append(name, value)
    return rebuilt


class GatedRoute(APIRoute):
    """An :class:`APIRoute` that redacts its response body for the request's principal.

    Constructing a router with ``route_class=GatedRoute`` makes every endpoint on it
    gated by construction (§8.3, layer 1): the author cannot forget to redact because
    there is no redaction call to write. The route-table test of task 5.4 turns that
    construction guarantee into a build-time one — a router created without this class,
    or an endpoint whose ``response_model`` is not a :class:`GatedModel`, fails there.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        inner = super().get_route_handler()
        # response_model is set on the route before this runs, so the item model is
        # resolved once at wiring time rather than on every request.
        item_model = _gated_item_model(self.response_model)

        async def gated(request: Request) -> Response:
            response = await inner(request)

            # Only a JSON body backed by a gated model is ours to redact. HTML (gated
            # before rendering), a bodyless response, or a route with no gated model is
            # passed through: gating it here would be too late or meaningless.
            if item_model is None or not isinstance(response, JSONResponse):
                return response
            if not response.body:
                return response

            principal = getattr(request.state, "principal", None)
            payload = json.loads(response.body)
            gated_body = ResponseGate.apply(payload, principal, item_model)
            return _reserialise(response, gated_body)

        return gated
