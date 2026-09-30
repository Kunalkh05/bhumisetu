"""Survival Risk Calibration & Production Risk Layer (LOOP 9).

Provides:
- Case-grouped survival calibration assessment and recalibration testing on TRAIN.
- ProductionRiskLayer for inference across statutory horizons (30d, 90d, 180d, 365d, 730d).
- Separation of concerns: OfficerRiskView (full analytics) vs CitizenRiskView (sanitized rights-centric view).
- Explicit data-quality and uncertainty guards for sparse-event administrative cohorts.
"""

from .survival_calibration import (
    CalibrationAssessmentResult,
    CalibrationStatus,
    CitizenRiskView,
    OfficerRiskView,
    ProductionRiskLayer,
    ProductionRiskPrediction,
    UncertaintyStatus,
    evaluate_train_calibration,
    load_production_risk_layer,
    run_full_survival_calibration,
    save_calibration_artifacts,
)

__all__ = [
    "CalibrationAssessmentResult",
    "CalibrationStatus",
    "CitizenRiskView",
    "OfficerRiskView",
    "ProductionRiskLayer",
    "ProductionRiskPrediction",
    "UncertaintyStatus",
    "evaluate_train_calibration",
    "load_production_risk_layer",
    "run_full_survival_calibration",
    "save_calibration_artifacts",
]
