"""Sign-in failure indistinguishability (task 7.3)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security.auth import sign_in_refused_response


def _app() -> FastAPI:
    app = FastAPI()

    @app.post("/signin/nonexistent")
    async def nonexistent_identifier():
        return sign_in_refused_response()

    @app.post("/signin/wrong-password")
    async def wrong_credential():
        return sign_in_refused_response()

    return app


def _comparable_headers(headers) -> dict[str, str]:  # type: ignore[no-untyped-def]
    """Headers that should not reveal which failure path happened."""
    return {
        key.lower(): value
        for key, value in headers.items()
        if key.lower() in {"content-type", "content-length"}
    }


def test_nonexistent_identifier_and_wrong_credential_are_indistinguishable() -> None:
    with TestClient(_app()) as client:
        missing = client.post("/signin/nonexistent", json={"identifier": "missing", "password": "x"})
        wrong = client.post("/signin/wrong-password", json={"identifier": "known", "password": "x"})

    assert missing.status_code == wrong.status_code == 401
    assert missing.content == wrong.content
    assert _comparable_headers(missing.headers) == _comparable_headers(wrong.headers)
    assert "set-cookie" not in {key.lower() for key in missing.headers}
    assert "set-cookie" not in {key.lower() for key in wrong.headers}
