"""Pure delay label definition and labelling function."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Protocol

from features.asof import AsOfView, StageEntry
from labelling.sources import LABEL_SOURCE_ATTRIBUTES

__all__ = [
    "DeadlineBaseline",
    "DeadlineResolver",
    "LabelDefinition",
    "LabelOutcome",
    "STATUTORY_WINDOW_DAYS_SEC11_TO_SEC19",
    "STATUTORY_WINDOW_DAYS_SEC19_TO_AWARD",
    "TRANSITION_CASE_INITIATION_TO_MILESTONE",
    "TRANSITION_SECTION_11_TO_SECTION_19",
    "TRANSITION_SECTION_19_TO_AWARD",
    "label_row",
    "resolve_deadline",
    "survival_definition",
]

TRANSITION_SECTION_11_TO_SECTION_19 = "SECTION_11_TO_SECTION_19"
TRANSITION_SECTION_19_TO_AWARD = "SECTION_19_TO_AWARD"
TRANSITION_CASE_INITIATION_TO_MILESTONE = "CASE_INITIATION_TO_MILESTONE"

STATUTORY_WINDOW_DAYS_SEC11_TO_SEC19 = 365
STATUTORY_WINDOW_DAYS_SEC19_TO_AWARD = 365

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
    if definition.formulation == "SURVIVAL_STAGE_EXIT":
        return _label_survival_row(
            view,
            t,
            definition=definition,
            deadline=deadline,
            now=now,
        )

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
    from_stage = None
    if (
        definition.stage_transitions_in_scope != "ALL_NON_TERMINAL"
        and definition.stage_transitions_in_scope
    ):
        from_stage, _ = _parse_transition(definition.stage_transitions_in_scope[0])
    entry_event = (
        _find_entry_event(
            view,
            from_stage,
            datetime.combine(as_of, datetime.min.time(), tzinfo=timezone.utc),
        )
        if from_stage
        else None
    )
    entered = entry_event.occurrence_time.date() if entry_event else _stage_entered_on_or_none(view)
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


def survival_definition(
    transition: str = TRANSITION_SECTION_11_TO_SECTION_19,
    *,
    version: str = "survival-v1",
    statutory_window_days: int = 365,
    horizon_days: int = 365,
) -> LabelDefinition:
    """Convenience factory for statutory survival target definitions."""
    return LabelDefinition(
        version=version,
        formulation="SURVIVAL_STAGE_EXIT",
        stage_transitions_in_scope=(transition,),
        deadline_baseline=DeadlineBaseline(
            kind="FIXED_DAYS",
            fixed_days=statutory_window_days,
        ),
        baseline_fallback=None,
        horizon_days=horizon_days,
        censoring="SURVIVAL_RETAIN",
    )


def _normalize_stage_key(key: str) -> str:
    cleaned = key.strip().upper()
    if cleaned.startswith("STAGE_"):
        cleaned = cleaned[6:]
    aliases = {
        "PN": "SECTION_11",
        "PRELIMINARY_NOTIFICATION": "SECTION_11",
        "PRELIMINARY_NOTICE": "SECTION_11",
        "SEC_11": "SECTION_11",
        "SEC11": "SECTION_11",
        "S11": "SECTION_11",
        "DECLARATION": "SECTION_19",
        "SEC_19": "SECTION_19",
        "SEC19": "SECTION_19",
        "S19": "SECTION_19",
        "NOTICE_CLAIMS": "SECTION_21",
        "CLAIMS_NOTICE": "SECTION_21",
        "SEC_21": "SECTION_21",
        "SEC21": "SECTION_21",
        "S21": "SECTION_21",
        "FINAL_AWARD": "AWARD",
        "INTAKE": "CASE_INITIATION",
        "FIRST_NOTICE": "CASE_INITIATION",
        "INITIATION": "CASE_INITIATION",
    }
    return aliases.get(cleaned, cleaned)


def _stages_match(stage_key_in_event: str, target_stage_key: str) -> bool:
    if stage_key_in_event.upper() == target_stage_key.upper():
        return True
    norm_event = _normalize_stage_key(stage_key_in_event)
    norm_target = _normalize_stage_key(target_stage_key)
    if norm_event == norm_target:
        return True
    if norm_target == "MILESTONE":
        return norm_event in {"SECTION_19", "SECTION_21", "AWARD"}
    return False


def _parse_transition(transition: str) -> tuple[str | None, str]:
    cleaned = transition.strip()
    if "->" in cleaned:
        parts = cleaned.split("->", 1)
        return parts[0].strip(), parts[1].strip()
    if "_TO_" in cleaned.upper():
        parts = cleaned.upper().split("_TO_", 1)
        return parts[0].strip(), parts[1].strip()
    return None, cleaned


def _find_entry_event(
    view: AsOfView,
    from_stage: str | None,
    t: datetime,
) -> StageEntry | None:
    if not view.stage_history:
        return None
    if from_stage is not None:
        norm_from = _normalize_stage_key(from_stage)
        if norm_from == "CASE_INITIATION":
            return min(view.stage_history, key=lambda s: s.occurrence_time)
        for entry in view.stage_history:
            if _stages_match(entry.stage_key, from_stage):
                return entry
        return None
    candidates = [s for s in view.stage_history if s.occurrence_time <= t]
    if candidates:
        return candidates[-1]
    return view.stage_history[0]


def _find_exit_event(
    view: AsOfView,
    entry_event: StageEntry,
    to_stage: str,
) -> StageEntry | None:
    candidates: list[StageEntry] = []
    for entry in view.stage_history:
        if entry.event_id == entry_event.event_id:
            continue
        if to_stage == "ALL_NON_TERMINAL":
            if entry.occurrence_time >= entry_event.occurrence_time:
                candidates.append(entry)
        elif _stages_match(entry.stage_key, to_stage):
            candidates.append(entry)

    if not candidates:
        return None
    candidates.sort(key=lambda s: s.occurrence_time)
    return candidates[0]


def _label_survival_row(
    view: AsOfView,
    t: datetime,
    *,
    definition: LabelDefinition,
    deadline: date | None,
    now: date,
) -> LabelOutcome:
    from_stage: str | None = None
    to_stage = "ALL_NON_TERMINAL"
    if definition.stage_transitions_in_scope != "ALL_NON_TERMINAL":
        if not definition.stage_transitions_in_scope:
            raise ValueError("stage_transitions_in_scope cannot be empty for SURVIVAL_STAGE_EXIT")
        first_transition = definition.stage_transitions_in_scope[0]
        from_stage, to_stage = _parse_transition(first_transition)

    entry_event = _find_entry_event(view, from_stage, t)
    if entry_event is None:
        raise ValueError(
            f"Missing stage entry date for survival labelling (target: {from_stage or 'current'} -> {to_stage})"
        )

    entry_date = entry_event.occurrence_time.date()

    if now < entry_date:
        raise ValueError(
            f"Observation cutoff ({now}) cannot precede stage entry date ({entry_date})"
        )

    exit_event = _find_exit_event(view, entry_event, to_stage)

    if exit_event is not None and exit_event.occurrence_time.date() < entry_date:
        raise ValueError(
            f"Event date ({exit_event.occurrence_time.date()}) cannot precede entry date ({entry_date})"
        )

    if exit_event is not None and exit_event.occurrence_time.date() <= now:
        exit_date = exit_event.occurrence_time.date()
        t_days = (exit_date - entry_date).days
        if t_days < 0:
            raise ValueError(f"Negative duration impossible: {t_days} days")

        if deadline is not None and exit_date > deadline:
            label: Literal["DELAYED", "NOT_DELAYED", "CENSORED"] = "DELAYED"
            reason = "EXIT_AFTER_DEADLINE"
        elif deadline is not None and exit_date <= deadline:
            label = "NOT_DELAYED"
            reason = "EXITED_BY_DEADLINE"
        else:
            label = "NOT_DELAYED"
            reason = "EVENT_OBSERVED"

        return LabelOutcome(
            label=label,
            time_to_event_days=t_days,
            event_observed=True,
            reason=reason,
            label_definition_version=definition.version,
        )

    t_days = (now - entry_date).days
    if t_days < 0:
        raise ValueError(f"Negative duration impossible: {t_days} days")

    return LabelOutcome(
        label="CENSORED",
        time_to_event_days=t_days,
        event_observed=False,
        reason="RIGHT_CENSORED",
        label_definition_version=definition.version,
    )

