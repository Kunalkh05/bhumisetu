"""LOOP 15 — Security Audit: Adversarial Input Validation & API Fuzzing Test Suite.

Attacks API boundaries with malformed, malicious, boundary, and unexpected inputs:
1. Missing, null, empty, whitespace strings.
2. Non-convertible string types where numerical values are expected.
3. Non-finite floating-point numbers (NaN, +Inf, -Inf).
4. Negative durations and negative event counts.
5. Future snapshot dates and malformed date strings.
6. SQL injection, path traversal, newline/log injection strings.
7. Nested unexpected objects, arrays where scalars are expected.
8. Invalid statutory transitions and invalid horizons.
9. Purged leakage feature vectors.

Verifies:
- All malformed requests trigger clean HTTP 422 VALIDATION_FAILED.
- Zero traceback or filesystem leakage in responses.
- No arbitrary code execution or unhandled 500 crashes.
"""

from __future__ import annotations

import copy
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.errors import ErrorCode
from app.main import create_app
from app.security.access import Principal, authenticate
from app.settings import CoreSettings


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


@pytest.fixture
def officer_principal():
    return Principal(kind="OFFICER", id="officer-fuzz-tester")


@pytest.fixture
def valid_payload():
    return {
        "case_id": "CASE-E2E-LOOP14",
        "snapshot_date": "2026-03-15",
        "transition": "SECTION_11_TO_SECTION_19",
        "features": {
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
        },
    }


# ============================================================================
# 1. NUMERICAL FEATURE FUZZING
# ============================================================================

@pytest.mark.parametrize("bad_val", [
    "invalid_string",
    "NaN",
    "Infinity",
    "-Infinity",
    "1e999",
    "None",
    "<script>alert(1)</script>",
    "'; DROP TABLE cases; --",
    {"nested": "object"},
    [1, 2, 3],
])
def test_fuzz_numerical_feature_non_convertible_or_complex(client, app_instance, officer_principal, valid_payload, bad_val):
    """Numerical feature passed non-convertible or structured types must return HTTP 422."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = copy.deepcopy(valid_payload)
    payload["features"]["derived_days_in_current_stage"] = bad_val

    resp = client.post("/api/officer/survival-risk/predict", json=payload)
    assert resp.status_code == 422
    err = resp.json()
    assert err["code"] == ErrorCode.VALIDATION_FAILED
    assert "Traceback" not in resp.text


@pytest.mark.parametrize("bad_num", [
    -1.0,
    -100.0,
    -999999.0,
])
def test_fuzz_negative_durations_rejected(client, app_instance, officer_principal, valid_payload, bad_num):
    """Negative duration or count features must be rejected with HTTP 422."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = copy.deepcopy(valid_payload)
    payload["features"]["derived_days_in_current_stage"] = bad_num

    resp = client.post("/api/officer/survival-risk/predict", json=payload)
    assert resp.status_code == 422
    assert resp.json()["code"] == ErrorCode.VALIDATION_FAILED


# ============================================================================
# 2. DATE & TEMPORAL FUZZING
# ============================================================================

@pytest.mark.parametrize("bad_date", [
    "2099-01-01",  # Future date
    "2026-13-45",  # Invalid month/day
    "not-a-date",
    "2026/03/15",  # Slashes
    "2026-03",     # Incomplete
    "   ",         # Whitespace
    "",            # Empty
    "2026-03-15\x00extra",  # Null byte
    "2026-03-15\nDROP",     # Newline
])
def test_fuzz_snapshot_dates(client, app_instance, officer_principal, valid_payload, bad_date):
    """Malformed or future snapshot dates must trigger HTTP 422."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = copy.deepcopy(valid_payload)
    payload["snapshot_date"] = bad_date

    resp = client.post("/api/officer/survival-risk/predict", json=payload)
    assert resp.status_code == 422
    assert resp.json()["code"] == ErrorCode.VALIDATION_FAILED


# ============================================================================
# 3. TRANSITION & HORIZON FUZZING
# ============================================================================

@pytest.mark.parametrize("bad_trans", [
    "UNKNOWN_TRANSITION",
    "SECTION_11",
    "AWARD_TO_POSSESSION",
    "SELECT * FROM cases",
    "../../etc/passwd",
    "SECTION_11_TO_SECTION_19;--",
])
def test_fuzz_transitions(client, app_instance, officer_principal, valid_payload, bad_trans):
    """Unsupported or injected transition strings must trigger HTTP 422."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = copy.deepcopy(valid_payload)
    payload["transition"] = bad_trans

    resp = client.post("/api/officer/survival-risk/predict", json=payload)
    assert resp.status_code == 422
    assert resp.json()["code"] == ErrorCode.VALIDATION_FAILED


@pytest.mark.parametrize("bad_horizon", [
    -1,
    0,
    15,
    45,
    100,
    1000,
    99999,
])
def test_fuzz_horizons(client, app_instance, officer_principal, valid_payload, bad_horizon):
    """Unsupported horizon values outside [30, 90, 180, 365, 730] must trigger HTTP 422."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = copy.deepcopy(valid_payload)
    payload["horizon"] = bad_horizon

    resp = client.post("/api/officer/survival-risk/predict", json=payload)
    assert resp.status_code == 422
    assert resp.json()["code"] == ErrorCode.VALIDATION_FAILED


# ============================================================================
# 4. CASE ID INJECTION & TRAVERSAL
# ============================================================================

@pytest.mark.parametrize("bad_case_id", [
    "",
    "   ",
    "CASE-001\nINJECT_LOG",
    "CASE-001\r\nSET-COOKIE",
    "CASE-001\x00NULL",
    "../../secrets/credentials.json",
    "CASE-' OR '1'='1",
])
def test_fuzz_case_id_injection(client, app_instance, officer_principal, valid_payload, bad_case_id):
    """Injected or malformed case identifiers must be safely rejected with HTTP 422."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = copy.deepcopy(valid_payload)
    payload["case_id"] = bad_case_id

    resp = client.post("/api/officer/survival-risk/predict", json=payload)
    assert resp.status_code == 422
    assert resp.json()["code"] == ErrorCode.VALIDATION_FAILED


# ============================================================================
# 5. PURGED LEAKAGE FEATURES
# ============================================================================

@pytest.mark.parametrize("purged", [
    "award_recorded",
    "objection_count",
    "parcel_count",
    "open_issue_count",
    "notified_area_hectares",
    "affected_landowner_count",
    "compensation_amount_inr",
])
def test_fuzz_purged_features_rejected(client, app_instance, officer_principal, valid_payload, purged):
    """Purged features must trigger strict HTTP 422 leakage rejection."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)
    payload = copy.deepcopy(valid_payload)
    payload["features"][purged] = 1.0

    resp = client.post("/api/officer/survival-risk/predict", json=payload)
    assert resp.status_code == 422
    err = resp.json()
    assert err["code"] == ErrorCode.VALIDATION_FAILED
    assert "purged" in err["message"]
