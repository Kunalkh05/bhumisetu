from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.priority import (
    PriorityWeights,
    priority_score,
    recompute_priority,
    should_trigger_priority,
)


NOW = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)


class _Session:
    def __init__(self) -> None:
        self.flushed = False

    def flush(self) -> None:
        self.flushed = True


class _Resolver:
    def __init__(self) -> None:
        self.calls = []

    def get(self, key: str, *, state: str, act: str | None, as_of: date):
        self.calls.append((key, state, act, as_of))
        if key == "priority.weights":
            return {
                "version": "priority-v1",
                "weights": {"risk": 3, "deadline": 2, "value": 1},
            }
        if key == "priority.reference_amount":
            return "100000"
        raise KeyError(key)


@dataclass
class _Case:
    state_key: str = "IN-MH"
    act_key: str = "RFCTLARR-2013"
    risk_probability: float | None = 0.5
    stage_entered_on: date = date(2026, 2, 1)
    stage_deadline: date | None = date(2026, 3, 2)
    aggregate_awarded: Decimal = Decimal("50000")
    priority_score: Decimal | None = None
    priority_weight_version: str | None = None
    priority_computed_at: datetime | None = None


def test_priority_score_combines_risk_pressure_and_value() -> None:
    case = _Case()

    result = priority_score(
        case,
        weights=PriorityWeights(
            risk=Decimal("3"),
            deadline=Decimal("2"),
            value=Decimal("1"),
            version="priority-v1",
        ),
        reference_amount=Decimal("100000"),
        as_of=NOW.date(),
    )

    assert result.inputs.risk_probability == Decimal("0.5")
    assert result.inputs.deadline_pressure == Decimal("0.9655172413793103448275862069")
    assert result.inputs.case_value == Decimal("0.5")
    assert result.score == Decimal("65.517")
    assert result.weight_version == "priority-v1"


def test_priority_clamps_overdue_and_large_value_to_hundred() -> None:
    case = _Case(
        risk_probability=1.0,
        stage_deadline=date(2026, 2, 1),
        aggregate_awarded=Decimal("10000000"),
    )

    result = priority_score(
        case,
        weights=PriorityWeights(
            risk=Decimal("1"),
            deadline=Decimal("1"),
            value=Decimal("1"),
            version="priority-v1",
        ),
        reference_amount=Decimal("100000"),
        as_of=NOW.date(),
    )

    assert result.inputs.deadline_pressure == Decimal("1")
    assert result.inputs.case_value == Decimal("1")
    assert result.score == Decimal("100.000")


def test_unscored_case_and_missing_deadline_contribute_zero() -> None:
    case = _Case(risk_probability=None, stage_deadline=None, aggregate_awarded=Decimal("0"))

    result = priority_score(
        case,
        weights=PriorityWeights(
            risk=Decimal("1"),
            deadline=Decimal("1"),
            value=Decimal("1"),
            version="priority-v1",
        ),
        reference_amount=Decimal("100000"),
        as_of=NOW.date(),
    )

    assert result.inputs.risk_probability == Decimal("0")
    assert result.inputs.deadline_pressure == Decimal("0")
    assert result.score == Decimal("0.000")


def test_recompute_priority_stores_score_version_and_timestamp() -> None:
    case = _Case()
    session = _Session()

    result = recompute_priority(session, case=case, resolver=_Resolver(), now=NOW)

    assert case.priority_score == result.score
    assert case.priority_weight_version == "priority-v1"
    assert case.priority_computed_at == NOW
    assert session.flushed


def test_priority_recomputes_on_risk_deadline_or_value_change() -> None:
    assert should_trigger_priority("risk_probability")
    assert should_trigger_priority("CASE_UPDATED", changed_attributes={"stage_deadline"})
    assert should_trigger_priority("CASE_UPDATED", changed_attributes={"aggregate_awarded"})
    assert not should_trigger_priority("CASE_UPDATED", changed_attributes={"owner_name"})


@given(
    risk=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    amount=st.decimals(min_value=0, max_value=1_000_000, places=2),
    days_elapsed=st.integers(min_value=0, max_value=100),
    period_days=st.integers(min_value=1, max_value=100),
)
@settings(max_examples=100)
def test_property_priority_score_is_bounded(
    risk: float,
    amount: Decimal,
    days_elapsed: int,
    period_days: int,
) -> None:
    stage_entered = date(2026, 1, 1)
    case = _Case(
        risk_probability=risk,
        stage_entered_on=stage_entered,
        stage_deadline=stage_entered + timedelta(days=period_days),
        aggregate_awarded=amount,
    )

    result = priority_score(
        case,
        weights=PriorityWeights(Decimal("3"), Decimal("2"), Decimal("1"), "v"),
        reference_amount=Decimal("100000"),
        as_of=stage_entered + timedelta(days=days_elapsed),
    )

    assert Decimal("0") <= result.score <= Decimal("100")


@given(
    low=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    high=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_property_priority_score_does_not_decrease_when_risk_increases(
    low: float,
    high: float,
) -> None:
    low, high = sorted((low, high))
    base = _Case(risk_probability=low)
    raised = _Case(risk_probability=high)
    weights = PriorityWeights(Decimal("3"), Decimal("2"), Decimal("1"), "v")

    low_score = priority_score(
        base,
        weights=weights,
        reference_amount=Decimal("100000"),
        as_of=NOW.date(),
    ).score
    high_score = priority_score(
        raised,
        weights=weights,
        reference_amount=Decimal("100000"),
        as_of=NOW.date(),
    ).score

    assert high_score >= low_score


@given(
    earlier_day=st.integers(min_value=0, max_value=29),
    later_day=st.integers(min_value=0, max_value=60),
)
@settings(max_examples=100)
def test_property_priority_score_does_not_decrease_as_deadline_approaches(
    earlier_day: int,
    later_day: int,
) -> None:
    earlier_day, later_day = sorted((earlier_day, later_day))
    stage_entered = date(2026, 2, 1)
    case = _Case(
        stage_entered_on=stage_entered,
        stage_deadline=stage_entered + timedelta(days=30),
    )
    weights = PriorityWeights(Decimal("3"), Decimal("2"), Decimal("1"), "v")

    earlier = priority_score(
        case,
        weights=weights,
        reference_amount=Decimal("100000"),
        as_of=stage_entered + timedelta(days=earlier_day),
    ).score
    later = priority_score(
        case,
        weights=weights,
        reference_amount=Decimal("100000"),
        as_of=stage_entered + timedelta(days=later_day),
    ).score

    assert later >= earlier


@given(
    risk_weight=st.decimals(min_value=0, max_value=10, places=2),
    deadline_weight=st.decimals(min_value=0, max_value=10, places=2),
    value_weight=st.decimals(min_value=0, max_value=10, places=2),
)
@settings(max_examples=100)
def test_property_degenerate_missing_inputs_stay_bounded_and_versioned(
    risk_weight: Decimal,
    deadline_weight: Decimal,
    value_weight: Decimal,
) -> None:
    if risk_weight + deadline_weight + value_weight == 0:
        deadline_weight = Decimal("1")
    result = priority_score(
        _Case(risk_probability=None, stage_deadline=None, aggregate_awarded=Decimal("0")),
        weights=PriorityWeights(risk_weight, deadline_weight, value_weight, "degenerate-v1"),
        reference_amount=Decimal("100000"),
        as_of=NOW.date(),
    )

    assert result.score == Decimal("0.000")
    assert result.weight_version == "degenerate-v1"
    assert Decimal("0") <= result.score <= Decimal("100")
