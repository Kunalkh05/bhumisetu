"""Citizen passcode issue and verification (tasks 7.4-7.5).

The citizen access flow deliberately keeps its externally visible response dull:
whether a submitted case reference/mobile pair matches a stored owner or not, the
body is the same. The service still records the difference internally through the
event log and stores only a short-lived Argon2id hash of the generated passcode.
"""

from __future__ import annotations

import json
import secrets
import string
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.db.outbox import enqueue
from app.models.acquisition_case import AcquisitionCase
from app.models.case_parcel import CaseParcel
from app.models.ownership_record import OwnershipRecord
from app.security.auth import CitizenSessionBundle, RedisOfficerSessionBackend
from app.security.rate_limit import RedisRateLimiter, hmac_key

__all__ = [
    "CITIZEN_ACCESS_ACCEPTED_BODY",
    "OTP_RESPONSE_FLOOR_MS",
    "PASSCODE_DIGITS",
    "PASSCODE_VALIDITY_SECONDS",
    "Argon2idPasscodeHasher",
    "CitizenAccessService",
    "CitizenAccessSubject",
    "PasscodeIssueResult",
    "RedisCitizenPasscodeStore",
    "pad_to_floor",
]

PASSCODE_DIGITS = 6
PASSCODE_VALIDITY_SECONDS = 10 * 60
OTP_RESPONSE_FLOOR_MS = 0
OTP_TASK = "app.security.otp.send_otp"
CITIZEN_ACCESS_ACCEPTED_BODY = {
    "code": "PASSCODE_REQUEST_ACCEPTED",
    "message": "If the case reference and mobile number match, a passcode will be sent.",
    "details": {},
}


class PasscodeHasher(Protocol):
    def hash(self, passcode: str) -> str:
        ...

    def verify(self, stored_hash: str, passcode: str) -> bool:
        ...


class PendingPasscodeStore(Protocol):
    def store(
        self,
        *,
        case_reference: str,
        mobile_hash: str,
        code_hash: str,
        case_id: int,
        owner_record_ids: tuple[int, ...],
    ) -> None:
        ...

    def consume(self, *, case_reference: str) -> "StoredPasscode | None":
        ...


class RedisPasscodeLike(Protocol):
    def setex(self, name: str, time: int, value: str) -> object:
        ...

    def getdel(self, name: str) -> bytes | str | None:
        ...

    def delete(self, name: str) -> object:
        ...


@dataclass(frozen=True)
class CitizenAccessSubject:
    case_id: int
    owner_record_ids: tuple[int, ...]


@dataclass(frozen=True)
class StoredPasscode:
    mobile_hash: str
    code_hash: str
    case_id: int
    owner_record_ids: tuple[int, ...]


@dataclass(frozen=True)
class PasscodeIssueResult:
    body: dict[str, object]
    issued: bool


@dataclass(frozen=True)
class _SystemActor:
    kind: str = "SYSTEM"
    id: str = "citizen-access"


class _CitizenAccessEntity:
    def __init__(self, case_reference: str, case_id: int | None = None) -> None:
        self.__tablename__ = "citizen_access"
        self.id = case_id or 0
        self.case_reference = case_reference


class Argon2idPasscodeHasher:
    """Argon2id hasher for pending passcodes.

    Imported lazily so test environments can exercise the service with a fake
    hasher before dependencies are installed, while production fails loudly if the
    configured hasher is unavailable.
    """

    def hash(self, passcode: str) -> str:
        try:
            from argon2 import PasswordHasher
            from argon2.low_level import Type
        except ImportError as exc:  # pragma: no cover - exercised where dependency exists
            raise RuntimeError("argon2-cffi is required for citizen passcode storage") from exc
        return PasswordHasher(type=Type.ID).hash(passcode)

    def verify(self, stored_hash: str, passcode: str) -> bool:
        try:
            from argon2 import PasswordHasher
            from argon2.exceptions import VerifyMismatchError
            from argon2.low_level import Type
        except ImportError as exc:  # pragma: no cover - exercised where dependency exists
            raise RuntimeError("argon2-cffi is required for citizen passcode storage") from exc
        try:
            return bool(PasswordHasher(type=Type.ID).verify(stored_hash, passcode))
        except VerifyMismatchError:
            return False


