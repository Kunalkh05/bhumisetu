from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.errors import NotAuthorised
from app.security.access import Principal

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.builder import FeatureRow  # noqa: E402
from labelling.definition import DeadlineBaseline, LabelDefinition, LabelOutcome  # noqa: E402
from training.trainer import (  # noqa: E402
    MetricSet,
    PromotionThresholds,
    TrainingExample,
    expected_calibration_error,
    fit_isotonic_calibrator,
    metric_set,
    quantile_bins,
    temporal_split,
    train_model,
)


class _Session:
    def __init__(self) -> None:
        self.added = []
        self.flushed = False

    def add(self, obj) -> None:
        obj.id = len(self.added) + 1
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed = True


def _definition(version: str = "delay-v1") -> LabelDefinition:
    return LabelDefinition(
        version=version,
        formulation="BINARY_STAGE_EXIT",
        stage_transitions_in_scope="ALL_NON_TERMINAL",
        deadline_baseline=DeadlineBaseline(
            kind="STATUTORY_PERIOD",
            period_key="period.pn.to_declaration",
        ),
        baseline_fallback=None,
        horizon_days=60,
        censoring="EXCLUDE",
    )


def _row(
    index: int,
    label: str,
    *,
    score: float,
    baseline: float | None = None,
    version: str = "delay-v1",
) -> TrainingExample:
    t = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)
    return TrainingExample(
        feature_row=FeatureRow(
            case_id=index,
            reference_t=t,
            as_of_mode="KNOWABLE_AT",
            feature_set_version="fs-v1",
            purpose="TRAINING",
            values={"days": {"value": index, "missing_reason": None}},
            model_input={"days": float(index), "days_is_missing": 0.0},
            consumed_event_ids=(index,),
            content_hash=f"h-{index}",
        ),
        outcome=LabelOutcome(
            label=label,
            time_to_event_days=index,
            event_observed=label != "CENSORED",
            reason="fixture",
            label_definition_version=version,
        ),
        raw_probability=score,
        deadline_rule_probability=score if baseline is None else baseline,
    )


def test_temporal_split_excludes_censored_and_orders_eval_after_train() -> None:
    split = temporal_split(
        [
            _row(1, "NOT_DELAYED", score=0.1),
            _row(2, "CENSORED", score=0.4),
            _row(3, "DELAYED", score=0.9),
            _row(4, "DELAYED", score=0.8),
        ],
        eval_fraction=0.34,
    )

    assert [row.outcome.label for row in split.train_rows] == ["NOT_DELAYED"]
    assert [row.outcome.label for row in split.eval_rows] == ["DELAYED", "DELAYED"]
    assert split.censored_count == 1
    assert split.censoring_rate == pytest.approx(0.25)
    assert split.train_rows[-1].reference_t < split.eval_rows[0].reference_t


def test_metric_set_reports_core_metrics_and_pr_lift_formula() -> None:
    train_rows = (
        _row(1, "NOT_DELAYED", score=0.1),
        _row(2, "DELAYED", score=0.9),
    )
    eval_rows = (
        _row(3, "NOT_DELAYED", score=0.2),
        _row(4, "DELAYED", score=0.8),
    )

    metrics = metric_set(
        train_rows=train_rows,
        eval_rows=eval_rows,
        eval_probabilities=(0.2, 0.8),
    )

    assert metrics.auprc == pytest.approx(1.0)
    assert metrics.auroc == pytest.approx(1.0)
    assert metrics.brier == pytest.approx(0.04)
    assert metrics.ece == pytest.approx(
        expected_calibration_error([0, 1], [0.2, 0.8], n_bins=10)
    )
    assert metrics.pr_lift == pytest.approx(
        (metrics.auprc - metrics.eval_base_rate) / (1 - metrics.eval_base_rate)
    )
    assert metrics.train_base_rate == pytest.approx(0.5)
    assert metrics.eval_base_rate == pytest.approx(0.5)


def test_isotonic_calibrator_is_monotone() -> None:
    calibrator = fit_isotonic_calibrator(
        [
            _row(1, "DELAYED", score=0.2),
            _row(2, "NOT_DELAYED", score=0.4),
            _row(3, "DELAYED", score=0.9),
        ]
    )

    predicted = calibrator.predict((0.1, 0.3, 0.8))
    assert predicted == tuple(sorted(predicted))


def test_quantile_bins_store_training_distribution_edges() -> None:
    rows = [
        _row(index, "DELAYED" if index % 2 else "NOT_DELAYED", score=0.5)
        for index in range(1, 6)
    ]

    bins = quantile_bins(rows, n_bins=5)

    assert bins["days"] == pytest.approx((1.8, 2.6, 3.4, 4.2))
    assert "days_is_missing" not in bins


def test_training_requires_model_administer_permission() -> None:
    with pytest.raises(NotAuthorised):
        train_model(
            _Session(),
            rows=[_row(1, "NOT_DELAYED", score=0.1), _row(2, "DELAYED", score=0.9)],
            label_definition=_definition(),
            feature_set_version="fs-v1",
            thresholds=PromotionThresholds(0, 0, 0, 1),
            actor=Principal(kind="OFFICER", id="officer"),
            eval_fraction=0.5,
            hyperparameters={},
        )


