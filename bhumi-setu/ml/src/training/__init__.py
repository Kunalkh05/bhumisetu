"""Model training contracts and metrics."""

from __future__ import annotations

from training.trainer import (
    MetricSet,
    PromotionThresholds,
    TrainingExample,
    TrainingReport,
    TrainingSplit,
    expected_calibration_error,
    fit_isotonic_calibrator,
    metric_set,
    quantile_bins,
    train_model,
    temporal_split,
)

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
