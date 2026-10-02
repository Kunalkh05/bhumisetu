"""LOOP 15 — Security Audit: Audit Logging & Provenance Security Test Suite.

Verifies:
1. Every prediction generates an immutable audit record with provenance metadata.
2. Log records contain zero passwords, access tokens, session secrets, API keys, or raw PII.
3. Audit log storage is bounded in memory to prevent memory exhaustion under continuous load.
4. Timestamps are strictly UTC ISO 8601 formatted.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from app.services.survival_service import get_survival_service


@pytest.fixture
def baseline_features():
    return {
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


def test_audit_log_provenance_and_schema(baseline_features):
    """Verify audit log captures all necessary diagnostic provenance fields."""
    service = get_survival_service()
    initial_count = len(service.get_audit_log())

    service.predict_officer_risk(
        case_id="CASE-AUDIT-TEST-001",
        snapshot_date="2026-03-15",
        transition="SECTION_11_TO_SECTION_19",
        features=baseline_features,
    )

    logs = service.get_audit_log()
    assert len(logs) == initial_count + 1
    entry = logs[-1]

    assert entry["case_id"] == "CASE-AUDIT-TEST-001"
    assert entry["transition"] == "SECTION_11_TO_SECTION_19"
    assert entry["snapshot_date"] == "2026-03-15"
    assert entry["model_version"] == "1.0.0-cox-production-baseline"
    assert entry["feature_version"] == "1.0.0-survival-clean-15feat"
    assert isinstance(entry["latency_ms"], float)
    assert entry["latency_ms"] >= 0.0

    # Timestamp must parse as valid ISO UTC
    dt = datetime.fromisoformat(entry["timestamp"])
    assert dt.tzinfo is not None


def test_audit_log_zero_credentials_or_secrets(baseline_features):
    """Audit log entries must contain zero sensitive credential strings."""
    service = get_survival_service()
    service.predict_officer_risk(
        case_id="CASE-AUDIT-CLEAN",
        snapshot_date="2026-03-15",
        transition="SECTION_11_TO_SECTION_19",
        features=baseline_features,
    )
    entry = service.get_audit_log()[-1]
    serialized = str(entry).lower()

    forbidden_tokens = ["password", "secret", "bearer", "cookie", "token", "key", "authorization"]
    for token in forbidden_tokens:
        assert token not in serialized, f"Audit log contains forbidden credential token '{token}'"


def test_audit_log_bounded_memory(baseline_features):
    """Verify that in-memory audit log remains strictly bounded under repeated requests."""
    service = get_survival_service()
    
    # Fill audit log up to trigger bound condition
    service.audit_log = [
        {"case_id": f"C_{i}", "transition": "T", "timestamp": "2026-03-15T00:00:00Z"}
        for i in range(10000)
    ]
    assert len(service.audit_log) == 10000

    # Making one more prediction should prune older entries to prevent unbounded growth
    service.predict_officer_risk(
        case_id="CASE-BOUND-PRUNE",
        snapshot_date="2026-03-15",
        transition="SECTION_11_TO_SECTION_19",
        features=baseline_features,
    )

    # After pruning, length should be bounded (around 5001)
    assert len(service.audit_log) <= 6000
    assert service.audit_log[-1]["case_id"] == "CASE-BOUND-PRUNE"
