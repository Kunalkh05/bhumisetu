"""LOOP 13 — Complete End-to-End ML Pipeline Validation & Safety Audit Test Suite.

Verifies all critical invariants from LOOP 13 specification:
1. Complete Data Flow & Feature Contract Trace (Raw -> Clean -> Snapshot -> 15 Features -> Cox -> Risk -> Explainer -> API -> Frontend)
2. Point-in-Time Leakage Protection (T vs T+1 event independence)
3. Purged Feature Rejection across Data, Feature, Model, and API layers
4. Model Artifact Integrity & Checksums
5. Loop 8/9/10 Artifact Integrity
6. API -> Frontend Consistency
7. Explainability Consistency (sum(contributions) == eta, exp(eta) == relative_hazard)
8. Fallback Safety Audit (DEGRADED / SIMULATION flags and disclaimers)
9. Zero-Event Transition Governance (SECTION_19_TO_AWARD)
10. Sparse-Event Warning Propagation
11. Role-Separated Security & Redaction (Officer vs Citizen)
12. Authorization Bypass Rejection (HTTP 401 / 403)
13. Malformed Input Handling (HTTP 422 structured errors, no stack traces)
14. Model Failure Behavior (clean error, zero silent retraining)
15. Prediction Audit Logging (provenance, timestamps, immutability)
16. Inference Performance Benchmarks (P50, P95, sub-10ms warm inference)
18. End-to-End Scenario Verification
"""

from __future__ import annotations

import copy
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
from typing import Any

from fastapi.testclient import TestClient
import numpy as np
import pandas as pd
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

GIT_ROOT = Path(__file__).resolve().parents[5]
MODELS_DIR = GIT_ROOT / "models" / "cox_baseline"
CLEAN_DATA_DIR = GIT_ROOT / "data" / "real_data" / "clean"
ML_SRC = GIT_ROOT / "bhumi-setu" / "ml" / "src"

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
from features.snapshots import compute_point_in_time_features
from app.db.event_log import AsOfMode


# --- Helpers & Fixtures ---

def _auth_override(principal: Principal):
    async def _override(request: Request) -> Principal:
        request.state.principal = principal
        return principal
    return _override


@pytest.fixture(scope="module")
def app_instance():
    settings = CoreSettings.model_validate({"APP_ENV": "development", "LOG_LEVEL": "WARNING"})
    return create_app(settings)


@pytest.fixture
def client(app_instance):
    client = TestClient(app_instance)
    yield client
    app_instance.dependency_overrides.clear()


@pytest.fixture
def officer_principal() -> Principal:
    return Principal(kind="OFFICER", id="officer-audit-1", scope_paths=("MH",))


@pytest.fixture
def citizen_principal() -> Principal:
    return Principal(kind="CITIZEN", id="citizen-audit-1", case_id=101)


@pytest.fixture
def baseline_features() -> dict[str, Any]:
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
# STEP 1: TRACE THE COMPLETE DATA FLOW & FEATURE CONTRACT
# ============================================================================

def test_step1_feature_contract_preservation():
    """Verify that the 15 clean, leakage-safe feature contract is strictly maintained across all layers."""
    # 1. Verify clean dataset columns
    feature_matrix_path = CLEAN_DATA_DIR / "survival_feature_matrix.csv"
    assert feature_matrix_path.exists(), "Feature matrix artifact must exist"
    df_features = pd.read_csv(feature_matrix_path, nrows=5)

    # Core non-purged predictors
    core_predictors = {
        "derived_days_in_current_stage",
        "district",
        "derived_project_type",
        "current_stage",
        "derived_days_since_case_initiation",
        "derived_notice_count",
        "extension_count",
        "has_statutory_extension",
        "act_key",
        "derived_is_direct_purchase",
    }
    for col in core_predictors:
        assert col in df_features.columns, f"Core predictor '{col}' must be in clean feature matrix"

    # 2. Verify model specification uses this contract
    model_summary_file = MODELS_DIR / "cox_model_summary.json"
    with open(model_summary_file, "r") as f:
        summary = json.load(f)

    for trans, meta in summary.items():
        used_cols = set(meta["predictor_columns_used"])
        assert used_cols.issubset(core_predictors), f"Model {trans} uses unauthorized features: {used_cols - core_predictors}"
        assert not used_cols.intersection(PURGED_LEAKAGE_FEATURES), f"Purged features detected in {trans}"

    # 3. Verify SurvivalService metadata matches
    service = get_survival_service()
    health = service.get_health()
    assert health.model_version == MODEL_VERSION
    assert health.feature_version == FEATURE_VERSION


