from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

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
    t = datetime(2026, 1, index + 1, tzinfo=timezone.utc)
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
