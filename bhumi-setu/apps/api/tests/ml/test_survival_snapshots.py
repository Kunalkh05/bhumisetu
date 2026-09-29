from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.db.event_log import AsOfMode

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.snapshots import (
    compute_point_in_time_features,
    generate_all_survival_snapshots,
    generate_snapshots_for_case,
)
from labelling.definition import (
    TRANSITION_CASE_INITIATION_TO_MILESTONE,
    TRANSITION_SECTION_11_TO_SECTION_19,
    TRANSITION_SECTION_19_TO_AWARD,
)


def _case_dict(**overrides) -> dict[str, str]:
    base = {
        "case_id": "CAS_CLEAN_999",
        "case_number": "99/A-65/2024-25",
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


# TEST A: Event B (future) cannot affect snapshot features
def test_adversarial_test_a_future_event_masking() -> None:
    case = _case_dict()
    events = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_11",
            "event_date": "2025-01-01",
            "recording_date": "2025-01-01",
        },
        {
            "event_id": "EVT_2",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_19",
            "event_date": "2025-06-01",
            "recording_date": "2025-06-01",
        },
        {
            "event_id": "EVT_3",
            "case_id": "CAS_CLEAN_999",
            "event_type": "EXTENSION",
            "event_date": "2025-06-01",
            "recording_date": "2025-06-01",
        },
    ]

    snapshot_date = date(2025, 3, 1)  # Between Event A and Event B
    feats = compute_point_in_time_features(case, events, snapshot_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["current_stage"] == "SECTION_11"
    assert feats["derived_notice_count"] == 1
    assert feats["extension_count"] == 0
    assert feats["has_statutory_extension"] is False
    assert feats["award_recorded"] is False
    assert feats["derived_days_in_current_stage"] == 59  # Jan 1 to March 1 (non-leap)


# TEST B: Future Award cannot affect award_recorded before Award date
def test_adversarial_test_b_future_award_masking() -> None:
    case = _case_dict()
    events = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_19",
            "event_date": "2025-01-01",
            "recording_date": "2025-01-01",
        },
        {
            "event_id": "EVT_2",
            "case_id": "CAS_CLEAN_999",
            "event_type": "AWARD",
            "event_date": "2025-08-01",
            "recording_date": "2025-08-01",
        },
    ]

    pre_award_feats = compute_point_in_time_features(
        case, events, date(2025, 6, 1), mode=AsOfMode.KNOWABLE_AT
    )
    assert pre_award_feats["award_recorded"] is False

    post_award_feats = compute_point_in_time_features(
        case, events, date(2025, 8, 1), mode=AsOfMode.KNOWABLE_AT
    )
    assert post_award_feats["award_recorded"] is True


# TEST C: Future extension cannot affect extension_count before extension date
def test_adversarial_test_c_future_extension_masking() -> None:
    case = _case_dict()
    events = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_11",
            "event_date": "2026-01-01",
            "recording_date": "2026-01-01",
        },
        {
            "event_id": "EVT_2",
            "case_id": "CAS_CLEAN_999",
            "event_type": "EXTENSION",
            "event_date": "2026-08-01",
            "recording_date": "2026-08-01",
        },
    ]

    pre_ext = compute_point_in_time_features(
        case, events, date(2026, 7, 15), mode=AsOfMode.KNOWABLE_AT
    )
    assert pre_ext["extension_count"] == 0
    assert pre_ext["has_statutory_extension"] is False

    post_ext = compute_point_in_time_features(
        case, events, date(2026, 8, 15), mode=AsOfMode.KNOWABLE_AT
    )
    assert post_ext["extension_count"] == 1
    assert post_ext["has_statutory_extension"] is True