def test_training_records_promotion_report_and_base_rate_shift_event() -> None:
    session = _Session()
    actor = Principal(
        kind="OFFICER",
        id="officer",
        permissions=frozenset({"model.administer"}),
    )

    report = train_model(
        session,
        rows=[
            _row(1, "NOT_DELAYED", score=0.1),
            _row(2, "NOT_DELAYED", score=0.2),
            _row(3, "DELAYED", score=0.8),
            _row(4, "DELAYED", score=0.9),
        ],
        label_definition=_definition(),
        feature_set_version="fs-v1",
        thresholds=PromotionThresholds(
            min_pr_lift=0,
            min_auprc=0,
            min_auroc=0,
            max_ece=1,
        ),
        actor=actor,
        eval_fraction=0.5,
        hyperparameters={"max_depth": 3},
        now=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    assert report.promotion_state == "PROMOTED"
    assert report.promoted_by == "officer"
    assert report.hyperparameters == {"max_depth": 3}
    assert report.base_rate_shift_event_id == 1
    assert session.added[0].event_type == "LABEL_BASE_RATE_SHIFT"
    assert session.flushed


def test_training_withholds_when_any_threshold_fails() -> None:
    session = _Session()
    actor = Principal(
        kind="OFFICER",
        id="officer",
        permissions=frozenset({"model.administer"}),
    )

    report = train_model(
        session,
        rows=[
            _row(1, "NOT_DELAYED", score=0.9),
            _row(2, "DELAYED", score=0.1),
            _row(3, "NOT_DELAYED", score=0.8),
            _row(4, "DELAYED", score=0.2),
        ],
        label_definition=_definition(),
        feature_set_version="fs-v1",
        thresholds=PromotionThresholds(
            min_pr_lift=0.9,
            min_auprc=0.9,
            min_auroc=0.9,
            max_ece=0.01,
        ),
        actor=actor,
        eval_fraction=0.5,
        hyperparameters={},
    )

    assert report.promotion_state == "WITHHELD"
    assert report.withheld_event_id is not None
    assert any(event.event_type == "MODEL_PROMOTION_WITHHELD" for event in session.added)


def test_training_refuses_mixed_label_definition_versions() -> None:
    actor = Principal(
        kind="OFFICER",
        id="officer",
        permissions=frozenset({"model.administer"}),
    )

    with pytest.raises(ValueError, match="mixed label_definition_version"):
        train_model(
            _Session(),
            rows=[
                _row(1, "NOT_DELAYED", score=0.1, version="delay-v1"),
                _row(2, "DELAYED", score=0.9, version="delay-v2"),
            ],
            label_definition=_definition("delay-v1"),
            feature_set_version="fs-v1",
            thresholds=PromotionThresholds(0, 0, 0, 1),
            actor=actor,
            eval_fraction=0.5,
            hyperparameters={},
        )


@given(
    usable_count=st.integers(min_value=2, max_value=12),
    censored_count=st.integers(min_value=0, max_value=5),
    eval_fraction=st.floats(min_value=0.15, max_value=0.85, allow_nan=False),
)
@settings(max_examples=60)
def test_temporal_split_properties(
    usable_count: int,
    censored_count: int,
    eval_fraction: float,
) -> None:
    usable = [
        _row(index, "DELAYED" if index % 2 else "NOT_DELAYED", score=0.5)
        for index in range(1, usable_count + 1)
    ]
    censored = [
        _row(usable_count + index, "CENSORED", score=0.5)
        for index in range(1, censored_count + 1)
    ]

    split = temporal_split([*usable, *censored], eval_fraction=eval_fraction)

    assert all(row.outcome.label != "CENSORED" for row in split.train_rows)
    assert all(row.outcome.label != "CENSORED" for row in split.eval_rows)
    assert split.train_rows[-1].reference_t < split.eval_rows[0].reference_t
    assert split.censored_count == censored_count
    assert split.censoring_rate == pytest.approx(censored_count / (usable_count + censored_count))


@given(
    first_label=st.sampled_from(["DELAYED", "NOT_DELAYED"]),
    raw_scores=st.lists(
        st.floats(min_value=0, max_value=1, allow_nan=False),
        min_size=4,
        max_size=10,
    ),
)
@settings(max_examples=60)
def test_metric_properties_match_independent_reference(
    first_label: str,
    raw_scores: list[float],
) -> None:
    labels = [
        first_label if index % 2 == 0 else _opposite(first_label)
        for index in range(len(raw_scores))
    ]
    train_rows = tuple(_row(index + 1, label, score=score) for index, (label, score) in enumerate(zip(labels, raw_scores)))
    eval_rows = train_rows

    metrics = metric_set(
        train_rows=train_rows,
        eval_rows=eval_rows,
        eval_probabilities=tuple(raw_scores),
    )

    label_ints = [1 if label == "DELAYED" else 0 for label in labels]
    eval_base = sum(label_ints) / len(label_ints)
    expected_auprc = _reference_average_precision(label_ints, raw_scores)
    assert metrics.auprc == pytest.approx(expected_auprc)
    assert metrics.auroc == pytest.approx(_reference_auroc(label_ints, raw_scores))
    assert metrics.brier == pytest.approx(
        sum((score - label) ** 2 for label, score in zip(label_ints, raw_scores)) / len(label_ints)
    )
    assert metrics.ece == pytest.approx(
        expected_calibration_error(label_ints, raw_scores, n_bins=10)
    )
    assert metrics.pr_lift == pytest.approx(
        (expected_auprc - eval_base) / (1 - eval_base) if eval_base < 1 else 0.0
    )


@given(
    min_pr_lift=st.floats(min_value=-1, max_value=2, allow_nan=False),
    min_auprc=st.floats(min_value=0, max_value=1, allow_nan=False),
    min_auroc=st.floats(min_value=0, max_value=1, allow_nan=False),
    max_ece=st.floats(min_value=0, max_value=1, allow_nan=False),
)
@settings(max_examples=60)
def test_promotion_gate_and_events_match_thresholds(
    min_pr_lift: float,
    min_auprc: float,
    min_auroc: float,
    max_ece: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import training.trainer as trainer

    metrics = MetricSet(
        auprc=0.7,
        auroc=0.8,
        brier=0.1,
        ece=0.2,
        pr_lift=0.4,
        train_base_rate=0.2,
        eval_base_rate=0.5,
        train_rows=2,
        eval_rows=2,
    )
    baseline = MetricSet(
        auprc=0.5,
        auroc=0.5,
        brier=0.25,
        ece=0.3,
        pr_lift=0.0,
        train_base_rate=0.2,
        eval_base_rate=0.5,
        train_rows=2,
        eval_rows=2,
    )
    calls = iter([metrics, baseline])
    monkeypatch.setattr(trainer, "metric_set", lambda **kwargs: next(calls))
    session = _Session()
    actor = Principal(
        kind="OFFICER",
        id="officer",
        permissions=frozenset({"model.administer"}),
    )
    thresholds = PromotionThresholds(min_pr_lift, min_auprc, min_auroc, max_ece)

    report = train_model(
        session,
        rows=[
            _row(1, "NOT_DELAYED", score=0.2),
            _row(2, "NOT_DELAYED", score=0.2),
            _row(3, "DELAYED", score=0.8),
            _row(4, "DELAYED", score=0.8),
        ],
        label_definition=_definition(),
        feature_set_version="fs-v1",
        thresholds=thresholds,
        actor=actor,
        eval_fraction=0.5,
        hyperparameters={},
    )

    should_promote = (
        metrics.pr_lift >= min_pr_lift
        and metrics.auprc >= min_auprc
        and metrics.auroc >= min_auroc
        and metrics.ece <= max_ece
    )
    assert report.promotion_state == ("PROMOTED" if should_promote else "WITHHELD")
    assert (report.withheld_event_id is None) is should_promote
    assert report.base_rate_shift_event_id == 1
    assert [event.event_type for event in session.added] == (
        ["LABEL_BASE_RATE_SHIFT"] if should_promote else ["LABEL_BASE_RATE_SHIFT", "MODEL_PROMOTION_WITHHELD"]
    )


def test_isotonic_calibration_reduces_ece_on_synthetic_dataset() -> None:
    train_rows = [
        *(_row(index, "NOT_DELAYED", score=0.2) for index in range(1, 11)),
        *(_row(index, "DELAYED", score=0.8) for index in range(11, 21)),
    ]
    eval_rows = [
        *(_row(index, "NOT_DELAYED", score=0.2) for index in range(21, 31)),
        *(_row(index, "DELAYED", score=0.8) for index in range(31, 41)),
    ]
    labels = [0] * 10 + [1] * 10
    raw_scores = [row.raw_probability for row in eval_rows]
    calibrated = fit_isotonic_calibrator(train_rows).predict(raw_scores)

    assert expected_calibration_error(labels, calibrated, n_bins=10) < expected_calibration_error(
        labels,
        raw_scores,
        n_bins=10,
    )


def _opposite(label: str) -> str:
    return "NOT_DELAYED" if label == "DELAYED" else "DELAYED"


def _reference_average_precision(labels: list[int], scores: list[float]) -> float:
    pairs = sorted(zip(scores, labels), reverse=True)
    positives = sum(labels)
    if positives == 0:
        return 0.0
    found = 0
    total = 0.0
    for index, (_, label) in enumerate(pairs, start=1):
        if label:
            found += 1
            total += found / index
    return total / positives


def _reference_auroc(labels: list[int], scores: list[float]) -> float:
    positives = [score for label, score in zip(labels, scores) if label]
    negatives = [score for label, score in zip(labels, scores) if not label]
    if not positives or not negatives:
        return 0.5
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            wins += positive > negative
            wins += 0.5 if positive == negative else 0.0
    return wins / (len(positives) * len(negatives))
