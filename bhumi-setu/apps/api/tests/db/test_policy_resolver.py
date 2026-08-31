"""``PolicyResolver`` (§4.2): refusal, caching, and snapshots.

Property 64: *for any Policy_Config key with no value effective on the required
date, the dependent operation is refused and the missing key and date are
returned; no operation substitutes a default.*

The tests that matter here are the ones about what the resolver refuses to do.
Anyone can make a lookup work; the value of this class is that it cannot be talked
into a default.
"""

from __future__ import annotations

import ast
import inspect
from datetime import date
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from contextlib import contextmanager

from sqlalchemy import Connection, event, text
from sqlalchemy.orm import Session

from app.services import policy as policy_module
from app.services.policy import (
    PolicyResolver,
    PolicySnapshot,
    PolicyValueMissing,
)

STATE = "IN-MH"
ACT = "RFCTLARR-2013"
KEY = "period.pn.to_declaration"
D = date(2024, 6, 1)


@pytest.fixture
def officer_id(db_connection: Connection) -> str:
    return db_connection.execute(
        text(
            """
            INSERT INTO officer (officer_code, display_name, credential_hash)
            VALUES ('resolver-officer', 'Resolver Officer', 'argon2-placeholder')
            RETURNING id
            """
        )
    ).scalar_one()


@pytest.fixture
def session(db_connection: Connection) -> Session:
    return Session(bind=db_connection, join_transaction_mode="create_savepoint")


@pytest.fixture
def put(db_connection: Connection, officer_id: str):
    def _put(key: str, value: str, *, state: str = STATE, act: str | None = ACT,
             effective_from: str = "2024-04-01") -> None:
        db_connection.execute(
            text(
                """
                INSERT INTO policy_config
                    (policy_key, state_key, act_key, effective_from, value, created_by)
                VALUES (:k, :s, :a, :ef, CAST(:v AS jsonb), :o)
                """
            ),
            {"k": key, "s": state, "a": act, "ef": effective_from,
             "v": value, "o": officer_id},
        )

    return _put


@pytest.fixture
def resolver(session: Session) -> PolicyResolver:
    return PolicyResolver(session)


# ---------------------------------------------------------------------------
# Property 64 — refuses, never defaults
# ---------------------------------------------------------------------------


def test_missing_value_raises_carrying_key_and_date(resolver: PolicyResolver) -> None:
    with pytest.raises(PolicyValueMissing) as exc:
        resolver.get(KEY, state=STATE, act=ACT, as_of=D)

    error = exc.value
    assert error.details["policy_key"] == KEY
    assert error.details["as_of"] == "2024-06-01"
    assert error.details["state_key"] == STATE
    assert error.details["act_key"] == ACT
    assert error.status_code == 409, "a missing statutory period is not a server fault"
    assert error.code == "POLICY_VALUE_MISSING"


@given(
    key=st.sampled_from(["period.x", "risk.band_cutoffs", "policy.stage_set",
                         "retention.period.OWNER_CONTACT", "priority.weights"]),
    as_of=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
)
@settings(max_examples=50)
def test_no_key_and_no_date_yields_a_value(
    resolver: PolicyResolver, key: str, as_of: date
) -> None:
    """Property 64, over keys and dates: an empty table answers nothing, ever.

    The failure this guards against is a default that only appears for some keys —
    a ``.get(key, 0)`` in one branch. Sweeping keys and dates makes that visible
    rather than depending on a test having picked the wrong one.
    """
    with pytest.raises(PolicyValueMissing):
        resolver.get(key, state=STATE, act=ACT, as_of=as_of)


def test_get_has_no_default_parameter() -> None:
    """A structural guard, not a behavioural one.

    ``get(key, default=30)`` is how a legal deadline ends up in Python, and it
    would keep working while being wrong in any state with a different period. The
    AST lint in task 2.6 catches ``timedelta(days=30)`` but cannot catch a
    plausible keyword argument, so the parameter must not exist to be passed.
    """
    params = inspect.signature(PolicyResolver.get).parameters
    assert "default" not in params
    assert "fallback" not in params
    assert set(params) == {"self", "key", "state", "act", "as_of"}


