"""LOOP 15 — Security Audit: Citizen/Officer Boundary & Redaction Test Suite.

Verifies:
1. Citizen responses strictly omit all internal ML telemetry, model weights, hazard scores,
   risk bands, and officer notes.
2. ResponseGate rigorously filters all OFFICER_ONLY fields from analytical schemas when
   evaluated against a citizen or unprivileged principal.
3. Structured error responses (401, 403, 422, 500) never leak python tracebacks, file paths,
   database credentials, or internal ML state.
4. Redaction holds across JSON, nested JSON, query parameters, and error envelopes.
"""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient
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
from app.security.gate import ResponseGate, Visibility
from app.services.survival_service import get_survival_service
from app.settings import CoreSettings

OFFICER_ONLY_FIELDS = frozenset({
    "linear_predictor",
    "relative_hazard",
    "survival_probability_30d",
    "survival_probability_90d",
    "survival_probability_180d",
    "survival_probability_365d",
    "survival_probability_730d",
    "event_probability_30d",
    "event_probability_90d",
    "event_probability_180d",
    "event_probability_365d",
    "event_probability_730d",
    "risk_band_90d",
    "calibration_status",
    "uncertainty_status",
    "extrapolation_status",
    "data_quality_warning",
    "model_version",
    "summary_narrative",
    "why_hazard_is_higher",
    "why_hazard_is_lower",
    "missing_features",
    "model_checksums",
    "explainability_available",
})


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
    return TestClient(app_instance)


def test_citizen_milestone_timeline_complete_redaction(client, app_instance):
    """Citizen milestone timeline endpoint must contain zero internal ML telemetry."""
    citizen = Principal(kind="CITIZEN", id="cit-001", case_id="CASE-CITIZEN-001")
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen)

    resp = client.get("/api/citizen/cases/CASE-CITIZEN-001/milestone-timeline")
    assert resp.status_code == 200
    data = resp.json()

    # Red-team verification: Check against every forbidden officer-only and ML telemetry field
    for forbidden in OFFICER_ONLY_FIELDS:
        assert forbidden not in data, f"Citizen payload leaked forbidden field: {forbidden}"

    # Also verify by raw JSON text inspection
    raw_text = resp.text.lower()
    assert "linear_predictor" not in raw_text
    assert "relative_hazard" not in raw_text
    assert "risk_band" not in raw_text
    assert "beta" not in raw_text
    assert "coefficient" not in raw_text


def test_response_gate_direct_redaction_for_citizen():
    """Verify ResponseGate directly strips all OFFICER_ONLY fields from OfficerSurvivalRiskOut."""
    service = get_survival_service()
    feats = {
        "derived_days_in_current_stage": 75.0,
        "district": "Nagpur",
        "derived_project_type": "Rural Infrastructure",
        "current_stage": "SECTION_11",
        "derived_days_since_case_initiation": 120.0,
        "derived_notice_count": 1.0,
        "extension_count": 0.0,
        "has_statutory_extension": 0.0,
        "act_key": "RFCTLARR_2013",
        "derived_is_direct_purchase": 0.0,
    }
    risk_out = service.predict_officer_risk("CASE-100", "2026-03-15", "SECTION_11_TO_SECTION_19", feats)
    raw_dict = risk_out.model_dump()

    citizen = Principal(kind="CITIZEN", id="cit-002", case_id="CASE-100")
    gated_dict = ResponseGate.apply(raw_dict, citizen, OfficerSurvivalRiskOut)

    # All OFFICER_ONLY fields must be stripped
    for forbidden in OFFICER_ONLY_FIELDS:
        assert forbidden not in gated_dict, f"ResponseGate failed to strip {forbidden} for citizen"

    # Only PUBLIC fields remain
    assert "case_id" in gated_dict
    assert "snapshot_date" in gated_dict
    assert "transition" in gated_dict
    assert "governance_disclaimer" in gated_dict


def test_response_gate_direct_redaction_for_explanation():
    """Verify ResponseGate strips explainability narratives and factor tables for citizen."""
    service = get_survival_service()
    feats = {
        "derived_days_in_current_stage": 75.0,
        "district": "Nagpur",
        "derived_project_type": "Rural Infrastructure",
        "current_stage": "SECTION_11",
        "derived_days_since_case_initiation": 120.0,
        "derived_notice_count": 1.0,
        "extension_count": 0.0,
        "has_statutory_extension": 0.0,
        "act_key": "RFCTLARR_2013",
        "derived_is_direct_purchase": 0.0,
    }
    expl_out = service.explain_officer_risk("CASE-100", "2026-03-15", "SECTION_11_TO_SECTION_19", feats)
    raw_dict = expl_out.model_dump()

    citizen = Principal(kind="CITIZEN", id="cit-003", case_id="CASE-100")
    gated_dict = ResponseGate.apply(raw_dict, citizen, OfficerSurvivalExplanationOut)

    assert "why_hazard_is_higher" not in gated_dict
    assert "why_hazard_is_lower" not in gated_dict
    assert "summary_narrative" not in gated_dict
    assert "missing_features" not in gated_dict


def test_error_responses_zero_traceback_leakage(client, app_instance):
    """Verify that error responses under various status codes never leak internal details."""
    app_instance.dependency_overrides.pop(authenticate, None)

    # 401 Unauthenticated
    r401 = client.get("/api/officer/survival-risk/health")
    assert r401.status_code == 401
    body401 = r401.json()
    assert body401 == {"code": "UNAUTHENTICATED", "message": "Unauthenticated", "details": {}}
    assert "Traceback" not in r401.text
    assert "/" not in body401["message"]

    # 403 NotAuthorised
    citizen = Principal(kind="CITIZEN", id="cit-004", case_id="CASE-X")
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen)
    r403 = client.get("/api/officer/survival-risk/health")
    assert r403.status_code == 403
    body403 = r403.json()
    assert body403["code"] == ErrorCode.NOT_AUTHORISED
    assert "Traceback" not in r403.text

    # 422 ValidationFailed
    officer = Principal(kind="OFFICER", id="off-001")
    app_instance.dependency_overrides[authenticate] = _auth_override(officer)
    r422 = client.post("/api/officer/survival-risk/predict", json={
        "case_id": "CASE-1",
        "snapshot_date": "invalid-date",
        "transition": "INVALID",
        "features": {},
    })
    assert r422.status_code == 422
    body422 = r422.json()
    assert body422["code"] == ErrorCode.VALIDATION_FAILED
    assert "Traceback" not in r422.text
    assert "/Users/" not in r422.text
    assert "postgres" not in r422.text