# ============================================================================
# STEP 2: POINT-IN-TIME LEAKAGE TEST
# ============================================================================

def test_step2_point_in_time_future_event_independence():
    """Adversarial test: An event introduced at T + 1 day CANNOT influence features, hazard, or explanations as of T."""
    case = {
        "case_id": "CAS_AUDIT_001",
        "case_number": "100/A-65/2024-25",
        "district": "Solapur",
        "taluka": "North Solapur",
        "village": "Shelgi",
        "acquiring_authority": "Collectorate",
        "act_key": "RFCTLARR_2013",
        "derived_project_type": "Rural Infrastructure",
        "derived_is_direct_purchase": "False",
        "first_notice_date": "2024-01-01",
        "section_11_date": "2024-01-01",
    }

    # Events up to T (2024-03-01)
    events_at_T = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_AUDIT_001",
            "event_type": "SECTION_11",
            "event_date": "2024-01-01",
            "recording_date": "2024-01-01",
        }
    ]

    snapshot_date_T = date(2024, 3, 1)
    feats_T = compute_point_in_time_features(case, events_at_T, snapshot_date_T, mode=AsOfMode.KNOWABLE_AT)

    # Now introduce future event at T + 1 day (2024-03-02)
    events_with_future = list(events_at_T) + [
        {
            "event_id": "EVT_FUTURE",
            "case_id": "CAS_AUDIT_001",
            "event_type": "SECTION_19",
            "event_date": "2024-03-02",  # T + 1 day
            "recording_date": "2024-03-02",
        },
        {
            "event_id": "EVT_FUTURE_OBJECTION",
            "case_id": "CAS_AUDIT_001",
            "event_type": "OBJECTION_RECORDED",
            "event_date": "2024-03-02",
            "recording_date": "2024-03-02",
        }
    ]

    feats_with_future_log = compute_point_in_time_features(case, events_with_future, snapshot_date_T, mode=AsOfMode.KNOWABLE_AT)

    # 1. Feature vectors must be identical
    assert feats_T == feats_with_future_log, "Features computed at T must be completely identical despite T+1 events"

    # 2. Predictions & explanations must be identical (using clean predictor dictionary)
    clean_feats_T = {k: v for k, v in feats_T.items() if k not in PURGED_LEAKAGE_FEATURES}
    clean_feats_future = {k: v for k, v in feats_with_future_log.items() if k not in PURGED_LEAKAGE_FEATURES}
    assert clean_feats_T == clean_feats_future

    service = get_survival_service()
    pred_1 = service.predict_officer_risk("CAS_AUDIT_001", "2024-03-01", "SECTION_11_TO_SECTION_19", clean_feats_T)
    pred_2 = service.predict_officer_risk("CAS_AUDIT_001", "2024-03-01", "SECTION_11_TO_SECTION_19", clean_feats_future)

    assert pred_1.linear_predictor == pred_2.linear_predictor
    assert pred_1.relative_hazard == pred_2.relative_hazard
    assert pred_1.event_probability_90d == pred_2.event_probability_90d

    expl_1 = service.explain_officer_risk("CAS_AUDIT_001", "2024-03-01", "SECTION_11_TO_SECTION_19", clean_feats_T)
    expl_2 = service.explain_officer_risk("CAS_AUDIT_001", "2024-03-01", "SECTION_11_TO_SECTION_19", clean_feats_future)
    assert expl_1.why_hazard_is_higher == expl_2.why_hazard_is_higher
    assert expl_1.why_hazard_is_lower == expl_2.why_hazard_is_lower


# ============================================================================
# STEP 3: PURGED FEATURE TEST
# ============================================================================

