"""Pydantic and GatedModel schemas for Survival Risk & Explainability (LOOP 11).

Defines strict field-level visibility annotations:
- Visibility.PUBLIC: Allowed for citizens and officers.
- Visibility.OFFICER_ONLY: Redacted at the serialization gate for any citizen caller.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from app.security.gate import GatedModel, Sensitive, Visibility


class SurvivalPredictIn(BaseModel):
    """Point-in-time survival prediction request."""

    case_id: str | int = Field(..., description="Acquisition proceeding case identifier")
    snapshot_date: str = Field(..., description="Point-in-time snapshot date (YYYY-MM-DD or YYYYMMDD)")
    transition: str = Field(..., description="Target statutory transition milestone")
    features: dict[str, Any] = Field(..., description="Dictionary of point-in-time feature values")
    horizon: int | None = Field(default=None, description="Optional target horizon in days (30, 90, 180, 365, 730)")
    require_features: bool = Field(default=False, description="Strictly validate that core transition predictors are present")


class OfficerSurvivalRiskOut(GatedModel):
    """Officer-facing analytical survival risk response."""

    case_id: str = Sensitive(Visibility.PUBLIC)
    snapshot_date: str = Sensitive(Visibility.PUBLIC)
    transition: str = Sensitive(Visibility.PUBLIC)
    model_version: str = Sensitive(Visibility.OFFICER_ONLY)
    linear_predictor: float = Sensitive(Visibility.OFFICER_ONLY)
    relative_hazard: float = Sensitive(Visibility.OFFICER_ONLY)
    survival_probability_30d: float = Sensitive(Visibility.OFFICER_ONLY)
    survival_probability_90d: float = Sensitive(Visibility.OFFICER_ONLY)
    survival_probability_180d: float = Sensitive(Visibility.OFFICER_ONLY)
    survival_probability_365d: float = Sensitive(Visibility.OFFICER_ONLY)
    survival_probability_730d: float = Sensitive(Visibility.OFFICER_ONLY)
    event_probability_30d: float = Sensitive(Visibility.OFFICER_ONLY)
    event_probability_90d: float = Sensitive(Visibility.OFFICER_ONLY)
    event_probability_180d: float = Sensitive(Visibility.OFFICER_ONLY)
    event_probability_365d: float = Sensitive(Visibility.OFFICER_ONLY)
    event_probability_730d: float = Sensitive(Visibility.OFFICER_ONLY)
    risk_band_90d: str = Sensitive(Visibility.OFFICER_ONLY)
    calibration_status: str = Sensitive(Visibility.OFFICER_ONLY)
    uncertainty_status: str = Sensitive(Visibility.OFFICER_ONLY)
    extrapolation_status: dict[str, bool] = Sensitive(Visibility.OFFICER_ONLY)
    data_quality_warning: str = Sensitive(Visibility.OFFICER_ONLY)
    governance_disclaimer: str = Sensitive(Visibility.PUBLIC)


class OfficerSurvivalExplanationOut(OfficerSurvivalRiskOut):
    """Officer-facing auditable explanation response."""

    summary_narrative: str = Sensitive(Visibility.OFFICER_ONLY)
    why_hazard_is_higher: list[dict[str, Any]] = Sensitive(Visibility.OFFICER_ONLY)
    why_hazard_is_lower: list[dict[str, Any]] = Sensitive(Visibility.OFFICER_ONLY)
    missing_features: list[dict[str, Any]] = Sensitive(Visibility.OFFICER_ONLY)


class CitizenMilestoneTimelineOut(GatedModel):
    """Citizen-facing plain-language milestone progress and rights response.

    Strictly does NOT contain any internal model coefficients, hazard scores,
    or internal administrative rankings.
    """

    case_id: str = Sensitive(Visibility.PUBLIC)
    current_stage: str = Sensitive(Visibility.PUBLIC)
    milestone_name: str = Sensitive(Visibility.PUBLIC)
    statutory_time_limit_days: int = Sensitive(Visibility.PUBLIC)
    days_in_current_stage: int = Sensitive(Visibility.PUBLIC)
    proceedings_status: str = Sensitive(Visibility.PUBLIC)
    statutory_rights_summary: str = Sensitive(Visibility.PUBLIC)
    citizen_procedural_explanation: str = Sensitive(Visibility.PUBLIC)


class SurvivalMLHealthOut(GatedModel):
    """ML subsystem health check response."""

    status: str = Sensitive(Visibility.PUBLIC)
    model_version: str = Sensitive(Visibility.PUBLIC)
    feature_version: str = Sensitive(Visibility.PUBLIC)
    available_transitions: list[str] = Sensitive(Visibility.PUBLIC)
    model_checksums: dict[str, str] = Sensitive(Visibility.OFFICER_ONLY)
    calibration_status: dict[str, str] = Sensitive(Visibility.OFFICER_ONLY)
    explainability_available: bool = Sensitive(Visibility.OFFICER_ONLY)
    governance_disclaimer: str = Sensitive(Visibility.PUBLIC)
