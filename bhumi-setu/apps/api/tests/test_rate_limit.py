"""Redis rate limits and lockouts (task 7.2)."""

from __future__ import annotations

from app.security.rate_limit import (
    AUTH_FAILURE_LIMIT,
    AUTH_FAILURE_LOCK_SECONDS,
    AUTH_FAILURE_WINDOW_SECONDS,
    OTP_ISSUE_LIMIT,
    OTP_ISSUE_WINDOW_SECONDS,
    OTP_VERIFY_LIMIT,
    OTP_VERIFY_WINDOW_SECONDS,
    RedisRateLimiter,
    hmac_key,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str | int] = {}
        self.ttls: dict[str, int] = {}

    def incr(self, name: str) -> int:
        self.values[name] = int(self.values.get(name, 0)) + 1
        return int(self.values[name])

    def expire(self, name: str, time: int) -> None:
        self.ttls[name] = time

    def setex(self, name: str, time: int, value: str) -> None:
        self.values[name] = value
        self.ttls[name] = time

    def get(self, name: str):
        return self.values.get(name)

    def ttl(self, name: str) -> int:
        return self.ttls.get(name, -1)

    def delete(self, name: str) -> None:
        self.values.pop(name, None)
        self.ttls.pop(name, None)


SECRET = b"test-secret"


def test_hmac_key_is_stable_and_hides_the_identifier() -> None:
    key = hmac_key(SECRET, "9000000000")
    assert key == hmac_key(SECRET, "9000000000")
    assert key != hmac_key(SECRET, "9000000001")
    assert "9000000000" not in key
    assert len(key) == 64


def test_auth_failures_lock_on_the_fifth_failure_for_fifteen_minutes() -> None:
    redis = FakeRedis()
    limiter = RedisRateLimiter(redis, key_secret=SECRET)

    decisions = [limiter.hit_auth_failure("officer-1") for _ in range(AUTH_FAILURE_LIMIT)]

    assert [d.allowed for d in decisions] == [True, True, True, True, False]
    assert decisions[-1].locked is True
    assert decisions[-1].retry_after_seconds == AUTH_FAILURE_LOCK_SECONDS
    assert redis.ttls[decisions[0].key] == AUTH_FAILURE_WINDOW_SECONDS

    locked = limiter.hit_auth_failure("officer-1")
    assert not locked.allowed
    assert locked.locked
    assert locked.retry_after_seconds == AUTH_FAILURE_LOCK_SECONDS


def test_clear_auth_failures_removes_counter_and_lock() -> None:
    redis = FakeRedis()
    limiter = RedisRateLimiter(redis, key_secret=SECRET)
    for _ in range(AUTH_FAILURE_LIMIT):
        limiter.hit_auth_failure("officer-1")

    limiter.clear_auth_failures("officer-1")

    assert limiter.hit_auth_failure("officer-1").allowed


def test_otp_mobile_limit_uses_hmac_and_blocks_on_fifth_attempt() -> None:
    redis = FakeRedis()
    limiter = RedisRateLimiter(redis, key_secret=SECRET)

    decisions = [limiter.hit_otp_issue("+91-9000000000") for _ in range(OTP_ISSUE_LIMIT)]

    assert [d.allowed for d in decisions] == [True, True, True, True, False]
    assert decisions[-1].retry_after_seconds == OTP_ISSUE_WINDOW_SECONDS
    assert all("+91-9000000000" not in key for key in redis.values)
    assert all("+91-9000000000" not in key for key in redis.ttls)


def test_otp_verify_limit_blocks_on_tenth_attempt() -> None:
    limiter = RedisRateLimiter(FakeRedis(), key_secret=SECRET)

    decisions = [limiter.hit_otp_verify("MH-CASE-1") for _ in range(OTP_VERIFY_LIMIT)]

    assert all(decision.allowed for decision in decisions[:-1])
    assert not decisions[-1].allowed
    assert decisions[-1].retry_after_seconds == OTP_VERIFY_WINDOW_SECONDS


def test_session_ceiling_is_parameterised_and_hmac_keyed() -> None:
    redis = FakeRedis()
    limiter = RedisRateLimiter(redis, key_secret=SECRET)

    first = limiter.hit_session("raw-session-token", limit=2, window_seconds=60)
    second = limiter.hit_session("raw-session-token", limit=2, window_seconds=60)

    assert first.allowed
    assert not second.allowed
    assert second.retry_after_seconds == 60
    assert all("raw-session-token" not in key for key in redis.values)