# TEST D: Future Section 19 cannot influence S11 -> S19 features before Section 19 date
def test_adversarial_test_d_future_section_19_masking() -> None:
    case = _case_dict()
    events = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_11",
            "event_date": "2025-01-01",
            "recording_date": "2025-01-01",
        },
        {
            "event_id": "EVT_2",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_19",
            "event_date": "2025-10-01",
            "recording_date": "2025-10-01",
        },
    ]

    snap_date = date(2025, 5, 1)  # 120 days after Section 11
    feats = compute_point_in_time_features(case, events, snap_date, mode=AsOfMode.KNOWABLE_AT)

    assert feats["current_stage"] == "SECTION_11"
    assert feats["derived_notice_count"] == 1
    # 120 / 365 = ~0.3288
    assert feats["derived_statutory_sec19_proximity_ratio"] == round(120 / 365.0, 4)


# TEST E: Recording-time masking under KNOWABLE_AT
def test_adversarial_test_e_recording_time_knowable_at_masking() -> None:
    case = _case_dict()
    # Event occurred on Feb 1, but was uploaded/recorded in the gazette on May 1
    events = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_11",
            "event_date": "2025-01-01",
            "recording_date": "2025-01-01",
        },
        {
            "event_id": "EVT_2",
            "case_id": "CAS_CLEAN_999",
            "event_type": "GENERAL_NOTICE",
            "event_date": "2025-02-01",
            "recording_date": "2025-05-01",  # Late recorded!
        },
    ]

    snap_date = date(2025, 3, 1)  # After occurrence (Feb 1) but BEFORE recording (May 1)

    # Under KNOWABLE_AT, EVT_2 is not knowable yet
    knowable_feats = compute_point_in_time_features(
        case, events, snap_date, mode=AsOfMode.KNOWABLE_AT
    )
    assert knowable_feats["derived_notice_count"] == 1

    # Under OCCURRED_BY, EVT_2 did occur in the real world
    occurred_feats = compute_point_in_time_features(
        case, events, snap_date, mode=AsOfMode.OCCURRED_BY
    )
    assert occurred_feats["derived_notice_count"] == 2


# Duration at risk and snapshot generation integrity (Landmark Analysis)
def test_duration_at_risk_and_snapshot_generation() -> None:
    case = _case_dict(
        section_11_date="2024-01-01",
        section_19_date="2024-07-01",  # 182 days
    )
    events = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_11",
            "event_date": "2024-01-01",
            "recording_date": "2024-01-01",
        },
        {
            "event_id": "EVT_2",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_19",
            "event_date": "2024-07-01",
            "recording_date": "2024-07-01",
        },
    ]

    snaps = generate_snapshots_for_case(
        case,
        events,
        TRANSITION_SECTION_11_TO_SECTION_19,
        cutoff_date=date(2026, 1, 1),
    )

    assert len(snaps) > 0
    # Every snapshot measures remaining time to event from snapshot_date
    for s in snaps:
        s_date = datetime.strptime(s.snapshot_date, "%Y-%m-%d").date()
        ev_date = datetime.strptime(s.event_date, "%Y-%m-%d").date()
        expected_remaining = (ev_date - s_date).days
        assert s.duration_at_risk_days == expected_remaining
        assert s.duration_at_risk_days > 0
        assert s.event_observed is True
        assert s.event_date == "2024-07-01"
        assert s.entry_date == "2024-01-01"
        assert s_date < ev_date  # Predictive: strictly before event!


# Censoring retains remaining duration
def test_censored_snapshot_retains_duration() -> None:
    case = _case_dict(
        section_11_date="2024-01-01",
        section_19_date="",  # Ongoing
    )
    events = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_11",
            "event_date": "2024-01-01",
            "recording_date": "2024-01-01",
        },
    ]

    cutoff = date(2025, 1, 1)  # 366 days after entry
    snaps = generate_snapshots_for_case(
        case,
        events,
        TRANSITION_SECTION_11_TO_SECTION_19,
        cutoff_date=cutoff,
    )

    assert len(snaps) > 0
    for s in snaps:
        s_date = datetime.strptime(s.snapshot_date, "%Y-%m-%d").date()
        cens_date = datetime.strptime(s.censoring_date, "%Y-%m-%d").date()
        expected_remaining = (cens_date - s_date).days
        assert s.event_observed is False
        assert s.duration_at_risk_days == expected_remaining
        assert s.duration_at_risk_days > 0
        assert s.censoring_date == "2025-01-01"
        assert s.event_date == ""
        assert s_date < cens_date


