from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from monitoring.monitor import (  # noqa: E402
    CalibrationObservation,
    DriftResult,
    calibration_groups,
    check_watchdog,
    feature_drift,
    maybe_trigger_model_age,
    monitor_calibration,
    monitor_drift,
    psi,
    supersede_model,
)


NOW = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)


class _Session:
    def __init__(self) -> None:
        self.added = []
        self.flushed = 0

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed += 1


class _Notifier:
    def __init__(self) -> None:
        self.calls = []

    def notify_permission_holders(self, permission, *, event_type, payload):  # type: ignore[no-untyped-def]
        self.calls.append(
            {"permission": permission, "event_type": event_type, "payload": payload}
        )


@dataclass
class _Model:
    id: int = 7
    version: str = "model-v7"
    training_window_start: datetime = NOW - timedelta(days=40)
    training_window_end: datetime = NOW - timedelta(days=20)
    promotion_state: str = "PROMOTED"
    superseded_by: int | None = None


@dataclass
class _Replacement:
    id: int = 8
    version: str = "model-v8"


def _events(session: _Session, event_type: str):
    return [obj for obj in session.added if getattr(obj, "event_type", None) == event_type]


def test_calibration_groups_use_prediction_time_band_not_current_case_band() -> None:
    groups = calibration_groups(
        [
            CalibrationObservation(1, "HIGH", 0.8, True),
            CalibrationObservation(2, "HIGH", 0.6, False),
            CalibrationObservation(3, "LOW", 0.2, False),
        ]
    )

    by_band = {group.risk_band: group for group in groups}
    assert by_band["HIGH"].case_count == 2
    assert by_band["HIGH"].realized_delay_rate == pytest.approx(0.5)
    assert by_band["HIGH"].mean_risk_probability == pytest.approx(0.7)
    assert by_band["HIGH"].divergence == pytest.approx(0.2)


def test_psi_is_finite_and_tracks_missing_bucket() -> None:
    unchanged = psi([0.1, 0.2, None, 0.9], [0.1, 0.2, None, 0.9], [0.25, 0.5, 0.75])
    shifted = psi([0.1, 0.2, None, 0.9], [None, None, None, 0.9], [0.25, 0.5, 0.75])

    assert unchanged == pytest.approx(0.0)
    assert shifted > 0
    assert math.isfinite(shifted)


def test_monitor_calibration_records_divergence_event_notification_and_training() -> None:
    session = _Session()
    notifier = _Notifier()
    enqueued = []
    monitor_calibration(
        session,
        model_version=_Model(),
        observations=[
            CalibrationObservation(1, "HIGH", 0.9, False),
            CalibrationObservation(2, "HIGH", 0.8, False),
        ],
        divergence_threshold=0.2,
        min_evaluable_count=1,
        now=NOW,
        notifier=notifier,
        enqueue_training=lambda *args: enqueued.append(args),
    )

    divergence = _events(session, "MODEL_CALIBRATION_DIVERGED")[0]
    assert divergence.payload["risk_band"] == "HIGH"
    assert divergence.payload["case_count"] == 2
    assert _events(session, "RETRAINING_TRIGGERED")[0].payload["triggering_condition"] == "CALIBRATION_DIVERGENCE"
    assert notifier.calls[0]["permission"] == "model.administer"
    assert len(enqueued) == 1


def test_monitor_calibration_withholds_below_minimum_count() -> None:
    session = _Session()
    monitor_calibration(
        session,
        model_version=_Model(),
        observations=[],
        divergence_threshold=0.2,
        min_evaluable_count=3,
        now=NOW,
    )

    run = session.added[0]
    assert run.state == "WITHHELD"
    assert run.withholding_reason == "MIN_EVALUABLE_CASE_COUNT"
    assert run.evaluable_case_count == 0


def test_monitor_drift_records_feature_events_and_single_training_trigger() -> None:
    session = _Session()
    notifier = _Notifier()
    enqueued = []
    drift = DriftResult(
        feature_name="notice_count",
        drift=0.42,
        threshold=0.2,
        training_window_start=NOW - timedelta(days=30),
        training_window_end=NOW - timedelta(days=20),
        inference_window_start=NOW - timedelta(days=7),
        inference_window_end=NOW,
    )

    monitor_drift(
        session,
        model_version=_Model(),
        drift_results=[drift],
        min_drifted_feature_count=1,
        now=NOW,
        notifier=notifier,
        enqueue_training=lambda *args: enqueued.append(args),
    )

    feature_event = _events(session, "FEATURE_DRIFT_DETECTED")[0]
    assert feature_event.payload["feature_name"] == "notice_count"
    assert _events(session, "RETRAINING_TRIGGERED")[0].payload["triggering_condition"] == "FEATURE_DRIFT"
    assert notifier.calls[0]["event_type"] == "FEATURE_DRIFT_DETECTED"
    assert len(enqueued) == 1


def test_feature_drift_uses_stored_edges_and_window_boundaries() -> None:
    result = feature_drift(
        feature_name="notice_count",
        reference_values=[0.0, 1.0, None],
        inference_values=[1.0, 1.0, None],
        edges=[0.5],
        threshold=0.1,
        training_window_start=NOW - timedelta(days=30),
        training_window_end=NOW - timedelta(days=20),
        inference_window_start=NOW - timedelta(days=7),
        inference_window_end=NOW,
    )

    assert result.feature_name == "notice_count"
    assert result.drift > 0
    assert result.training_window_end == NOW - timedelta(days=20)
    assert result.inference_window_end == NOW


