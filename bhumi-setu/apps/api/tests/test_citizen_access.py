"""Citizen passcode issue, verification and sessions (tasks 7.4-7.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from time import perf_counter

from app.security.access import CITIZEN_SESSION_COOKIE, CitizenSession
from app.security.auth import (
    CITIZEN_SESSION_SECONDS,
    RedisOfficerSessionBackend,
    set_citizen_session_cookie,
)
from app.security.rate_limit import RedisRateLimiter
from app.services import citizen_access
from app.services.citizen_access import (
    CITIZEN_ACCESS_ACCEPTED_BODY,
    PASSCODE_DIGITS,
    PASSCODE_VALIDITY_SECONDS,
    CitizenAccessService,
    CitizenAccessSubject,
    RedisCitizenPasscodeStore,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str | int] = {}
        self.ttls: dict[str, int] = {}
        self.expire_calls: list[tuple[str, int]] = []

    def setex(self, name: str, time: int, value: str) -> None:
        self.values[name] = value
        self.ttls[name] = time

    def get(self, name: str):
        return self.values.get(name)

    def getdel(self, name: str):
        return self.values.pop(name, None)

    def incr(self, name: str) -> int:
        self.values[name] = int(self.values.get(name, 0)) + 1
        return int(self.values[name])

    def expire(self, name: str, time: int) -> None:
        if name in self.values:
            self.ttls[name] = time
            self.expire_calls.append((name, time))

    def ttl(self, name: str) -> int:
        return self.ttls.get(name, -1)

    def delete(self, name: str) -> None:
        self.values.pop(name, None)
        self.ttls.pop(name, None)


class FakeHasher:
    def __init__(self) -> None:
        self.hashed: list[str] = []
        self.verified: list[tuple[str, str]] = []

    def hash(self, passcode: str) -> str:
        self.hashed.append(passcode)
        return f"argon2id:{passcode}"

    def verify(self, stored_hash: str, passcode: str) -> bool:
        self.verified.append((stored_hash, passcode))
        return stored_hash == f"argon2id:{passcode}"


@dataclass
class RecordedEvent:
    event_type: str
    entity_type: str
    entity_id: int


class FakeSession:
    def __init__(self) -> None:
        self.events: list[RecordedEvent] = []
        self.outbox: list[dict] = []


SECRET = b"citizen-test-secret"
OCCURRED = datetime(2024, 8, 1, tzinfo=timezone.utc)


def _service(redis: FakeRedis, hasher: FakeHasher) -> CitizenAccessService:
    limiter = RedisRateLimiter(redis, key_secret=SECRET)
    sessions = RedisOfficerSessionBackend(redis)
    passcodes = RedisCitizenPasscodeStore(redis, key_secret=SECRET)
    return CitizenAccessService(
        rate_limiter=limiter,
        passcodes=passcodes,
        sessions=sessions,
        key_secret=SECRET,
        hasher=hasher,
        response_floor_ms=0,
    )


def _patch_side_effects(monkeypatch, session: FakeSession) -> None:
    def _enqueue(session_arg, *, queue, task_name, kwargs, idempotency_key):  # type: ignore[no-untyped-def]
        assert session_arg is session
        session.outbox.append(
            {
                "queue": queue,
                "task_name": task_name,
                "kwargs": dict(kwargs),
                "idempotency_key": idempotency_key,
            }
        )
        return len(session.outbox)

    def _append(session_arg, *, event_type, entity, actor, changes, occurrence_time, **kw):  # type: ignore[no-untyped-def]
        assert session_arg is session
        assert occurrence_time == OCCURRED
        session.events.append(RecordedEvent(event_type, entity.__tablename__, entity.id))

    monkeypatch.setattr("app.services.citizen_access.enqueue", _enqueue)
    monkeypatch.setattr("app.services.citizen_access.EventLog.append", _append)


def test_request_passcode_matching_and_non_matching_responses_are_identical(monkeypatch) -> None:
    redis = FakeRedis()
    hasher = FakeHasher()
    service = _service(redis, hasher)
    positive_session = FakeSession()
    negative_session = FakeSession()

    monkeypatch.setattr(
        citizen_access,
        "_find_subject",
        lambda session, *, case_reference, mobile_hash: (
            CitizenAccessSubject(case_id=101, owner_record_ids=(11, 12))
            if session is positive_session
            else None
        ),
    )
    _patch_side_effects(monkeypatch, positive_session)
    positive = service.request_passcode(
        positive_session,
        case_reference="MH-CASE-1",
        mobile="+919000000000",
        occurrence_time=OCCURRED,
    )
    _patch_side_effects(monkeypatch, negative_session)
    negative = service.request_passcode(
        negative_session,
        case_reference="MH-CASE-1",
        mobile="+919000000001",
        occurrence_time=OCCURRED,
    )

    assert positive.body == negative.body == CITIZEN_ACCESS_ACCEPTED_BODY
    assert positive.issued is True
    assert negative.issued is False
    assert [event.event_type for event in positive_session.events] == ["CITIZEN_PASSCODE_ISSUED"]
    assert [event.event_type for event in negative_session.events] == ["CITIZEN_PASSCODE_REFUSED"]
    assert len(hasher.hashed) == 2
    assert all(len(code) == PASSCODE_DIGITS and code.isdigit() for code in hasher.hashed)
    assert len(positive_session.outbox) == len(negative_session.outbox) == 1
    assert positive_session.outbox[0]["kwargs"]["mobile"] == "+919000000000"
    assert negative_session.outbox[0]["kwargs"] == {"mobile": None, "passcode": None}


def test_stored_passcode_has_ten_minute_ttl_and_is_single_use() -> None:
    redis = FakeRedis()
    store = RedisCitizenPasscodeStore(redis, key_secret=SECRET)

    store.store(
        case_reference="MH-CASE-1",
        mobile_hash="a" * 64,
        code_hash="argon2id:123456",
        case_id=101,
        owner_record_ids=(11, 12),
    )

    [key] = [name for name in redis.values if name.startswith("citizen:passcode:")]
    assert redis.ttls[key] == PASSCODE_VALIDITY_SECONDS
    assert "MH-CASE-1" not in key
    stored = store.consume(case_reference="MH-CASE-1")
    assert stored is not None
    assert stored.case_id == 101
    assert stored.owner_record_ids == (11, 12)
    assert store.consume(case_reference="MH-CASE-1") is None


def test_verify_passcode_consumes_code_and_issues_case_scoped_session(monkeypatch) -> None:
    redis = FakeRedis()
    hasher = FakeHasher()
    service = _service(redis, hasher)
    session = FakeSession()
    _patch_side_effects(monkeypatch, session)
    RedisCitizenPasscodeStore(redis, key_secret=SECRET).store(
        case_reference="MH-CASE-1",
        mobile_hash="b" * 64,
        code_hash="argon2id:654321",
        case_id=202,
        owner_record_ids=(21,),
    )

    bundle = service.verify_passcode(
        session,
        case_reference="MH-CASE-1",
        passcode="654321",
        occurrence_time=OCCURRED,
    )

    assert bundle is not None
    assert bundle.case_id == 202
    assert bundle.owner_record_ids == (21,)
    assert [event.event_type for event in session.events] == ["CITIZEN_SESSION_ISSUED"]
    assert service.verify_passcode(
        session,
        case_reference="MH-CASE-1",
        passcode="654321",
        occurrence_time=OCCURRED,
    ) is None


def test_citizen_session_is_absolute_expiry_not_sliding() -> None:
    redis = FakeRedis()
    backend = RedisOfficerSessionBackend(redis)

    bundle = backend.create_citizen_session(
        subject_id="citizen:MH-CASE-1:h",
        case_id=303,
        owner_record_ids=(31, 32),
    )

    key = f"citizen:session:{bundle.session_token}"
    assert redis.ttls[key] == CITIZEN_SESSION_SECONDS
    assert backend.citizen_session(bundle.session_token) == CitizenSession(
        subject_id="citizen:MH-CASE-1:h",
        case_id=303,
        owner_record_ids=(31, 32),
    )
    assert redis.expire_calls == []


def test_set_citizen_session_cookie_is_secure_http_only() -> None:
    redis = FakeRedis()
    bundle = RedisOfficerSessionBackend(redis).create_citizen_session(
        subject_id="citizen:MH-CASE-1:h",
        case_id=303,
        owner_record_ids=(31,),
    )
    from starlette.responses import Response

    response = Response()
    set_citizen_session_cookie(response, bundle)

    cookie_lines = [value.decode("latin-1") for name, value in response.raw_headers if name == b"set-cookie"]
    [session_cookie] = [
        line for line in cookie_lines if line.startswith(CITIZEN_SESSION_COOKIE)
    ]
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=strict" in session_cookie
    assert "Max-Age=900" in session_cookie


def test_otp_issue_timing_medians_stay_within_two_hundred_ms(monkeypatch) -> None:
    redis = FakeRedis()
    hasher = FakeHasher()
    service = _service(redis, hasher)

    matching = FakeSession()
    non_matching = FakeSession()

    def _enqueue(session_arg, *, queue, task_name, kwargs, idempotency_key):  # type: ignore[no-untyped-def]
        session_arg.outbox.append(
            {
                "queue": queue,
                "task_name": task_name,
                "kwargs": dict(kwargs),
                "idempotency_key": idempotency_key,
            }
        )
        return len(session_arg.outbox)

    def _append(session_arg, *, event_type, entity, actor, changes, occurrence_time, **kw):  # type: ignore[no-untyped-def]
        assert occurrence_time == OCCURRED
        session_arg.events.append(RecordedEvent(event_type, entity.__tablename__, entity.id))

    monkeypatch.setattr("app.services.citizen_access.enqueue", _enqueue)
    monkeypatch.setattr("app.services.citizen_access.EventLog.append", _append)
    monkeypatch.setattr(
        citizen_access,
        "_find_subject",
        lambda session, *, case_reference, mobile_hash: (
            CitizenAccessSubject(case_id=404, owner_record_ids=(41,))
            if session is matching
            else None
        ),
    )

    matching_latencies: list[float] = []
    non_matching_latencies: list[float] = []
    matching_bodies: list[dict[str, object]] = []
    non_matching_bodies: list[dict[str, object]] = []

    for index in range(200):
        start = perf_counter()
        matching_bodies.append(
            service.request_passcode(
                matching,
                case_reference=f"MH-CASE-M-{index}",
                mobile=f"+91900000{index:04d}",
                occurrence_time=OCCURRED,
            ).body
        )
        matching_latencies.append((perf_counter() - start) * 1000)

        start = perf_counter()
        non_matching_bodies.append(
            service.request_passcode(
                non_matching,
                case_reference=f"MH-CASE-N-{index}",
                mobile=f"+91800000{index:04d}",
                occurrence_time=OCCURRED,
            ).body
        )
        non_matching_latencies.append((perf_counter() - start) * 1000)

    assert all(body == CITIZEN_ACCESS_ACCEPTED_BODY for body in matching_bodies)
    assert matching_bodies == non_matching_bodies
    assert abs(median(matching_latencies) - median(non_matching_latencies)) <= 200
