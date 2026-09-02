"""Priority score computation for the intervention queue."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.models.acquisition_case import AcquisitionCase
from app.services.policy import PolicyResolver

__all__ = [
    "PriorityInputs",
    "PriorityResult",
    "PriorityWeights",
    "priority_score",
    "recompute_priority",
    "should_trigger_priority",
]

PRIORITY_WEIGHTS_KEY = "priority.weights"
PRIORITY_REFERENCE_AMOUNT_KEY = "priority.reference_amount"
PRIORITY_TRIGGER_ATTRIBUTES = frozenset(
    {
        "risk_probability",
        "risk_band",
        "risk_generated_at",
        "stage_deadline",
        "stage_entered_on",
        "aggregate_awarded",
    }
)


@dataclass(frozen=True)
class PriorityWeights:
    risk: Decimal
    deadline: Decimal
    value: Decimal
    version: str

    @property
    def total(self) -> Decimal:
        return self.risk + self.deadline + self.value


@dataclass(frozen=True)
class PriorityInputs:
    risk_probability: Decimal
    deadline_pressure: Decimal
    case_value: Decimal


@dataclass(frozen=True)
class PriorityResult:
    score: Decimal
    weight_version: str
    inputs: PriorityInputs


def priority_score(
    case: AcquisitionCase,
    *,
    weights: PriorityWeights,
    reference_amount: Decimal,
    as_of: date,
) -> PriorityResult:
    """Compute a bounded score in [0, 100] from risk, deadline pressure and value."""
    if weights.total <= 0:
        raise ValueError("priority weights must have positive total")
    if reference_amount <= 0:
        raise ValueError("priority reference amount must be positive")

    inputs = PriorityInputs(
        risk_probability=_clamp(_decimal(case.risk_probability or 0)),
        deadline_pressure=_deadline_pressure(case, as_of),
        case_value=_clamp(_decimal(case.aggregate_awarded or 0) / reference_amount),
    )
    raw = (
        weights.risk * inputs.risk_probability
        + weights.deadline * inputs.deadline_pressure
        + weights.value * inputs.case_value
    )
    score = _clamp(raw / weights.total) * Decimal("100")
    return PriorityResult(
        score=score.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
        weight_version=weights.version,
        inputs=inputs,
    )


def recompute_priority(
    session: Session,
    *,
    case: AcquisitionCase,
    resolver: PolicyResolver,
    now: datetime | None = None,
) -> PriorityResult:
    """Resolve configuration, compute, and denormalize the current priority score."""
    timestamp = now or datetime.now(UTC)
    weights = _priority_weights(
        resolver.get(
            PRIORITY_WEIGHTS_KEY,
            state=case.state_key,
            act=case.act_key,
            as_of=timestamp.date(),
        )
    )
    reference_amount = _decimal(
        resolver.get(
            PRIORITY_REFERENCE_AMOUNT_KEY,
            state=case.state_key,
            act=case.act_key,
            as_of=timestamp.date(),
        )
    )
    result = priority_score(
        case,
        weights=weights,
        reference_amount=reference_amount,
        as_of=timestamp.date(),
    )
    case.priority_score = result.score
    case.priority_weight_version = result.weight_version
    case.priority_computed_at = timestamp
    session.flush()
    return result


def should_trigger_priority(
    event_type: str,
    *,
    changed_attributes: set[str] | frozenset[str] | None = None,
) -> bool:
    return event_type in PRIORITY_TRIGGER_ATTRIBUTES or bool(
        (changed_attributes or set()) & PRIORITY_TRIGGER_ATTRIBUTES
    )


def _priority_weights(value: Mapping[str, Any]) -> PriorityWeights:
    raw_weights = value.get("weights", value)
    return PriorityWeights(
        risk=_decimal(raw_weights.get("risk", 0)),
        deadline=_decimal(raw_weights.get("deadline", raw_weights.get("pressure", 0))),
        value=_decimal(raw_weights.get("value", 0)),
        version=str(value.get("version", value.get("policy_version", PRIORITY_WEIGHTS_KEY))),
    )


def _deadline_pressure(case: AcquisitionCase, as_of: date) -> Decimal:
    if case.stage_deadline is None:
        return Decimal("0")
    period_days = (case.stage_deadline - case.stage_entered_on).days
    if period_days <= 0:
        return Decimal("1")
    remaining_days = (case.stage_deadline - as_of).days
    return _clamp(Decimal("1") - (Decimal(remaining_days) / Decimal(period_days)))


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("1"), value))


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))
