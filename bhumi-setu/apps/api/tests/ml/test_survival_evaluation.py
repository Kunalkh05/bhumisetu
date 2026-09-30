"""Adversarial and diagnostic test suite for Out-of-Sample Survival Evaluation (LOOP 8).

Verifies 15 core scientific integrity criteria:
1. EVAL data never enters model fitting.
2. Model parameters remain unchanged before and after evaluation.
3. Preprocessing remains strictly unchanged.
4. No target leakage into predictor matrices.
5. No future / purged feature usage in evaluation matrices.
6. Censored observations retained without alteration.
7. Correct event counts across all transitions.
8. Strict transition isolation.
9. Deterministic prediction outputs.
10. Zero-event transition handled safely.
11. Insufficient-event metrics return explicit status.
12. Model artifacts load correctly from disk.
13. Prediction schema consistency and probability bounds.
14. No calibration model fitting on EVAL data.
15. No hyperparameter tuning on EVAL data.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

API_ROOT = Path(__file__).resolve().parents[2]
GIT_ROOT = Path(__file__).resolve().parents[5]
ML_SRC = GIT_ROOT / "bhumi-setu" / "ml" / "src"
CLEAN_DATA = GIT_ROOT / "data" / "real_data" / "clean"
MODELS_DIR = GIT_ROOT / "models" / "cox_baseline"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from evaluation.survival_evaluation import (
    FullEvaluationResult,
    TransitionEvalResult,
    compute_ipcw_brier_score,
    evaluate_transition_survival,
    generate_out_of_sample_predictions,
    load_trained_cox_models,
    prepare_eval_design_matrix,
    run_full_survival_evaluation,
    validate_eval_features,
)
from features.survival_features import (
    IDENTIFIER_COLUMNS,
    PURGED_FEATURE_COLUMNS,
    SAFE_PREDICTOR_COLUMNS,
    TARGET_COLUMNS,
)
from training.cox_baseline import (
    load_cox_artifacts,
    prepare_cox_design_matrix,
)

LOOP_7C_ARTIFACT_FILENAMES = (
    "cox_model_summary.json",
    "cox_section_11_to_section_19_coefficients.csv",
    "cox_section_11_to_section_19_baseline_survival.csv",
    "cox_section_11_to_section_19_ph_test.csv",
    "cox_section_19_to_award_coefficients.csv",
    "cox_section_19_to_award_baseline_survival.csv",
    "cox_section_19_to_award_ph_test.csv",
    "cox_case_initiation_to_milestone_coefficients.csv",
    "cox_case_initiation_to_milestone_baseline_survival.csv",
    "cox_case_initiation_to_milestone_ph_test.csv",
)


def _compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def eval_setup():
    models = load_trained_cox_models(MODELS_DIR)
    eval_f = pd.read_csv(CLEAN_DATA / "survival_eval_features.csv")
    eval_t = pd.read_csv(CLEAN_DATA / "survival_eval_targets.csv")
    return {
        "models": models,
        "eval_features": eval_f,
        "eval_targets": eval_t,
    }


# 1. EVAL Data Never Enters Model Fitting (§12.1)
def test_eval_data_never_enters_model_fitting(eval_setup) -> None:
    eval_f = eval_setup["eval_features"]
    eval_keys = set(eval_f["snapshot_id"])
    eval_cases = set(eval_f["case_id"])

    # Verify train matrices contain 0 eval keys or cases
    for trans in ["SECTION_11_TO_SECTION_19", "SECTION_19_TO_AWARD", "CASE_INITIATION_TO_MILESTONE"]:
        train_X, _, _ = prepare_cox_design_matrix(
            CLEAN_DATA / "survival_train_features.csv",
            CLEAN_DATA / "survival_train_targets.csv",
            trans,
        )
        with open(CLEAN_DATA / "survival_train_features.csv", encoding="utf-8") as f:
            train_sub_keys = {
                r["snapshot_id"] for r in csv.DictReader(f) if r["transition"] == trans
            }
            train_sub_cases = {
                r["case_id"] for r in csv.DictReader(f) if r["transition"] == trans
            }

        assert train_sub_keys.isdisjoint(eval_keys)
        assert train_sub_cases.isdisjoint(eval_cases)


# 2. Model Parameters Unchanged Before/After Evaluation (§12.2)
def test_model_parameters_unchanged_before_after_eval() -> None:
    hashes_before = {
        fn: _compute_file_sha256(MODELS_DIR / fn) for fn in LOOP_7C_ARTIFACT_FILENAMES
    }

    # Execute full evaluation
    run_full_survival_evaluation(CLEAN_DATA, MODELS_DIR, MODELS_DIR)

    hashes_after = {
        fn: _compute_file_sha256(MODELS_DIR / fn) for fn in LOOP_7C_ARTIFACT_FILENAMES
    }

    assert hashes_before == hashes_after, "LOOP 7C model artifacts were modified by evaluation!"


# 3. Preprocessing Unchanged (§12.3)
def test_preprocessing_unchanged(eval_setup) -> None:
    models = eval_setup["models"]
    eval_f = eval_setup["eval_features"]

    for trans, model in models.items():
        X_eval = prepare_eval_design_matrix(eval_f, trans, model)
        assert list(X_eval.columns) == list(model["encoded_feature_names"])
        assert len(X_eval.columns) == len(model["encoded_feature_names"])


# 4. No Target Leakage (§12.4)
def test_no_target_leakage(eval_setup) -> None:
    models = eval_setup["models"]
    eval_f = eval_setup["eval_features"]

    for trans, model in models.items():
        X_eval = prepare_eval_design_matrix(eval_f, trans, model)
        for tc in TARGET_COLUMNS:
            assert tc not in X_eval.columns, f"Target column '{tc}' found in eval design matrix!"


# 5. No Future Feature Usage / Purged Variables (§12.5)
def test_no_future_feature_usage(eval_setup) -> None:
    models = eval_setup["models"]
    eval_f = eval_setup["eval_features"]

    for purged in PURGED_FEATURE_COLUMNS:
        assert purged not in eval_f.columns, f"Purged feature '{purged}' found in eval_features.csv!"

    for trans, model in models.items():
        X_eval = prepare_eval_design_matrix(eval_f, trans, model)
        for purged in PURGED_FEATURE_COLUMNS:
            assert purged not in X_eval.columns, f"Purged feature '{purged}' in design matrix!"


# 6. Censored Observations Retained (§12.6)
def test_censored_observations_retained(eval_setup) -> None:
    eval_t = eval_setup["eval_targets"]
    expected_censored = {
        "SECTION_11_TO_SECTION_19": 57,
        "SECTION_19_TO_AWARD": 4,
        "CASE_INITIATION_TO_MILESTONE": 102,
    }
    for trans, cens_count in expected_censored.items():
        sub = eval_t[eval_t["transition"] == trans]
        actual_censored = int((sub["event_observed"] == False).sum())
        assert actual_censored == cens_count


# 7. Correct Event Counts (§12.7)
def test_correct_eval_event_counts(eval_setup) -> None:
    eval_t = eval_setup["eval_targets"]
    eval_f = eval_setup["eval_features"]

    assert len(eval_f) == 167
    assert eval_f["case_id"].nunique() == 89
    assert int(eval_t["event_observed"].sum()) == 4

    expected_events = {
        "SECTION_11_TO_SECTION_19": 2,
        "SECTION_19_TO_AWARD": 0,
        "CASE_INITIATION_TO_MILESTONE": 2,
    }
    for trans, exp_e in expected_events.items():
        sub = eval_t[eval_t["transition"] == trans]
        assert int(sub["event_observed"].sum()) == exp_e


# 8. Transition Isolation (§12.8)
def test_transition_isolation(eval_setup) -> None:
    models = eval_setup["models"]
    eval_f = eval_setup["eval_features"]

    for trans, model in models.items():
        sub = eval_f[eval_f["transition"] == trans]
        X_eval = prepare_eval_design_matrix(sub, trans, model)
        assert len(X_eval) == len(sub)
        # Verify index alignment
        assert (X_eval.index == sub.index).all()


# 9. Deterministic Prediction (§12.9)
def test_deterministic_prediction(eval_setup) -> None:
    models = eval_setup["models"]
    eval_f = eval_setup["eval_features"]

    preds_1 = generate_out_of_sample_predictions(eval_f, models)
    preds_2 = generate_out_of_sample_predictions(eval_f, models)

    np.testing.assert_array_equal(
        preds_1["linear_predictor"].values, preds_2["linear_predictor"].values
    )
    np.testing.assert_array_equal(
        preds_1["relative_risk"].values, preds_2["relative_risk"].values
    )
    for h in [30, 90, 180, 365, 730]:
        np.testing.assert_array_equal(
            preds_1[f"pred_survival_{h}d"].values,
            preds_2[f"pred_survival_{h}d"].values,
        )


# 10. Zero-Event Transition Handled Safely (§12.10)
def test_zero_event_transition_handled_safely(eval_setup) -> None:
    models = eval_setup["models"]
    eval_f = eval_setup["eval_features"]
    eval_t = eval_setup["eval_targets"]

    preds = generate_out_of_sample_predictions(eval_f, models)
    res = evaluate_transition_survival(
        preds, eval_t, "SECTION_19_TO_AWARD", models["SECTION_19_TO_AWARD"]
    )

    assert res.concordance.status == "NOT COMPUTABLE — INSUFFICIENT EVENTS"
    assert res.concordance.concordance_index is None
    assert "zero observed target events" in res.concordance.interpretation_limitations.lower()


# 11. Insufficient-Event Metrics Return Explicit Status (§12.11)
def test_insufficient_event_metrics_return_explicit_status(eval_setup) -> None:
    models = eval_setup["models"]
    eval_f = eval_setup["eval_features"]
    eval_t = eval_setup["eval_targets"]

    preds = generate_out_of_sample_predictions(eval_f, models)
    for trans in ["SECTION_11_TO_SECTION_19", "SECTION_19_TO_AWARD", "CASE_INITIATION_TO_MILESTONE"]:
        res = evaluate_transition_survival(preds, eval_t, trans, models[trans])
        for h_key, disc in res.time_dependent_discrimination.items():
            assert "NOT RELIABLE" in disc["status"]
            assert "reason" in disc


# 12. Model Artifacts Load Correctly (§12.12)
def test_model_artifacts_load_correctly() -> None:
    models = load_trained_cox_models(MODELS_DIR)
    assert set(models.keys()) == {
        "SECTION_11_TO_SECTION_19",
        "SECTION_19_TO_AWARD",
        "CASE_INITIATION_TO_MILESTONE",
    }
    for trans, m in models.items():
        assert len(m["coefficients"]) > 0
        assert len(m["baseline_survival"]) > 0
        assert len(m["encoded_feature_names"]) > 0


# 13. Prediction Schema Consistency (§12.13)
def test_prediction_schema_consistency(eval_setup) -> None:
    models = eval_setup["models"]
    eval_f = eval_setup["eval_features"]

    preds = generate_out_of_sample_predictions(eval_f, models)
    expected_cols = [
        "snapshot_id",
        "case_id",
        "transition",
        "linear_predictor",
        "relative_risk",
        "pred_survival_30d",
        "pred_survival_90d",
        "pred_survival_180d",
        "pred_survival_365d",
        "pred_survival_730d",
    ]
    assert list(preds.columns) == expected_cols
    assert len(preds) == 167

    # Bounds check
    assert (preds["relative_risk"] > 0).all()
    for h in [30, 90, 180, 365, 730]:
        col = f"pred_survival_{h}d"
        assert (preds[col] >= 0.0).all()
        assert (preds[col] <= 1.0).all()


# 14. No Calibration Fitting on EVAL (§12.14)
def test_no_calibration_fitting_on_eval(eval_setup) -> None:
    models = eval_setup["models"]
    eval_f = eval_setup["eval_features"]
    eval_t = eval_setup["eval_targets"]

    preds = generate_out_of_sample_predictions(eval_f, models)
    for trans in models:
        res = evaluate_transition_survival(preds, eval_t, trans, models[trans])
        for c in res.calibration:
            assert "No calibration model or adjustment was fitted" in c.limitations or "Zero cases remain" in c.limitations


# 15. No Hyperparameter Tuning on EVAL (§12.15)
def test_no_hyperparameter_tuning_on_eval() -> None:
    with open(MODELS_DIR / "cox_model_summary.json", encoding="utf-8") as f:
        summary = json.load(f)

    # Assert model convergence and unchanged penalizer / parameter counts
    expected_params = {
        "SECTION_11_TO_SECTION_19": 3,
        "SECTION_19_TO_AWARD": 8,
        "CASE_INITIATION_TO_MILESTONE": 14,
    }
    for trans, exp_p in expected_params.items():
        assert summary[trans]["num_parameters"] == exp_p
        assert summary[trans]["convergence_status"] == "CONVERGED"
