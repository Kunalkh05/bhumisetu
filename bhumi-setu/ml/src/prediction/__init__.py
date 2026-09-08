"""Delay prediction scoring service."""

from __future__ import annotations

from prediction.banding import BandingResult, band_for, classify, reband_predictions
from prediction.explanations import (
    ExplanationFactor,
    ShapFactor,
    explanation_payload,
    persist_explanation_factors,
    rank_explanation_factors,
)
from prediction.overrides import PredictionOverride, record_prediction_override
from prediction.service import (
    BandingDecision,
    PredictionView,
    Scorer,
    current_promoted_model,
    feature_trigger_keys,
    score_case,
    should_trigger_scoring,
    stale_cutoff,
    stale_case_ids,
)

__all__ = [
    "BandingDecision",
    "BandingResult",
    "ExplanationFactor",
    "PredictionOverride",
    "PredictionView",
    "Scorer",
    "ShapFactor",
    "band_for",
    "classify",
    "current_promoted_model",
    "explanation_payload",
    "feature_trigger_keys",
    "persist_explanation_factors",
    "rank_explanation_factors",
    "reband_predictions",
    "record_prediction_override",
    "score_case",
    "should_trigger_scoring",
    "stale_cutoff",
    "stale_case_ids",
]
