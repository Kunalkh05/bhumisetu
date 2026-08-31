"""Officer opaque sessions (task 7.1)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import Response

from app.security.access import OFFICER_SESSION_COOKIE, OfficerSession
from app.security.auth import (
    CSRF_COOKIE,
    CSRF_HEADER,
    OFFICER_SESSION_SECONDS,
    OfficerAuthService,
    RedisOfficerSessionBackend,
    csrf_matches,
    new_opaque_token,
    set_officer_session_cookies,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.expire_calls: list[tuple[str, int]] = []

    def setex(self, name: str, time: int, value: str) -> None:
        self.values[name] = value
        self.ttls[name] = time

    def get(self, name: str):
        return self.values.get(name)

    def expire(self, name: str, time: int) -> None:
        if name in self.values:
            self.ttls[name] = time
            self.expire_calls.append((name, time))

    def delete(self, name: str) -> None:
        self.values.pop(name, None)
        self.ttls.pop(name, None)


@dataclass
class RecordedEvent:
    event_type: str
    actor_id: str
    payload: dict


class FakeSession:
    def __init__(self) -> None:
        self.events: list[RecordedEvent] = []


def _request(cookies: dict[str, str] | None = None, headers: dict[str, str] | None = None) -> Request:
    raw: list[tuple[bytes, bytes]] = []
    if cookies:
        raw.append((b"cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()).encode()))
    for key, value in (headers or {}).items():
        raw.append((key.encode(), value.encode()))
    return Request({"type": "http", "method": "POST", "path": "/", "headers": raw})


def test_new_opaque_token_has_256_bits_of_entropy_shape() -> None:
    token = new_opaque_token()
    assert len(token) >= 43
    assert token != new_opaque_token()


def test_create_officer_session_stores_only_identity_and_csrf_with_sliding_ttl() -> None:
    redis = FakeRedis()
    backend = RedisOfficerSessionBackend(redis)
    officer_id = uuid.uuid4()

    bundle = backend.create_officer_session(officer_id)

    key = f"officer:session:{bundle.session_token}"
    assert redis.ttls[key] == OFFICER_SESSION_SECONDS
    assert str(officer_id) in redis.values[key]
    assert "permissions" not in redis.values[key]
    assert "scope" not in redis.values[key]

    assert backend.officer_session(bundle.session_token) == OfficerSession(officer_id)
    assert redis.expire_calls == [(key, OFFICER_SESSION_SECONDS)]


def test_invalidated_session_no_longer_resolves() -> None:
    redis = FakeRedis()
    backend = RedisOfficerSessionBackend(redis)
    bundle = backend.create_officer_session(uuid.uuid4())

    backend.invalidate_officer_session(bundle.session_token)

    assert backend.officer_session(bundle.session_token) is None


def test_corrupt_session_is_deleted_and_refused() -> None:
    redis = FakeRedis()
    backend = RedisOfficerSessionBackend(redis)
    redis.setex("officer:session:bad", OFFICER_SESSION_SECONDS, "{not-json")

    assert backend.officer_session("bad") is None
    assert "officer:session:bad" not in redis.values


def test_set_officer_session_cookies_uses_secure_http_only_session_cookie() -> None:
    bundle = RedisOfficerSessionBackend(FakeRedis()).create_officer_session(uuid.uuid4())
    response = Response()

    set_officer_session_cookies(response, bundle)

    headers = response.raw_headers
    cookie_lines = [value.decode("latin-1") for name, value in headers if name == b"set-cookie"]
    session_cookie = next(line for line in cookie_lines if line.startswith(OFFICER_SESSION_COOKIE))
    csrf_cookie = next(line for line in cookie_lines if line.startswith(CSRF_COOKIE))
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=strict" in session_cookie
    assert "Max-Age=3600" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "Secure" in csrf_cookie
    assert "SameSite=strict" in csrf_cookie


def test_csrf_double_submit_must_match_stored_cookie_and_header() -> None:
    backend = RedisOfficerSessionBackend(FakeRedis())
    bundle = backend.create_officer_session(uuid.uuid4())

    good = _request(
        cookies={
            OFFICER_SESSION_COOKIE: bundle.session_token,
            CSRF_COOKIE: bundle.csrf_token,
        },
        headers={CSRF_HEADER: bundle.csrf_token},
    )
    assert csrf_matches(good, backend)

    missing_header = _request(
        cookies={
            OFFICER_SESSION_COOKIE: bundle.session_token,
            CSRF_COOKIE: bundle.csrf_token,
        }
    )
    assert not csrf_matches(missing_header, backend)

    wrong = _request(
        cookies={OFFICER_SESSION_COOKIE: bundle.session_token, CSRF_COOKIE: "wrong"},
        headers={CSRF_HEADER: bundle.csrf_token},
    )
    assert not csrf_matches(wrong, backend)


def test_sign_in_records_success_event_and_issues_session(monkeypatch) -> None:
    backend = RedisOfficerSessionBackend(FakeRedis())
    service = OfficerAuthService(backend)
    session = FakeSession()
    officer_id = uuid.uuid4()
    occurred = datetime(2024, 7, 1, tzinfo=timezone.utc)

    def _append(session_arg, *, event_type, entity, actor, changes, occurrence_time, **kw):  # type: ignore[no-untyped-def]
        assert session_arg is session
        assert entity.__tablename__ == "auth_session"
        assert occurrence_time == occurred
        session.events.append(
            RecordedEvent(
                event_type,
                actor.id,
                {name: {"from": old, "to": new} for name, (old, new) in changes.items()},
            )
        )

    monkeypatch.setattr("app.security.auth.EventLog.append", _append)

    bundle = service.sign_in(
        session,
        officer_id=officer_id,
        credentials_valid=True,
        occurrence_time=occurred,
    )

    assert bundle is not None
    assert backend.officer_session(bundle.session_token) == OfficerSession(officer_id)
    assert session.events == [
        RecordedEvent(
            "OFFICER_SIGNED_IN",
            "auth-service",
            {"officer_id": {"from": None, "to": str(officer_id)}},
        )
    ]


def test_failed_sign_in_records_failure_and_issues_no_session(monkeypatch) -> None:
    backend = RedisOfficerSessionBackend(FakeRedis())
    service = OfficerAuthService(backend)
    session = FakeSession()
    officer_id = uuid.uuid4()

    def _append(session_arg, *, event_type, entity, actor, changes, occurrence_time, **kw):  # type: ignore[no-untyped-def]
        session.events.append(RecordedEvent(event_type, actor.id, {}))

    monkeypatch.setattr("app.security.auth.EventLog.append", _append)

    bundle = service.sign_in(
        session,
        officer_id=officer_id,
        credentials_valid=False,
    )

    assert bundle is None
    assert session.events == [RecordedEvent("OFFICER_SIGNIN_FAILED", "auth-service", {})]
