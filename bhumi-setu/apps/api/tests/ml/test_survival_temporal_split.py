"""Automated test suite for Case-Aware Temporal Cohort Split (LOOP 6).

Verifies the 12 Hard Invariants:
1. TRAIN case IDs ∩ EVAL case IDs = ∅.
2. Every evaluation case has a later case-entry date than every training case.
3. max(train case-entry date) < min(eval case-entry date).
4. No row exists in both datasets (row identity: case_id, snapshot_id, transition).
5. Features and targets remain strictly disjoint.
6. Censored observations are preserved in both train and eval.
7. event_observed remains binary.
8. duration_at_risk_days remains > 0.
9. No future event information entered the split.
10. All three transitions obey the same case-level partitioning rule.
11. Split is deterministic and reproducible.
12. No random seed is used to determine cohort membership.
"""

from __future__ import annotations

import csv
from pathlib import Path
import sys

import pytest

API_ROOT = Path(__file__).resolve().parents[2]
GIT_ROOT = Path(__file__).resolve().parents[5]
ML_SRC = GIT_ROOT / "bhumi-setu" / "ml" / "src"
CLEAN_DATA = GIT_ROOT / "data" / "real_data" / "clean"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.snapshots import (
    DEFAULT_TEMPORAL_CUTOFF_DATE,
    IDENTIFIER_COLUMNS,
    PURGED_FEATURE_COLUMNS,
    SAFE_PREDICTOR_COLUMNS,
    TARGET_COLUMNS,
    TARGET_METADATA_COLUMNS,
    TRAINING_TARGET_COLUMNS,
    SurvivalTemporalSplit,
    case_aware_temporal_split,
    compute_case_entry_dates,
    generate_survival_split_report,
    load_survival_split_artifacts,
)
from labelling.definition import (
    TRANSITION_CASE_INITIATION_TO_MILESTONE,
    TRANSITION_SECTION_11_TO_SECTION_19,
    TRANSITION_SECTION_19_TO_AWARD,
)


@pytest.fixture(scope="module")
def split_data():
    """Load the canonical exported split artifacts from disk."""
    tr_feats, tr_targs, ev_feats, ev_targs = load_survival_split_artifacts(CLEAN_DATA)
    return {
        "train_features": tr_feats,
        "train_targets": tr_targs,
        "eval_features": ev_feats,
        "eval_targets": ev_targs,
    }


# Invariant 1: TRAIN case IDs ∩ EVAL case IDs = empty set (§8.1)
def test_invariant_1_case_disjointness(split_data) -> None:
    train_cases = {r["case_id"] for r in split_data["train_features"]}
    eval_cases = {r["case_id"] for r in split_data["eval_features"]}

    assert len(train_cases) == 159
    assert len(eval_cases) == 89
    assert train_cases.isdisjoint(eval_cases), f"Case overlap found: {train_cases & eval_cases}"


# Invariants 2 & 3: Chronological ordering and temporal boundary (§8.2, §8.3)
def test_invariant_2_and_3_temporal_boundary(split_data) -> None:
    with open(CLEAN_DATA / "survival_snapshots.csv", encoding="utf-8") as f:
        snapshots = list(csv.DictReader(f))

    entry_dates = compute_case_entry_dates(snapshots)
    train_cases = {r["case_id"] for r in split_data["train_features"]}
    eval_cases = {r["case_id"] for r in split_data["eval_features"]}

    train_entry_dates = [entry_dates[cid] for cid in train_cases]
    eval_entry_dates = [entry_dates[cid] for cid in eval_cases]

    max_train_entry = max(train_entry_dates)
    min_eval_entry = min(eval_entry_dates)

    assert max_train_entry == "2026-04-28"
    assert min_eval_entry == "2026-05-04"
    assert max_train_entry < min_eval_entry, (
        f"Temporal leakage violation: max train ({max_train_entry}) >= min eval ({min_eval_entry})"
    )

    # Every evaluation case entry date must be strictly after every train entry date
    for e_dt in eval_entry_dates:
        for t_dt in train_entry_dates:
            assert t_dt < e_dt, f"Train case entry {t_dt} is not earlier than eval case entry {e_dt}"