# SECTION 3 TEST: Landmark remaining time-to-event from snapshot_date
def test_landmark_remaining_time_to_event() -> None:
    """Entry: 2025-01-01, Event: 2025-07-01, Snapshot: 2025-04-01.
    Expected:
    event_observed = True
    duration_at_risk_days = 2025-07-01 - 2025-04-01 = 91 days
    NOT: 2025-07-01 - 2025-01-01 = 181 days
    """
    case = _case_dict(
        section_11_date="2025-01-01",
        section_19_date="2025-07-01",
    )
    events = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_11",
            "event_date": "2025-01-01",
            "recording_date": "2025-01-01",
        },
        {
            "event_id": "EVT_2",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_19",
            "event_date": "2025-07-01",
            "recording_date": "2025-07-01",
        },
    ]

    snaps = generate_snapshots_for_case(
        case,
        events,
        TRANSITION_SECTION_11_TO_SECTION_19,
        cutoff_date=date(2026, 1, 1),
        checkpoints=[90],  # 2025-01-01 + 90 days = 2025-04-01
    )

    day_90_snap = next(s for s in snaps if s.snapshot_date == "2025-04-01")
    assert day_90_snap.event_observed is True
    # Exactly 2025-07-01 - 2025-04-01 = 91 days
    assert day_90_snap.duration_at_risk_days == 91
    assert day_90_snap.duration_at_risk_days != 181


# SECTION 6 TEST: Transition Examples (Observed & Censored at Day 90)
def test_landmark_transition_examples() -> None:
    # Example A: Section 11 -> Section 19 with S19 on Day 180
    case_obs = _case_dict(
        section_11_date="2025-01-01",
        section_19_date="2025-06-30",  # Day 180
    )
    events_obs = [
        {"event_id": "1", "case_id": "CAS_CLEAN_999", "event_type": "SECTION_11", "event_date": "2025-01-01"},
        {"event_id": "2", "case_id": "CAS_CLEAN_999", "event_type": "SECTION_19", "event_date": "2025-06-30"},
    ]
    snaps_obs = generate_snapshots_for_case(
        case_obs, events_obs, TRANSITION_SECTION_11_TO_SECTION_19,
        cutoff_date=date(2026, 1, 1), checkpoints=[90]
    )
    snap_day90_obs = next(s for s in snaps_obs if s.snapshot_date == "2025-04-01")
    # Day 180 - Day 90 = 90 days remaining!
    assert snap_day90_obs.duration_at_risk_days == 90
    assert snap_day90_obs.event_observed is True

    # Example B: Section 11 -> Section 19 with no S19 by cutoff Day 365
    case_cens = _case_dict(
        section_11_date="2025-01-01",
        section_19_date="",
    )
    events_cens = [
        {"event_id": "1", "case_id": "CAS_CLEAN_999", "event_type": "SECTION_11", "event_date": "2025-01-01"},
    ]
    cutoff_day365 = date(2026, 1, 1)  # Day 365
    snaps_cens = generate_snapshots_for_case(
        case_cens, events_cens, TRANSITION_SECTION_11_TO_SECTION_19,
        cutoff_date=cutoff_day365, checkpoints=[90]
    )
    snap_day90_cens = next(s for s in snaps_cens if s.snapshot_date == "2025-04-01")
    # Day 365 - Day 90 = 275 days remaining!
    assert snap_day90_cens.duration_at_risk_days == 275
    assert snap_day90_cens.event_observed is False


