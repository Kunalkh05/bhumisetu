"""Redis-backed rate limits and lockouts (task 7.2)."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Protocol

__all__ = [
    "AUTH_FAILURE_LIMIT",
    "AUTH_FAILURE_LOCK_SECONDS",
    "AUTH_FAILURE_WINDOW_SECONDS",
    "OTP_ISSUE_LIMIT",
    "OTP_ISSUE_WINDOW_SECONDS",
    "OTP_VERIFY_LIMIT",
    "OTP_VERIFY_WINDOW_SECONDS",
    "RateLimitDecision",
    "RedisRateLimiter",
    "hmac_key",
]

AUTH_FAILURE_LIMIT = 5
AUTH_FAILURE_WINDOW_SECONDS = 15 * 60
AUTH_FAILURE_LOCK_SECONDS = 15 * 60
OTP_ISSUE_LIMIT = 5
OTP_ISSUE_WINDOW_SECONDS = 60 * 60
OTP_VERIFY_LIMIT = 10
OTP_VERIFY_WINDOW_SECONDS = 24 * 60 * 60


class RedisCounterLike(Protocol):
    def incr(self, name: str) -> int:
        ...

    def expire(self, name: str, time: int) -> object:
        ...

    def setex(self, name: str, time: int, value: str) -> object:
        ...

    def get(self, name: str) -> bytes | str | None:
        ...

    def ttl(self, name: str) -> int:
        ...

    def delete(self, name: str) -> object:
        ...


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    key: str
    count: int
    limit: int
    retry_after_seconds: int | None = None
    locked: bool = False


def hmac_key(secret: bytes, identifier: str) -> str:
    """Stable opaque key fragment for Redis identifiers."""
    return hmac.new(secret, identifier.encode("utf-8"), hashlib.sha256).hexdigest()


class RedisRateLimiter:
    """Fixed-window counters plus explicit lockout keys."""

    def __init__(self, redis: RedisCounterLike, *, key_secret: bytes) -> None:
        self._redis = redis
        self._secret = key_secret

    def _id(self, identifier: str) -> str:
        return hmac_key(self._secret, identifier)

    def _locked(self, key: str, limit: int) -> RateLimitDecision | None:
        if self._redis.get(key) is None:
            return None
        ttl = self._redis.ttl(key)
        return RateLimitDecision(
            allowed=False,
            key=key,
            count=limit,
            limit=limit,
            retry_after_seconds=max(ttl, 0),
            locked=True,
        )

    def _hit(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        lock_key: str | None = None,
        lock_seconds: int | None = None,
    ) -> RateLimitDecision:
        if lock_key is not None:
            locked = self._locked(lock_key, limit)
            if locked is not None:
                return locked

        count = self._redis.incr(key)
        if count == 1:
            self._redis.expire(key, window_seconds)
        if count < limit:
            return RateLimitDecision(True, key, count, limit)

        retry_after = self._redis.ttl(key)
        if lock_key is not None and lock_seconds is not None:
            self._redis.setex(lock_key, lock_seconds, "1")
            retry_after = lock_seconds
        return RateLimitDecision(
            allowed=False,
            key=key,
            count=count,
            limit=limit,
            retry_after_seconds=max(retry_after, 0),
            locked=lock_key is not None,
        )

    def clear_auth_failures(self, officer_id: str) -> None:
        ident = self._id(officer_id)
        self._redis.delete(f"auth:fail:{ident}")
        self._redis.delete(f"auth:lock:{ident}")

    def hit_auth_failure(self, officer_id: str) -> RateLimitDecision:
        ident = self._id(officer_id)
        return self._hit(
            f"auth:fail:{ident}",
            limit=AUTH_FAILURE_LIMIT,
            window_seconds=AUTH_FAILURE_WINDOW_SECONDS,
            lock_key=f"auth:lock:{ident}",
            lock_seconds=AUTH_FAILURE_LOCK_SECONDS,
        )

    def hit_otp_issue(self, mobile_identifier: str) -> RateLimitDecision:
        return self._hit(
            f"otp:mobile:{self._id(mobile_identifier)}",
            limit=OTP_ISSUE_LIMIT,
            window_seconds=OTP_ISSUE_WINDOW_SECONDS,
        )

    def hit_otp_verify(self, case_reference: str) -> RateLimitDecision:
        return self._hit(
            f"otp:verify:{self._id(case_reference)}",
            limit=OTP_VERIFY_LIMIT,
            window_seconds=OTP_VERIFY_WINDOW_SECONDS,
        )

    def hit_session(self, session_token: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        return self._hit(
            f"session:req:{self._id(session_token)}",
            limit=limit,
            window_seconds=window_seconds,
        )