# Invariant 4: No row exists in both datasets (row identity disjointness) (§8.4)
def test_invariant_4_row_identity_disjointness(split_data) -> None:
    def _row_key(r: dict[str, str]) -> tuple[str, str, str]:
        return (r["case_id"], r["snapshot_id"], r["transition"])

    train_keys = [_row_key(r) for r in split_data["train_features"]]
    eval_keys = [_row_key(r) for r in split_data["eval_features"]]

    assert len(train_keys) == len(set(train_keys)), "Duplicate keys inside train features!"
    assert len(eval_keys) == len(set(eval_keys)), "Duplicate keys inside eval features!"
    assert set(train_keys).isdisjoint(set(eval_keys)), "Row overlap detected between train and eval!"
    assert len(train_keys) + len(eval_keys) == 1063, "Total rows do not sum to 1,063!"


# Invariant 5: Feature and target columns remain strictly disjoint (§8.5)
def test_invariant_5_feature_target_disjointness() -> None:
    feat_path = CLEAN_DATA / "survival_train_features.csv"
    targ_path = CLEAN_DATA / "survival_train_targets.csv"

    with open(feat_path, encoding="utf-8") as f:
        feat_header = next(csv.reader(f))
    with open(targ_path, encoding="utf-8") as f:
        targ_header = next(csv.reader(f))

    # Shared columns must strictly be the identifier keys
    shared_cols = set(feat_header).intersection(set(targ_header))
    assert shared_cols == set(IDENTIFIER_COLUMNS), f"Unexpected shared columns: {shared_cols}"

    # Target columns must never be in feature columns
    for tc in TARGET_COLUMNS:
        assert tc not in feat_header, f"Target column {tc} leaked into features!"

    # Purged columns must never be in feature columns
    for pc in PURGED_FEATURE_COLUMNS:
        assert pc not in feat_header, f"Purged column {pc} found in features!"


# Invariant 6: Censored observations are preserved in both train and eval (§8.6)
def test_invariant_6_censored_preservation(split_data) -> None:
    tr_obs = sum(1 for r in split_data["train_targets"] if r["event_observed"].lower() == "true")
    tr_cens = sum(1 for r in split_data["train_targets"] if r["event_observed"].lower() == "false")
    ev_obs = sum(1 for r in split_data["eval_targets"] if r["event_observed"].lower() == "true")
    ev_cens = sum(1 for r in split_data["eval_targets"] if r["event_observed"].lower() == "false")

    assert tr_obs == 40
    assert tr_cens == 856
    assert ev_obs == 4
    assert ev_cens == 163

    assert tr_obs + tr_cens == 896
    assert ev_obs + ev_cens == 167
    assert tr_obs + ev_obs == 44
    assert tr_cens + ev_cens == 1019


# Invariant 7: event_observed remains strictly binary (§8.7)
def test_invariant_7_binary_event_indicator(split_data) -> None:
    for partition_name, targets in [("train", split_data["train_targets"]), ("eval", split_data["eval_targets"])]:
        for r in targets:
            val = r["event_observed"].lower()
            assert val in ("true", "false"), f"Non-binary event indicator '{val}' in {partition_name}"


# Invariant 8: duration_at_risk_days remains > 0 (§8.8)
def test_invariant_8_positive_duration_at_risk(split_data) -> None:
    for partition_name, targets in [("train", split_data["train_targets"]), ("eval", split_data["eval_targets"])]:
        for r in targets:
            dur = int(r["duration_at_risk_days"])
            assert dur > 0, f"Non-positive duration_at_risk_days ({dur}) found in {partition_name}!"


