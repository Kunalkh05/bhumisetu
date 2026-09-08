"""Pure delay label definition and labelling function."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal, Protocol

from features.asof import AsOfView, StageEntry
from labelling.sources import LABEL_SOURCE_ATTRIBUTES

__all__ = [
    "DeadlineBaseline",
    "DeadlineResolver",
    "LabelDefinition",
    "LabelOutcome",
    "label_row",
    "resolve_deadline",
]

Formulation = Literal["BINARY_STAGE_EXIT", "SURVIVAL_STAGE_EXIT"]
Censoring = Literal["EXCLUDE", "SURVIVAL_RETAIN"]
BaselineKind = Literal["STATUTORY_PERIOD", "HISTORICAL_PERCENTILE", "FIXED_DAYS"]


class DeadlineResolver(Protocol):
    def get(self, key: str, *, state: str, act: str | None, as_of: date) -> int:
        ...


@dataclass(frozen=True)
class DeadlineBaseline:
    kind: BaselineKind
    period_key: str | None = None
    percentile: float | None = None
    fixed_days: int | None = None

    def __post_init__(self) -> None:
        if self.kind == "STATUTORY_PERIOD" and not self.period_key:
            raise ValueError("STATUTORY_PERIOD baseline requires period_key")
        if self.kind == "HISTORICAL_PERCENTILE" and self.percentile is None:
            raise ValueError("HISTORICAL_PERCENTILE baseline requires percentile")
        if self.kind == "FIXED_DAYS" and self.fixed_days is None:
            raise ValueError("FIXED_DAYS baseline requires fixed_days")


@dataclass(frozen=True)
class LabelDefinition:
    version: str
    formulation: Formulation
    stage_transitions_in_scope: tuple[str, ...] | Literal["ALL_NON_TERMINAL"]
    deadline_baseline: DeadlineBaseline
    baseline_fallback: DeadlineBaseline | None
    horizon_days: int
    censoring: Censoring
    source_attributes: frozenset[str] = LABEL_SOURCE_ATTRIBUTES

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("label definition version is required")
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive")


@dataclass(frozen=True)
class LabelOutcome:
    label: Literal["DELAYED", "NOT_DELAYED", "CENSORED"]
    time_to_event_days: int | None
    event_observed: bool | None
    reason: str
    label_definition_version: str


def label_row(
    view: AsOfView,
    t: datetime,
    *,
    definition: LabelDefinition,
    deadline: date | None,
    now: date,
) -> LabelOutcome:
    """Label one row from supplied inputs only: no DB, config lookup, or clock."""
    horizon_end = t.date() + timedelta(days=definition.horizon_days)
    exit_event = _stage_exit_after(view, t, definition)

    if horizon_end > now:
        return _outcome("CENSORED", None, False, "HORIZON_NOT_ELAPSED", definition)
    if deadline is None or deadline > horizon_end:
        return _outcome("CENSORED", None, False, "DEADLINE_BEYOND_HORIZON", definition)
    if exit_event is None or exit_event.occurrence_time.date() > deadline:
        days = _days_to_event(t, exit_event) if exit_event else None
        return _outcome("DELAYED", days, exit_event is not None, "NO_EXIT_BY_DEADLINE", definition)
    return _outcome(
        "NOT_DELAYED",
        _days_to_event(t, exit_event),
        True,
        "EXITED_BY_DEADLINE",
        definition,
    )


def resolve_deadline(
    view: AsOfView,
    *,
    definition: LabelDefinition,
    resolver: DeadlineResolver,
    state: str,
    act: str | None,
    as_of: date,
) -> date | None:
    """Resolve the deadline outside ``label_row`` from definition configuration."""
    entered = _stage_entered_on_or_none(view)
    if entered is None:
        return None
    return _resolve_with(
        definition.deadline_baseline,
        view,
        entered,
        resolver=resolver,
        state=state,
        act=act,
        as_of=as_of,
    ) or (
        _resolve_with(
            definition.baseline_fallback,
            view,
            entered,
            resolver=resolver,
            state=state,
            act=act,
            as_of=as_of,
        )
        if definition.baseline_fallback is not None
        else None
    )


def _resolve_with(
    baseline: DeadlineBaseline | None,
    view: AsOfView,
    entered: date,
    *,
    resolver: DeadlineResolver,
    state: str,
    act: str | None,
    as_of: date,
) -> date | None:
    if baseline is None:
        return None
    if baseline.kind == "STATUTORY_PERIOD":
        days = resolver.get(baseline.period_key or "", state=state, act=act, as_of=as_of)
    elif baseline.kind == "HISTORICAL_PERCENTILE":
        days = _historical_percentile_days(view, baseline.percentile or 0)
    else:
        days = baseline.fixed_days or 0
    return entered + timedelta(days=days) if days else None


def _stage_entered_on_or_none(view: AsOfView) -> date | None:
    if not view.stage_history:
        return None
    return view.stage_history[-1].occurrence_time.date()


def _stage_exit_after(
    view: AsOfView,
    t: datetime,
    definition: LabelDefinition,
) -> StageEntry | None:
    current = _stage_at_or_before(view, t)
    for entry in view.stage_history:
        if entry.occurrence_time <= t:
            continue
        if _transition_in_scope(current, entry.stage_key, definition):
            return entry
    return None


def _stage_at_or_before(view: AsOfView, t: datetime) -> str | None:
    current: str | None = None
    for entry in view.stage_history:
        if entry.occurrence_time <= t:
            current = entry.stage_key
    return current


def _transition_in_scope(
    current: str | None,
    target: str,
    definition: LabelDefinition,
) -> bool:
    scope = definition.stage_transitions_in_scope
    if scope == "ALL_NON_TERMINAL":
        return True
    return target in scope or (current is not None and f"{current}->{target}" in scope)


def _days_to_event(t: datetime, event: StageEntry) -> int:
    return (event.occurrence_time.date() - t.date()).days


def _historical_percentile_days(view: AsOfView, percentile: float) -> int:
    if not view.stage_history:
        return 0
    return max(int(round(percentile)), 0)


def _outcome(
    label: Literal["DELAYED", "NOT_DELAYED", "CENSORED"],
    time_to_event_days: int | None,
    event_observed: bool | None,
    reason: str,
    definition: LabelDefinition,
) -> LabelOutcome:
    return LabelOutcome(
        label=label,
        time_to_event_days=time_to_event_days,
        event_observed=event_observed,
        reason=reason,
        label_definition_version=definition.version,
    )
