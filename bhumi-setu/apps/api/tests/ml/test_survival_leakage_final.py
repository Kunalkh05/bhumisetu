from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
import sys

import pytest

from app.db.event_log import AsOfMode

API_ROOT = Path(__file__).resolve().parents[2]
GIT_ROOT = Path(__file__).resolve().parents[5]
ML_SRC = GIT_ROOT / "bhumi-setu" / "ml" / "src"
CLEAN_DATA = GIT_ROOT / "data" / "real_data" / "clean"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.snapshots import (
    FEATURE_COLUMNS,
    IDENTIFIER_COLUMNS,
    PURGED_FEATURE_COLUMNS,
    SAFE_PREDICTOR_COLUMNS,
    TARGET_COLUMNS,
    TARGET_METADATA_COLUMNS,
    TRAINING_TARGET_COLUMNS,
    compute_point_in_time_features,
    generate_snapshots_for_case,
)
from labelling.definition import (
    TRANSITION_CASE_INITIATION_TO_MILESTONE,
    TRANSITION_SECTION_11_TO_SECTION_19,
    TRANSITION_SECTION_19_TO_AWARD,
)


def _case_dict(**overrides) -> dict[str, str]:
    base = {
        "case_id": "CAS_AUDIT_001",
        "case_number": "77/A-65/2024-25",
        "district": "Nagpur",
        "taluka": "Kuhi",
        "village": "Mandhal",
        "acquiring_authority": "Collectorate",
        "act_key": "RFCTLARR_2013",
        "derived_project_type": "Irrigation Canal",
        "derived_is_direct_purchase": "False",
        "first_notice_date": "2025-01-01",
        "section_11_date": "2025-01-01",
        "section_19_date": "2025-07-01",
        "award_date": "2026-03-01",
    }
    base.update(overrides)
    return base


# 1. Target and Identifier Disjointness Invariants (§14)
def test_disjointness_invariants() -> None:
    # Target columns must NEVER enter predictor matrix
    assert set(SAFE_PREDICTOR_COLUMNS).isdisjoint(set(TARGET_COLUMNS))
    assert set(SAFE_PREDICTOR_COLUMNS).isdisjoint(set(TARGET_METADATA_COLUMNS))
    # Identifier columns must NEVER enter predictor set
    assert set(SAFE_PREDICTOR_COLUMNS).isdisjoint(set(IDENTIFIER_COLUMNS))
    # Rejected / purged features must NEVER appear in safe training features
    assert set(SAFE_PREDICTOR_COLUMNS).isdisjoint(set(PURGED_FEATURE_COLUMNS))


# 2. Disk Artifact Schema Audit: survival_training_features.csv (§12, §14)
def test_disk_training_features_leakage_free() -> None:
    path = CLEAN_DATA / "survival_training_features.csv"
    assert path.exists(), f"{path} does not exist"

    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    assert len(rows) == 1063

    # Expected exact header: IDENTIFIER_COLUMNS + SAFE_PREDICTOR_COLUMNS
    expected_header = list(IDENTIFIER_COLUMNS) + list(SAFE_PREDICTOR_COLUMNS)
    assert header == expected_header, f"Header mismatch: {header} != {expected_header}"

    # Verify no target columns enter training features
    for tc in TARGET_COLUMNS:
        assert tc not in header, f"Target column {tc} leaked into training features!"

    # Verify no purged feature appears in final training features
    for pf in PURGED_FEATURE_COLUMNS:
        assert pf not in header, f"Purged feature {pf} appeared in training features!"


# 3. Disk Artifact Schema Audit: survival_training_targets.csv (§12, §14)
def test_disk_training_targets_leakage_free() -> None:
    path = CLEAN_DATA / "survival_training_targets.csv"
    assert path.exists(), f"{path} does not exist"

    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    assert len(rows) == 1063

    expected_header = list(IDENTIFIER_COLUMNS) + list(TRAINING_TARGET_COLUMNS)
    assert header == expected_header

    # Verify no predictor columns exist in target file
    for sc in SAFE_PREDICTOR_COLUMNS:
        assert sc not in header, f"Predictor column {sc} found in target file!"


# 4. Target Consistency: Event Dates, Censoring Dates & Positive Durations (§9, §14)
def test_all_observations_have_strictly_positive_durations_and_future_horizons() -> None:
    path = CLEAN_DATA / "survival_targets.csv"
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1063

    for r in rows:
        snap_dt = datetime.strptime(r["snapshot_date"], "%Y-%m-%d").date()
        dur = int(r["duration_at_risk_days"])
        obs = r["event_observed"].lower() == "true"

        # MUST FAIL if negative or zero duration exists
        assert dur > 0, f"Snapshot {r['snapshot_id']} has non-positive duration: {dur}"

        if obs:
            assert r["event_date"] != "", f"Snapshot {r['snapshot_id']} observed without event_date"
            ev_dt = datetime.strptime(r["event_date"], "%Y-%m-%d").date()
            # MUST FAIL if event_date <= snapshot_date for an observed event
            assert ev_dt > snap_dt, f"Observed event_date <= snapshot_date: {ev_dt} <= {snap_dt}"
            assert (ev_dt - snap_dt).days == dur
        else:
            assert r["censoring_date"] != "", f"Snapshot {r['snapshot_id']} censored without censoring_date"
            cens_dt = datetime.strptime(r["censoring_date"], "%Y-%m-%d").date()
            # MUST FAIL if censoring_date <= snapshot_date for a censored event
            assert cens_dt > snap_dt, f"Censoring date <= snapshot_date: {cens_dt} <= {snap_dt}"
            assert (cens_dt - snap_dt).days == dur