def test_no_call_site_passes_a_default_to_get() -> None:
    """Scan the tree: nobody may call get() with an extra keyword.

    The signature guard above stops the parameter existing. This stops a caller
    from routing around it via ``**kwargs``, and it will keep failing as services
    are added in later tasks.
    """
    permitted = {"state", "act", "as_of"}
    offences: list[str] = []
    api_root = Path(__file__).resolve().parents[2]
    for source in list((api_root / "app").rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name not in {"get", "try_get"}:
                continue
            keywords = {kw.arg for kw in node.keywords if kw.arg}
            extra = keywords - permitted
            # Only flag calls that look like policy resolution: they carry the
            # resolution keywords. A dict.get() elsewhere is not our business.
            if keywords & permitted and extra:
                offences.append(f"{source.name}:{node.lineno} extra={sorted(extra)}")
    assert not offences, f"policy lookups passing extra keywords: {offences}"


# ---------------------------------------------------------------------------
# try_get — absence as a legitimate branch
# ---------------------------------------------------------------------------


def test_try_get_returns_none_instead_of_raising(resolver: PolicyResolver) -> None:
    """R32.14's retention sweep withholds rather than failing, and needs this."""
    assert resolver.try_get(KEY, state=STATE, act=ACT, as_of=D) is None


def test_try_get_returns_the_value_when_present(put, resolver: PolicyResolver) -> None:
    put(KEY, "365")
    assert resolver.try_get(KEY, state=STATE, act=ACT, as_of=D) == 365


def test_try_get_does_not_cache_a_miss(put, resolver: PolicyResolver) -> None:
    """A miss usually means someone is about to configure the value.

    Caching the absence would make the resolver keep reporting nothing inside the
    same unit of work after the row appeared.
    """
    assert resolver.try_get(KEY, state=STATE, act=ACT, as_of=D) is None
    put(KEY, "365")
    assert resolver.try_get(KEY, state=STATE, act=ACT, as_of=D) == 365


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def test_repeated_reads_hit_the_database_once(
    put, resolver: PolicyResolver, db_connection: Connection
) -> None:
    """Counts real SELECTs against policy_config, via a cursor listener.

    Written first with a placeholder counter that returned a constant. It passed,
    and verified nothing — which is worse than having no test, because the suite
    then reports the cache as covered.
    """
    put(KEY, "365")
    with count_policy_selects(db_connection) as counter:
        for _ in range(5):
            assert resolver.get(KEY, state=STATE, act=ACT, as_of=D) == 365
    assert counter.count == 1, f"expected 1 query, saw {counter.count}"


def test_a_cache_miss_on_a_different_key_does_query(
    put, resolver: PolicyResolver, db_connection: Connection
) -> None:
    """The counter has to be able to see a query, or the test above proves nothing
    beyond the listener being wired up wrong."""
    put(KEY, "365")
    put("period.objection.window", "60")
    with count_policy_selects(db_connection) as counter:
        resolver.get(KEY, state=STATE, act=ACT, as_of=D)
        resolver.get("period.objection.window", state=STATE, act=ACT, as_of=D)
    assert counter.count == 2


def test_cache_distinguishes_date_state_and_act(put, resolver: PolicyResolver) -> None:
    """A cache keyed only on the policy key would serve one state's period to
    another, which is the worst possible caching bug here."""
    put(KEY, "365", state="*")
    put(KEY, "180", state=STATE)
    assert resolver.get(KEY, state=STATE, act=ACT, as_of=D) == 180
    assert resolver.get(KEY, state="IN-KA", act=ACT, as_of=D) == 365


def test_invalidate_drops_cached_values(put, resolver: PolicyResolver) -> None:
    """After a policy write in the same unit of work, the resolver must not keep
    serving the value the write replaced."""
    put(KEY, "365", effective_from="2024-04-01")
    assert resolver.get(KEY, state=STATE, act=ACT, as_of=D) == 365
    put(KEY, "180", effective_from="2024-05-01")
    assert resolver.get(KEY, state=STATE, act=ACT, as_of=D) == 365, "still cached"
    resolver.invalidate()
    assert resolver.get(KEY, state=STATE, act=ACT, as_of=D) == 180


class _SelectCounter:
    def __init__(self) -> None:
        self.count = 0


@contextmanager
def count_policy_selects(connection: Connection):
    """Count statements issued against policy_config while the block runs."""
    counter = _SelectCounter()

    def on_execute(conn, cursor, statement, parameters, context, executemany):
        if "policy_config" in statement and statement.lstrip().upper().startswith("SELECT"):
            counter.count += 1

    event.listen(connection, "before_cursor_execute", on_execute)
    try:
        yield counter
    finally:
        event.remove(connection, "before_cursor_execute", on_execute)


# ---------------------------------------------------------------------------
# PolicySnapshot
# ---------------------------------------------------------------------------


def test_snapshot_is_frozen_and_hashable(put, resolver: PolicyResolver) -> None:
    put(KEY, "365")
    put("period.objection.window", "60")
    snap = resolver.snapshot([KEY, "period.objection.window"], state=STATE, act=ACT, as_of=D)

    assert isinstance(snap, PolicySnapshot)
    assert snap[KEY] == 365
    assert hash(snap.content_hash)
    with pytest.raises(Exception):
        snap.values["injected"] = 1  # type: ignore[index]
    with pytest.raises(Exception):
        snap.resolved_at = date(2025, 1, 1)  # type: ignore[misc]


def test_snapshot_hash_is_stable_for_the_same_values(put, resolver: PolicyResolver) -> None:
    """R7.8 and R21.3 compare these across processes, so the hash cannot depend on
    dict ordering, repr(), or PYTHONHASHSEED."""
    put(KEY, "365")
    put("period.objection.window", "60")
    a = resolver.snapshot([KEY, "period.objection.window"], state=STATE, act=ACT, as_of=D)
    resolver.invalidate()
    b = resolver.snapshot(["period.objection.window", KEY], state=STATE, act=ACT, as_of=D)
    assert a.content_hash == b.content_hash, "key order changed the hash"


def test_snapshot_hash_changes_when_a_value_changes(put, resolver: PolicyResolver) -> None:
    put(KEY, "365", effective_from="2024-04-01")
    before = resolver.snapshot([KEY], state=STATE, act=ACT, as_of=D)
    put(KEY, "180", effective_from="2024-05-01")
    resolver.invalidate()
    after = resolver.snapshot([KEY], state=STATE, act=ACT, as_of=D)
    assert before.content_hash != after.content_hash


def test_snapshot_refuses_on_the_first_missing_key(put, resolver: PolicyResolver) -> None:
    """A snapshot with a hole would hash to something authoritative-looking while
    describing configuration that was never complete."""
    put(KEY, "365")
    with pytest.raises(PolicyValueMissing) as exc:
        resolver.snapshot([KEY, "period.absent"], state=STATE, act=ACT, as_of=D)
    assert exc.value.details["policy_key"] == "period.absent"