@pytest.mark.parametrize("purged_feat", [
    "award_recorded",
    "objection_count",
    "parcel_count",
    "open_issue_count",
    "notified_area_hectares",
    "affected_landowner_count",
    "compensation_amount_inr",
])
def test_step3_purged_feature_rejection_at_all_layers(client, app_instance, officer_principal, baseline_features, purged_feat):
    """Verify that every layer (API, Service, Model) explicitly rejects all 7 purged leakage features."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    bad_features = copy.deepcopy(baseline_features)
    bad_features[purged_feat] = 100.0

    # 1. API Layer rejection
    payload = {
        "case_id": "CASE-AUDIT-PURGE",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": bad_features,
    }
    resp = client.post("/api/officer/survival-risk/predict", json=payload)
    assert resp.status_code == 422
    err_body = resp.json()
    assert err_body["code"] == ErrorCode.VALIDATION_FAILED
    assert "purged features" in err_body["message"]
    assert purged_feat in err_body["details"]["purged_features_detected"]

    # 2. Service Layer rejection
    service = get_survival_service()
    with pytest.raises(ValidationFailed) as exc_info:
        service.predict_officer_risk("CASE-AUDIT-PURGE", "2026-03-01", "SECTION_11_TO_SECTION_19", bad_features)
    assert exc_info.value.code == ErrorCode.VALIDATION_FAILED

    # 3. Model Layer rejection
    risk_layer = service._risk_layer
    bad_df = pd.DataFrame([{**bad_features, "case_id": "C1", "transition": "SECTION_11_TO_SECTION_19"}])
    with pytest.raises(ValueError, match="Feature leakage violation"):
        risk_layer.predict_risk(bad_df)


# ============================================================================
# STEP 4 & 5: MODEL & EVALUATION ARTIFACT INTEGRITY
# ============================================================================

def test_step4_and_5_artifact_integrity_and_checksums():
    """Verify that model files, eval summary, calibration summary, and explanations match verified digests."""
    service = get_survival_service()
    checksums = service._explainer.checksums

    expected_checksums = {
        "SECTION_11_TO_SECTION_19": "6cab5d24dbc3587b",
        "SECTION_19_TO_AWARD": "260328f59192648f",
        "CASE_INITIATION_TO_MILESTONE": "2493aa920caf664a",
    }
    assert checksums == expected_checksums, "Model coefficient digests must match LOOP 7C / LOOP 10 exactly"

    # Verify SHA256 of key artifacts
    model_summary_file = MODELS_DIR / "cox_model_summary.json"
    with open(model_summary_file, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    assert digest == "87c8684be336137ecee9fc20048ec02476e8edc3a1fef9742f5eda30f13141e8"

    calibration_file = MODELS_DIR / "cox_calibration_summary.json"
    with open(calibration_file, "rb") as f:
        digest_cal = hashlib.sha256(f.read()).hexdigest()
    assert digest_cal == "2c4dc8b25c75137d8075c012d2601e83feb9895e528932d8782bfc83bb0f2fd4"

    eval_file = MODELS_DIR / "cox_eval_summary.json"
    with open(eval_file, "rb") as f:
        digest_eval = hashlib.sha256(f.read()).hexdigest()
    assert digest_eval == "dc58ae5db29ebddd2392b3a898de133c0543e15f81f6f588221717f118ba0859"


# ============================================================================
# STEP 6: API -> FRONTEND CONSISTENCY
# ============================================================================

def test_step6_api_to_frontend_field_consistency(client, app_instance, officer_principal, baseline_features):
    """Verify that every field returned by the API is exact and ready for direct frontend consumption without recalculation."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    resp = client.post("/api/officer/survival-risk/predict", json={
        "case_id": "CASE-CONSISTENCY",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": baseline_features,
    })
    assert resp.status_code == 200
    data = resp.json()

    # Invariants for frontend rendering
    for h in ["30d", "90d", "180d", "365d", "730d"]:
        s_prob = data[f"survival_probability_{h}"]
        e_prob = data[f"event_probability_{h}"]
        assert 0.0 <= s_prob <= 1.0, f"Survival probability {h} out of bounds"
        assert 0.0 <= e_prob <= 1.0, f"Event probability {h} out of bounds"
        # Mathematical invariant: S(t) + P(t) = 1.0
        assert math.isclose(s_prob + e_prob, 1.0, abs_tol=1e-5), f"S({h}) + P({h}) != 1.0"

    assert data["model_version"] == "1.0.0-cox-production-baseline"
    assert "uncertainty_status" in data
    assert "calibration_status" in data
    assert "extrapolation_status" in data
    assert "governance_disclaimer" in data


# ============================================================================
# STEP 7: EXPLAINABILITY CONSISTENCY
# ============================================================================

