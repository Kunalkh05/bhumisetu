"""LOOP 15 — Security Audit: Authentication & Authorization Test Suite.

Verifies:
1. Unauthenticated rejection (HTTP 401) on all sensitive endpoints.
2. Citizen principal attempting officer endpoints is strictly forbidden (HTTP 403).
3. Citizen principal attempting internal endpoints is strictly forbidden (HTTP 403).
4. Cross-case access / IDOR protection: Citizen A cannot view Citizen B's milestone timeline.
5. Citizen principal with case_id=None fails closed (HTTP 403).
6. Officer principal can access officer analytical routes and health checks.
7. Internal service principal can access internal ML prediction endpoint.
"""

from __future__ import annotations

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
    return Principal(kind="OFFICER", id="officer-security-tester")


@pytest.fixture
def citizen_principal_case_a():
    return Principal(kind="CITIZEN", id="citizen-user-a", case_id="CASE-A")


@pytest.fixture
def citizen_principal_no_case():
    return Principal(kind="CITIZEN", id="citizen-user-no-case", case_id=None)


@pytest.fixture
def service_principal():
    return Principal(kind="SERVICE", id="internal-service-client")


@pytest.fixture
def sample_payload():
    return {
        "case_id": "CASE-A",
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


def test_unauthenticated_rejection_across_sensitive_endpoints(client, app_instance, sample_payload):
    """Every sensitive route must fail-closed with HTTP 401 when no auth is presented."""
    app_instance.dependency_overrides.pop(authenticate, None)

    # 1. Officer prediction
    res1 = client.post("/api/officer/survival-risk/predict", json=sample_payload)
    assert res1.status_code == 401
    assert res1.json()["code"] == ErrorCode.UNAUTHENTICATED

    # 2. Officer case projection
    res2 = client.get("/api/officer/cases/CASE-A/survival-risk")
    assert res2.status_code == 401
    assert res2.json()["code"] == ErrorCode.UNAUTHENTICATED

    # 3. Officer explanation
    res3 = client.get("/api/officer/cases/CASE-A/survival-risk/explanation")
    assert res3.status_code == 401
    assert res3.json()["code"] == ErrorCode.UNAUTHENTICATED

    # 4. Officer ML health
    res4 = client.get("/api/officer/survival-risk/health")
    assert res4.status_code == 401
    assert res4.json()["code"] == ErrorCode.UNAUTHENTICATED

    # 5. Citizen milestone timeline
    res5 = client.get("/api/citizen/cases/CASE-A/milestone-timeline")
    assert res5.status_code == 401
    assert res5.json()["code"] == ErrorCode.UNAUTHENTICATED

    # 6. Internal ML prediction
    res6 = client.post("/internal/ml/survival/predict", json=sample_payload)
    assert res6.status_code == 401
    assert res6.json()["code"] == ErrorCode.UNAUTHENTICATED


def test_citizen_to_officer_endpoints_denial(client, app_instance, citizen_principal_case_a, sample_payload):
    """Citizen principal attempting any officer endpoint must receive HTTP 403 NotAuthorised."""
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen_principal_case_a)

    # POST /api/officer/survival-risk/predict
    res1 = client.post("/api/officer/survival-risk/predict", json=sample_payload)
    assert res1.status_code == 403
    assert res1.json()["code"] == ErrorCode.NOT_AUTHORISED

    # GET /api/officer/cases/{id}/survival-risk
    res2 = client.get("/api/officer/cases/CASE-A/survival-risk")
    assert res2.status_code == 403
    assert res2.json()["code"] == ErrorCode.NOT_AUTHORISED

    # GET /api/officer/cases/{id}/survival-risk/explanation
    res3 = client.get("/api/officer/cases/CASE-A/survival-risk/explanation")
    assert res3.status_code == 403
    assert res3.json()["code"] == ErrorCode.NOT_AUTHORISED

    # GET /api/officer/survival-risk/health
    res4 = client.get("/api/officer/survival-risk/health")
    assert res4.status_code == 403
    assert res4.json()["code"] == ErrorCode.NOT_AUTHORISED


def test_citizen_to_internal_endpoint_denial(client, app_instance, citizen_principal_case_a, sample_payload):
    """Citizen principal attempting internal service endpoint must receive HTTP 403 NotAuthorised."""
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen_principal_case_a)

    res = client.post("/internal/ml/survival/predict", json=sample_payload)
    assert res.status_code == 403
    assert res.json()["code"] == ErrorCode.NOT_AUTHORISED


def test_citizen_cross_case_idor_denial(client, app_instance, citizen_principal_case_a):
    """Citizen authorized for CASE-A cannot access CASE-B or CASE-C (IDOR protection)."""
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen_principal_case_a)

    # 1. Accessing own case CASE-A succeeds
    res_own = client.get("/api/citizen/cases/CASE-A/milestone-timeline")
    assert res_own.status_code == 200
    assert res_own.json()["case_id"] == "CASE-A"

    # 2. Accessing other cases CASE-B and CASE-C fails closed with HTTP 403
    res_b = client.get("/api/citizen/cases/CASE-B/milestone-timeline")
    assert res_b.status_code == 403
    assert res_b.json()["code"] == ErrorCode.NOT_AUTHORISED

    res_c = client.get("/api/citizen/cases/CASE-C/milestone-timeline")
    assert res_c.status_code == 403
    assert res_c.json()["code"] == ErrorCode.NOT_AUTHORISED


def test_citizen_with_no_case_fails_closed(client, app_instance, citizen_principal_no_case):
    """Citizen with case_id=None must be denied access to any case timeline (HTTP 403)."""
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen_principal_no_case)

    res = client.get("/api/citizen/cases/CASE-A/milestone-timeline")
    assert res.status_code == 403
    assert res.json()["code"] == ErrorCode.NOT_AUTHORISED


def test_officer_access_permitted(client, app_instance, officer_principal, sample_payload):
    """Officer principal has legitimate access to analytical and health endpoints."""
    app_instance.dependency_overrides[authenticate] = _auth_override(officer_principal)

    res_health = client.get("/api/officer/survival-risk/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_pred = client.post("/api/officer/survival-risk/predict", json=sample_payload)
    assert res_pred.status_code == 200
    assert "relative_hazard" in res_pred.json()


def test_service_principal_internal_access(client, app_instance, service_principal, sample_payload):
    """Internal service principal can invoke /internal/ml/survival/predict."""
    app_instance.dependency_overrides[authenticate] = _auth_override(service_principal)

    res = client.post("/internal/ml/survival/predict", json=sample_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["case_id"] == "CASE-A"
    assert body["transition"] == "SECTION_11_TO_SECTION_19"
    # Note: OFFICER_ONLY fields like model_version are redacted for SERVICE principal by ResponseGate
    assert "governance_disclaimer" in body
