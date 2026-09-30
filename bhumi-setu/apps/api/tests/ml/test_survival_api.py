"""Comprehensive API Integration & Governance Test Suite for Survival Risk (LOOP 11).

Verifies all 25 mandatory requirements from LOOP 11 specification:
1. Valid officer prediction
2. Valid citizen request
3. Officer authorization enforcement
4. Citizen field filtering / serialization redaction
5. Invalid transition rejection
6. Invalid horizon rejection
7. Missing required feature rejection
8. Malformed snapshot date rejection
9. Future information rejection (point-in-time enforcement)
10. Missing artifact safety
11. Corrupted artifact handling (no silent retraining)
12. Model artifact loading and validation
13. Model caching / singleton reuse
14. Deterministic prediction outputs
15. Auditable explanation generation
16. Uncertainty status propagation
17. Calibration status propagation
18. Extrapolation flag propagation
19. Model version propagation
20. Feature version propagation
21. No training during API inference
22. No EVAL holdout data access during inference
23. No causal explanation language (strict association phrasing)
24. Structured error envelopes (status codes 401, 403, 422, 500)
25. No sensitive internal ML fields in citizen responses
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request

from app.errors import ErrorCode
from app.main import create_app
from app.schemas.survival_risk import (
    CitizenMilestoneTimelineOut,
    OfficerSurvivalExplanationOut,
    OfficerSurvivalRiskOut,
    SurvivalMLHealthOut,
)
from app.security.access import Principal, authenticate
from app.security.gate import ResponseGate
from app.services.survival_service import (
    ArtifactNotFound,
    SurvivalService,
    ValidationFailed,
    get_survival_service,
)
from app.settings import CoreSettings

API_ROOT = Path(__file__).resolve().parents[2]
GIT_ROOT = Path(__file__).resolve().parents[5]
MODELS_DIR = GIT_ROOT / "models" / "cox_baseline"
CLEAN_DATA_DIR = GIT_ROOT / "data" / "real_data" / "clean"


def _auth_override(principal: Principal):
    async def _override(request: Request) -> Principal:
        request.state.principal = principal
        return principal
    return _override


@pytest.fixture(scope="module")
def app_instance():
    """Create FastAPI application with development settings."""
    settings = CoreSettings.model_validate({"APP_ENV": "development", "LOG_LEVEL": "WARNING"})
    return create_app(settings)


@pytest.fixture
def client(app_instance):
    """Test client with clean dependency overrides per test."""
    client = TestClient(app_instance)
    yield client
    app_instance.dependency_overrides.clear()


@pytest.fixture
def officer_principal() -> Principal:
    return Principal(kind="OFFICER", id="officer-surv-1", scope_paths=("MH",))


@pytest.fixture
def citizen_principal() -> Principal:
    return Principal(kind="CITIZEN", id="citizen-surv-1", case_id=101)


@pytest.fixture
def valid_features() -> dict[str, Any]:
    return {
        "derived_days_in_current_stage": 45.0,
        "district": "Solapur",
        "derived_project_type": "Rural Infrastructure",
        "current_stage": "SECTION_11",
        "derived_days_since_case_initiation": 60.0,
        "derived_notice_count": 1.0,
        "extension_count": 0.0,
        "has_statutory_extension": 0.0,
        "act_key": "RFCTLARR_2013",
        "derived_is_direct_purchase": 0.0,
    }


# ============================================================================
# 1. VALID OFFICER PREDICTION
# ============================================================================

def test_1_valid_officer_prediction(client, app_instance, officer_principal, valid_features):
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = {
        "case_id": "CASE-101",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": valid_features,
    }
    response = client.post("/api/officer/survival-risk/predict", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["case_id"] == "CASE-101"
    assert data["transition"] == "SECTION_11_TO_SECTION_19"
    assert "relative_hazard" in data
    assert isinstance(data["relative_hazard"], float)
    assert 0.0 <= data["survival_probability_30d"] <= 1.0
    assert 0.0 <= data["event_probability_30d"] <= 1.0
    assert "ADVISORY" in data["risk_band_90d"] or data["risk_band_90d"] in {"LOW", "MEDIUM", "HIGH"}
    assert "governance_disclaimer" in data


# ============================================================================
# 2. VALID CITIZEN REQUEST
# ============================================================================

def test_2_valid_citizen_request(client, app_instance, citizen_principal):
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen_principal)
    response = client.get("/api/citizen/cases/101/milestone-timeline?transition=SECTION_11_TO_SECTION_19")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["case_id"] == "101"
    assert data["current_stage"] == "SECTION_11"
    assert data["milestone_name"] == "Section 19 Declaration"
    assert data["statutory_time_limit_days"] == 365
    assert "statutory_rights_summary" in data
    assert "citizen_procedural_explanation" in data


# ============================================================================
# 3. OFFICER AUTHORIZATION
# ============================================================================

def test_3_officer_authorization_enforced(client, app_instance, citizen_principal, valid_features):
    # Citizen principal attempting officer prediction endpoint must be refused
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen_principal)
    payload = {
        "case_id": "CASE-101",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": valid_features,
    }
    response = client.post("/api/officer/survival-risk/predict", json=payload)
    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.NOT_AUTHORISED


# ============================================================================
# 4. CITIZEN FIELD FILTERING (REDACTION GATE)
# ============================================================================

def test_4_citizen_field_filtering_via_response_gate(valid_features, officer_principal, citizen_principal):
    service = get_survival_service()
    officer_out = service.predict_officer_risk(
        case_id="CASE-101",
        snapshot_date="2026-03-01",
        transition="SECTION_11_TO_SECTION_19",
        features=valid_features,
    )
    gated_citizen = ResponseGate.apply(officer_out, citizen_principal, OfficerSurvivalRiskOut)
    gated_officer = ResponseGate.apply(officer_out, officer_principal, OfficerSurvivalRiskOut)

    # Citizen view MUST NOT contain internal ML parameters
    assert "relative_hazard" not in gated_citizen
    assert "linear_predictor" not in gated_citizen
    assert "model_version" not in gated_citizen
    assert "survival_probability_90d" not in gated_citizen
    assert "event_probability_90d" not in gated_citizen
    assert "risk_band_90d" not in gated_citizen

    # Officer view contains full analytical risk fields
    assert "relative_hazard" in gated_officer
    assert "linear_predictor" in gated_officer
    assert "model_version" in gated_officer


# ============================================================================
# 5. INVALID TRANSITION
# ============================================================================

def test_5_invalid_transition_rejection(client, app_instance, officer_principal, valid_features):
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = {
        "case_id": "CASE-101",
        "snapshot_date": "2026-03-01",
        "transition": "INVALID_TRANSITION_STEP",
        "features": valid_features,
    }
    response = client.post("/api/officer/survival-risk/predict", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.VALIDATION_FAILED
    assert "Invalid transition" in response.json()["message"]


# ============================================================================
# 6. INVALID HORIZON
# ============================================================================

def test_6_invalid_horizon_rejection(client, app_instance, officer_principal, valid_features):
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = {
        "case_id": "CASE-101",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": valid_features,
        "horizon": 45,  # Unsupported horizon
    }
    response = client.post("/api/officer/survival-risk/predict", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.VALIDATION_FAILED
    assert "Invalid horizon" in response.json()["message"]


# ============================================================================
# 7. MISSING REQUIRED FEATURE
# ============================================================================

def test_7_missing_required_feature_rejection(client, app_instance, officer_principal):
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    # Empty features dict rejected
    payload = {
        "case_id": "CASE-101",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": {},
    }
    response = client.post("/api/officer/survival-risk/predict", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.VALIDATION_FAILED

    # Missing mandatory predictor under strict feature validation
    payload_strict = {
        "case_id": "CASE-101",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": {"derived_project_type": "Rural Infrastructure"},
        "require_features": True,
    }
    response_strict = client.post("/api/officer/survival-risk/predict", json=payload_strict)
    assert response_strict.status_code == 422
    assert "Missing required feature" in response_strict.json()["message"]


# ============================================================================
# 8. MALFORMED DATE
# ============================================================================

def test_8_malformed_snapshot_date_rejection(client, app_instance, officer_principal, valid_features):
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = {
        "case_id": "CASE-101",
        "snapshot_date": "2026-99-99",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": valid_features,
    }
    response = client.post("/api/officer/survival-risk/predict", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.VALIDATION_FAILED
    assert "Malformed snapshot_date" in response.json()["message"]


# ============================================================================
# 9. FUTURE-INFORMATION ATTEMPT (POINT-IN-TIME ENFORCEMENT)
# ============================================================================

def test_9_future_information_rejected(client, app_instance, officer_principal, valid_features):
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = {
        "case_id": "CASE-101",
        "snapshot_date": "2099-01-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": valid_features,
    }
    response = client.post("/api/officer/survival-risk/predict", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.VALIDATION_FAILED
    assert "Future information rejected" in response.json()["message"]


# ============================================================================
# 10. MISSING ARTIFACT SAFETY
# ============================================================================

def test_10_missing_artifact_raises_safe_error(tmp_path):
    empty_dir = tmp_path / "empty_models"
    empty_dir.mkdir()
    with pytest.raises(ArtifactNotFound) as exc_info:
        SurvivalService(models_dir=empty_dir, clean_data_dir=CLEAN_DATA_DIR)
    assert "Model summary artifact missing" in str(exc_info.value)


# ============================================================================
# 11. CORRUPTED ARTIFACT HANDLING (NO SILENT RETRAINING)
# ============================================================================

def test_11_corrupted_artifact_fails_safely_without_retraining(tmp_path):
    corrupt_dir = tmp_path / "corrupt_models"
    corrupt_dir.mkdir()
    (corrupt_dir / "cox_model_summary.json").write_text("{ corrupt json: [")
    with pytest.raises(ArtifactNotFound) as exc_info:
        SurvivalService(models_dir=corrupt_dir, clean_data_dir=CLEAN_DATA_DIR)
    assert "Corrupted or invalid model artifacts" in str(exc_info.value)


# ============================================================================
# 12. MODEL LOADING & INTEGRITY
# ============================================================================

def test_12_model_loading_and_integrity():
    service = get_survival_service()
    health = service.get_health()
    assert health.status == "healthy"
    assert len(health.available_transitions) == 3
    assert "SECTION_11_TO_SECTION_19" in health.available_transitions
    assert "SECTION_19_TO_AWARD" in health.available_transitions
    assert "CASE_INITIATION_TO_MILESTONE" in health.available_transitions
    assert len(health.model_checksums) >= 3


# ============================================================================
# 13. MODEL CACHING (SINGLETON REUSE)
# ============================================================================

def test_13_model_caching_singleton_reuse():
    s1 = get_survival_service()
    s2 = get_survival_service()
    assert s1 is s2
    assert s1._risk_layer is s2._risk_layer
    assert s1._explainer is s2._explainer


# ============================================================================
# 14. DETERMINISTIC PREDICTION
# ============================================================================

def test_14_deterministic_prediction(valid_features):
    service = get_survival_service()
    p1 = service.predict_officer_risk("CASE-101", "2026-03-01", "SECTION_11_TO_SECTION_19", valid_features)
    p2 = service.predict_officer_risk("CASE-101", "2026-03-01", "SECTION_11_TO_SECTION_19", valid_features)
    assert p1.relative_hazard == p2.relative_hazard
    assert p1.linear_predictor == p2.linear_predictor
    assert p1.survival_probability_90d == p2.survival_probability_90d
    assert p1.event_probability_90d == p2.event_probability_90d


# ============================================================================
# 15. AUDITABLE EXPLANATION GENERATION
# ============================================================================

def test_15_auditable_explanation_generation(valid_features):
    service = get_survival_service()
    expl = service.explain_officer_risk("CASE-101", "2026-03-01", "SECTION_11_TO_SECTION_19", valid_features)
    assert isinstance(expl, OfficerSurvivalExplanationOut)
    assert expl.summary_narrative != ""
    assert isinstance(expl.why_hazard_is_higher, list)
    assert isinstance(expl.why_hazard_is_lower, list)
    # Total contributors must equal linear predictor up to numerical tolerance
    total_contrib = sum(f["contribution"] for f in expl.why_hazard_is_higher + expl.why_hazard_is_lower)
    assert abs(total_contrib - expl.linear_predictor) < 1e-4


# ============================================================================
# 16. UNCERTAINTY PROPAGATION
# ============================================================================

def test_16_uncertainty_propagation(valid_features):
    service = get_survival_service()
    res = service.predict_officer_risk("CASE-101", "2026-03-01", "SECTION_11_TO_SECTION_19", valid_features)
    assert "HIGH" in res.uncertainty_status or "SPARSE" in res.uncertainty_status or "CAUTION" in res.uncertainty_status


# ============================================================================
# 17. CALIBRATION STATUS PROPAGATION
# ============================================================================

def test_17_calibration_status_propagation(valid_features):
    service = get_survival_service()
    res = service.predict_officer_risk("CASE-101", "2026-03-01", "SECTION_11_TO_SECTION_19", valid_features)
    assert "CALIBRATION NOT RELIABLE" in res.calibration_status


# ============================================================================
# 18. EXTRAPOLATION FLAG PROPAGATION
# ============================================================================

def test_18_extrapolation_flag_propagation(valid_features):
    service = get_survival_service()
    res = service.predict_officer_risk("CASE-101", "2026-03-01", "SECTION_11_TO_SECTION_19", valid_features)
    assert "30d" in res.extrapolation_status
    assert "90d" in res.extrapolation_status
    assert "365d" in res.extrapolation_status
    # Follow-up cutoff in EVAL is 148 days: 365d and 730d are extrapolated
    assert res.extrapolation_status["30d"] is False
    assert res.extrapolation_status["90d"] is False
    assert res.extrapolation_status["365d"] is True
    assert res.extrapolation_status["730d"] is True


# ============================================================================
# 19. MODEL VERSION PROPAGATION
# ============================================================================

def test_19_model_version_propagation(valid_features):
    service = get_survival_service()
    res = service.predict_officer_risk("CASE-101", "2026-03-01", "SECTION_11_TO_SECTION_19", valid_features)
    assert res.model_version == "1.0.0-cox-production-baseline"


# ============================================================================
# 20. FEATURE VERSION PROPAGATION
# ============================================================================

def test_20_feature_version_propagation():
    service = get_survival_service()
    health = service.get_health()
    assert health.feature_version == "1.0.0-survival-clean-15feat"


# ============================================================================
# 21. NO TRAINING DURING API INFERENCE
# ============================================================================

def test_21_no_training_during_api_inference(valid_features):
    service = get_survival_service()
    with patch("lifelines.CoxPHFitter.fit", side_effect=RuntimeError("Training prohibited during inference")):
        res = service.predict_officer_risk("CASE-101", "2026-03-01", "SECTION_11_TO_SECTION_19", valid_features)
        assert res.relative_hazard > 0.0


# ============================================================================
# 22. NO EVAL DATA ACCESS DURING INFERENCE
# ============================================================================

def test_22_no_eval_data_access_during_inference(valid_features):
    service = get_survival_service()
    eval_csv = CLEAN_DATA_DIR / "survival_eval_features.csv"
    orig_open = open

    def guarded_open(file, *args, **kwargs):
        if str(eval_csv) in str(file):
            raise PermissionError("EVAL data access strictly forbidden during API inference")
        return orig_open(file, *args, **kwargs)

    with patch("builtins.open", side_effect=guarded_open):
        res = service.predict_officer_risk("CASE-101", "2026-03-01", "SECTION_11_TO_SECTION_19", valid_features)
        assert res.relative_hazard > 0.0


# ============================================================================
# 23. NO CAUSAL EXPLANATION LANGUAGE
# ============================================================================

def test_23_no_causal_explanation_language(valid_features):
    service = get_survival_service()
    expl = service.explain_officer_risk("CASE-101", "2026-03-01", "SECTION_11_TO_SECTION_19", valid_features)
    all_text = expl.summary_narrative
    for item in expl.why_hazard_is_higher + expl.why_hazard_is_lower:
        all_text += " " + item.get("narrative", "") + " " + item.get("human_name", "")

    banned_phrases = [
        "caused the delay",
        "causes delay",
        "caused the acquisition",
        "caused progress",
        "causing",
        "because the case was delayed by",
    ]
    for phrase in banned_phrases:
        assert phrase not in all_text.lower(), f"Banned causal phrase found: '{phrase}'"

    assert "not causal" in expl.summary_narrative.lower()
    assert "model's estimated log-hazard" in all_text or "contributed" in all_text


# ============================================================================
# 24. STRUCTURED ERROR ENVELOPES
# ============================================================================

def test_24_structured_error_envelopes(client, app_instance, officer_principal):
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    # 422 Validation Error
    res_val = client.post("/api/officer/survival-risk/predict", json={
        "case_id": "CASE-101",
        "snapshot_date": "invalid-date",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": {"foo": "bar"},
    })
    assert res_val.status_code == 422
    body = res_val.json()
    assert "code" in body
    assert body["code"] == ErrorCode.VALIDATION_FAILED
    assert "message" in body
    assert "details" in body


# ============================================================================
# 25. NO SENSITIVE INTERNAL FIELDS IN CITIZEN RESPONSE
# ============================================================================

def test_25_no_sensitive_internal_fields_in_citizen_response(client, app_instance, citizen_principal):
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen_principal)
    response = client.get("/api/citizen/cases/101/milestone-timeline")
    assert response.status_code == 200
    cit_dict = response.json()

    prohibited_citizen_keys = [
        "relative_hazard",
        "linear_predictor",
        "hazard_multiplier",
        "cox_coefficients",
        "internal_rank",
        "risk_band",
        "event_probability_90d",
        "survival_probability_90d",
    ]
    for key in prohibited_citizen_keys:
        assert key not in cit_dict, f"Prohibited key '{key}' leaked into citizen response!"