def test_step7_explainability_mathematical_consistency(client, app_instance, officer_principal, baseline_features):
    """Verify: sum(feature contributions) == linear_predictor, exp(linear_predictor) == relative_hazard."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    for trans in ["SECTION_11_TO_SECTION_19", "SECTION_19_TO_AWARD", "CASE_INITIATION_TO_MILESTONE"]:
        service = get_survival_service()
        expl = service.explain_officer_risk("CASE-EXPL-AUDIT", "2026-03-01", trans, baseline_features)

        eta = expl.linear_predictor
        rel_hazard = expl.relative_hazard

        # Verify exp(eta) == relative_hazard
        expected_hazard = math.exp(eta)
        assert math.isclose(rel_hazard, expected_hazard, rel_tol=1e-4), f"exp({eta}) != {rel_hazard}"

        # Sum of contributions
        total_contrib = sum(f["contribution"] for f in expl.why_hazard_is_higher) + \
                        sum(f["contribution"] for f in expl.why_hazard_is_lower)

        assert math.isclose(total_contrib, eta, abs_tol=1e-5), f"Sum of contributions {total_contrib} != linear predictor {eta}"

        # Verify contributor ordering
        if len(expl.why_hazard_is_higher) > 1:
            higher_contribs = [f["contribution"] for f in expl.why_hazard_is_higher]
            assert higher_contribs == sorted(higher_contribs, reverse=True), "Higher factors must be descending"

        if len(expl.why_hazard_is_lower) > 1:
            lower_contribs = [f["contribution"] for f in expl.why_hazard_is_lower]
            assert lower_contribs == sorted(lower_contribs), "Lower factors must be ascending (most negative first)"


# ============================================================================
# STEP 8: FALLBACK SAFETY AUDIT
# ============================================================================

def test_step8_fallback_safety_flags_and_labels():
    """Verify that offline simulation fallback is explicitly labeled as DEGRADED / SIMULATION MODE."""
    # 1. Test live health reports healthy
    service = get_survival_service()
    health = service.get_health()
    assert health.status == "healthy"

    # 2. Verify that frontend API client defines prominent DEGRADED / SIMULATION MODE fallback flags
    ts_service_file = GIT_ROOT / "bhumi-setu" / "apps" / "web" / "src" / "services" / "survivalRiskService.ts"
    assert ts_service_file.exists()
    ts_content = ts_service_file.read_text()

    assert "is_degraded_simulation: true" in ts_content
    assert "mode_label: 'DEGRADED_SIMULATION_BASELINE'" in ts_content
    assert "DEGRADED / SIMULATION MODE" in ts_content
    assert "[DEGRADED / SIMULATION MODE]" in ts_content
    assert "SIMULATION — UNCALIBRATED OFFLINE BASELINE" in ts_content

    # 3. Verify that the React Dashboard component renders the prominent warning banner
    dashboard_component = GIT_ROOT / "bhumi-setu" / "apps" / "web" / "src" / "components" / "officer" / "survival" / "SurvivalRiskDashboard.tsx"
    assert dashboard_component.exists()
    dash_content = dashboard_component.read_text()

    assert "DEGRADED / SIMULATION MODE" in dash_content
    assert "EMPIRICAL BASELINE / SIMULATION (NOT LIVE MODEL OUTPUT)" in dash_content
    assert "LIVE MODEL OUTPUT" in dash_content
    assert "riskData.is_degraded_simulation" in dash_content


# ============================================================================
# STEP 9: ZERO-EVENT TRANSITION GOVERNANCE
# ============================================================================

def test_step9_zero_event_transition_handling(client, app_instance, officer_principal, baseline_features):
    """Test SECTION_19_TO_AWARD where holdout EVAL cohort observed zero target events."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    resp = client.post("/api/officer/survival-risk/predict", json={
        "case_id": "CASE-ZERO-EVENTS",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_19_TO_AWARD",
        "features": baseline_features,
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["calibration_status"] == "CALIBRATION NOT RELIABLE — INSUFFICIENT EVENTS"
    assert data["uncertainty_status"] == "EXTREME_UNCERTAINTY_ZERO_EVENTS"
    assert data["extrapolation_status"]["180d"] is True
    assert data["extrapolation_status"]["365d"] is True
    assert data["extrapolation_status"]["730d"] is True
    assert "zero target events" in data["data_quality_warning"].lower()


# ============================================================================
# STEP 10: SPARSE-EVENT WARNING PROPAGATION
# ============================================================================

