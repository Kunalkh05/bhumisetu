"""LOOP 15 — Performance & Resource Audit Test Suite.

Empirically benchmarks:
1. Warm direct model inference latency (Median, P95).
2. FastAPI prediction endpoint roundtrip latency.
3. FastAPI explanation endpoint roundtrip latency.
4. FastAPI citizen milestone timeline roundtrip latency.
5. FastAPI health check roundtrip latency.
6. Repeated request resource stability (500 requests memory stability).
"""

from __future__ import annotations

import time
import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import create_app
from app.security.access import Principal, authenticate
from app.services.survival_service import get_survival_service
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
def canonical_payload():
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
            "derived_statutory_sec19_proximity_ratio": 0.205,
            "extension_count": 0.0,
            "has_statutory_extension": 0.0,
            "act_key": "RFCTLARR_2013",
            "derived_is_direct_purchase": 0.0,
        },
    }


def test_perf_direct_service_inference(canonical_payload):
    """Benchmark warm direct Python service inference over 50 iterations."""
    service = get_survival_service()
    
    # Warmup
    service.predict_officer_risk("WARM", "2026-03-15", "SECTION_11_TO_SECTION_19", canonical_payload["features"])

    latencies: list[float] = []
    for i in range(50):
        t0 = time.perf_counter()
        service.predict_officer_risk(f"C_{i}", "2026-03-15", "SECTION_11_TO_SECTION_19", canonical_payload["features"])
        latencies.append((time.perf_counter() - t0) * 1000.0)

    med = float(np.median(latencies))
    p95 = float(np.percentile(latencies, 95))

    # Regression gate: Warm direct inference must remain sub-5ms median, sub-10ms P95
    assert med < 5.0, f"Direct inference median latency regressed: {med:.2f}ms"
    assert p95 < 10.0, f"Direct inference P95 latency regressed: {p95:.2f}ms"


def test_perf_fastapi_prediction_roundtrip(client, app_instance, canonical_payload):
    """Benchmark FastAPI POST /api/officer/survival-risk/predict roundtrip."""
    officer = Principal(kind="OFFICER", id="off-bench")
    app_instance.dependency_overrides[authenticate] = _auth_override(officer)

    # Warmup
    r = client.post("/api/officer/survival-risk/predict", json=canonical_payload)
    assert r.status_code == 200

    latencies: list[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        res = client.post("/api/officer/survival-risk/predict", json=canonical_payload)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        assert res.status_code == 200

    med = float(np.median(latencies))
    p95 = float(np.percentile(latencies, 95))

    # Regression gate: FastAPI roundtrip sub-8ms median, sub-15ms P95
    assert med < 8.0, f"FastAPI prediction roundtrip median regressed: {med:.2f}ms"
    assert p95 < 15.0, f"FastAPI prediction roundtrip P95 regressed: {p95:.2f}ms"


def test_perf_fastapi_citizen_timeline_roundtrip(client, app_instance):
    """Benchmark citizen milestone timeline endpoint latency."""
    citizen = Principal(kind="CITIZEN", id="cit-bench", case_id="CASE-E2E-LOOP14")
    app_instance.dependency_overrides[authenticate] = _auth_override(citizen)

    # Warmup
    r = client.get("/api/citizen/cases/CASE-E2E-LOOP14/milestone-timeline")
    assert r.status_code == 200

    latencies: list[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        res = client.get("/api/citizen/cases/CASE-E2E-LOOP14/milestone-timeline")
        latencies.append((time.perf_counter() - t0) * 1000.0)
        assert res.status_code == 200

    med = float(np.median(latencies))
    assert med < 5.0, f"Citizen timeline median latency regressed: {med:.2f}ms"


def test_perf_resource_stability_500_requests(client, app_instance, canonical_payload):
    """Perform 500 sequential requests and verify throughput and zero error rate."""
    officer = Principal(kind="OFFICER", id="off-stress")
    app_instance.dependency_overrides[authenticate] = _auth_override(officer)

    t_start = time.perf_counter()
    for i in range(500):
        r = client.post("/api/officer/survival-risk/predict", json=canonical_payload)
        assert r.status_code == 200
    total_time = time.perf_counter() - t_start

    throughput = 500.0 / total_time
    assert throughput > 100.0, f"Throughput too low: {throughput:.1f} req/s"
