"""The concurrency-control request contract: ``expected_version`` and ``If-Match``.

Task 4.3's request-plumbing half (the description half is in
``tests/db/test_conflict_description.py``). R29.2 requires a modification request to
present the version the officer observed; this module offers the two idioms a route
uses to receive it — a :class:`VersionedWrite` body field or the ``If-Match`` header
dependency — and task 4.5 will assert every mutating route uses one of them. These
tests pin the parsing and validation of both, and confirm the header dependency
integrates through a real route: a good tag yields the version, a malformed one
leaves as the §9.4 ``VALIDATION_FAILED`` envelope.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.api.versioning import IfMatchVersion, VersionedWrite, if_match_version


# ===========================================================================
# The If-Match header dependency (R29.2)
# ===========================================================================


class TestIfMatchParsing:
    @pytest.mark.parametrize(
        "header",
        ["5", '"5"', "W/\"5\"", "  5  ", '"  5  "'],
        ids=["bare", "quoted", "weak-quoted", "padded-bare", "padded-quoted"],
    )
    def test_it_parses_the_integer_version_out_of_an_entity_tag(self, header: str) -> None:
        """Bare, strongly quoted and weak-prefixed tags all carry the same integer
        version; surrounding whitespace is tolerated."""
        assert if_match_version(header) == 5

    @pytest.mark.parametrize(
        "header",
        ["", "abc", '"abc"', "*", "5.0", "v5"],
        ids=["empty", "word", "quoted-word", "any", "decimal", "prefixed"],
    )
    def test_a_value_that_is_not_an_integer_version_is_a_422(self, header: str) -> None:
        """A present but unparseable If-Match is a malformed request, not a stale one:
        a 422 the envelope renders as VALIDATION_FAILED, never a silent fallback."""
        with pytest.raises(HTTPException) as caught:
            if_match_version(header)
        assert caught.value.status_code == 422


# ===========================================================================
# The VersionedWrite body field (R29.2)
# ===========================================================================


class _StageTransition(VersionedWrite):
    """A representative write body inheriting the presented version."""

    new_stage: str


class TestVersionedWrite:
    def test_a_body_carries_the_presented_version_alongside_its_fields(self) -> None:
        body = _StageTransition(expected_version=8, new_stage="AWARD")
        assert body.expected_version == 8
        assert body.new_stage == "AWARD"

    def test_the_version_is_required(self) -> None:
        with pytest.raises(ValidationError):
            _StageTransition(new_stage="AWARD")  # type: ignore[call-arg]

    @pytest.mark.parametrize("bad_version", [0, -1])
    def test_a_version_below_one_is_rejected_as_malformed(self, bad_version: int) -> None:
        """Version 1 is the lowest an entity is ever at, so a lower value was never
        issued — a validation error rather than a conflict guaranteed to lose."""
        with pytest.raises(ValidationError):
            _StageTransition(expected_version=bad_version, new_stage="AWARD")


# ===========================================================================
# The dependency on a real route
# ===========================================================================


def _app_with_if_match_route() -> FastAPI:
    app = FastAPI()

    @app.exception_handler(HTTPException)
    async def _http_exc(request, exc):  # type: ignore[no-untyped-def]
        # Mirror app.main's envelope so the malformed-header path is asserted in the
        # shape a client actually receives, without importing the whole application.
        from fastapi.responses import JSONResponse

        code = "VALIDATION_FAILED" if exc.status_code == 422 else f"HTTP_{exc.status_code}"
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": str(exc.detail), "details": {}},
        )

    @app.patch("/thing")
    async def modify(expected_version: IfMatchVersion) -> dict[str, int]:
        return {"expected_version": expected_version}

    return app


class TestIfMatchOnARoute:
    def test_a_valid_tag_reaches_the_handler_as_an_int(self) -> None:
        with TestClient(_app_with_if_match_route()) as client:
            response = client.patch("/thing", headers={"If-Match": '"12"'})
        assert response.status_code == 200
        assert response.json() == {"expected_version": 12}

    def test_a_missing_tag_is_a_validation_error(self) -> None:
        """A required header: a route using this idiom must be told the version."""
        with TestClient(_app_with_if_match_route()) as client:
            response = client.patch("/thing")
        assert response.status_code == 422

    def test_a_malformed_tag_leaves_as_the_validation_failed_envelope(self) -> None:
        with TestClient(_app_with_if_match_route()) as client:
            response = client.patch("/thing", headers={"If-Match": "not-a-version"})
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_FAILED"
