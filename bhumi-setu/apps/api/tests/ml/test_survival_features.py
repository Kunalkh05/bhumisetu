from __future__ import annotations

import csv
import math
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

from app.db.event_log import AsOfMode

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.snapshots import (
    BOOLEAN_FEATURE_COLUMNS,
    CATEGORICAL_FEATURE_COLUMNS,
    FEATURE_COLUMNS,
    IDENTIFIER_COLUMNS,
    MISSING_ATTRIBUTE_COLUMNS,
    MISSING_REASON_COLUMNS,
    NUMERICAL_FEATURE_COLUMNS,
    TARGET_COLUMNS,
    TARGET_METADATA_COLUMNS,
    assert_target_feature_disjointness,
    compute_point_in_time_features,
    generate_all_survival_snapshots,
    generate_snapshots_for_case,
)
from labelling.definition import (
    TRANSITION_CASE_INITIATION_TO_MILESTONE,
    TRANSITION_SECTION_11_TO_SECTION_19,
    TRANSITION_SECTION_19_TO_AWARD,
)


def _base_case(**overrides) -> dict[str, str]:
    base = {
        "case_id": "CAS_TEST_001",
        "case_number": "101/A-65/2024-25",
        "district": "Nagpur",
        "taluka": "Kuhi",
        "village": "Mandhal",
        "acquiring_authority": "Collectorate",
        "act_key": "RFCTLARR_2013",
        "derived_project_type": "Irrigation Canal",
        "derived_is_direct_purchase": "False",
        "first_notice_date": "2025-01-01",
        "section_11_date": "2025-01-01",
        "section_19_date": "2025-06-01",
        "award_date": "2026-02-01",
    }
    base.update(overrides)
    return base


# 1. Target Metadata Disjointness Tests (§8)
def test_target_feature_disjointness() -> None:
    """Ensure that FEATURE_COLUMNS, TARGET_COLUMNS, and IDENTIFIER_COLUMNS are strictly disjoint."""
    assert_target_feature_disjointness()
    assert set(FEATURE_COLUMNS).isdisjoint(set(TARGET_COLUMNS))
    assert set(FEATURE_COLUMNS).isdisjoint(set(IDENTIFIER_COLUMNS))
    assert set(FEATURE_COLUMNS).isdisjoint(set(TARGET_METADATA_COLUMNS))
    assert set(IDENTIFIER_COLUMNS).isdisjoint(set(TARGET_COLUMNS))


# 2. Future Notice Cannot Affect Notice Features (§7)
def test_future_notice_leakage_protection() -> None:
    case = _base_case()
    events = [
        {"event_id": "1", "case_id": "CAS_TEST_001", "event_type": "SECTION_11", "event_date": "2025-01-01"},
        {"event_id": "2", "case_id": "CAS_TEST_001", "event_type": "GENERAL_NOTICE", "event_date": "2025-03-01"},
        {"event_id": "3", "case_id": "CAS_TEST_001", "event_type": "GENERAL_NOTICE", "event_date": "2025-06-01"},  # Future!
    ]

    snap_date = date(2025, 4, 1)
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["derived_notice_count"] == 2  # EVT 1 and 2 only
    assert feats["derived_days_since_latest_notice"] == 31  # From 2025-03-01, NOT 2025-06-01


# 3. Future Extension Cannot Affect Extension Features (§7)
def test_future_extension_leakage_protection() -> None:
    case = _base_case()
    events = [
        {"event_id": "1", "case_id": "CAS_TEST_001", "event_type": "SECTION_11", "event_date": "2025-01-01"},
        {"event_id": "2", "case_id": "CAS_TEST_001", "event_type": "EXTENSION", "event_date": "2025-04-01"},
        {"event_id": "3", "case_id": "CAS_TEST_001", "event_type": "EXTENSION", "event_date": "2025-08-01"},  # Future!
    ]

    snap_date = date(2025, 5, 15)
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["extension_count"] == 1  # Extension A only
    assert feats["has_statutory_extension"] is True


# 4. Future Award Cannot Affect award_recorded (§7)
def test_future_award_leakage_protection() -> None:
    case = _base_case()
    events = [
        {"event_id": "1", "case_id": "CAS_TEST_001", "event_type": "SECTION_19", "event_date": "2025-06-19"},
        {"event_id": "2", "case_id": "CAS_TEST_001", "event_type": "AWARD", "event_date": "2026-07-14"},  # Future Award!
    ]

    snap_date = date(2026, 3, 16)
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["award_recorded"] is False


# 5. Future Section 19 Cannot Affect Section 11 Proximity Ratio (§7)
def test_future_section_19_cannot_affect_sec11_proximity() -> None:
    case = _base_case()
    events = [
        {"event_id": "1", "case_id": "CAS_TEST_001", "event_type": "SECTION_11", "event_date": "2025-01-01"},
        {"event_id": "2", "case_id": "CAS_TEST_001", "event_type": "SECTION_19", "event_date": "2025-10-01"},
    ]

    snap_date = date(2025, 5, 1)  # Day 120
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["current_stage"] == "SECTION_11"
    # Ratio = 120 / 365 = ~0.3288
    assert feats["derived_statutory_sec19_proximity_ratio"] == round(120 / 365.0, 4)