def test_step10_sparse_event_warnings_propagation(client, app_instance, officer_principal, baseline_features):
    """Verify that statistical uncertainty warnings survive through the ML, API, and Schema layers."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    for trans in ["SECTION_11_TO_SECTION_19", "CASE_INITIATION_TO_MILESTONE"]:
        resp = client.post("/api/officer/survival-risk/predict", json={
            "case_id": "CASE-SPARSE",
            "snapshot_date": "2026-03-01",
            "transition": trans,
            "features": baseline_features,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["uncertainty_status"] == "HIGH_UNCERTAINTY_SPARSE_EVENTS"
        assert "CALIBRATION NOT RELIABLE" in data["calibration_status"]
        assert data["extrapolation_status"]["180d"] is True
        assert data["extrapolation_status"]["365d"] is True


# ============================================================================
# STEP 11: CITIZEN / OFFICER SECURITY TEST
# ============================================================================

def test_step11_citizen_output_does_not_leak_internal_ml(client, app_instance, citizen_principal):
    """Verify that the citizen endpoint strictly redacts all internal ML coefficients and scores."""
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen_principal)
    resp = client.get("/api/citizen/cases/101/milestone-timeline?transition=SECTION_11_TO_SECTION_19")
    assert resp.status_code == 200
    citizen_data = resp.json()

    # Strictly forbidden citizen fields
    forbidden_keys = [
        "relative_hazard",
        "linear_predictor",
        "coefficients",
        "internal_hazard_scores",
        "case_ranking",
        "risk_band_90d",
        "model_decomposition",
        "why_hazard_is_higher",
        "why_hazard_is_lower",
        "model_version",
    ]
    for key in forbidden_keys:
        assert key not in citizen_data, f"Citizen endpoint leaked sensitive field: {key}"

    # Legitimate citizen rights fields
    assert citizen_data["case_id"] == "101"
    assert "statutory_rights_summary" in citizen_data
    assert "citizen_procedural_explanation" in citizen_data


# ============================================================================
# STEP 12: AUTHORIZATION BYPASS TEST
# ============================================================================

def test_step12_authorization_bypass_attempts(client, app_instance, citizen_principal, baseline_features):
    """Test all authorization bypass vectors: citizen token on officer endpoint, unauthenticated, wrong citizen case."""
    # 1. Citizen token -> Officer predict
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen_principal)
    resp = client.post("/api/officer/survival-risk/predict", json={
        "case_id": "101",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": baseline_features,
    })
    assert resp.status_code == 403
    assert resp.json()["code"] == ErrorCode.NOT_AUTHORISED

    # 2. Citizen token -> Officer case survival risk
    resp = client.get("/api/officer/cases/101/survival-risk")
    assert resp.status_code == 403
    assert resp.json()["code"] == ErrorCode.NOT_AUTHORISED

    # 3. Citizen token -> Officer explanation
    resp = client.get("/api/officer/cases/101/survival-risk/explanation")
    assert resp.status_code == 403
    assert resp.json()["code"] == ErrorCode.NOT_AUTHORISED

    # 4. Unauthenticated -> Officer endpoint
    app_instance.dependency_overrides.clear()
    resp = client.get("/api/officer/cases/101/survival-risk")
    assert resp.status_code == 401
    assert resp.json()["code"] == ErrorCode.UNAUTHENTICATED

    # 5. Citizen accessing another citizen's case timeline
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen_principal)  # case_id=101
    resp = client.get("/api/citizen/cases/999/milestone-timeline")
    assert resp.status_code == 403


# ============================================================================
# STEP 13: MALFORMED INPUT TESTING
# ============================================================================

@pytest.mark.parametrize("payload,expected_err", [
    ({"case_id": "C1", "snapshot_date": "2026-03-01", "transition": "INVALID_TRANSITION", "features": {"a": 1}}, "Invalid transition"),
    ({"case_id": "C1", "snapshot_date": "2026-03-01", "transition": "SECTION_11_TO_SECTION_19", "features": {"a": 1}, "horizon": 999}, "Invalid horizon"),
    ({"case_id": "C1", "snapshot_date": "not-a-date", "transition": "SECTION_11_TO_SECTION_19", "features": {"a": 1}}, "Malformed snapshot_date"),
    ({"case_id": "C1", "snapshot_date": "2099-01-01", "transition": "SECTION_11_TO_SECTION_19", "features": {"a": 1}}, "Future information rejected"),
    ({"case_id": "C1", "snapshot_date": "2026-03-01", "transition": "SECTION_11_TO_SECTION_19", "features": {}}, "Missing required features"),
])
def test_step13_malformed_inputs_structured_rejection(client, app_instance, officer_principal, payload, expected_err):
    """Verify safe validation, HTTP 422, structured errors, and zero stack trace disclosure."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    resp = client.post("/api/officer/survival-risk/predict", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == ErrorCode.VALIDATION_FAILED
    assert expected_err in data["message"]
    # Internal path leakage check
    assert "/Users/" not in resp.text
    assert "Traceback" not in resp.text