class RedisCitizenPasscodeStore:
    """Short-lived Redis storage for one-use citizen passcodes."""

    def __init__(self, redis: RedisPasscodeLike, *, key_secret: bytes) -> None:
        self._redis = redis
        self._secret = key_secret

    def _key(self, case_reference: str) -> str:
        return f"citizen:passcode:{hmac_key(self._secret, case_reference)}"

    def store(
        self,
        *,
        case_reference: str,
        mobile_hash: str,
        code_hash: str,
        case_id: int,
        owner_record_ids: tuple[int, ...],
    ) -> None:
        self._redis.setex(
            self._key(case_reference),
            PASSCODE_VALIDITY_SECONDS,
            json.dumps(
                {
                    "mobile_hash": mobile_hash,
                    "code_hash": code_hash,
                    "case_id": case_id,
                    "owner_record_ids": list(owner_record_ids),
                }
            ),
        )

    def consume(self, *, case_reference: str) -> StoredPasscode | None:
        raw = self._redis.getdel(self._key(case_reference))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            data = json.loads(raw)
            return StoredPasscode(
                mobile_hash=str(data["mobile_hash"]),
                code_hash=str(data["code_hash"]),
                case_id=int(data["case_id"]),
                owner_record_ids=tuple(int(value) for value in data["owner_record_ids"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self._redis.delete(self._key(case_reference))
            return None


def _generate_passcode() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(PASSCODE_DIGITS))


def pad_to_floor(start: float, *, floor_ms: int, sleep: Callable[[float], None] = time.sleep) -> None:
    elapsed_ms = (time.perf_counter() - start) * 1000
    remaining_ms = floor_ms - elapsed_ms
    if remaining_ms > 0:
        sleep(remaining_ms / 1000)


class CitizenAccessService:
    """Issue passcodes, verify them, and mint case-scoped citizen sessions."""

    def __init__(
        self,
        *,
        rate_limiter: RedisRateLimiter,
        passcodes: PendingPasscodeStore,
        sessions: RedisOfficerSessionBackend,
        key_secret: bytes,
        hasher: PasscodeHasher | None = None,
        sleep: Callable[[float], None] = time.sleep,
        response_floor_ms: int = OTP_RESPONSE_FLOOR_MS,
    ) -> None:
        self._rate_limiter = rate_limiter
        self._passcodes = passcodes
        self._sessions = sessions
        self._secret = key_secret
        self._hasher = hasher or Argon2idPasscodeHasher()
        self._sleep = sleep
        self._response_floor_ms = response_floor_ms

    def request_passcode(
        self,
        session: Session,
        *,
        case_reference: str,
        mobile: str,
        actor: Actor | None = None,
        occurrence_time: datetime | None = None,
    ) -> PasscodeIssueResult:
        started = time.perf_counter()
        occurred = occurrence_time or datetime.now(timezone.utc)
        mobile_hash = hmac_key(self._secret, mobile)
        subject = _find_subject(session, case_reference=case_reference, mobile_hash=mobile_hash)
        allowed = self._rate_limiter.hit_otp_issue(mobile).allowed

        passcode = _generate_passcode()
        code_hash = self._hasher.hash(passcode)
        issued = bool(subject is not None and allowed)

        enqueue(
            session,
            queue="maintenance",
            task_name=OTP_TASK,
            kwargs={"mobile": mobile if issued else None, "passcode": passcode if issued else None},
            idempotency_key=f"otp:issue:{case_reference}:{mobile_hash}:{passcode}",
        )

        if issued and subject is not None:
            self._passcodes.store(
                case_reference=case_reference,
                mobile_hash=mobile_hash,
                code_hash=code_hash,
                case_id=subject.case_id,
                owner_record_ids=subject.owner_record_ids,
            )

        EventLog.append(
            session,
            event_type="CITIZEN_PASSCODE_ISSUED" if issued else "CITIZEN_PASSCODE_REFUSED",
            entity=_CitizenAccessEntity(case_reference, subject.case_id if subject else None),
            actor=actor or _SystemActor(),
            changes={"case_reference": (None, case_reference)},
            occurrence_time=occurred,
        )
        pad_to_floor(started, floor_ms=self._response_floor_ms, sleep=self._sleep)
        return PasscodeIssueResult(body=dict(CITIZEN_ACCESS_ACCEPTED_BODY), issued=issued)

    def verify_passcode(
        self,
        session: Session,
        *,
        case_reference: str,
        passcode: str,
        actor: Actor | None = None,
        occurrence_time: datetime | None = None,
    ) -> CitizenSessionBundle | None:
        occurred = occurrence_time or datetime.now(timezone.utc)
        if not self._rate_limiter.hit_otp_verify(case_reference).allowed:
            EventLog.append(
                session,
                event_type="CITIZEN_ACCESS_LOCKED",
                entity=_CitizenAccessEntity(case_reference),
                actor=actor or _SystemActor(),
                changes={"case_reference": (None, case_reference)},
                occurrence_time=occurred,
            )
            return None

        stored = self._passcodes.consume(case_reference=case_reference)
        if stored is None or not self._hasher.verify(stored.code_hash, passcode):
            EventLog.append(
                session,
                event_type="CITIZEN_ACCESS_REFUSED",
                entity=_CitizenAccessEntity(case_reference, stored.case_id if stored else None),
                actor=actor or _SystemActor(),
                changes={"case_reference": (None, case_reference)},
                occurrence_time=occurred,
            )
            return None

        subject_id = f"citizen:{case_reference}:{stored.mobile_hash}"
        bundle = self._sessions.create_citizen_session(
            subject_id=subject_id,
            case_id=stored.case_id,
            owner_record_ids=stored.owner_record_ids,
        )
        EventLog.append(
            session,
            event_type="CITIZEN_SESSION_ISSUED",
            entity=_CitizenAccessEntity(case_reference, stored.case_id),
            actor=actor or _SystemActor(),
            changes={"case_id": (None, stored.case_id)},
            occurrence_time=occurred,
        )
        return bundle


def _find_subject(
    session: Session, *, case_reference: str, mobile_hash: str
) -> CitizenAccessSubject | None:
    mobile_hash_bytes = bytes.fromhex(mobile_hash)
    rows = session.execute(
        select(AcquisitionCase.id, OwnershipRecord.id)
        .join(CaseParcel, CaseParcel.case_id == AcquisitionCase.id)
        .join(OwnershipRecord, OwnershipRecord.parcel_id == CaseParcel.parcel_id)
        .where(
            AcquisitionCase.case_reference == case_reference,
            OwnershipRecord.contact_mobile_hash == mobile_hash_bytes,
        )
        .order_by(OwnershipRecord.id)
    ).all()
    if not rows:
        return None
    return CitizenAccessSubject(
        case_id=int(rows[0][0]),
        owner_record_ids=tuple(int(row[1]) for row in rows),
    )
