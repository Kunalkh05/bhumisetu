from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.predictions import (
    ExplanationFactorOut,
    PredictionExplanationOut,
    PredictionOverrideOut,
)
from app.security.access import Principal
from app.security.gate import ResponseGate


def _citizen() -> Principal:
    return Principal(kind="CITIZEN", id="citizen-1", case_id=42)


def _officer() -> Principal:
    return Principal(kind="OFFICER", id="officer-1")


def test_prediction_fields_are_excluded_from_citizen_response() -> None:
    generated_at = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)
    response = PredictionExplanationOut(
        case_id=42,
        risk_probability=0.72,
        risk_band="HIGH",
        priority_score=0.91,
        model_version="model-v3",
        generated_at=generated_at,
        monitoring_state="UNAVAILABLE",
        monitoring_last_successful_at=generated_at,
        explanation_factors=[
            ExplanationFactorOut(
                rank=1,
                feature_name="notice_count",
                label_key="ml.feature.notice_count",
                direction="INCREASES_RISK",
                magnitude=0.4,
            )
        ],
    )

    citizen_body = ResponseGate.apply(response, _citizen(), PredictionExplanationOut)
    officer_body = ResponseGate.apply(response, _officer(), PredictionExplanationOut)

    assert citizen_body == {"case_id": 42}
    assert officer_body["risk_probability"] == 0.72
    assert officer_body["risk_band"] == "HIGH"
    assert officer_body["priority_score"] == 0.91
    assert officer_body["monitoring_state"] == "UNAVAILABLE"
    assert officer_body["explanation_factors"][0]["label_key"] == "ml.feature.notice_count"


def test_override_model_output_is_excluded_from_citizen_response() -> None:
    response = PredictionOverrideOut(
        case_id=42,
        officer_id="officer-1",
        overridden_value="LOW",
        reason="resolved",
        occurrence_time=datetime(2026, 3, 1, 10, tzinfo=timezone.utc),
        model_probability=0.72,
        model_band="HIGH",
        model_version="model-v3",
        model_generated_at=datetime(2026, 3, 1, 9, tzinfo=timezone.utc),
    )

    assert ResponseGate.apply(response, _citizen(), PredictionOverrideOut) == {"case_id": 42}
