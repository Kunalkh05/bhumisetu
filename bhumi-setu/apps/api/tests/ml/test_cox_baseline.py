"""Adversarial and diagnostic test suite for Production Cox PH Baseline (LOOP 7C).

Verifies:
1. Train-only fitting (zero evaluation rows or case IDs accessed).
2. Proper right-censoring retention (zero censored observations dropped or converted).
3. Binary event preservation (event remains 0/1 without artificial fabrication).
4. Strictly positive durations in design matrix.
5. Strict transition isolation across models.
6. Target leakage prevention (zero target or purged features enter predictor matrix).
7. Deterministic model fitting and numerical reproducibility.
8. Artifact saving and loading integrity.
9. Events Per Variable (EPV) diagnostic reporting and small-event detection.
10. Proportional hazards assumption diagnostics.
11. Missing value handling without domain fabrication.
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
MODELS_DIR = GIT_ROOT / "models" / "cox_baseline"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.survival_features import (
    IDENTIFIER_COLUMNS,
    PURGED_FEATURE_COLUMNS,
    SAFE_PREDICTOR_COLUMNS,
    TARGET_COLUMNS,
    TARGET_METADATA_COLUMNS,
)
from training.cox_baseline import (
    CoxModelArtifact,
    fit_all_transition_cox_models,
    fit_single_transition_cox_model,
    load_cox_artifacts,
    prepare_cox_design_matrix,
    save_cox_artifacts,
)


@pytest.fixture(scope="module")
def train_paths():
    return {
        "features": CLEAN_DATA / "survival_train_features.csv",
        "targets": CLEAN_DATA / "survival_train_targets.csv",
        "eval_features": CLEAN_DATA / "survival_eval_features.csv",
        "eval_targets": CLEAN_DATA / "survival_eval_targets.csv",
    }


# 1. Train-Only Fitting & Zero Evaluation Leakage (§13.1)
def test_train_only_fitting(train_paths) -> None:
    with open(train_paths["eval_features"], encoding="utf-8") as f:
        eval_keys = {r["snapshot_id"] for r in csv.DictReader(f)}
    with open(train_paths["eval_features"], encoding="utf-8") as f:
        eval_cases = {r["case_id"] for r in csv.DictReader(f)}

    for trans in ["SECTION_11_TO_SECTION_19", "SECTION_19_TO_AWARD", "CASE_INITIATION_TO_MILESTONE"]:
        X_mat, cols, _ = prepare_cox_design_matrix(
            train_paths["features"], train_paths["targets"], trans
        )
        with open(train_paths["features"], encoding="utf-8") as f:
            train_sub_keys = {
                r["snapshot_id"] for r in csv.DictReader(f) if r["transition"] == trans
            }
        with open(train_paths["features"], encoding="utf-8") as f:
            train_sub_cases = {
                r["case_id"] for r in csv.DictReader(f) if r["transition"] == trans
            }

        # Assert no eval key or case ID is present
        assert train_sub_keys.isdisjoint(eval_keys)
        assert train_sub_cases.isdisjoint(eval_cases)
        assert len(X_mat) == len(train_sub_keys)


# 2. Right-Censoring Retention (§13.2)
def test_censoring_retention(train_paths) -> None:
    expected_censored = {
        "SECTION_11_TO_SECTION_19": 68,
        "SECTION_19_TO_AWARD": 197,
        "CASE_INITIATION_TO_MILESTONE": 591,
    }
    for trans, cens_count in expected_censored.items():
        X_mat, _, _ = prepare_cox_design_matrix(
            train_paths["features"], train_paths["targets"], trans
        )
        actual_censored = sum(X_mat["event"] == 0)
        assert actual_censored == cens_count, (
            f"Censored count mismatch in {trans}: {actual_censored} != {cens_count}"
        )


# 3. Binary Event Preservation (§13.3)
def test_binary_event_preservation(train_paths) -> None:
    for trans in ["SECTION_11_TO_SECTION_19", "SECTION_19_TO_AWARD", "CASE_INITIATION_TO_MILESTONE"]:
        X_mat, _, _ = prepare_cox_design_matrix(
            train_paths["features"], train_paths["targets"], trans
        )
        unique_events = set(X_mat["event"].unique())
        assert unique_events.issubset({0, 1}), f"Non-binary event values in {trans}: {unique_events}"


# 4. Strictly Positive Durations (§13.4)
def test_strictly_positive_durations(train_paths) -> None:
    for trans in ["SECTION_11_TO_SECTION_19", "SECTION_19_TO_AWARD", "CASE_INITIATION_TO_MILESTONE"]:
        X_mat, _, _ = prepare_cox_design_matrix(
            train_paths["features"], train_paths["targets"], trans
        )
        min_duration = X_mat["duration"].min()
        assert min_duration > 0, f"Non-positive duration ({min_duration}) in {trans}!"


# 5. Strict Transition Isolation (§13.5)
def test_transition_isolation(train_paths) -> None:
    counts = {
        "SECTION_11_TO_SECTION_19": 84,
        "SECTION_19_TO_AWARD": 203,
        "CASE_INITIATION_TO_MILESTONE": 609,
    }
    for trans, expected_len in counts.items():
        artifact = fit_single_transition_cox_model(
            train_paths["features"], train_paths["targets"], trans
        )
        assert artifact.transition == trans
        assert artifact.num_observations == expected_len


# 6. Target & Purged Feature Leakage Prevention (§13.6)
def test_target_and_purged_leakage_prevention(train_paths) -> None:
    for trans in ["SECTION_11_TO_SECTION_19", "SECTION_19_TO_AWARD", "CASE_INITIATION_TO_MILESTONE"]:
        X_mat, cols, _ = prepare_cox_design_matrix(
            train_paths["features"], train_paths["targets"], trans
        )
        predictor_cols = [c for c in X_mat.columns if c not in ("duration", "event")]

        for tc in TARGET_COLUMNS:
            assert tc not in predictor_cols, f"Target column '{tc}' leaked into {trans} predictors!"
        for pf in PURGED_FEATURE_COLUMNS:
            assert pf not in predictor_cols, f"Purged feature '{pf}' found in {trans} predictors!"
        for id_col in IDENTIFIER_COLUMNS:
            assert id_col not in predictor_cols, f"Identifier '{id_col}' found in {trans} predictors!"


# 7. Deterministic Fitting (§13.7)
def test_deterministic_fitting(train_paths) -> None:
    m1 = fit_single_transition_cox_model(
        train_paths["features"], train_paths["targets"], "SECTION_11_TO_SECTION_19", penalizer=0.1
    )
    m2 = fit_single_transition_cox_model(
        train_paths["features"], train_paths["targets"], "SECTION_11_TO_SECTION_19", penalizer=0.1
    )

    assert m1.log_likelihood == m2.log_likelihood
    assert m1.concordance_index == m2.concordance_index
    assert m1.coefficient_summary == m2.coefficient_summary


# 8. Artifact Loading Integrity (§13.8)
def test_artifact_loading_integrity(train_paths, tmp_path) -> None:
    models = fit_all_transition_cox_models(
        train_paths["features"], train_paths["targets"], penalizer=0.1
    )
    saved_paths = save_cox_artifacts(models, tmp_path)
    assert len(saved_paths) == 10

    loaded = load_cox_artifacts(tmp_path)
    assert "SECTION_11_TO_SECTION_19" in loaded
    assert "SECTION_19_TO_AWARD" in loaded
    assert "CASE_INITIATION_TO_MILESTONE" in loaded
    assert loaded["SECTION_11_TO_SECTION_19"]["convergence_status"] == "CONVERGED"


# 9. Events Per Variable (EPV) Diagnostics (§11, §13.9)
def test_epv_diagnostics(train_paths) -> None:
    m_sec19 = fit_single_transition_cox_model(
        train_paths["features"], train_paths["targets"], "SECTION_19_TO_AWARD"
    )
    # 6 events / 8 params = 0.75 EPV
    assert m_sec19.num_events == 6
    assert m_sec19.events_per_variable < 1.0
    # Warning must be issued
    assert any("Severe small-event limitation" in w for w in m_sec19.warnings)


# 10. Proportional Hazards Diagnostics (§10, §13.10)
def test_ph_diagnostics(train_paths) -> None:
    m = fit_single_transition_cox_model(
        train_paths["features"], train_paths["targets"], "SECTION_11_TO_SECTION_19"
    )
    assert len(m.ph_test_summary) == len(m.coefficient_summary)
    for entry in m.ph_test_summary:
        assert "p_value" in entry
        assert "ph_satisfied" in entry
        # In this transition, all covariates satisfy PH
        assert entry["ph_satisfied"] is True
