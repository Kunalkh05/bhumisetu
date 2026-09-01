"""Opaque officer sessions in Redis (task 7.1).

Officer sessions are not JWTs. A session token is 256 bits of randomness stored as
an opaque key in Redis; revocation is ``DEL`` and a role/scope change applies on the
next request because the session stores only the officer id. Authorization-bearing
state is still resolved by :mod:`app.security.access` on every request.
"""

from __future__ import annotations

import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.db.event_log import Actor, EventLog
from app.security.access import (
    CITIZEN_SESSION_COOKIE,
    OFFICER_SESSION_COOKIE,
    AuthBackend,
    CitizenSession,
    OfficerSession,
    ServiceIdentity,
)

__all__ = [
    "CSRF_COOKIE",
    "CSRF_HEADER",
    "CITIZEN_SESSION_SECONDS",
    "CitizenSessionBundle",
    "OFFICER_SESSION_SECONDS",
    "OfficerAuthService",
    "OfficerSessionBundle",
    "RedisOfficerSessionBackend",
    "set_citizen_session_cookie",
    "csrf_matches",
    "new_opaque_token",
    "sign_in_refused_response",
    "set_officer_session_cookies",
]

OFFICER_SESSION_SECONDS = 60 * 60
CITIZEN_SESSION_SECONDS = 15 * 60
CSRF_COOKIE = "bhumisetu_csrf"
CSRF_HEADER = "x-csrf-token"
SIGN_IN_REFUSED_BODY = {"code": "SIGN_IN_REFUSED", "message": "Invalid credentials", "details": {}}


class RedisLike(Protocol):
    """The Redis operations this module needs, kept narrow for tests and adapters."""

    def setex(self, name: str, time: int, value: str) -> object:
        ...

    def get(self, name: str) -> bytes | str | None:
        ...

    def expire(self, name: str, time: int) -> object:
        ...

    def delete(self, name: str) -> object:
        ...


@dataclass(frozen=True)
class OfficerSessionBundle:
    """The tokens returned to the client when an officer signs in."""

    session_token: str
    csrf_token: str
    officer_id: uuid.UUID


@dataclass(frozen=True)
class CitizenSessionBundle:
    """The opaque token returned after a citizen passcode verifies."""

    session_token: str
    subject_id: str
    case_id: int
    owner_record_ids: tuple[int, ...]


@dataclass(frozen=True)
class _SystemActor:
    kind: str = "SYSTEM"
    id: str = "auth-service"


class _AuthEventEntity:
    def __init__(self, officer_id: uuid.UUID | None = None) -> None:
        self.__tablename__ = "auth_session"
        self.id = 0
        self.officer_id = str(officer_id) if officer_id is not None else None


