"""The concurrency-control request contract: ``expected_version`` and ``If-Match``.

R29.2 requires a modification request to *present* the version the officer observed
when the entity was opened, and R29.10 requires that contract to hold for every
mutating route regardless of origin. :class:`~app.db.versioned_repository.VersionedRepository`
enforces the check; this module is the other half — how a route *receives* the
presented version — and task 4.5 turns "every mutating route uses one of these" into
a build-time check over ``app.routes``.

There are two idioms, and a route may use either:

* **A body field.** A JSON write body inherits :class:`VersionedWrite`, so it carries
  ``expected_version``. This suits a form-style ``PATCH``/``PUT`` where the version
  rides with the fields being changed.
* **An ``If-Match`` header.** A route depends on :data:`IfMatchVersion`, and the
  version arrives as the request's ``If-Match`` entity-tag. This suits the officer
  portal's data layer, which captures ``entity_version`` on read and replays it as
  ``If-Match`` on the mutation (§8's front-end note), so R29.2 is satisfied by the
  data layer rather than by every form remembering to echo a field.

Either way the handler ends up with an ``int`` it hands to
``VersionedRepository.update(expected_version=...)``. This module deliberately holds
no domain logic and imports nothing from ``app/db`` — it only shapes the request; the
version check itself is the repository's.

Why an int, and why malformed is a 422
---------------------------------------

An entity version is an integer that starts at 1 and only increases
(``app/db/versioned.py``), so the presented version is an ``int`` and a value below 1
was never issued — :class:`VersionedWrite` constrains it ``>= 1`` so a client bug is
a validation error rather than a guaranteed-to-lose conflict. The ``If-Match`` header
carries the same integer as an entity-tag; :func:`if_match_version` accepts it bare
(``5``), quoted (``"5"``), or with the weak prefix (``W/"5"``) and parses the integer
out. A missing or unparseable ``If-Match`` is a malformed request, raised as a 422
that ``app.main``'s handler renders as the ``VALIDATION_FAILED`` envelope — the same
shape every other request-shape failure takes, so a client parses one thing.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field

__all__ = [
    "EXPECTED_VERSION_DESCRIPTION",
    "IfMatchVersion",
    "VersionedWrite",
    "if_match_version",
]

#: Shared description for the presented version, so the body field and the header
#: dependency document the same contract in the OpenAPI schema.
EXPECTED_VERSION_DESCRIPTION = (
    "The entity_version observed when the entity was opened (R29.2). The modification "
    "commits only if the entity is still at this version; otherwise it is rejected "
    "with a 409 ENTITY_VERSION_CONFLICT describing the divergence."
)


class VersionedWrite(BaseModel):
    """Base for any request body that modifies a versioned entity (R29.2).

    A write body inherits this to carry ``expected_version`` alongside its fields::

        class CaseStageTransition(VersionedWrite):
            new_stage: str

    The handler passes ``body.expected_version`` to
    ``VersionedRepository.update(expected_version=...)``. Constrained ``>= 1`` because
    version 1 is the lowest an entity is ever at, so a lower value is malformed rather
    than merely stale.
    """

    expected_version: int = Field(..., ge=1, description=EXPECTED_VERSION_DESCRIPTION)


def _parse_entity_tag(raw: str) -> int | None:
    """Parse an ``If-Match`` entity-tag to the integer version it carries.

    Accepts the version bare (``5``), strongly quoted (``"5"``), or with the weak
    validator prefix (``W/"5"``) — the shapes a client or proxy may produce for what
    is, to us, an integer entity-tag. Returns ``None`` for anything that is not an
    integer once unwrapped, including ``*`` (which asserts "any version" and so
    carries none), so the caller can turn that into a clear 422.
    """
    token = raw.strip()
    if token.startswith("W/"):
        token = token[2:].strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        token = token[1:-1]
    try:
        return int(token)
    except ValueError:
        return None


def if_match_version(
    if_match: Annotated[
        str,
        Header(
            alias="If-Match",
            description=EXPECTED_VERSION_DESCRIPTION,
        ),
    ],
) -> int:
    """FastAPI dependency: the presented version from the ``If-Match`` header (R29.2).

    A required header — a mutating route that uses this idiom must be told which
    version the caller believes it is modifying, so an absent ``If-Match`` is a
    validation error (FastAPI raises it before this runs). A present but unparseable
    value is refused here as a 422, rendered by ``app.main`` as ``VALIDATION_FAILED``.

    :returns: the integer entity version to pass to
        ``VersionedRepository.update(expected_version=...)``.
    :raises HTTPException: 422 if ``If-Match`` is present but not an integer entity-tag.
    """
    version = _parse_entity_tag(if_match)
    if version is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "If-Match must be an integer entity version (optionally quoted), the "
                "entity_version observed when the entity was opened (R29.2)."
            ),
        )
    return version


#: Annotated dependency a route uses to receive the presented version from ``If-Match``::
#:
#:     @officer_router.patch("/cases/{case_id}/stage")
#:     async def transition(case_id: int, expected_version: IfMatchVersion) -> ...:
#:         ...
#:
#: Declaring this on a route is one of the two ways task 4.5 accepts a mutating route
#: as satisfying R29.10; the other is a :class:`VersionedWrite` body field.
IfMatchVersion = Annotated[int, Depends(if_match_version)]
