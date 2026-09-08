"""Calibration, drift and watchdog checks for promoted models."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy.orm import Session

from app.db.outbox import enqueue
from app.models.event import ActorType, Event, Provenance
from app.models.ml import MLModelVersion, MLMonitorRun

__all__ = [
    "CalibrationGroup",
    "CalibrationObservation",
    "DriftResult",
    "MonitoringState",
    "calibration_groups",
    "check_watchdog",
    "feature_drift",
    "maybe_trigger_model_age",
    "monitor_calibration",
    "monitor_drift",
    "psi",
    "supersede_model",
]

EPS = 1e-6
MODEL_ADMINISTER = "model.administer"


class Notifier(Protocol):
    def notify_permission_holders(
        self,
        permission: str,
        *,
        event_type: str,
        payload: Mapping[str, object],
    ) -> None:
        ...


EnqueueTraining = Callable[[Session, MLModelVersion, str, Mapping[str, object]], None]


@dataclass(frozen=True)
class CalibrationObservation:
    case_id: int
    risk_band: str
    risk_probability: float
    delayed: bool


@dataclass(frozen=True)
class CalibrationGroup:
    risk_band: str
    realized_delay_rate: float
    mean_risk_probability: float
    case_count: int
    divergence: float


@dataclass(frozen=True)
class DriftResult:
    feature_name: str
    drift: float
    threshold: float
    training_window_start: datetime
    training_window_end: datetime
    inference_window_start: datetime
    inference_window_end: datetime


@dataclass(frozen=True)
class MonitoringState:
    state: str
    last_successful_at: datetime | None
    reason: str | None = None


def calibration_groups(
    observations: Iterable[CalibrationObservation],
) -> tuple[CalibrationGroup, ...]:
    """Group realized outcomes by the band assigned at prediction time."""
    by_band: dict[str, list[CalibrationObservation]] = defaultdict(list)
    for observation in observations:
        by_band[observation.risk_band].append(observation)
    return tuple(
        CalibrationGroup(
            risk_band=band,
            realized_delay_rate=sum(row.delayed for row in rows) / len(rows),
            mean_risk_probability=sum(row.risk_probability for row in rows) / len(rows),
            case_count=len(rows),
            divergence=abs(
                (sum(row.delayed for row in rows) / len(rows))
                - (sum(row.risk_probability for row in rows) / len(rows))
            ),
        )
        for band, rows in sorted(by_band.items())
    )


def psi(
    training_values: Sequence[float | None],
    inference_values: Sequence[float | None],
    edges: Sequence[float],
) -> float:
    """Population stability index with an additional missing-value bucket."""
    if not training_values or not inference_values:
        raise ValueError("PSI requires non-empty training and inference populations")
    train_counts = _bucket_counts(training_values, edges)
    inference_counts = _bucket_counts(inference_values, edges)
    total_train = len(training_values)
    total_inference = len(inference_values)
    value = 0.0
    for train_count, inference_count in zip(train_counts, inference_counts, strict=True):
        expected = max(train_count / total_train, EPS)
        actual = max(inference_count / total_inference, EPS)
        value += (actual - expected) * math.log(actual / expected)
    return value


def feature_drift(
    *,
    feature_name: str,
    reference_values: Sequence[float | None],
    inference_values: Sequence[float | None],
    edges: Sequence[float],
    threshold: float,
    training_window_start: datetime,
    training_window_end: datetime,
    inference_window_start: datetime,
    inference_window_end: datetime,
) -> DriftResult:
    return DriftResult(
        feature_name=feature_name,
        drift=psi(reference_values, inference_values, edges),
        threshold=threshold,
        training_window_start=training_window_start,
        training_window_end=training_window_end,
        inference_window_start=inference_window_start,
        inference_window_end=inference_window_end,
    )


def monitor_calibration(
    session: Session,
    *,
    model_version: MLModelVersion,
    observations: Sequence[CalibrationObservation],
    divergence_threshold: float,
    min_evaluable_count: int,
    now: datetime | None = None,
    notifier: Notifier | None = None,
    enqueue_training: EnqueueTraining | None = None,
) -> tuple[CalibrationGroup, ...]:
    now = now or datetime.now(UTC)
    run = _start_run(session, model_version, "CALIBRATION", now)
    if len(observations) < min_evaluable_count:
        run.state = "WITHHELD"
        run.finished_at = now
        run.withholding_reason = "MIN_EVALUABLE_CASE_COUNT"
        run.evaluable_case_count = len(observations)
        session.flush()
        return ()

    groups = calibration_groups(observations)
    run.results = {"groups": [group.__dict__ for group in groups]}
    run.evaluable_case_count = len(observations)
    triggered = False
    for group in groups:
        if group.divergence > divergence_threshold:
            payload = {
                "risk_band": group.risk_band,
                "realized_delay_rate": group.realized_delay_rate,
                "mean_risk_probability": group.mean_risk_probability,
                "case_count": group.case_count,
                "threshold": divergence_threshold,
            }
            _record_event(session, model_version, "MODEL_CALIBRATION_DIVERGED", now, payload)
            _notify(notifier, "MODEL_CALIBRATION_DIVERGED", payload)
            if not triggered:
                _trigger_retraining(
                    session,
                    model_version,
                    now,
                    "CALIBRATION_DIVERGENCE",
                    payload,
                    enqueue_training,
                )
                triggered = True

    run.state = "SUCCEEDED"
    run.finished_at = now
    session.flush()
    return groups


def monitor_drift(
    session: Session,
    *,
    model_version: MLModelVersion,
    drift_results: Sequence[DriftResult],
    min_drifted_feature_count: int,
    now: datetime | None = None,
    notifier: Notifier | None = None,
    enqueue_training: EnqueueTraining | None = None,
) -> tuple[DriftResult, ...]:
    now = now or datetime.now(UTC)
    run = _start_run(session, model_version, "DRIFT", now)
    drifted = tuple(result for result in drift_results if result.drift > result.threshold)
    run.results = {"drifted_features": [result.feature_name for result in drifted]}
    for result in drifted:
        payload = {
            "feature_name": result.feature_name,
            "feature_drift": result.drift,
            "threshold": result.threshold,
            "training_window_start": result.training_window_start.isoformat(),
            "training_window_end": result.training_window_end.isoformat(),
            "inference_window_start": result.inference_window_start.isoformat(),
            "inference_window_end": result.inference_window_end.isoformat(),
        }
        _record_event(session, model_version, "FEATURE_DRIFT_DETECTED", now, payload)
        _notify(notifier, "FEATURE_DRIFT_DETECTED", payload)

    if len(drifted) >= min_drifted_feature_count:
        _trigger_retraining(
            session,
            model_version,
            now,
            "FEATURE_DRIFT",
            {"drifted_feature_names": [result.feature_name for result in drifted]},
            enqueue_training,
        )
    run.state = "SUCCEEDED"
    run.finished_at = now
    session.flush()
    return drifted


def check_watchdog(
    session: Session,
    *,
    model_version: MLModelVersion,
    last_successful_at: datetime | None,
    cadence: timedelta,
    now: datetime | None = None,
    reason: str = "CADENCE_OVERRUN",
) -> MonitoringState:
    now = now or datetime.now(UTC)
    if last_successful_at is not None and now <= last_successful_at + cadence * 1.5:
        return MonitoringState("AVAILABLE", last_successful_at)
    payload = {
        "reason": reason,
        "last_successful_computation_time": last_successful_at.isoformat()
        if last_successful_at is not None
        else None,
    }
    _record_event(session, model_version, "MODEL_MONITORING_UNAVAILABLE", now, payload)
    session.add(
        MLMonitorRun(
            model_version_id=model_version.id,
            kind="WATCHDOG",
            started_at=now,
            finished_at=now,
            state="UNAVAILABLE",
            withholding_reason=reason,
            evaluable_case_count=None,
            results=payload,
        )
    )
    session.flush()
    return MonitoringState("UNAVAILABLE", last_successful_at, reason)


def maybe_trigger_model_age(
    session: Session,
    *,
    model_version: MLModelVersion,
    max_model_age_days: int,
    now: datetime | None = None,
    enqueue_training: EnqueueTraining | None = None,
) -> bool:
    now = now or datetime.now(UTC)
    elapsed_days = (now.date() - model_version.training_window_end.date()).days
    if elapsed_days < max_model_age_days:
        return False
    _trigger_retraining(
        session,
        model_version,
        now,
        "MODEL_AGE",
        {"elapsed_days": elapsed_days, "maximum_days": max_model_age_days},
        enqueue_training,
    )
    session.flush()
    return True


def supersede_model(
    session: Session,
    *,
    prior: MLModelVersion,
    replacement: MLModelVersion,
) -> None:
    prior.promotion_state = "SUPERSEDED"
    prior.superseded_by = replacement.id
    session.flush()


def _bucket_counts(values: Sequence[float | None], edges: Sequence[float]) -> list[int]:
    counts = [0 for _ in range(len(edges) + 2)]
    for value in values:
        if value is None or math.isnan(float(value)):
            counts[-1] += 1
            continue
        placed = False
        for index, edge in enumerate(edges):
            if float(value) <= edge:
                counts[index] += 1
                placed = True
                break
        if not placed:
            counts[len(edges)] += 1
    return counts


def _start_run(
    session: Session,
    model_version: MLModelVersion,
    kind: str,
    now: datetime,
) -> MLMonitorRun:
    run = MLMonitorRun(
        model_version_id=model_version.id,
        kind=kind,
        started_at=now,
        finished_at=None,
        state="RUNNING",
        withholding_reason=None,
        evaluable_case_count=None,
        results=None,
    )
    session.add(run)
    session.flush()
    return run


def _record_event(
    session: Session,
    model_version: MLModelVersion,
    event_type: str,
    now: datetime,
    payload: Mapping[str, object],
) -> None:
    session.add(
        Event(
            event_type=event_type,
            entity_type="ml_model_version",
            entity_id=model_version.id,
            case_id=None,
            actor_type=ActorType.SYSTEM,
            actor_id="ml.monitor",
            occurrence_time=now,
            payload=dict(payload) | {"model_version": model_version.version},
            has_pd_refs=False,
            provenance=Provenance.SYSTEM,
        )
    )


def _trigger_retraining(
    session: Session,
    model_version: MLModelVersion,
    now: datetime,
    condition: str,
    details: Mapping[str, object],
    enqueue_training: EnqueueTraining | None,
) -> None:
    payload = {"triggering_condition": condition} | dict(details)
    _record_event(session, model_version, "RETRAINING_TRIGGERED", now, payload)
    if enqueue_training is None:
        enqueue(
            session,
            queue="ml",
            task_name="ml.tasks.train_model",
            kwargs={"triggering_condition": condition, "model_version": model_version.version},
            idempotency_key=f"train:{model_version.version}:{condition}:{now.isoformat()}",
        )
    else:
        enqueue_training(session, model_version, condition, payload)


def _notify(
    notifier: Notifier | None,
    event_type: str,
    payload: Mapping[str, object],
) -> None:
    if notifier is not None:
        notifier.notify_permission_holders(
            MODEL_ADMINISTER,
            event_type=event_type,
            payload=payload,
        )
