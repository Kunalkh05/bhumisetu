"""Render the citizen surface from the *gated* payload (§8.2, §10, task 5.3).

The strongest guarantee in R26.7 is not that a template avoids printing a co-owner's
name — it is that the template *cannot*, because the name is not in the data it was
given. This module is where that guarantee is made real for the server-rendered
citizen surface: :func:`render_gated` runs :meth:`ResponseGate.apply` first and hands
the template the redacted dict, so ``owner_name`` for a record the citizen does not own
is simply an absent key, and a masked ``government_identifier`` (R26.5) arrives already
masked. There is no unredacted model in scope for a template to reach into.

This is why the citizen HTML routes need no help from :class:`~app.api.gated_route.GatedRoute`
to be safe: by the time the route class sees the response it is already an
:class:`~starlette.responses.HTMLResponse`, and the redaction happened here, before a
single field was written into markup. Gating after rendering would be too late — the
value would already be in the HTML string. Gating before, by omission from the context,
is the only point at which it works.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.templating import _TemplateResponse

from app.security.access import Principal
from app.security.gate import GatedModel, ResponseGate

__all__ = ["CITIZEN_TEMPLATES_DIR", "citizen_templates", "render_gated"]

#: Where the citizen templates live. Colocated with the package so the surface —
#: templates, static service worker (§10.2), and the endpoints that use them — sits
#: together under ``app/citizen/``.
CITIZEN_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

#: The one Jinja2 environment for the citizen surface. Autoescaping is on (the
#: :class:`Jinja2Templates` default), so even a value that survives redaction is
#: HTML-escaped rather than injected as markup.
citizen_templates = Jinja2Templates(directory=str(CITIZEN_TEMPLATES_DIR))


def render_gated(
    request: Request,
    name: str,
    model: GatedModel | list[GatedModel] | None,
    principal: Principal | None,
    *,
    templates: Jinja2Templates = citizen_templates,
    status_code: int = 200,
    **extra: Any,
) -> _TemplateResponse:
    """Render template ``name`` from ``model`` redacted for ``principal``.

    The redaction is :meth:`ResponseGate.apply` with no ``response_model`` argument,
    because ``model`` is already a :class:`GatedModel` instance (or a list of them):
    the gate walks its fields and returns a dict with the ones ``principal`` may not
    see omitted and any masked ones masked. That dict becomes the template context, so
    the template's whole universe of data is the gated view — it can render nothing it
    was not handed.

    A single model spreads its fields into the context as top-level names; a list is
    placed under ``items``. Additional context (page number, selected language, a
    stale-cache marker) is passed as keyword arguments; a model field of the same name
    wins, so ``extra`` cannot reintroduce a redacted attribute.

    :param request: the incoming request (Jinja2 needs it in context for ``url_for``).
    :param name: the template file name within the citizen templates directory.
    :param model: the gated model, list of gated models, or ``None`` to redact.
    :param principal: the requesting principal; ``None`` redacts everything (§8.2).
    :param templates: the Jinja2 environment, overridable for testing.
    :param status_code: the HTTP status of the rendered response.
    :param extra: additional, non-sensitive context values.
    :returns: an HTML template response over the gated context.
    """
    gated = ResponseGate.apply(model, principal)
    if isinstance(gated, dict):
        context: dict[str, Any] = {**extra, **gated}
    elif isinstance(gated, list):
        context = {**extra, "items": gated}
    else:
        context = {**extra, "value": gated}
    return templates.TemplateResponse(request, name, context, status_code=status_code)
