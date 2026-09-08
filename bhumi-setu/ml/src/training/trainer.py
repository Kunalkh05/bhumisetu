"""Deterministic trainer primitives for delay-risk models."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable, Mapping, Sequence

from sqlalchemy.orm import Session

from app.errors import NotAuthorised
from app.models.event import ActorType, Event, Provenance
from app.security.access import Principal
from features.builder import FeatureRow
from labelling.definition import LabelDefinition, LabelOutcome

__all__ = [
    "MetricSet",
    "PromotionThresholds",
    "TrainingExample",
    "TrainingReport",
    "TrainingSplit",
    "expected_calibration_error",
    "fit_isotonic_calibrator",
    "metric_set",
    "quantile_bins",
    "train_model",
    "temporal_split",
]

MODEL_ADMINISTER = "model.administer"
BASE_RATE_SHIFT_THRESHOLD = 0.10


@dataclass(frozen=True)
class TrainingExample:
    feature_row: FeatureRow
    outcome: LabelOutcome
    raw_probability: float
    deadline_rule_probability: float

    @property
    def reference_t(self) -> datetime:
        return self.feature_row.reference_t


@dataclass(frozen=True)
class TrainingSplit:
    train_rows: tuple[TrainingExample, ...]
    eval_rows: tuple[TrainingExample, ...]
    censored_count: int
    censoring_rate: float


@dataclass(frozen=True)
class MetricSet:
    auprc: float
    auroc: float
    brier: float
    ece: float
    pr_lift: float
    train_base_rate: float
    eval_base_rate: float
    train_rows: int
    eval_rows: int

    def meets(self, thresholds: "PromotionThresholds") -> bool:
        return (
            self.pr_lift >= thresholds.min_pr_lift
            and self.auprc >= thresholds.min_auprc
            and self.auroc >= thresholds.min_auroc
            and self.ece <= thresholds.max_ece
        )


@dataclass(frozen=True)
class PromotionThresholds:
    min_pr_lift: float
    min_auprc: float
    min_auroc: float
    max_ece: float


@dataclass(frozen=True)
class IsotonicCalibrator:
    thresholds: tuple[float, ...]
    probabilities: tuple[float, ...]

    def predict_one(self, score: float) -> float:
        for threshold, probability in zip(self.thresholds, self.probabilities):
            if score <= threshold:
                return probability
        return self.probabilities[-1]

    def predict(self, scores: Iterable[float]) -> tuple[float, ...]:
        return tuple(self.predict_one(score) for score in scores)


@dataclass(frozen=True)
class TrainingReport:
    promotion_state: str
    metrics: MetricSet
    baseline_metrics: MetricSet
    feature_reference_bins: Mapping[str, tuple[float, ...]]
    hyperparameters: Mapping[str, object]
    censored_count: int
    censoring_rate: float
    label_definition_version: str
    feature_set_version: str
    training_window_start: datetime
    training_window_end: datetime
    promoted_by: str | None
    base_rate_shift_event_id: int | None = None
    withheld_event_id: int | None = None


def temporal_split(
    rows: Sequence[TrainingExample],
    *,
    eval_fraction: float,
) -> TrainingSplit:
    labelled = tuple(sorted(rows, key=lambda row: row.reference_t))
    censored = tuple(row for row in labelled if row.outcome.label == "CENSORED")
    usable = tuple(row for row in labelled if row.outcome.label != "CENSORED")
    if not 0 < eval_fraction < 1:
        raise ValueError("eval_fraction must be between 0 and 1")
    if len(usable) < 2:
        raise ValueError("at least two non-censored rows are required")

    eval_count = max(1, math.ceil(len(usable) * eval_fraction))
    train_count = len(usable) - eval_count
    if train_count < 1:
        train_count = 1
        eval_count = len(usable) - train_count

    train_rows = usable[:train_count]
    eval_rows = usable[train_count:]
    if train_rows[-1].reference_t >= eval_rows[0].reference_t:
        raise ValueError("temporal split requires eval reference_t later than train")
    return TrainingSplit(
        train_rows=train_rows,
        eval_rows=eval_rows,
        censored_count=len(censored),
        censoring_rate=len(censored) / len(labelled),
    )


def fit_isotonic_calibrator(rows: Sequence[TrainingExample]) -> IsotonicCalibrator:
    pairs = sorted((row.raw_probability, _label_int(row)) for row in rows)
    blocks = [[score, score, float(label), 1] for score, label in pairs]
    index = 0
    while index < len(blocks) - 1:
        if blocks[index][2] <= blocks[index + 1][2]:
            index += 1
            continue
        left = blocks[index]
        right = blocks.pop(index + 1)
        total = left[3] + right[3]
        left[1] = right[1]
        left[2] = ((left[2] * left[3]) + (right[2] * right[3])) / total
        left[3] = total
        index = max(index - 1, 0)
    return IsotonicCalibrator(
        thresholds=tuple(block[1] for block in blocks),
        probabilities=tuple(block[2] for block in blocks),
    )


def metric_set(
    *,
    train_rows: Sequence[TrainingExample],
    eval_rows: Sequence[TrainingExample],
    eval_probabilities: Sequence[float],
) -> MetricSet:
    train_labels = [_label_int(row) for row in train_rows]
    eval_labels = [_label_int(row) for row in eval_rows]
    eval_base = _base_rate(eval_labels)
    auprc = _average_precision(eval_labels, eval_probabilities)
    return MetricSet(
        auprc=auprc,
        auroc=_auroc(eval_labels, eval_probabilities),
        brier=_brier(eval_labels, eval_probabilities),
        ece=expected_calibration_error(eval_labels, eval_probabilities, n_bins=10),
        pr_lift=(auprc - eval_base) / (1 - eval_base) if eval_base < 1 else 0.0,
        train_base_rate=_base_rate(train_labels),
        eval_base_rate=eval_base,
        train_rows=len(train_rows),
        eval_rows=len(eval_rows),
    )


def train_model(
    session: Session,
    *,
    rows: Sequence[TrainingExample],
    label_definition: LabelDefinition,
    feature_set_version: str,
    thresholds: PromotionThresholds,
    actor: Principal,
    eval_fraction: float,
    hyperparameters: Mapping[str, object],
    now: datetime | None = None,
) -> TrainingReport:
    if not actor.has_permission(MODEL_ADMINISTER):
        raise NotAuthorised()
    now = now or datetime.now(UTC)
    split = temporal_split(rows, eval_fraction=eval_fraction)
    _assert_one_label_definition(rows, label_definition.version)

    calibrator = fit_isotonic_calibrator(split.train_rows)
    probabilities = calibrator.predict(row.raw_probability for row in split.eval_rows)
    metrics = metric_set(
        train_rows=split.train_rows,
        eval_rows=split.eval_rows,
        eval_probabilities=probabilities,
    )
    baseline_metrics = metric_set(
        train_rows=split.train_rows,
        eval_rows=split.eval_rows,
        eval_probabilities=[row.deadline_rule_probability for row in split.eval_rows],
    )

    shift_event = _record_base_rate_shift(session, metrics, actor, now)
    promoted = metrics.meets(thresholds)
    withheld_event = None if promoted else _record_withheld(session, metrics, actor, now)
    session.flush()

    return TrainingReport(
        promotion_state="PROMOTED" if promoted else "WITHHELD",
        metrics=metrics,
        baseline_metrics=baseline_metrics,
        feature_reference_bins=quantile_bins(split.train_rows),
        hyperparameters=dict(hyperparameters),
        censored_count=split.censored_count,
        censoring_rate=split.censoring_rate,
        label_definition_version=label_definition.version,
        feature_set_version=feature_set_version,
        training_window_start=split.train_rows[0].reference_t,
        training_window_end=split.eval_rows[-1].reference_t,
        promoted_by=actor.id if promoted else None,
        base_rate_shift_event_id=getattr(shift_event, "id", None),
        withheld_event_id=getattr(withheld_event, "id", None),
    )


def quantile_bins(
    rows: Sequence[TrainingExample],
    *,
    n_bins: int = 10,
) -> dict[str, tuple[float, ...]]:
    names = sorted({
        name
        for row in rows
        for name, value in row.feature_row.model_input.items()
        if not name.endswith("_is_missing") and not math.isnan(value)
    })
    result: dict[str, tuple[float, ...]] = {}
    for name in names:
        values = sorted(
            row.feature_row.model_input[name]
            for row in rows
            if name in row.feature_row.model_input
            and not math.isnan(row.feature_row.model_input[name])
        )
        if not values:
            continue
        result[name] = tuple(_quantile(values, q / n_bins) for q in range(1, n_bins))
    return result


def expected_calibration_error(
    labels: Sequence[int],
    probabilities: Sequence[float],
    *,
    n_bins: int,
) -> float:
    if len(labels) != len(probabilities):
        raise ValueError("labels and probabilities must have the same length")
    total = len(labels)
    if total == 0:
        raise ValueError("at least one label is required")
    error = 0.0
    for index in range(n_bins):
        lower = index / n_bins
        upper = (index + 1) / n_bins
        in_bin = []
        for label, prob in zip(labels, probabilities):
            upper_match = prob <= upper if index == n_bins - 1 else prob < upper
            if lower <= prob and upper_match:
                in_bin.append((label, prob))
        if not in_bin:
            continue
        avg_prob = sum(prob for _, prob in in_bin) / len(in_bin)
        avg_label = sum(label for label, _ in in_bin) / len(in_bin)
        error += (len(in_bin) / total) * abs(avg_prob - avg_label)
    return error


def _assert_one_label_definition(
    rows: Sequence[TrainingExample],
    expected_version: str,
) -> None:
    versions = {row.outcome.label_definition_version for row in rows}
    if versions != {expected_version}:
        raise ValueError(f"mixed label_definition_version in training set: {sorted(versions)}")


def _record_base_rate_shift(
    session: Session,
    metrics: MetricSet,
    actor: Principal,
    now: datetime,
) -> Event | None:
    if abs(metrics.eval_base_rate - metrics.train_base_rate) <= BASE_RATE_SHIFT_THRESHOLD:
        return None
    event = _event(
        "LABEL_BASE_RATE_SHIFT",
        actor,
        now,
        {
            "train_base_rate": metrics.train_base_rate,
            "eval_base_rate": metrics.eval_base_rate,
        },
    )
    session.add(event)
    return event


def _record_withheld(
    session: Session,
    metrics: MetricSet,
    actor: Principal,
    now: datetime,
) -> Event:
    event = _event(
        "MODEL_PROMOTION_WITHHELD",
        actor,
        now,
        {
            "auprc": metrics.auprc,
            "auroc": metrics.auroc,
            "brier": metrics.brier,
            "ece": metrics.ece,
            "pr_lift": metrics.pr_lift,
        },
    )
    session.add(event)
    return event


def _event(
    event_type: str,
    actor: Principal,
    now: datetime,
    payload: Mapping[str, object],
) -> Event:
    return Event(
        event_type=event_type,
        entity_type="ml_model_version",
        entity_id=0,
        case_id=None,
        actor_type=ActorType.SYSTEM if actor.kind == "SERVICE" else actor.kind,
        actor_id=actor.id,
        occurrence_time=now,
        payload=dict(payload),
        has_pd_refs=False,
        provenance=Provenance.SYSTEM,
    )


def _label_int(row: TrainingExample) -> int:
    if row.outcome.label == "DELAYED":
        return 1
    if row.outcome.label == "NOT_DELAYED":
        return 0
    raise ValueError("censored rows cannot be scored")


def _base_rate(labels: Sequence[int]) -> float:
    return sum(labels) / len(labels) if labels else 0.0


def _average_precision(labels: Sequence[int], scores: Sequence[float]) -> float:
    pairs = sorted(zip(scores, labels), reverse=True)
    positives = sum(labels)
    if positives == 0:
        return 0.0
    seen_positive = 0
    precision_sum = 0.0
    for index, (_, label) in enumerate(pairs, start=1):
        if label:
            seen_positive += 1
            precision_sum += seen_positive / index
    return precision_sum / positives


def _auroc(labels: Sequence[int], scores: Sequence[float]) -> float:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return 0.5
    ranks = _average_ranks(scores)
    positive_rank_sum = sum(rank for rank, label in zip(ranks, labels) if label)
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def _average_ranks(scores: Sequence[float]) -> list[float]:
    ordered = sorted(enumerate(scores), key=lambda item: item[1])
    ranks = [0.0] * len(scores)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        rank = (index + 1 + end) / 2
        for original, _ in ordered[index:end]:
            ranks[original] = rank
        index = end
    return ranks


def _brier(labels: Sequence[int], scores: Sequence[float]) -> float:
    return sum((score - label) ** 2 for label, score in zip(labels, scores)) / len(labels)


def _quantile(values: Sequence[float], q: float) -> float:
    position = (len(values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight
