"""LOOP 14 — End-to-End Product Integration & System Validation Test Suite.

Validates the complete BHUMISETU application as a single coherent system:
OFFICIAL DATA
      ↓
DATA INGESTION / CLEAN RECORD
      ↓
CASE ENTITY
      ↓
POINT-IN-TIME SNAPSHOT (T)
      ↓
15 SAFE ML FEATURES (Contract)
      ↓
SURVIVAL RISK SERVICE
      ↓
COX PH MODEL
      ↓
RISK + SURVIVAL PROBABILITIES
      ↓
UNCERTAINTY & CALIBRATION FLAGS
      ↓
EXPLAINABILITY (Additive Decomposition)
      ↓
FASTAPI ENDPOINTS
      ↓
AUTHORIZATION / REDACTION GATES
      ↓
OFFICER EXPERIENCE CONTRACT
      ↓
CITIZEN EXPERIENCE CONTRACT (Redaction)
      ↓
AUDIT / PROVENANCE
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
from features.survival_features import (
    PURGED_FEATURE_COLUMNS,
    SAFE_PREDICTOR_COLUMNS,
)


# --- Canonical E2E Case Specification ---

CANONICAL_CASE_ID = "CASE-E2E-LOOP14"
CANONICAL_SNAPSHOT_DATE = "2026-03-15"
CANONICAL_TRANSITION = "SECTION_11_TO_SECTION_19"

CANONICAL_FEATURES: dict[str, Any] = {
    "derived_days_since_case_initiation": 120.0,
    "derived_days_in_current_stage": 75.0,
    "derived_days_since_latest_notice": 45.0,
    "derived_notice_count": 1.0,
    "derived_statutory_sec19_proximity_ratio": 0.205,
    "extension_count": 0.0,
    "has_statutory_extension": 0.0,
    "current_stage": "SECTION_11",
    "district": "Nagpur",
    "taluka": "Kuhi",
    "village": "Aamti",
    "acquiring_authority": "District Collectorate & Administration Nagpur",
    "act_key": "RFCTLARR_2013",
    "derived_project_type": "Rural Infrastructure",
    "derived_is_direct_purchase": 0.0,
}


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
    c = TestClient(app_instance)
    yield c
    app_instance.dependency_overrides.clear()


@pytest.fixture
def officer_principal() -> Principal:
    return Principal(kind="OFFICER", id="officer-e2e-loop14", scope_paths=("MH", "Nagpur"))


@pytest.fixture
def authorized_citizen_principal() -> Principal:
    return Principal(kind="CITIZEN", id="citizen-e2e-loop14", case_id=CANONICAL_CASE_ID)


@pytest.fixture
def unauthorized_citizen_principal() -> Principal:
    return Principal(kind="CITIZEN", id="citizen-unauthorized", case_id="CASE_DIFFERENT_999")


@pytest.fixture
def survival_service() -> SurvivalService:
    return SurvivalService(models_dir=MODELS_DIR, clean_data_dir=CLEAN_DATA_DIR)


# ============================================================================
# PHASE 2 & 3: CANONICAL E2E CASE & DATA INTEGRATION
# ============================================================================

def test_phase2_canonical_case_point_in_time_invariants():
    """Verify CANONICAL_CASE_ID has point-in-time integrity anchored to T."""
    snapshot_dt = datetime.strptime(CANONICAL_SNAPSHOT_DATE, "%Y-%m-%d").date()
    today = datetime.now(timezone.utc).date()
    assert snapshot_dt <= today, "Snapshot date T must be on or before system date."

    # Verify no post-T milestones are present in features
    forbidden_future_keys = {
        "section_19_date", "award_date", "compensation_disbursed_date",
        "award_recorded", "final_award_amount", "actual_completion_date",
    }
    for key in forbidden_future_keys:
        assert key not in CANONICAL_FEATURES, f"Future key '{key}' found in canonical input snapshot!"


def test_phase3_clean_data_ingestion_preserves_explicit_missingness():
    """Verify clean dataset records preserve explicit missingness without NULL->0 coercion."""
    clean_cases_file = CLEAN_DATA_DIR / "real_land_acquisition_cases_clean.csv"
    assert clean_cases_file.exists(), f"Missing clean cases file: {clean_cases_file}"

    df = pd.read_csv(clean_cases_file)
    assert len(df) > 0, "Clean cases dataset is empty."
    assert "case_id" in df.columns
    assert "district" in df.columns

    # Verify missing attributes remain NaN/null in raw columns
    missing_cols = ["objection_count", "parcel_count", "compensation_amount_inr"]
    for col in missing_cols:
        if col in df.columns:
            has_null = df[col].isna().any()
            assert has_null, f"Expected explicit NaN in '{col}', but none found."


# ============================================================================
# PHASE 4: SNAPSHOT -> FEATURE CONTRACT (15 APPROVED SAFE PREDICTORS)
# ============================================================================

def test_phase4_feature_contract_adherence():
    """Verify input features strictly conform to the 15-feature production allowlist."""
    # Check that all canonical features belong to SAFE_PREDICTOR_COLUMNS or are metadata
    for col in CANONICAL_FEATURES:
        assert col in SAFE_PREDICTOR_COLUMNS, f"Feature '{col}' not in approved SAFE_PREDICTOR_COLUMNS."

    # Check that none of the 7 purged leakage features exist
    for purged in PURGED_FEATURE_COLUMNS:
        assert purged not in CANONICAL_FEATURES, f"Purged feature '{purged}' leaked into canonical feature set!"


def test_phase4_purged_feature_rejection_at_service_boundary(survival_service):
    """Verify SurvivalService rejects any request containing purged features."""
    for purged in PURGED_FEATURE_COLUMNS:
        bad_features = dict(CANONICAL_FEATURES)
        bad_features[purged] = 1.0
        with pytest.raises(ValidationFailed) as exc_info:
            survival_service.predict_officer_risk(
                case_id=CANONICAL_CASE_ID,
                snapshot_date=CANONICAL_SNAPSHOT_DATE,
                transition=CANONICAL_TRANSITION,
                features=bad_features,
            )
        assert "Feature leakage violation" in str(exc_info.value)


# ============================================================================
# PHASE 5: FEATURE -> ML INTEGRATION
# ============================================================================

def test_phase5_ml_risk_layer_prediction(survival_service):
    """Verify SurvivalService and Cox PH model generate mathematically sound predictions."""
    risk = survival_service.predict_officer_risk(
        case_id=CANONICAL_CASE_ID,
        snapshot_date=CANONICAL_SNAPSHOT_DATE,
        transition=CANONICAL_TRANSITION,
        features=CANONICAL_FEATURES,
    )

    assert risk.case_id == CANONICAL_CASE_ID
    assert risk.snapshot_date == CANONICAL_SNAPSHOT_DATE
    assert risk.transition == CANONICAL_TRANSITION
    assert risk.model_version == MODEL_VERSION

    # Mathematical consistency checks
    assert math.isfinite(risk.linear_predictor)
    assert risk.relative_hazard > 0.0
    # exp(linear_predictor) == relative_hazard
    expected_rh = math.exp(risk.linear_predictor)
    assert abs(risk.relative_hazard - round(expected_rh, 6)) < 1e-4

    # Horizon probabilities monotonic decrease for survival
    assert 0.0 <= risk.survival_probability_30d <= 1.0
    assert 0.0 <= risk.survival_probability_90d <= 1.0
    assert 0.0 <= risk.survival_probability_180d <= 1.0
    assert 0.0 <= risk.survival_probability_365d <= 1.0
    assert 0.0 <= risk.survival_probability_730d <= 1.0

    assert risk.survival_probability_30d >= risk.survival_probability_90d
    assert risk.survival_probability_90d >= risk.survival_probability_180d
    assert risk.survival_probability_180d >= risk.survival_probability_365d

    # Event probabilities: 1 - S(t)
    assert abs(risk.event_probability_90d - (1.0 - risk.survival_probability_90d)) < 1e-4


# ============================================================================
# PHASE 6: ML -> EXPLAINABILITY INTEGRATION
# ============================================================================

def test_phase6_explainability_exact_decomposition_and_non_causal_language(survival_service):
    """Verify linear predictor equals sum of contributions and narratives use non-causal phrasing."""
    expl = survival_service.explain_officer_risk(
        case_id=CANONICAL_CASE_ID,
        snapshot_date=CANONICAL_SNAPSHOT_DATE,
        transition=CANONICAL_TRANSITION,
        features=CANONICAL_FEATURES,
    )

    # 1. Additive decomposition: sum(contributions) == linear_predictor
    contrib_sum = (
        sum(item["contribution"] for item in expl.why_hazard_is_higher)
        + sum(item["contribution"] for item in expl.why_hazard_is_lower)
    )
    assert abs(contrib_sum - expl.linear_predictor) < 1e-5, (
        f"Contribution sum {contrib_sum} does not match linear predictor {expl.linear_predictor}"
    )

    # 2. exp(eta) == relative_hazard
    assert abs(math.exp(expl.linear_predictor) - expl.relative_hazard) < 1e-4

    # 3. Non-causal language audit
    prohibited_causal_words = {"caused", "causes", "because", "due to your", "responsible for"}
    for item in (expl.why_hazard_is_higher + expl.why_hazard_is_lower):
        narrative = item.get("narrative", "").lower()
        for bad_word in prohibited_causal_words:
            assert bad_word not in narrative, f"Prohibited causal word '{bad_word}' found in narrative: {narrative}"
        assert "contributed" in narrative or "associated with" in narrative


# ============================================================================
# PHASE 7 & 8: FASTAPI -> OFFICER EXPERIENCE INTEGRATION
# ============================================================================

def test_phase7_officer_predict_endpoint_contract(client, app_instance, officer_principal):
    """Verify POST /api/officer/survival-risk/predict returns full validated schema."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    payload = {
        "case_id": CANONICAL_CASE_ID,
        "snapshot_date": CANONICAL_SNAPSHOT_DATE,
        "transition": CANONICAL_TRANSITION,
        "features": CANONICAL_FEATURES,
    }

    res = client.post("/api/officer/survival-risk/predict", json=payload)
    assert res.status_code == 200, f"Predict failed: {res.text}"

    data = res.json()
    assert data["case_id"] == CANONICAL_CASE_ID
    assert data["transition"] == CANONICAL_TRANSITION
    assert data["model_version"] == MODEL_VERSION
    assert "relative_hazard" in data
    assert "survival_probability_90d" in data
    assert "event_probability_90d" in data
    assert "uncertainty_status" in data
    assert "calibration_status" in data
    assert GOVERNANCE_SAFETY_DISCLAIMER in data["governance_disclaimer"]


def test_phase8_officer_case_level_endpoints(client, app_instance, officer_principal):
    """Verify GET /api/officer/cases/{id}/survival-risk and explanation."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    # 1. Survival risk
    res_risk = client.get(
        f"/api/officer/cases/{CANONICAL_CASE_ID}/survival-risk",
        params={"transition": CANONICAL_TRANSITION, "snapshot_date": CANONICAL_SNAPSHOT_DATE},
    )
    assert res_risk.status_code == 200
    risk_data = res_risk.json()
    assert risk_data["case_id"] == CANONICAL_CASE_ID
    assert "survival_probability_365d" in risk_data

    # 2. Explanation
    res_expl = client.get(
        f"/api/officer/cases/{CANONICAL_CASE_ID}/survival-risk/explanation",
        params={"transition": CANONICAL_TRANSITION, "snapshot_date": CANONICAL_SNAPSHOT_DATE},
    )
    assert res_expl.status_code == 200
    expl_data = res_expl.json()
    assert "why_hazard_is_higher" in expl_data
    assert "why_hazard_is_lower" in expl_data
    assert expl_data["model_version"] == MODEL_VERSION


# ============================================================================
# PHASE 9: CITIZEN EXPERIENCE & STRICT REDACTION
# ============================================================================

def test_phase9_citizen_milestone_timeline_sanitization(client, app_instance, authorized_citizen_principal):
    """Verify citizen milestone timeline provides statutory guidance without internal ML scores."""
    app_instance.dependency_overrides[authenticate] = _auth_override(authorized_citizen_principal)

    res = client.get(
        f"/api/citizen/cases/{CANONICAL_CASE_ID}/milestone-timeline",
        params={"transition": CANONICAL_TRANSITION},
    )
    assert res.status_code == 200
    data = res.json()

    # Allowed statutory fields
    assert data["case_id"] == CANONICAL_CASE_ID
    assert data["milestone_name"] == "Section 19 Declaration"
    assert data["statutory_time_limit_days"] == 365
    assert "RFCTLARR 2013" in data["statutory_rights_summary"]
    assert "procedural_explanation" in data["citizen_procedural_explanation"].lower() or "land acquisition proceeding" in data["citizen_procedural_explanation"].lower()

    # STRICT REDACTION: Prohibited internal ML and officer fields
    forbidden_keys = {
        "relative_hazard", "linear_predictor", "hazard_score", "risk_band",
        "risk_band_90d", "cox_coefficients", "feature_weights", "hazard_multiplier",
        "model_version", "why_hazard_is_higher", "why_hazard_is_lower",
    }
    for bad_key in forbidden_keys:
        assert bad_key not in data, f"Sensitive ML field '{bad_key}' leaked to citizen endpoint!"


# ============================================================================
# PHASE 10: ROLE-BASED AUTHORIZATION FLOWS
# ============================================================================

def test_phase10_authorization_matrix(
    client,
    app_instance,
    officer_principal,
    authorized_citizen_principal,
    unauthorized_citizen_principal,
):
    """Verify authorization gates across all role permutations."""
    predict_payload = {
        "case_id": CANONICAL_CASE_ID,
        "snapshot_date": CANONICAL_SNAPSHOT_DATE,
        "transition": CANONICAL_TRANSITION,
        "features": CANONICAL_FEATURES,
    }

    # 1. Unauthenticated -> 401
    app_instance.dependency_overrides.clear()
    res_unauth = client.post("/api/officer/survival-risk/predict", json=predict_payload)
    assert res_unauth.status_code == 401

    # 2. Citizen attempting officer predict endpoint -> 403
    app_instance.dependency_overrides[authenticate] = _auth_override(authorized_citizen_principal)
    res_cit_officer = client.post("/api/officer/survival-risk/predict", json=predict_payload)
    assert res_cit_officer.status_code == 403

    # 3. Citizen attempting officer explanation endpoint -> 403
    res_cit_expl = client.get(f"/api/officer/cases/{CANONICAL_CASE_ID}/survival-risk/explanation")
    assert res_cit_expl.status_code == 403

    # 4. Unauthorized citizen attempting another citizen's case -> 403
    app_instance.dependency_overrides[authenticate] = _auth_override(unauthorized_citizen_principal)
    res_cross = client.get(
        f"/api/citizen/cases/{CANONICAL_CASE_ID}/milestone-timeline",
        params={"transition": CANONICAL_TRANSITION},
    )
    assert res_cross.status_code == 403


# ============================================================================
# PHASE 11: DEGRADED / FAILURE MODES & UNCERTAINTY GOVERNANCE
# ============================================================================

def test_phase11_missing_artifact_fails_safely_without_silent_retraining():
    """Verify missing model artifact raises ArtifactNotFound without retrying or retraining."""
    with pytest.raises(ArtifactNotFound):
        SurvivalService(models_dir=GIT_ROOT / "models" / "nonexistent_dir_loop14")


def test_phase11_future_snapshot_rejected_point_in_time(client, app_instance, officer_principal):
    """Verify snapshot_date after system date is strictly rejected with HTTP 422."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    future_payload = {
        "case_id": CANONICAL_CASE_ID,
        "snapshot_date": "2099-01-01",
        "transition": CANONICAL_TRANSITION,
        "features": CANONICAL_FEATURES,
    }

    res = client.post("/api/officer/survival-risk/predict", json=future_payload)
    assert res.status_code == 422
    assert "Future information rejected" in res.json().get("message", "")


def test_phase11_zero_events_transition_uncertainty_governance(client, app_instance, officer_principal):
    """Verify SECTION_19_TO_AWARD correctly flags extreme uncertainty for 0 holdout events."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    payload = {
        "case_id": CANONICAL_CASE_ID,
        "snapshot_date": CANONICAL_SNAPSHOT_DATE,
        "transition": "SECTION_19_TO_AWARD",
        "features": {
            "derived_days_in_current_stage": 100.0,
            "current_stage": "SECTION_19",
            "district": "Solapur",
        },
    }

    res = client.post("/api/officer/survival-risk/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "UNCERTAINTY" in data["uncertainty_status"]


# ============================================================================
# PHASE 12: AUDIT & PROVENANCE LOGGING
# ============================================================================

def test_phase12_audit_trail_provenance_and_secret_redaction(survival_service):
    """Verify audit log captures timestamp, case_id, transition, versions, latency, and zero PII/secrets."""
    audit_before = len(survival_service.audit_log)
    survival_service.predict_officer_risk(
        case_id=CANONICAL_CASE_ID,
        snapshot_date=CANONICAL_SNAPSHOT_DATE,
        transition=CANONICAL_TRANSITION,
        features=CANONICAL_FEATURES,
    )
    audit_after = len(survival_service.audit_log)
    assert audit_after == audit_before + 1

    entry = survival_service.audit_log[-1]
    assert entry["case_id"] == CANONICAL_CASE_ID
    assert entry["transition"] == CANONICAL_TRANSITION
    assert entry["snapshot_date"] == CANONICAL_SNAPSHOT_DATE
    assert entry["model_version"] == MODEL_VERSION
    assert entry["feature_version"] == FEATURE_VERSION
    assert entry["latency_ms"] >= 0.0
    assert "timestamp" in entry

    # Zero secrets / credentials check
    serialized_entry = json.dumps(entry).lower()
    for sensitive_token in ["password", "token", "secret", "bearer", "authorization", "cookie"]:
        assert sensitive_token not in serialized_entry


# ============================================================================
# PHASE 13: CROSS-LAYER DATA CONSISTENCY
# ============================================================================

def test_phase13_cross_layer_data_consistency(client, app_instance, officer_principal, survival_service):
    """Compare direct ML Service output vs FastAPI serialized response for canonical case."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    # 1. Direct Service Call
    direct_risk = survival_service.predict_officer_risk(
        case_id=CANONICAL_CASE_ID,
        snapshot_date=CANONICAL_SNAPSHOT_DATE,
        transition=CANONICAL_TRANSITION,
        features=CANONICAL_FEATURES,
    )

    # 2. FastAPI HTTP Call
    res = client.post(
        "/api/officer/survival-risk/predict",
        json={
            "case_id": CANONICAL_CASE_ID,
            "snapshot_date": CANONICAL_SNAPSHOT_DATE,
            "transition": CANONICAL_TRANSITION,
            "features": CANONICAL_FEATURES,
        },
    )
    assert res.status_code == 200
    api_risk = res.json()

    # 3. Assert Exact Cross-Layer Equivalence
    assert direct_risk.case_id == api_risk["case_id"]
    assert direct_risk.transition == api_risk["transition"]
    assert direct_risk.snapshot_date == api_risk["snapshot_date"]
    assert direct_risk.model_version == api_risk["model_version"]
    assert direct_risk.relative_hazard == api_risk["relative_hazard"]
    assert direct_risk.survival_probability_90d == api_risk["survival_probability_90d"]
    assert direct_risk.event_probability_90d == api_risk["event_probability_90d"]
    assert direct_risk.uncertainty_status == api_risk["uncertainty_status"]
    assert direct_risk.calibration_status == api_risk["calibration_status"]


