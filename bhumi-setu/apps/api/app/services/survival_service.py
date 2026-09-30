"""Survival Risk & Explainability Backend Service Layer (LOOP 11).

Provides singleton-cached model loading, point-in-time invariant validation,
role-based projection, and audit logging for the FastAPI backend.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Any, Mapping

import numpy as np
import pandas as pd

from app.errors import DomainError, ErrorCode
from app.schemas.survival_risk import (
    CitizenMilestoneTimelineOut,
    OfficerSurvivalExplanationOut,
    OfficerSurvivalRiskOut,
    SurvivalMLHealthOut,
)

# Internal ML imports
API_ROOT = Path(__file__).resolve().parents[2]
GIT_ROOT = Path(__file__).resolve().parents[5]
ML_SRC = GIT_ROOT / "bhumi-setu" / "ml" / "src"
CLEAN_DATA_DIR = GIT_ROOT / "data" / "real_data" / "clean"
MODELS_DIR = GIT_ROOT / "models" / "cox_baseline"

import sys
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from calibration.survival_calibration import (
    GOVERNANCE_SAFETY_DISCLAIMER,
    MODEL_VERSION,
    PURGED_LEAKAGE_FEATURES,
    ProductionRiskLayer,
    load_production_risk_layer,
)
from explainability.survival_explainability import (
    FEATURE_VERSION,
    SurvivalExplainer,
    load_survival_explainer,
)

logger = logging.getLogger("bhumisetu.survival")

VALID_TRANSITIONS = frozenset({
    "SECTION_11_TO_SECTION_19",
    "SECTION_19_TO_AWARD",
    "CASE_INITIATION_TO_MILESTONE",
})

VALID_HORIZONS = frozenset({30, 90, 180, 365, 730})


class ValidationFailed(DomainError):
    code = ErrorCode.VALIDATION_FAILED
    status_code = 422


class ArtifactNotFound(DomainError):
    code = ErrorCode.INTERNAL_ERROR
    status_code = 500


REQUIRED_FEATURES_BY_TRANSITION: Mapping[str, tuple[str, ...]] = {
    "SECTION_11_TO_SECTION_19": ("derived_days_in_current_stage", "district"),
    "SECTION_19_TO_AWARD": ("derived_days_in_current_stage", "current_stage"),
    "CASE_INITIATION_TO_MILESTONE": ("derived_days_in_current_stage", "current_stage"),
}


class SurvivalService:
    """Cached singleton service for survival risk prediction and explainability."""

    def __init__(
        self,
        models_dir: str | Path = MODELS_DIR,
        clean_data_dir: str | Path = CLEAN_DATA_DIR,
    ) -> None:
        self.models_dir = Path(models_dir)
        self.clean_data_dir = Path(clean_data_dir)
        self._risk_layer: ProductionRiskLayer | None = None
        self._explainer: SurvivalExplainer | None = None
        self.audit_log: list[dict[str, Any]] = []
        self._initialize()

    def _initialize(self) -> None:
        """Validate and load artifacts on startup."""
        if not self.models_dir.exists():
            raise ArtifactNotFound(f"Model artifacts directory not found: {self.models_dir}")

        summary_file = self.models_dir / "cox_model_summary.json"
        if not summary_file.exists():
            raise ArtifactNotFound(f"Model summary artifact missing: {summary_file}")

        try:
            self._risk_layer = load_production_risk_layer(
                self.models_dir,
                self.clean_data_dir / "survival_train_features.csv",
                self.clean_data_dir / "survival_train_targets.csv",
            )
            self._explainer = load_survival_explainer(
                self.models_dir,
                self.clean_data_dir,
            )
            logger.info("SurvivalService successfully initialized and cached model artifacts.")
        except Exception as e:
            logger.exception("Failed to initialize SurvivalService: %s", e)
            raise ArtifactNotFound(f"Corrupted or invalid model artifacts: {e}") from e

    def validate_request(
        self,
        snapshot_date: str,
        transition: str,
        features: Mapping[str, Any],
        horizon: int | None = None,
        require_features: bool = False,
    ) -> datetime:
        """Validate point-in-time constraints, transition, and feature allowlists."""
        # 1. Transition validation
        if transition not in VALID_TRANSITIONS:
            raise ValidationFailed(
                f"Invalid transition '{transition}'. Supported: {sorted(VALID_TRANSITIONS)}",
                details={"transition": transition, "valid_transitions": sorted(VALID_TRANSITIONS)},
            )

        # 2. Horizon validation
        if horizon is not None and horizon not in VALID_HORIZONS:
            raise ValidationFailed(
                f"Invalid horizon '{horizon}'. Supported: {sorted(VALID_HORIZONS)}",
                details={"horizon": horizon, "valid_horizons": sorted(VALID_HORIZONS)},
            )

        # 3. Point-in-time date validation
        try:
            # Handle YYYY-MM-DD or YYYYMMDD
            clean_date = snapshot_date.replace("-", "").strip()
            parsed_date = datetime.strptime(clean_date, "%Y%m%d").date()
        except ValueError:
            raise ValidationFailed(
                f"Malformed snapshot_date '{snapshot_date}'. Expected format YYYY-MM-DD or YYYYMMDD.",
                details={"snapshot_date": snapshot_date},
            )

        today = datetime.now(timezone.utc).date()
        if parsed_date > today:
            raise ValidationFailed(
                f"Future information rejected: snapshot_date {parsed_date} is in the future relative to system date {today}.",
                details={"snapshot_date": str(parsed_date), "system_date": str(today)},
            )

        # 4. Empty features validation
        if not features:
            raise ValidationFailed(
                "Missing required features: features dictionary cannot be empty.",
                details={"error": "empty_features", "transition": transition},
            )

        # 5. Required features validation
        if require_features:
            required = REQUIRED_FEATURES_BY_TRANSITION.get(transition, ())
            missing = [k for k in required if k not in features or features[k] is None]
            if missing:
                raise ValidationFailed(
                    f"Missing required feature for transition '{transition}': {missing}",
                    details={"missing_features": missing, "transition": transition},
                )

        # 6. Purged features / leakage validation
        overlap = set(features.keys()).intersection(PURGED_LEAKAGE_FEATURES)
        if overlap:
            raise ValidationFailed(
                f"Feature leakage violation: request contains purged features {sorted(overlap)}.",
                details={"purged_features_detected": sorted(overlap)},
            )

        return datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)

    def predict_officer_risk(
        self,
        case_id: str | int,
        snapshot_date: str,
        transition: str,
        features: Mapping[str, Any],
        horizon: int | None = None,
        require_features: bool = False,
    ) -> OfficerSurvivalRiskOut:
        """Generate full analytical survival risk projection for officers."""
        start_t = time.perf_counter()
        self.validate_request(
            snapshot_date,
            transition,
            features,
            horizon=horizon,
            require_features=require_features,
        )

        row_dict = dict(features)
        row_dict["case_id"] = str(case_id)
        row_dict["snapshot_id"] = f"REQ_{case_id}_{transition}_{snapshot_date}"
        row_dict["snapshot_date"] = snapshot_date
        row_dict["transition"] = transition

        df = pd.DataFrame([row_dict])
        assert self._risk_layer is not None
        predictions = self._risk_layer.predict_risk(df)
        if not predictions:
            raise ValidationFailed("Could not generate prediction for input features.")

        pred = predictions[0]
        officer_view = self._risk_layer.to_officer_view(pred)

        latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "case_id": str(case_id),
            "transition": transition,
            "snapshot_date": snapshot_date,
            "model_version": officer_view.model_version,
            "feature_version": FEATURE_VERSION,
            "latency_ms": latency_ms,
        }
        self.audit_log.append(audit_entry)

        logger.info(
            "Officer survival risk predicted: case_id=%s trans=%s snapshot_date=%s latency=%.2fms",
            case_id,
            transition,
            snapshot_date,
            latency_ms,
        )

        return OfficerSurvivalRiskOut(
            case_id=officer_view.case_id,
            snapshot_date=officer_view.snapshot_date,
            transition=officer_view.transition,
            model_version=officer_view.model_version,
            linear_predictor=pred.linear_predictor,
            relative_hazard=officer_view.relative_hazard,
            survival_probability_30d=officer_view.survival_probability_30d,
            survival_probability_90d=officer_view.survival_probability_90d,
            survival_probability_180d=officer_view.survival_probability_180d,
            survival_probability_365d=officer_view.survival_probability_365d,
            survival_probability_730d=officer_view.survival_probability_730d,
            event_probability_30d=officer_view.event_probability_30d,
            event_probability_90d=officer_view.event_probability_90d,
            event_probability_180d=officer_view.event_probability_180d,
            event_probability_365d=officer_view.event_probability_365d,
            event_probability_730d=officer_view.event_probability_730d,
            risk_band_90d=officer_view.risk_band_advisory,
            calibration_status=officer_view.calibration_status,
            uncertainty_status=officer_view.uncertainty_status,
            extrapolation_status=officer_view.extrapolation_flags,
            data_quality_warning=officer_view.data_quality_warning,
            governance_disclaimer=officer_view.governance_disclaimer,
        )

    def explain_officer_risk(
        self,
        case_id: str | int,
        snapshot_date: str,
        transition: str,
        features: Mapping[str, Any],
        horizon: int | None = None,
        require_features: bool = False,
    ) -> OfficerSurvivalExplanationOut:
        """Generate audit-ready explanation for officers."""
        risk_out = self.predict_officer_risk(
            case_id,
            snapshot_date,
            transition,
            features,
            horizon=horizon,
            require_features=require_features,
        )

        row_dict = dict(features)
        row_dict["case_id"] = str(case_id)
        row_dict["snapshot_id"] = f"REQ_{case_id}_{transition}_{snapshot_date}"
        row_dict["snapshot_date"] = snapshot_date
        row_dict["transition"] = transition

        assert self._explainer is not None
        explanation = self._explainer.explain_snapshot(row_dict)
        off_expl = self._explainer.to_officer_view(explanation)

        return OfficerSurvivalExplanationOut(
            case_id=risk_out.case_id,
            snapshot_date=risk_out.snapshot_date,
            transition=risk_out.transition,
            model_version=risk_out.model_version,
            linear_predictor=risk_out.linear_predictor,
            relative_hazard=risk_out.relative_hazard,
            survival_probability_30d=risk_out.survival_probability_30d,
            survival_probability_90d=risk_out.survival_probability_90d,
            survival_probability_180d=risk_out.survival_probability_180d,
            survival_probability_365d=risk_out.survival_probability_365d,
            survival_probability_730d=risk_out.survival_probability_730d,
            event_probability_30d=risk_out.event_probability_30d,
            event_probability_90d=risk_out.event_probability_90d,
            event_probability_180d=risk_out.event_probability_180d,
            event_probability_365d=risk_out.event_probability_365d,
            event_probability_730d=risk_out.event_probability_730d,
            risk_band_90d=risk_out.risk_band_90d,
            calibration_status=risk_out.calibration_status,
            uncertainty_status=risk_out.uncertainty_status,
            extrapolation_status=risk_out.extrapolation_status,
            data_quality_warning=risk_out.data_quality_warning,
            governance_disclaimer=risk_out.governance_disclaimer,
            summary_narrative=off_expl.summary_narrative,
            why_hazard_is_higher=off_expl.why_hazard_is_higher,
            why_hazard_is_lower=off_expl.why_hazard_is_lower,
            missing_features=off_expl.missing_features,
        )

    def get_citizen_milestone_timeline(
        self,
        case_id: str | int,
        transition: str,
        current_stage: str = "SECTION_11",
        days_in_stage: int = 45,
    ) -> CitizenMilestoneTimelineOut:
        """Generate sanitized, rights-oriented timeline view for citizens."""
        if transition not in VALID_TRANSITIONS:
            raise ValidationFailed(f"Invalid transition '{transition}'.")

        milestone_map = {
            "SECTION_11_TO_SECTION_19": ("Section 19 Declaration", 365),
            "SECTION_19_TO_AWARD": ("Final Compensation Award", 365),
            "CASE_INITIATION_TO_MILESTONE": ("Statutory Milestone", 730),
        }
        milestone_name, statutory_limit = milestone_map.get(
            transition, ("Statutory Milestone", 365)
        )

        rights_summary = (
            "Under RFCTLARR 2013, land owners have statutory rights to submit claims and objections (Sec 15), "
            "review land valuation reports, participate in public inquiry hearings, and receive solatium "
            "and rehabilitation entitlements."
        )

        procedural_expl = (
            f"Your land acquisition proceeding is currently at stage '{current_stage}'. "
            f"The next formal statutory milestone is '{milestone_name}'. "
            f"Under RFCTLARR 2013 provisions, the statutory time limit for this milestone is {statutory_limit} days. "
            f"Current elapsed time: {days_in_stage} days."
        )

        return CitizenMilestoneTimelineOut(
            case_id=str(case_id),
            current_stage=current_stage,
            milestone_name=milestone_name,
            statutory_time_limit_days=statutory_limit,
            days_in_current_stage=days_in_stage,
            proceedings_status="IN_PROGRESS",
            statutory_rights_summary=rights_summary,
            citizen_procedural_explanation=procedural_expl,
        )

    def get_health(self) -> SurvivalMLHealthOut:
        """Report ML subsystem status, model versions, and checksums."""
        assert self._explainer is not None
        assert self._risk_layer is not None

        cal_statuses = {
            trans: res.calibration_status
            for trans, res in self._risk_layer.calibration_results.items()
        }

        return SurvivalMLHealthOut(
            status="healthy",
            model_version=MODEL_VERSION,
            feature_version=FEATURE_VERSION,
            available_transitions=sorted(VALID_TRANSITIONS),
            model_checksums=self._explainer.checksums,
            calibration_status=cal_statuses,
            explainability_available=True,
            governance_disclaimer=GOVERNANCE_SAFETY_DISCLAIMER,
        )

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Return a copy of point-in-time prediction audit logs."""
        return list(self.audit_log)


# Global service cache
_SURVIVAL_SERVICE: SurvivalService | None = None


def get_survival_service() -> SurvivalService:
    """Dependency injector and singleton accessor for SurvivalService."""
    global _SURVIVAL_SERVICE
    if _SURVIVAL_SERVICE is None:
        _SURVIVAL_SERVICE = SurvivalService()
    return _SURVIVAL_SERVICE