# 6. Future Stage Entry Cannot Affect Days In Current Stage or Current Stage (§7)
def test_future_stage_entry_leakage_protection() -> None:
    case = _base_case()
    events = [
        {"event_id": "1", "case_id": "CAS_TEST_001", "event_type": "SECTION_11", "event_date": "2025-01-01"},
        {"event_id": "2", "case_id": "CAS_TEST_001", "event_type": "SECTION_19", "event_date": "2025-07-01"},
    ]

    snap_date = date(2025, 3, 1)  # 59 days after Section 11, before Section 19
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["current_stage"] == "SECTION_11"
    assert feats["derived_days_in_current_stage"] == 59


# 7. Late Recording Protection under KNOWABLE_AT (§7)
def test_late_recording_leakage_protection() -> None:
    case = _base_case()
    events = [
        {"event_id": "1", "case_id": "CAS_TEST_001", "event_type": "SECTION_11", "event_date": "2025-01-01", "recording_date": "2025-01-01"},
        # Occurred on Feb 1, but recorded in gazette on May 1
        {"event_id": "2", "case_id": "CAS_TEST_001", "event_type": "EXTENSION", "event_date": "2025-02-01", "recording_date": "2025-05-01"},
    ]

    snap_date = date(2025, 3, 1)  # Between occurrence and recording
    feats_knowable = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)
    assert feats_knowable["extension_count"] == 0
    assert feats_knowable["has_statutory_extension"] is False

    feats_occurred = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.OCCURRED_BY)
    assert feats_occurred["extension_count"] == 1
    assert feats_occurred["has_statutory_extension"] is True


# 8. Strict Missingness Preservation (No NULL -> 0 Coercion) (§5)
def test_missing_attributes_never_coerced_to_zero() -> None:
    case = _base_case()
    events = [
        {"event_id": "1", "case_id": "CAS_TEST_001", "event_type": "SECTION_11", "event_date": "2025-01-01"},
    ]

    feats = compute_point_in_time_features(case, events, date(2025, 3, 1), mode=AsOfMode.KNOWABLE_AT)

    for attr in MISSING_ATTRIBUTE_COLUMNS:
        assert feats[attr] is None, f"Attribute {attr} was coerced or fabricated!"

    assert feats["missing_reason_objection_count"] == "NOT_PUBLISHED_IN_GAZETTE"
    assert feats["missing_reason_parcel_count"] == "NOT_PUBLISHED_IN_STRUCTURED_DATA"
    assert feats["missing_reason_open_issue_count"] == "NOT_APPLICABLE_IN_REAL_DATA"
    assert feats["missing_reason_notified_area"] == "UNPARSED_SCHEDULE_TABLE"
    assert feats["missing_reason_affected_landowners"] == "NOT_PUBLISHED_IN_STRUCTURED_DATA"
    assert feats["missing_reason_compensation"] == "NOT_APPLICABLE_PRE_AWARD"


# 9. Temporal Values Non-Negativity (§12)
def test_temporal_features_are_non_negative() -> None:
    case = _base_case()
    events = [
        {"event_id": "1", "case_id": "CAS_TEST_001", "event_type": "SECTION_11", "event_date": "2025-01-01"},
    ]
    snaps = generate_snapshots_for_case(
        case, events, TRANSITION_SECTION_11_TO_SECTION_19, cutoff_date=date(2026, 1, 1), checkpoints=[90, 180]
    )

    for s in snaps:
        assert s.derived_days_since_case_initiation >= 0
        assert s.derived_days_in_current_stage >= 0
        assert s.derived_days_since_latest_notice is not None and s.derived_days_since_latest_notice >= 0
        assert s.derived_notice_count >= 1
        assert s.duration_at_risk_days > 0


# 10. Clean Export Matrix Contains No Target Columns (§10)
def test_clean_feature_matrix_contains_zero_target_columns(tmp_path: Path) -> None:
    from features.snapshots import export_survival_feature_matrix_to_csv

    case = _base_case()
    events = [
        {"event_id": "1", "case_id": "CAS_TEST_001", "event_type": "SECTION_11", "event_date": "2025-01-01"},
    ]
    snaps = generate_snapshots_for_case(
        case, events, TRANSITION_SECTION_11_TO_SECTION_19, cutoff_date=date(2026, 1, 1), checkpoints=[90]
    )

    target_file = tmp_path / "test_matrix.csv"
    export_survival_feature_matrix_to_csv(snaps, target_file)

    with open(target_file, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

    # Verify no target columns exist in feature matrix
    for target_col in TARGET_COLUMNS:
        assert target_col not in header, f"Target column {target_col} leaked into feature matrix!"

    # Verify only IDENTIFIER_COLUMNS and FEATURE_COLUMNS are present
    expected_header = list(IDENTIFIER_COLUMNS) + list(FEATURE_COLUMNS)
    assert header == expected_header