# SECTION 4 TEST: Post-event and on-event snapshots are strictly excluded
def test_post_event_snapshots_are_excluded() -> None:
    case = _case_dict(
        section_11_date="2025-01-01",
        section_19_date="2025-03-01",  # Day 59
    )
    events = [
        {"event_id": "1", "case_id": "CAS_CLEAN_999", "event_type": "SECTION_11", "event_date": "2025-01-01"},
        {"event_id": "2", "case_id": "CAS_CLEAN_999", "event_type": "SECTION_19", "event_date": "2025-03-01"},
    ]
    snaps = generate_snapshots_for_case(
        case, events, TRANSITION_SECTION_11_TO_SECTION_19,
        cutoff_date=date(2026, 1, 1), checkpoints=[30, 60, 90]
    )
    snap_dates = [s.snapshot_date for s in snaps]
    assert "2025-01-01" in snap_dates
    assert "2025-01-31" in snap_dates
    assert "2025-03-01" not in snap_dates  # Excluded (on-event)
    assert "2025-03-02" not in snap_dates  # Excluded (post-event)
    assert "2025-04-01" not in snap_dates  # Excluded (post-event)
    for s in snaps:
        assert s.snapshot_date < "2025-03-01"


# Transition isolation
def test_transition_isolation() -> None:
    case = _case_dict(
        section_11_date="2024-01-01",
        section_19_date="2024-06-01",
        award_date="2025-03-01",
    )
    events = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_11",
            "event_date": "2024-01-01",
            "recording_date": "2024-01-01",
        },
        {
            "event_id": "EVT_2",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_19",
            "event_date": "2024-06-01",
            "recording_date": "2024-06-01",
        },
        {
            "event_id": "EVT_3",
            "case_id": "CAS_CLEAN_999",
            "event_type": "AWARD",
            "event_date": "2025-03-01",
            "recording_date": "2025-03-01",
        },
    ]

    cutoff = date(2026, 1, 1)

    s11_snaps = generate_snapshots_for_case(
        case, events, TRANSITION_SECTION_11_TO_SECTION_19, cutoff_date=cutoff
    )
    s19_snaps = generate_snapshots_for_case(
        case, events, TRANSITION_SECTION_19_TO_AWARD, cutoff_date=cutoff
    )

    # S11 transition entry is 2024-01-01, remaining duration to 2024-06-01 from snapshot_date
    assert all(s.entry_date == "2024-01-01" for s in s11_snaps)
    for s in s11_snaps:
        s_date = datetime.strptime(s.snapshot_date, "%Y-%m-%d").date()
        assert s.duration_at_risk_days == (date(2024, 6, 1) - s_date).days
        assert s.duration_at_risk_days > 0

    # S19 transition entry is 2024-06-01, remaining duration to 2025-03-01 from snapshot_date
    assert all(s.entry_date == "2024-06-01" for s in s19_snaps)
    for s in s19_snaps:
        s_date = datetime.strptime(s.snapshot_date, "%Y-%m-%d").date()
        assert s.duration_at_risk_days == (date(2025, 3, 1) - s_date).days
        assert s.duration_at_risk_days > 0


# NULL and missingness semantics preservation
def test_null_preservation() -> None:
    case = _case_dict()
    events = [
        {
            "event_id": "EVT_1",
            "case_id": "CAS_CLEAN_999",
            "event_type": "SECTION_11",
            "event_date": "2025-01-01",
            "recording_date": "2025-01-01",
        },
    ]

    feats = compute_point_in_time_features(
        case, events, date(2025, 2, 1), mode=AsOfMode.KNOWABLE_AT
    )

    assert feats["objection_count"] is None
    assert feats["missing_reason_objection_count"] == "NOT_PUBLISHED_IN_GAZETTE"
    assert feats["parcel_count"] is None
    assert feats["missing_reason_parcel_count"] == "NOT_PUBLISHED_IN_STRUCTURED_DATA"
    assert feats["open_issue_count"] is None
    assert feats["notified_area_hectares"] is None
    assert feats["compensation_amount_inr"] is None