# ============================================================================
# PHASE 14: FULL USER JOURNEY SCENARIOS
# ============================================================================

def test_phase14_user_journey_scenario_a_officer(client, app_instance, officer_principal):
    """SCENARIO A: Authorized officer views case, evaluates transition risk and explanation."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    # Step 1: Health check
    res_health = client.get("/api/officer/survival-risk/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    # Step 2: Request risk projection
    res_risk = client.post(
        "/api/officer/survival-risk/predict",
        json={
            "case_id": CANONICAL_CASE_ID,
            "snapshot_date": CANONICAL_SNAPSHOT_DATE,
            "transition": CANONICAL_TRANSITION,
            "features": CANONICAL_FEATURES,
        },
    )
    assert res_risk.status_code == 200
    risk = res_risk.json()
    assert risk["model_version"] == MODEL_VERSION
    assert risk["relative_hazard"] > 0.0

    # Step 3: Request explainability
    res_expl = client.get(
        f"/api/officer/cases/{CANONICAL_CASE_ID}/survival-risk/explanation",
        params={"transition": CANONICAL_TRANSITION, "snapshot_date": CANONICAL_SNAPSHOT_DATE},
    )
    assert res_expl.status_code == 200
    expl = res_expl.json()
    assert len(expl["why_hazard_is_lower"]) > 0


def test_phase14_user_journey_scenario_b_citizen(client, app_instance, authorized_citizen_principal):
    """SCENARIO B: Citizen logs in, views statutory progress, confirmed 0 internal risk leaks."""
    app_instance.dependency_overrides[authenticate] = _auth_override(authorized_citizen_principal)

    res = client.get(
        f"/api/citizen/cases/{CANONICAL_CASE_ID}/milestone-timeline",
        params={"transition": CANONICAL_TRANSITION},
    )
    assert res.status_code == 200
    timeline = res.json()
    assert timeline["case_id"] == CANONICAL_CASE_ID
    assert timeline["statutory_time_limit_days"] == 365
    assert "relative_hazard" not in timeline


# ============================================================================
# PHASE 15: PERFORMANCE & LATENCY BENCHMARKS
# ============================================================================

def test_phase15_inference_latency_benchmarks(client, app_instance, officer_principal):
    """Verify backend inference runs consistently fast (sub-25ms warm latency)."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    payload = {
        "case_id": CANONICAL_CASE_ID,
        "snapshot_date": CANONICAL_SNAPSHOT_DATE,
        "transition": CANONICAL_TRANSITION,
        "features": CANONICAL_FEATURES,
    }

    # Warmup
    client.post("/api/officer/survival-risk/predict", json=payload)

    latencies = []
    for _ in range(20):
        t0 = time.perf_counter()
        res = client.post("/api/officer/survival-risk/predict", json=payload)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        assert res.status_code == 200
        latencies.append(dt_ms)

    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile

    assert p50 < 25.0, f"P50 latency {p50:.2f}ms exceeded 25ms threshold."
    assert p95 < 60.0, f"P95 latency {p95:.2f}ms exceeded 60ms threshold."