def new_opaque_token() -> str:
    """Return a URL-safe token carrying 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def _key(token: str) -> str:
    return f"officer:session:{token}"


def _citizen_key(token: str) -> str:
    return f"citizen:session:{token}"


def _encode(officer_id: uuid.UUID, csrf_token: str) -> str:
    return json.dumps({"officer_id": str(officer_id), "csrf_token": csrf_token})


def _encode_citizen(subject_id: str, case_id: int, owner_record_ids: tuple[int, ...]) -> str:
    return json.dumps(
        {
            "subject_id": subject_id,
            "case_id": case_id,
            "owner_record_ids": list(owner_record_ids),
        }
    )


def _decode(raw: bytes | str) -> tuple[uuid.UUID, str] | None:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        data = json.loads(raw)
        return uuid.UUID(data["officer_id"]), str(data["csrf_token"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _decode_citizen(raw: bytes | str) -> CitizenSession | None:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        data = json.loads(raw)
        owner_record_ids = tuple(int(value) for value in data["owner_record_ids"])
        return CitizenSession(
            subject_id=str(data["subject_id"]),
            case_id=int(data["case_id"]),
            owner_record_ids=owner_record_ids,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


class RedisOfficerSessionBackend(AuthBackend):
    """AuthBackend implementation for opaque officer sessions."""

    def __init__(self, redis: RedisLike) -> None:
        self._redis = redis

    def create_officer_session(self, officer_id: uuid.UUID) -> OfficerSessionBundle:
        session_token = new_opaque_token()
        csrf_token = new_opaque_token()
        self._redis.setex(
            _key(session_token),
            OFFICER_SESSION_SECONDS,
            _encode(officer_id, csrf_token),
        )
        return OfficerSessionBundle(session_token, csrf_token, officer_id)

    def officer_session(self, token: str) -> OfficerSession | None:
        raw = self._redis.get(_key(token))
        if raw is None:
            return None
        decoded = _decode(raw)
        if decoded is None:
            self._redis.delete(_key(token))
            return None
        officer_id, _csrf = decoded
        self._redis.expire(_key(token), OFFICER_SESSION_SECONDS)
        return OfficerSession(officer_id=officer_id)

    def csrf_token(self, token: str) -> str | None:
        raw = self._redis.get(_key(token))
        if raw is None:
            return None
        decoded = _decode(raw)
        if decoded is None:
            return None
        _officer_id, csrf = decoded
        return csrf

    def invalidate_officer_session(self, token: str) -> None:
        self._redis.delete(_key(token))

    def create_citizen_session(
        self, *, subject_id: str, case_id: int, owner_record_ids: tuple[int, ...]
    ) -> CitizenSessionBundle:
        session_token = new_opaque_token()
        self._redis.setex(
            _citizen_key(session_token),
            CITIZEN_SESSION_SECONDS,
            _encode_citizen(subject_id, case_id, owner_record_ids),
        )
        return CitizenSessionBundle(
            session_token=session_token,
            subject_id=subject_id,
            case_id=case_id,
            owner_record_ids=owner_record_ids,
        )

    def citizen_session(self, token: str) -> CitizenSession | None:
        raw = self._redis.get(_citizen_key(token))
        if raw is None:
            return None
        decoded = _decode_citizen(raw)
        if decoded is None:
            self._redis.delete(_citizen_key(token))
            return None
        return decoded

    def service_identity(self, token: str) -> ServiceIdentity | None:
        return None


def set_officer_session_cookies(
    response: Response, bundle: OfficerSessionBundle
) -> None:
    """Attach the secure session and CSRF cookies to a sign-in response."""
    response.set_cookie(
        OFFICER_SESSION_COOKIE,
        bundle.session_token,
        max_age=OFFICER_SESSION_SECONDS,
        httponly=True,
        secure=True,
        samesite="strict",
    )
    response.set_cookie(
        CSRF_COOKIE,
        bundle.csrf_token,
        max_age=OFFICER_SESSION_SECONDS,
        httponly=False,
        secure=True,
        samesite="strict",
    )


def set_citizen_session_cookie(response: Response, bundle: CitizenSessionBundle) -> None:
    """Attach the absolute-expiry citizen session cookie."""
    response.set_cookie(
        CITIZEN_SESSION_COOKIE,
        bundle.session_token,
        max_age=CITIZEN_SESSION_SECONDS,
        httponly=True,
        secure=True,
        samesite="strict",
    )


def sign_in_refused_response() -> JSONResponse:
    """The indistinguishable failed-sign-in response (R1.2, task 7.3)."""
    return JSONResponse(status_code=401, content=SIGN_IN_REFUSED_BODY)


def csrf_matches(request: Request, backend: RedisOfficerSessionBackend) -> bool:
    """Double-submit CSRF check for officer mutations."""
    session_token = request.cookies.get(OFFICER_SESSION_COOKIE)
    header_token = request.headers.get(CSRF_HEADER)
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if not session_token or not header_token or not cookie_token:
        return False
    stored = backend.csrf_token(session_token)
    return (
        stored is not None
        and secrets.compare_digest(stored, header_token)
        and secrets.compare_digest(stored, cookie_token)
    )


class OfficerAuthService:
    """Issue/revoke officer sessions and record sign-in audit events."""

    def __init__(self, backend: RedisOfficerSessionBackend) -> None:
        self._backend = backend

    def sign_in(
        self,
        session,
        *,
        officer_id: uuid.UUID,
        credentials_valid: bool,
        actor: Actor | None = None,
        occurrence_time: datetime | None = None,
    ) -> OfficerSessionBundle | None:
        occurred = occurrence_time or datetime.now(timezone.utc)
        if not credentials_valid:
            EventLog.append(
                session,
                event_type="OFFICER_SIGNIN_FAILED",
                entity=_AuthEventEntity(officer_id),
                actor=actor or _SystemActor(),
                changes={"officer_id": (None, str(officer_id))},
                occurrence_time=occurred,
            )
            return None

        bundle = self._backend.create_officer_session(officer_id)
        EventLog.append(
            session,
            event_type="OFFICER_SIGNED_IN",
            entity=_AuthEventEntity(officer_id),
            actor=actor or _SystemActor(),
            changes={"officer_id": (None, str(officer_id))},
            occurrence_time=occurred,
        )
        return bundle

    def sign_out(self, token: str) -> None:
        self._backend.invalidate_officer_session(token)