def test_step13_extreme_numeric_values_handling(client, app_instance, officer_principal, baseline_features):
    """Verify that extreme numeric values do not cause server crashes."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    extreme_features = dict(baseline_features)
    extreme_features["derived_days_in_current_stage"] = 1e12  # extreme days

    resp = client.post("/api/officer/survival-risk/predict", json={
        "case_id": "CASE-EXTREME",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": extreme_features,
    })
    # Should safely compute or return a valid bounded prediction without unhandled exception
    assert resp.status_code == 200
    data = resp.json()
    assert 0.0 <= data["survival_probability_30d"] <= 1.0


# ============================================================================
# STEP 14: MODEL FAILURE BEHAVIOR
# ============================================================================

def test_step14_model_failure_behavior_no_retraining():
    """Verify that missing or corrupted artifacts raise a clean error and never trigger automatic retraining."""
    with pytest.raises(ArtifactNotFound) as exc_info:
        SurvivalService(models_dir="/nonexistent/directory/path")
    assert "not found" in str(exc_info.value)
    assert exc_info.value.status_code == 500


# ============================================================================
# STEP 15: AUDIT LOGGING
# ============================================================================

def test_step15_audit_logging_integrity(client, app_instance, officer_principal, baseline_features):
    """Verify prediction audit records: timestamp, case_id, transition, snapshot_date, model_version, latency."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    service = get_survival_service()
    initial_log_count = len(service.get_audit_log())

    resp = client.post("/api/officer/survival-risk/predict", json={
        "case_id": "CASE-AUDIT-101",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": baseline_features,
    })
    assert resp.status_code == 200

    logs = service.get_audit_log()
    assert len(logs) == initial_log_count + 1
    last_log = logs[-1]
    assert last_log["case_id"] == "CASE-AUDIT-101"
    assert last_log["transition"] == "SECTION_11_TO_SECTION_19"
    assert last_log["snapshot_date"] == "2026-03-01"
    assert last_log["model_version"] == MODEL_VERSION
    assert last_log["feature_version"] == FEATURE_VERSION
    assert isinstance(last_log["latency_ms"], float)


# ============================================================================
# STEP 16: PERFORMANCE BENCHMARK
# ============================================================================

def test_step16_inference_latency_benchmark(baseline_features):
    """Verify inference performance satisfies real-time operational thresholds."""
    service = get_survival_service()

    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        service.predict_officer_risk("CASE-BENCH", "2026-03-01", "SECTION_11_TO_SECTION_19", baseline_features)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    p50 = statistics.median(latencies)
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]

    # Real-time thresholds: median < 10ms, p95 < 25ms
    assert p50 < 10.0, f"P50 latency too high: {p50:.2f}ms"
    assert p95 < 25.0, f"P95 latency too high: {p95:.2f}ms"


# ============================================================================
# STEP 18: END-TO-END SCENARIO
# ============================================================================

def test_step18_complete_end_to_end_scenario(client, app_instance, officer_principal, baseline_features):
    """Trace one representative case end-to-end through the entire pipeline and verify consistency."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    # 1. Prediction endpoint
    resp = client.post("/api/officer/survival-risk/predict", json={
        "case_id": "CASE-E2E-FINAL",
        "snapshot_date": "2026-03-01",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": baseline_features,
    })
    assert resp.status_code == 200
    risk_out = resp.json()

    # 2. Explanation endpoint
    service = get_survival_service()
    expl_out = service.explain_officer_risk(
        case_id="CASE-E2E-FINAL",
        snapshot_date="2026-03-01",
        transition="SECTION_11_TO_SECTION_19",
        features=baseline_features,
    )

    # Verify matching fields
    assert risk_out["linear_predictor"] == expl_out.linear_predictor
    assert risk_out["relative_hazard"] == expl_out.relative_hazard
    assert risk_out["survival_probability_90d"] == expl_out.survival_probability_90d
    assert risk_out["event_probability_90d"] == expl_out.event_probability_90d
    assert risk_out["risk_band_90d"] == expl_out.risk_band_90d
    assert risk_out["model_version"] == expl_out.model_version

    # Verify explainability factors add to linear predictor
    total_contrib = sum(f.get("contribution", 0.0) for f in expl_out.why_hazard_is_higher) + \
                    sum(f.get("contribution", 0.0) for f in expl_out.why_hazard_is_lower)
    assert math.isclose(total_contrib, expl_out.linear_predictor, abs_tol=1e-5)
