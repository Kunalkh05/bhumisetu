"""Officer prediction response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from app.api.versioning import VersionedWrite
from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = [
    "ExplanationFactorOut",
    "PredictionExplanationOut",
    "PredictionOverrideIn",
    "PredictionOverrideOut",
]


class ExplanationFactorOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int = Sensitive(Visibility.OFFICER_ONLY)
    feature_name: str = Sensitive(Visibility.OFFICER_ONLY)
    label_key: str = Sensitive(Visibility.OFFICER_ONLY)
    direction: str = Sensitive(Visibility.OFFICER_ONLY)
    magnitude: float = Sensitive(Visibility.OFFICER_ONLY)


class PredictionExplanationOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: int = Sensitive(Visibility.PUBLIC)
    risk_probability: float | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    risk_band: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    priority_score: float | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    model_version: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    generated_at: datetime | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    explanation_factors: list[ExplanationFactorOut] = Sensitive(
        Visibility.OFFICER_ONLY,
        default_factory=list,
    )


class PredictionOverrideIn(VersionedWrite):
    overridden_value: str = Field(..., min_length=1, max_length=40)
    reason: str = Field(..., min_length=1, max_length=500)
    occurrence_time: datetime | None = None


class PredictionOverrideOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: int = Sensitive(Visibility.PUBLIC)
    officer_id: str = Sensitive(Visibility.OFFICER_ONLY)
    overridden_value: str = Sensitive(Visibility.OFFICER_ONLY)
    reason: str = Sensitive(Visibility.OFFICER_ONLY)
    occurrence_time: datetime = Sensitive(Visibility.OFFICER_ONLY)
    model_probability: float | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    model_band: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    model_version: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    model_generated_at: datetime | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
