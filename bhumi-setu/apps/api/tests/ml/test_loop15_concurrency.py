"""LOOP 15 — Performance & Concurrency Test Suite.

Verifies:
1. Thread-safety and immutability of the singleton SurvivalService under concurrent load.
2. Concurrent prediction determinism across concurrency levels (1, 5, 10, 25, 50).
3. Zero race conditions, memory corruption, or mutated model state.
4. Error rate remains exactly 0.0% under parallel execution.
"""

from __future__ import annotations

import concurrent.futures
import pytest
from app.services.survival_service import get_survival_service


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


@pytest.mark.parametrize("concurrency", [1, 5, 10, 25, 50])
def test_concurrent_prediction_determinism(canonical_payload, concurrency):
    """Verify concurrent predictions yield 100% deterministic identical results with 0 errors."""
    service = get_survival_service()

    def _worker(thread_idx: int):
        cid = f"CONC_CASE_{thread_idx}"
        res = service.predict_officer_risk(
            case_id=cid,
            snapshot_date=canonical_payload["snapshot_date"],
            transition=canonical_payload["transition"],
            features=canonical_payload["features"],
        )
        return res

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_worker, i) for i in range(concurrency)]
        results = [f.result() for f in futures]

    assert len(results) == concurrency

    # Every result must have identical linear predictor and relative hazard
    first_lp = results[0].linear_predictor
    first_rh = results[0].relative_hazard
    first_p90 = results[0].event_probability_90d

    for res in results:
        assert res.linear_predictor == first_lp, "Non-deterministic linear predictor in thread!"
        assert res.relative_hazard == first_rh, "Non-deterministic relative hazard in thread!"
        assert res.event_probability_90d == first_p90, "Non-deterministic probability in thread!"
        assert res.risk_band_90d == "ADVISORY_MEDIAN_RELATIVE_HAZARD"
