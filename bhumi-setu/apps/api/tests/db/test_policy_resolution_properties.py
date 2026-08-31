"""Effective-dated resolution as a property, and the unseeded-period precondition.

Feature: bhumisetu. Properties 13 and 64 (§4.1, §4.2; R28.2, R28.4, R28.5).

``test_policy_config.py`` pins the resolution rule with hand-chosen examples;
this module pins it as a property. It generates an arbitrary version *timeline* —
platform-wide and state-specific rows at arbitrary effective dates — and, for an
arbitrary query date, checks the resolved value against an independent oracle. The
example tests say "this case is right"; the property says "there is no timeline on
which the single ``ORDER BY`` and the two-query fallback the design rejects would
disagree", which is the whole reason the fallback is not written.

The oracle is derived from R28.4's three interacting rules, not copied from the SQL:

* only a row already in force on the date is eligible (``effective_from <= D``);
* a state-specific row beats the platform-wide default, and it does so on
  precedence, not recency — an older state override still wins over a newer
  platform default;
* among rows of equal precedence, the latest ``effective_from`` wins.

**No RFCTLARR period is seeded anywhere** — not in a migration, not in product code
(Q8, §1.2). ``test_no_policy_config_rows_are_seeded`` holds that line: a freshly
migrated database answers every period lookup with a refusal until a state
configures one. The period and stage-set rows the other tests resolve are synthetic
and supplied by fixtures, which is task 2.8's "ship period rows only as pytest
fixtures" made concrete. The real baseline is a precondition on operating the
platform (task 21.3), not code.

Isolation across Hypothesis examples follows the pattern documented in
``test_event_log_append.py``: the ``db_connection`` fixture is function-scoped and
shared across every example, so each example runs its writes through a session
bound to that connection with ``join_transaction_mode="create_savepoint"`` and
closes it, rolling back to the savepoint so the next example starts from an empty
table. The ``officer`` row the ``created_by`` foreign key needs is inserted once on
the connection itself, before any savepoint, so it survives every rollback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.services.policy import PolicyResolver, PolicyValueMissing

STATE = "IN-MH"
#: A state that never receives a row of its own, so a lookup against it exercises
#: the platform-wide fallback rather than a state override.
UNCONFIGURED_STATE = "IN-KA"
ACT = "RFCTLARR-2013"
PLATFORM = "*"
KEY = "period.test.window"
BASE = date(2020, 1, 1)

_INSERT = text(
    """
    INSERT INTO policy_config
        (policy_key, state_key, act_key, effective_from, value, created_by)
    VALUES (:key, :state, :act, :effective_from, CAST(:value AS jsonb), :officer)
    """
)


@pytest.fixture
def officer_id(db_connection: Connection) -> str:
    """One officer on the outer transaction, reused across every Hypothesis example.

    Inserted through the connection rather than a per-example session so it sits
    outside the savepoints those examples roll back — the ``created_by`` foreign key
    would otherwise dangle on the second example.
    """
    return db_connection.execute(
        text(
            """
            INSERT INTO officer (officer_code, display_name, credential_hash)
            VALUES ('resolution-prop-officer', 'Resolution Prop Officer', 'argon2-x')
            RETURNING id
            """
        )
    ).scalar_one()


# ---------------------------------------------------------------------------
# Property 13 / 64 — the value in force on a date, state beating platform
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Version:
    state: str
    effective_from: date
    value: int


@dataclass(frozen=True)
class _Scenario:
    rows: tuple[_Version, ...]
    query_state: str
    as_of: date


@st.composite
def st_resolution_scenario(draw) -> _Scenario:
    """A version timeline for one key, plus a query state and date.

    Effective dates are drawn as distinct day-offsets *within each state layer*, so
    the ``(policy_key, state_key, coalesce(act_key,''), effective_from)`` unique
    index is never violated — a platform row and a state row may share a date
    (different ``state_key``), which is exactly the collision the resolver must
    break by precedence. Values are distinct integers so a wrong pick is caught by
    value, not merely by count. The query date ranges from before the earliest row
    to after the latest, so "not yet in force" and "nothing at all" arise naturally
    alongside the ordinary hit.
    """
    platform_offsets = draw(
        st.lists(st.integers(min_value=0, max_value=3650), min_size=0, max_size=6, unique=True)
    )
    state_offsets = draw(
        st.lists(st.integers(min_value=0, max_value=3650), min_size=0, max_size=6, unique=True)
    )
    rows: list[_Version] = []
    value = 0
    for offset in platform_offsets:
        rows.append(_Version(PLATFORM, BASE + timedelta(days=offset), value))
        value += 1
    for offset in state_offsets:
        rows.append(_Version(STATE, BASE + timedelta(days=offset), value))
        value += 1
    query_state = draw(st.sampled_from([STATE, UNCONFIGURED_STATE]))
    as_of = BASE + timedelta(days=draw(st.integers(min_value=-60, max_value=3710)))
    return _Scenario(rows=tuple(rows), query_state=query_state, as_of=as_of)


def _resolve_oracle(scenario: _Scenario) -> int | None:
    """R28.4 by hand: eligible rows are those in force on the date for the query
    state or the platform; the winner is state-specific first, then latest date."""
    eligible = [
        row
        for row in scenario.rows
        if row.effective_from <= scenario.as_of
        and row.state in (scenario.query_state, PLATFORM)
    ]
    if not eligible:
        return None
    eligible.sort(key=lambda row: (row.state == scenario.query_state, row.effective_from))
    return eligible[-1].value


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(scenario=st_resolution_scenario())
def test_resolution_returns_the_latest_in_force_value_state_beating_platform(
    db_connection: Connection, officer_id: str, scenario: _Scenario
) -> None:
    """Feature: bhumisetu, Property 13: for any Policy_Config key and any date D the
    returned value is the one whose effective-from date is the latest at or before D
    (with a state-specific value beating a platform-wide one, R28.4); Property 64:
    where no value is in force, the lookup refuses rather than defaulting."""
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        for row in scenario.rows:
            session.execute(
                _INSERT,
                {
                    "key": KEY,
                    "state": row.state,
                    "act": ACT,
                    "effective_from": row.effective_from.isoformat(),
                    "value": json.dumps(row.value),
                    "officer": officer_id,
                },
            )
        session.flush()

        resolver = PolicyResolver(session)
        expected = _resolve_oracle(scenario)
        if expected is None:
            with pytest.raises(PolicyValueMissing) as exc:
                resolver.get(KEY, state=scenario.query_state, act=ACT, as_of=scenario.as_of)
            assert exc.value.details["policy_key"] == KEY
            assert exc.value.details["as_of"] == scenario.as_of.isoformat()
        else:
            assert (
                resolver.get(KEY, state=scenario.query_state, act=ACT, as_of=scenario.as_of)
                == expected
            )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Property 64 — a missing key refuses and returns the key and the date
# ---------------------------------------------------------------------------

_TARGET_KEYS = [
    "period.absent.window",
    "risk.band_cutoffs",
    "policy.stage_set",
    "retention.period.OWNER_CONTACT",
    "priority.weights",
]
_DISTRACTOR_KEY = "period.some.other"


@dataclass(frozen=True)
class _Row:
    key: str
    state: str
    effective_from: date
    value: int


@dataclass(frozen=True)
class _AbsentScenario:
    target_key: str
    query_state: str
    as_of: date
    rows: tuple[_Row, ...]


@st.composite
def st_absent_scenario(draw) -> _AbsentScenario:
    """A populated table in which the target key has *no* value in force on the date.

    Two kinds of distractor, so refusal cannot be an accident of an empty table:
    rows for the target key that exist only in the future of the query date (a real
    row for the right key, correctly excluded by date), and rows for a different key
    at any date (a real value the resolver must not return under the wrong key). The
    target rows sit on the platform layer with distinct future offsets, so no state
    or platform override is ever in force at the query date for either query state.
    """
    target_key = draw(st.sampled_from(_TARGET_KEYS))
    query_state = draw(st.sampled_from([STATE, UNCONFIGURED_STATE]))
    as_of_offset = draw(st.integers(min_value=0, max_value=3650))
    as_of = BASE + timedelta(days=as_of_offset)

    rows: list[_Row] = []
    value = 0
    future_offsets = draw(
        st.lists(
            st.integers(min_value=as_of_offset + 1, max_value=as_of_offset + 3650),
            min_size=0,
            max_size=4,
            unique=True,
        )
    )
    for offset in future_offsets:
        rows.append(_Row(target_key, PLATFORM, BASE + timedelta(days=offset), value))
        value += 1

    distractor_offsets = draw(
        st.lists(st.integers(min_value=0, max_value=3650), min_size=0, max_size=4, unique=True)
    )
    for offset in distractor_offsets:
        rows.append(_Row(_DISTRACTOR_KEY, PLATFORM, BASE + timedelta(days=offset), value))
        value += 1

    return _AbsentScenario(
        target_key=target_key, query_state=query_state, as_of=as_of, rows=tuple(rows)
    )


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(scenario=st_absent_scenario())
def test_a_missing_key_refuses_and_returns_the_key_and_date(
    db_connection: Connection, officer_id: str, scenario: _AbsentScenario
) -> None:
    """Feature: bhumisetu, Property 64: for any Policy_Config key with no value
    effective on the required date, the dependent operation is refused and the
    missing key and date are returned; no operation substitutes a default."""
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        for row in scenario.rows:
            session.execute(
                _INSERT,
                {
                    "key": row.key,
                    "state": row.state,
                    "act": ACT,
                    "effective_from": row.effective_from.isoformat(),
                    "value": json.dumps(row.value),
                    "officer": officer_id,
                },
            )
        session.flush()

        resolver = PolicyResolver(session)
        with pytest.raises(PolicyValueMissing) as exc:
            resolver.get(scenario.target_key, state=scenario.query_state, act=ACT, as_of=scenario.as_of)

        error = exc.value
        assert error.details["policy_key"] == scenario.target_key
        assert error.details["as_of"] == scenario.as_of.isoformat()
        assert error.details["state_key"] == scenario.query_state
        assert error.details["act_key"] == ACT
        assert error.status_code == 409

        # The branch that is allowed to tolerate absence still reports it as absence,
        # never as a fabricated value (R32.14's withhold-rather-than-fail path).
        assert (
            resolver.try_get(scenario.target_key, state=scenario.query_state, act=ACT, as_of=scenario.as_of)
            is None
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Q8 precondition (§1.2): periods and the stage set ship only as fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def put(db_connection: Connection, officer_id: str):
    """Insert one synthetic policy version on the outer transaction."""

    def _put(key: str, value, *, state: str = STATE, act: str | None = ACT,
             effective_from: str = "2024-04-01") -> None:
        db_connection.execute(
            _INSERT,
            {
                "key": key,
                "state": state,
                "act": act,
                "effective_from": effective_from,
                "value": json.dumps(value),
                "officer": officer_id,
            },
        )

    return _put


@pytest.fixture
def synthetic_periods(put) -> dict[str, int]:
    """Statutory-period rows supplied as a fixture, never seeded (Q8, §1.2).

    The values are deliberately not the RFCTLARR baseline — 111 and 222 days are
    obviously non-statutory, so no reader can mistake a test fixture for the legal
    numbers, which live in the seed/config task (21.3) and enter only there.
    """
    put("period.pn.to_declaration", 111)
    put("period.objection.window", 222)
    return {"period.pn.to_declaration": 111, "period.objection.window": 222}


@pytest.fixture
def synthetic_stage_set(put) -> dict:
    """A stage set supplied as a fixture (task 2.8), holding period *pointers* rather
    than day counts, per §4.3."""
    graph = {
        "stages": [
            {"key": "OPEN", "label_key": "stage.open", "successors": ["CLOSED"],
             "period_key": "period.pn.to_declaration", "terminal": False},
            {"key": "CLOSED", "label_key": "stage.closed", "successors": [],
             "period_key": None, "terminal": True},
        ]
    }
    put("policy.stage_set", graph)
    return graph


def test_no_policy_config_rows_are_seeded(db_connection: Connection) -> None:
    """Q8 (§1.2): a migrated database seeds no configuration at all, and in
    particular no RFCTLARR statutory period. Until a state configures one, every
    period lookup refuses (R28.5) — which is why the resolver has no default and
    this precondition is safe to carry unconfirmed."""
    total = db_connection.execute(text("SELECT count(*) FROM policy_config")).scalar_one()
    assert total == 0, "something seeded policy_config; periods must arrive as configuration"

    rfctlarr = db_connection.execute(
        text("SELECT count(*) FROM policy_config WHERE act_key = 'RFCTLARR-2013'")
    ).scalar_one()
    assert rfctlarr == 0, "an RFCTLARR period row is seeded; it belongs in task 21.3, not here"


def test_fixture_supplied_periods_resolve(db_connection: Connection, synthetic_periods) -> None:
    """The fixtures are real, resolvable configuration — the mechanism works; only
    the seeding of statutory values is withheld."""
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        resolver = PolicyResolver(session)
        as_of = date(2024, 6, 1)
        assert resolver.get("period.pn.to_declaration", state=STATE, act=ACT, as_of=as_of) == 111
        assert resolver.get("period.objection.window", state=STATE, act=ACT, as_of=as_of) == 222
    finally:
        session.close()


def test_fixture_supplied_stage_set_resolves(db_connection: Connection, synthetic_stage_set) -> None:
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        resolver = PolicyResolver(session)
        graph = resolver.get("policy.stage_set", state=STATE, act=ACT, as_of=date(2024, 6, 1))
        assert [stage["key"] for stage in graph["stages"]] == ["OPEN", "CLOSED"]
    finally:
        session.close()