def test_model_age_trigger_records_training_once_age_threshold_is_reached() -> None:
    session = _Session()
    enqueued = []
    assert maybe_trigger_model_age(
        session,
        model_version=_Model(training_window_end=NOW - timedelta(days=10)),
        max_model_age_days=10,
        now=NOW,
        enqueue_training=lambda *args: enqueued.append(args),
    )

    event = _events(session, "RETRAINING_TRIGGERED")[0]
    assert event.payload["triggering_condition"] == "MODEL_AGE"
    assert event.payload["elapsed_days"] == 10
    assert len(enqueued) == 1


def test_watchdog_records_unavailable_after_one_and_a_half_cadences() -> None:
    session = _Session()
    state = check_watchdog(
        session,
        model_version=_Model(),
        last_successful_at=NOW - timedelta(days=2),
        cadence=timedelta(days=1),
        now=NOW,
    )

    assert state.state == "UNAVAILABLE"
    event = _events(session, "MODEL_MONITORING_UNAVAILABLE")[0]
    assert event.payload["reason"] == "CADENCE_OVERRUN"
    assert event.payload["last_successful_computation_time"] == (
        NOW - timedelta(days=2)
    ).isoformat()


def test_supersession_updates_state_and_keeps_versions_referenced() -> None:
    session = _Session()
    prior = _Model()

    supersede_model(session, prior=prior, replacement=_Replacement())

    assert prior.promotion_state == "SUPERSEDED"
    assert prior.superseded_by == 8
    assert session.flushed


@given(
    band=st.sampled_from(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    probabilities=st.lists(
        st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=20,
    ),
    outcomes=st.lists(st.booleans(), min_size=1, max_size=20),
)
@settings(max_examples=50)
def test_property_calibration_divergence_matches_reference(
    band: str,
    probabilities: list[float],
    outcomes: list[bool],
) -> None:
    size = min(len(probabilities), len(outcomes))
    observations = [
        CalibrationObservation(index, band, probabilities[index], outcomes[index])
        for index in range(size)
    ]

    group = calibration_groups(observations)[0]

    realized = sum(outcomes[:size]) / size
    predicted = sum(probabilities[:size]) / size
    assert group.risk_band == band
    assert group.realized_delay_rate == pytest.approx(realized)
    assert group.mean_risk_probability == pytest.approx(predicted)
    assert group.divergence == pytest.approx(abs(realized - predicted))


@given(
    training=st.lists(
        st.one_of(
            st.none(),
            st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False),
        ),
        min_size=1,
        max_size=30,
    ),
    inference=st.lists(
        st.one_of(
            st.none(),
            st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False),
        ),
        min_size=1,
        max_size=30,
    ),
    edges=st.lists(
        st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=6,
        unique=True,
    ),
)
@settings(max_examples=50)
def test_property_psi_is_finite_and_zero_for_identical_inputs(
    training: list[float | None],
    inference: list[float | None],
    edges: list[float],
) -> None:
    sorted_edges = sorted(edges)

    value = psi(training, inference, sorted_edges)

    assert math.isfinite(value)
    assert value >= 0
    assert psi(training, training, sorted_edges) == pytest.approx(0.0)


@given(
    drift_count=st.integers(min_value=1, max_value=5),
    minimum=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=30)
def test_property_drift_training_trigger_fires_exactly_at_threshold(
    drift_count: int,
    minimum: int,
) -> None:
    session = _Session()
    enqueued = []
    results = [
        DriftResult(
            feature_name=f"feature_{index}",
            drift=0.5,
            threshold=0.1,
            training_window_start=NOW - timedelta(days=30),
            training_window_end=NOW - timedelta(days=20),
            inference_window_start=NOW - timedelta(days=7),
            inference_window_end=NOW,
        )
        for index in range(drift_count)
    ]

    monitor_drift(
        session,
        model_version=_Model(),
        drift_results=results,
        min_drifted_feature_count=minimum,
        now=NOW,
        enqueue_training=lambda *args: enqueued.append(args),
    )

    triggers = _events(session, "RETRAINING_TRIGGERED")
    assert len(triggers) == (1 if drift_count >= minimum else 0)
    assert len(enqueued) == len(triggers)


@given(
    elapsed_days=st.integers(min_value=0, max_value=100),
    maximum_days=st.integers(min_value=1, max_value=100),
)
@settings(max_examples=50)
def test_property_model_age_trigger_fires_exactly_at_age_threshold(
    elapsed_days: int,
    maximum_days: int,
) -> None:
    session = _Session()
    enqueued = []

    triggered = maybe_trigger_model_age(
        session,
        model_version=_Model(training_window_end=NOW - timedelta(days=elapsed_days)),
        max_model_age_days=maximum_days,
        now=NOW,
        enqueue_training=lambda *args: enqueued.append(args),
    )

    assert triggered is (elapsed_days >= maximum_days)
    assert len(_events(session, "RETRAINING_TRIGGERED")) == (1 if triggered else 0)
    assert len(enqueued) == (1 if triggered else 0)


@given(
    probability=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    days_since_success=st.integers(min_value=0, max_value=30),
)
@settings(max_examples=30)
def test_property_unavailable_state_is_visible_on_scored_responses(
    probability: float,
    days_since_success: int,
) -> None:
    from prediction.service import PredictionView

    last_success = NOW - timedelta(days=days_since_success)
    response = PredictionView(
        case_id=42,
        risk_probability=probability,
        risk_band="HIGH",
        risk_model_version="model-v7",
        risk_generated_at=NOW,
        risk_is_stale=False,
        risk_cutoff_source="PLATFORM",
    ).with_monitoring_state(
        state="UNAVAILABLE",
        last_successful_at=last_success,
    ).to_response()

    assert response["risk_probability"] == pytest.approx(probability)
    assert response["monitoring_state"] == "UNAVAILABLE"
    assert response["monitoring_last_successful_at"] == last_success