# Invariant 9: No future event information entered the split (§8.9)
def test_invariant_9_no_future_leakage(split_data) -> None:
    with open(CLEAN_DATA / "survival_snapshots.csv", encoding="utf-8") as f:
        snapshots = {r["snapshot_id"]: r for r in csv.DictReader(f)}

    for partition_name, feats in [("train", split_data["train_features"]), ("eval", split_data["eval_features"])]:
        for r in feats:
            sid = r["snapshot_id"]
            orig = snapshots[sid]
            # Ensure snapshot_date is strictly before event_date for observed events
            if orig["event_observed"].lower() == "true":
                assert orig["snapshot_date"] < orig["event_date"], (
                    f"Temporal violation: snapshot_date {orig['snapshot_date']} >= event_date {orig['event_date']}"
                )


# Invariant 10: All three transitions obey the same case-level partitioning (§8.10)
def test_invariant_10_transition_case_isolation(split_data) -> None:
    train_cases = {r["case_id"] for r in split_data["train_features"]}
    eval_cases = {r["case_id"] for r in split_data["eval_features"]}

    for t in [
        TRANSITION_SECTION_11_TO_SECTION_19,
        TRANSITION_SECTION_19_TO_AWARD,
        TRANSITION_CASE_INITIATION_TO_MILESTONE,
    ]:
        tr_t = {r["case_id"] for r in split_data["train_features"] if r["transition"] == t}
        ev_t = {r["case_id"] for r in split_data["eval_features"] if r["transition"] == t}

        # Any case participating in this transition must be a subset of that cohort
        assert tr_t.issubset(train_cases)
        assert ev_t.issubset(eval_cases)
        assert tr_t.isdisjoint(ev_t), f"Case overlap in transition {t}: {tr_t & ev_t}"


# Invariants 11 & 12: Deterministic, reproducible, no random seeds (§8.11, §8.12)
def test_invariants_11_and_12_determinism() -> None:
    with open(CLEAN_DATA / "survival_snapshots.csv", encoding="utf-8") as f:
        snapshots = list(csv.DictReader(f))

    # Run split multiple times independently
    split_1 = case_aware_temporal_split(snapshots, cutoff_date=DEFAULT_TEMPORAL_CUTOFF_DATE)
    split_2 = case_aware_temporal_split(snapshots, cutoff_date=DEFAULT_TEMPORAL_CUTOFF_DATE)

    assert split_1.train_case_ids == split_2.train_case_ids
    assert split_1.eval_case_ids == split_2.eval_case_ids
    assert len(split_1.train_records) == len(split_2.train_records)
    assert len(split_1.eval_records) == len(split_2.eval_records)


# 1:1 Row Key Alignment between Feature and Target Artifacts (§7)
def test_split_feature_target_alignment(split_data) -> None:
    def _keys(rows: list[dict[str, str]]) -> list[tuple[str, str, str]]:
        return [(r["case_id"], r["snapshot_id"], r["transition"]) for r in rows]

    tr_feat_keys = _keys(split_data["train_features"])
    tr_targ_keys = _keys(split_data["train_targets"])
    assert tr_feat_keys == tr_targ_keys, "Train features and targets row keys not 1:1 aligned!"

    ev_feat_keys = _keys(split_data["eval_features"])
    ev_targ_keys = _keys(split_data["eval_targets"])
    assert ev_feat_keys == ev_targ_keys, "Eval features and targets row keys not 1:1 aligned!"


# Validation error on case overlap or date inversion (§8)
def test_split_validation_errors() -> None:
    # Overlapping case IDs should raise ValueError
    with pytest.raises(ValueError, match="Case overlap detected"):
        SurvivalTemporalSplit(
            cutoff_date="2026-05-01",
            train_case_ids=("CAS_001", "CAS_002"),
            eval_case_ids=("CAS_002", "CAS_003"),
            case_entry_dates={"CAS_001": "2025-01-01", "CAS_002": "2025-02-01", "CAS_003": "2026-06-01"},
            train_records=(),
            eval_records=(),
        )

    # Inverted dates should raise ValueError
    with pytest.raises(ValueError, match="Temporal leakage violation"):
        SurvivalTemporalSplit(
            cutoff_date="2026-05-01",
            train_case_ids=("CAS_001",),
            eval_case_ids=("CAS_002",),
            case_entry_dates={"CAS_001": "2026-08-01", "CAS_002": "2025-01-01"},
            train_records=(),
            eval_records=(),
        )