# 5. Future Section 19 Event Leakage Protection (§5, §14)
def test_future_section_19_does_not_affect_predictors() -> None:
    case = _case_dict(section_11_date="2025-01-01", section_19_date="2025-07-01")
    events = [
        {"event_id": "1", "case_id": "CAS_AUDIT_001", "event_type": "SECTION_11", "event_date": "2025-01-01"},
        {"event_id": "2", "case_id": "CAS_AUDIT_001", "event_type": "SECTION_19", "event_date": "2025-07-01"},
    ]

    snap_date = date(2025, 5, 1)  # 120 days after Section 11, 61 days before Section 19
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["current_stage"] == "SECTION_11"
    assert feats["derived_notice_count"] == 1
    assert feats["derived_days_in_current_stage"] == 120
    assert feats["derived_statutory_sec19_proximity_ratio"] == round(120 / 365.0, 4)


# 6. Future Award Event Leakage Protection (§5, §14)
def test_future_award_does_not_affect_predictors() -> None:
    case = _case_dict(section_19_date="2025-06-01", award_date="2026-03-01")
    events = [
        {"event_id": "1", "case_id": "CAS_AUDIT_001", "event_type": "SECTION_19", "event_date": "2025-06-01"},
        {"event_id": "2", "case_id": "CAS_AUDIT_001", "event_type": "AWARD", "event_date": "2026-03-01"},
    ]

    snap_date = date(2025, 12, 1)
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["current_stage"] == "SECTION_19"
    assert feats["award_recorded"] is False


# 7. Future Extension Orders Leakage Protection (§5, §14)
def test_future_extension_does_not_affect_predictors() -> None:
    case = _case_dict(section_11_date="2025-01-01")
    events = [
        {"event_id": "1", "case_id": "CAS_AUDIT_001", "event_type": "SECTION_11", "event_date": "2025-01-01"},
        {"event_id": "2", "case_id": "CAS_AUDIT_001", "event_type": "EXTENSION", "event_date": "2025-08-01"},
    ]

    snap_date = date(2025, 6, 1)
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["extension_count"] == 0
    assert feats["has_statutory_extension"] is False


# 8. Future Section 21 Claims Notice Leakage Protection (§5, §14)
def test_future_section_21_does_not_affect_predictors() -> None:
    case = _case_dict(section_19_date="2025-06-01")
    events = [
        {"event_id": "1", "case_id": "CAS_AUDIT_001", "event_type": "SECTION_19", "event_date": "2025-06-01"},
        {"event_id": "2", "case_id": "CAS_AUDIT_001", "event_type": "SECTION_21", "event_date": "2025-10-01"},
    ]

    snap_date = date(2025, 8, 1)
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["current_stage"] == "SECTION_19"
    assert feats["derived_notice_count"] == 1


# 9. Future Corrigendum / Administrative Notice Leakage Protection (§5, §14)
def test_future_corrigendum_does_not_affect_predictors() -> None:
    case = _case_dict(section_11_date="2025-01-01")
    events = [
        {"event_id": "1", "case_id": "CAS_AUDIT_001", "event_type": "SECTION_11", "event_date": "2025-01-01"},
        {"event_id": "2", "case_id": "CAS_AUDIT_001", "event_type": "GENERAL_NOTICE", "event_date": "2025-09-01"},
    ]

    snap_date = date(2025, 5, 1)
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["derived_notice_count"] == 1
    assert feats["derived_days_since_latest_notice"] == 120  # Jan 1 to May 1


# 10. Future Recording Time Suppressed under KNOWABLE_AT (§4, §14)
def test_future_recording_time_suppression() -> None:
    case = _case_dict(section_11_date="2025-01-01")
    events = [
        {"event_id": "1", "case_id": "CAS_AUDIT_001", "event_type": "SECTION_11", "event_date": "2025-01-01", "recording_date": "2025-01-01"},
        # Physical date March 1, published in gazette portal June 1
        {"event_id": "2", "case_id": "CAS_AUDIT_001", "event_type": "EXTENSION", "event_date": "2025-03-01", "recording_date": "2025-06-01"},
    ]

    snap_date = date(2025, 4, 1)
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    # Must be 0 because recording_date (June 1) > snapshot_date (April 1)
    assert feats["extension_count"] == 0
    assert feats["has_statutory_extension"] is False
