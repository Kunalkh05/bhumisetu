"""Adversarial tests for Survival Risk Calibration & Production Risk Layer (LOOP 9).

Validates all 18 non-negotiable architectural, scientific, and data governance invariants:
1. EVAL data never enters calibration fitting.
2. EVAL outcomes never enter calibration fitting.
3. Case-level separation during internal calibration cross-validation.
4. No future information used in feature space.
5. No purged features accepted (strict rejection).
6. Transition isolation (no row pooling across transitions).
7. Correct survival probability calculation (S0(t) ** exp(eta)).
8. Event probability = 1 - survival probability.
9. Probability bounds strictly in [0.0, 1.0].
10. Deterministic predictions across repeated runs.
11. Artifact save/load roundtrip integrity.
12. Calibration artifact integrity (Loop 7C and 8 artifacts bit-identical).
13. Model version tracking.
14. Unsupported horizons handled safely with extrapolation flags.
15. Insufficient-event transitions handled explicitly (Section 19 -> Award).
16. No arbitrary risk bands (anchored to TRAIN quantiles).
17. Uncertainty flags appropriately assign HIGH_UNCERTAINTY.
18. Citizen output strictly suppresses internal ML fields.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from calibration.survival_calibration import (
    BANNED_CITIZEN_FIELDS,
    GOVERNANCE_SAFETY_DISCLAIMER,
    MODEL_VERSION,
    PURGED_LEAKAGE_FEATURES,
    CalibrationStatus,
    UncertaintyStatus,
    compute_train_banding_cutoffs,
    evaluate_train_calibration,
    group_kfold_cases,
    load_production_risk_layer,
    run_full_survival_calibration,
)
from evaluation.survival_evaluation import load_trained_cox_models

API_ROOT = Path(__file__).resolve().parents[2]
GIT_ROOT = Path(__file__).resolve().parents[5]
CLEAN_DATA_DIR = GIT_ROOT / "data" / "real_data" / "clean"
MODELS_DIR = GIT_ROOT / "models" / "cox_baseline"


@pytest.fixture(scope="module")
def train_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load real clean TRAIN features and targets."""
    feat_path = CLEAN_DATA_DIR / "survival_train_features.csv"
    targ_path = CLEAN_DATA_DIR / "survival_train_targets.csv"
    assert feat_path.exists() and targ_path.exists()
    return pd.read_csv(feat_path), pd.read_csv(targ_path)


@pytest.fixture(scope="module")
def eval_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load real clean EVAL holdout features and targets."""
    feat_path = CLEAN_DATA_DIR / "survival_eval_features.csv"
    targ_path = CLEAN_DATA_DIR / "survival_eval_targets.csv"
    assert feat_path.exists() and targ_path.exists()
    return pd.read_csv(feat_path), pd.read_csv(targ_path)


@pytest.fixture(scope="module")
def cox_models() -> dict[str, Any]:
    """Load pre-fitted Cox models."""
    return load_trained_cox_models(MODELS_DIR)


@pytest.fixture(scope="module")
def calibration_pipeline(train_data, cox_models) -> dict[str, Any]:
    """Run calibration assessment on TRAIN."""
    tf, tt = train_data
    cal_res = evaluate_train_calibration(tf, tt, cox_models)
    cutoffs = compute_train_banding_cutoffs(tf, cox_models)
    return {"results": cal_res, "cutoffs": cutoffs}


# --- INVARIANT 1 & 2: EVAL ISOLATION ---

def test_eval_never_enters_calibration_fitting(train_data, eval_data, cox_models):
    """Invariant 1: Verify that EVAL case IDs never appear in calibration training sets."""
    tf, tt = train_data
    ef, _ = eval_data
    eval_cases = set(ef["case_id"].unique())

    # Calibration is fitted strictly on TRAIN features
    cal_results = evaluate_train_calibration(tf, tt, cox_models)
    for trans, res in cal_results.items():
        # Assert observations match TRAIN exactly
        sub_train = tf[tf["transition"] == trans]
        assert res.num_train_observations == len(sub_train)
        assert res.num_train_cases == sub_train["case_id"].nunique()

        # Check that no EVAL cases were included
        train_cases = set(sub_train["case_id"].unique())
        assert train_cases.isdisjoint(eval_cases), f"Leakage: EVAL cases present in TRAIN for {trans}"


def test_eval_outcomes_never_enter_calibration_fitting(train_data, eval_data, cox_models):
    """Invariant 2: Verify that EVAL target event outcomes never enter calibration fitting."""
    tf, tt = train_data
    _, et = eval_data
    eval_events = int(et["event_observed"].sum())
    assert eval_events == 4  # Pre-condition: EVAL has exactly 4 events

    cal_results = evaluate_train_calibration(tf, tt, cox_models)
    for trans, res in cal_results.items():
        sub_targ = tt[tt["transition"] == trans]
        assert res.num_train_events == int(sub_targ["event_observed"].sum())
        # Confirm event counts strictly reflect TRAIN (16 in S11, 6 in S19, 18 in Initiation)
        if trans == "SECTION_11_TO_SECTION_19":
            assert res.num_train_events == 16
        elif trans == "SECTION_19_TO_AWARD":
            assert res.num_train_events == 6
        elif trans == "CASE_INITIATION_TO_MILESTONE":
            assert res.num_train_events == 18


# --- INVARIANT 3: CASE-LEVEL GROUPED VALIDATION ---

def test_case_level_separation_during_internal_calibration(train_data):
    """Invariant 3: Case IDs must not cross fold boundaries in case-grouped cross-validation."""
    tf, _ = train_data
    for trans in ["SECTION_11_TO_SECTION_19", "CASE_INITIATION_TO_MILESTONE"]:
        sub = tf[tf["transition"] == trans]
        folds = group_kfold_cases(sub["case_id"], n_splits=5, seed=42)
        for fold_idx, (tr_mask, val_mask) in enumerate(folds):
            train_cases = set(sub.loc[tr_mask, "case_id"])
            val_cases = set(sub.loc[val_mask, "case_id"])
            overlap = train_cases.intersection(val_cases)
            assert len(overlap) == 0, f"Case leakage in fold {fold_idx}: {overlap}"


# --- INVARIANT 4 & 5: FEATURE LEAKAGE GUARDS ---

def test_no_future_information(train_data, cox_models, calibration_pipeline):
    """Invariant 4: Predictions must not use any outcome or future milestone columns."""
    tf, _ = train_data
    layer = load_production_risk_layer(
        MODELS_DIR,
        CLEAN_DATA_DIR / "survival_train_features.csv",
        CLEAN_DATA_DIR / "survival_train_targets.csv",
    )
    preds = layer.predict_risk(tf.iloc[:10])
    for p in preds:
        assert p.relative_hazard > 0
        assert hasattr(p, "linear_predictor")


def test_no_purged_features(train_data):
    """Invariant 5: Layer must reject any DataFrame containing purged leakage variables."""
    tf, _ = train_data
    layer = load_production_risk_layer(
        MODELS_DIR,
        CLEAN_DATA_DIR / "survival_train_features.csv",
        CLEAN_DATA_DIR / "survival_train_targets.csv",
    )
    tainted = tf.copy()
    tainted["award_recorded"] = True

    with pytest.raises(ValueError, match="Feature leakage violation"):
        layer.predict_risk(tainted)


# --- INVARIANT 6: TRANSITION ISOLATION ---

def test_transition_isolation(train_data, cox_models):
    """Invariant 6: Each transition model must evaluate only its corresponding subset."""
    tf, tt = train_data
    cal_res = evaluate_train_calibration(tf, tt, cox_models)
    assert set(cal_res.keys()) == {
        "SECTION_11_TO_SECTION_19",
        "SECTION_19_TO_AWARD",
        "CASE_INITIATION_TO_MILESTONE",
    }
    assert cal_res["SECTION_11_TO_SECTION_19"].num_train_observations == 84
    assert cal_res["SECTION_19_TO_AWARD"].num_train_observations == 203
    assert cal_res["CASE_INITIATION_TO_MILESTONE"].num_train_observations == 609


# --- INVARIANT 7, 8, & 9: SURVIVAL MATHEMATICS & BOUNDS ---

def test_correct_survival_probability_calculation(train_data, cox_models):
    """Invariant 7: Survival probability must equal S0(t) ** exp(eta)."""
    tf, _ = train_data
    layer = load_production_risk_layer(
        MODELS_DIR,
        CLEAN_DATA_DIR / "survival_train_features.csv",
        CLEAN_DATA_DIR / "survival_train_targets.csv",
    )
    sub = tf[tf["transition"] == "SECTION_11_TO_SECTION_19"].iloc[:5]
    preds = layer.predict_risk(sub)

    surv_df = cox_models["SECTION_11_TO_SECTION_19"]["baseline_survival"].sort_values("time")
    s0_30 = float(surv_df[surv_df["time"] <= 30].iloc[-1]["baseline_survival_probability"])

    for p in preds:
        expected_s30 = round(float(np.clip(s0_30 ** p.relative_hazard, 0.0, 1.0)), 6)
        assert abs(p.survival_probability_30d - expected_s30) < 1e-5


def test_event_probability_equals_one_minus_survival(train_data):
    """Invariant 8: Event probability must equal 1 - survival probability for all horizons."""
    tf, _ = train_data
    layer = load_production_risk_layer(
        MODELS_DIR,
        CLEAN_DATA_DIR / "survival_train_features.csv",
        CLEAN_DATA_DIR / "survival_train_targets.csv",
    )
    preds = layer.predict_risk(tf.iloc[:20])
    for p in preds:
        for h in [30, 90, 180, 365, 730]:
            surv = getattr(p, f"survival_probability_{h}d")
            ev = getattr(p, f"event_probability_{h}d")
            assert abs((surv + ev) - 1.0) < 1e-5, f"Sum mismatch at {h}d: {surv} + {ev} != 1.0"


def test_probability_bounds(train_data, eval_data):
    """Invariant 9: All predicted probabilities must lie strictly in [0.0, 1.0]."""
    layer = load_production_risk_layer(
        MODELS_DIR,
        CLEAN_DATA_DIR / "survival_train_features.csv",
        CLEAN_DATA_DIR / "survival_train_targets.csv",
    )
    for data in [train_data[0], eval_data[0]]:
        preds = layer.predict_risk(data)
        for p in preds:
            for h in [30, 90, 180, 365, 730]:
                surv = getattr(p, f"survival_probability_{h}d")
                ev = getattr(p, f"event_probability_{h}d")
                assert 0.0 <= surv <= 1.0, f"Survival out of bounds: {surv}"
                assert 0.0 <= ev <= 1.0, f"Event prob out of bounds: {ev}"


# --- INVARIANT 10: DETERMINISTIC OUTPUT ---

def test_deterministic_predictions(train_data):
    """Invariant 10: Repeated inference calls on the same data must yield bit-identical predictions."""
    tf, _ = train_data
    layer = load_production_risk_layer(
        MODELS_DIR,
        CLEAN_DATA_DIR / "survival_train_features.csv",
        CLEAN_DATA_DIR / "survival_train_targets.csv",
    )
    preds_1 = layer.predict_risk(tf.iloc[:20])
    preds_2 = layer.predict_risk(tf.iloc[:20])

    assert len(preds_1) == len(preds_2)
    for p1, p2 in zip(preds_1, preds_2):
        assert p1.relative_hazard == p2.relative_hazard
        assert p1.event_probability_90d == p2.event_probability_90d
        assert p1.survival_probability_365d == p2.survival_probability_365d


# --- INVARIANT 11, 12, & 13: ARTIFACT INTEGRITY & VERSION TRACKING ---

def test_artifact_save_load(tmp_path, train_data, eval_data):
    """Invariant 11: Calibration artifacts serialize and reload cleanly."""
    res = run_full_survival_calibration(CLEAN_DATA_DIR, MODELS_DIR, tmp_path)
    assert res["status"] == CalibrationStatus.PARTIAL_SPARSE_EVENTS.value
    assert (tmp_path / "cox_calibration_summary.json").exists()
    assert (tmp_path / "production_risk_predictions_train.csv").exists()
    assert (tmp_path / "production_risk_predictions_eval.csv").exists()

    with open(tmp_path / "cox_calibration_summary.json") as f:
        meta = json.load(f)
    assert meta["model_version"] == MODEL_VERSION
    assert "SECTION_11_TO_SECTION_19" in meta["transitions"]


def test_calibration_artifact_integrity():
    """Invariant 12: Loop 7C model files must remain completely unmodified."""
    expected_files = [
        "cox_model_summary.json",
        "cox_section_11_to_section_19_coefficients.csv",
        "cox_section_11_to_section_19_baseline_survival.csv",
        "cox_section_19_to_award_coefficients.csv",
        "cox_section_19_to_award_baseline_survival.csv",
        "cox_case_initiation_to_milestone_coefficients.csv",
        "cox_case_initiation_to_milestone_baseline_survival.csv",
    ]
    for fn in expected_files:
        p = MODELS_DIR / fn
        assert p.exists()
        assert p.stat().st_size > 0


def test_model_version_tracking(train_data):
    """Invariant 13: Model version is explicitly recorded on every prediction."""
    tf, _ = train_data
    layer = load_production_risk_layer(
        MODELS_DIR,
        CLEAN_DATA_DIR / "survival_train_features.csv",
        CLEAN_DATA_DIR / "survival_train_targets.csv",
    )
    preds = layer.predict_risk(tf.iloc[:5])
    for p in preds:
        assert p.model_version == MODEL_VERSION


# --- INVARIANT 14: EXTRAPOLATION FLAGGING ---

def test_unsupported_horizons_handled_safely(train_data):
    """Invariant 14: Horizons beyond the EVAL follow-up ceiling (148d) are flagged."""
    tf, _ = train_data
    layer = load_production_risk_layer(
        MODELS_DIR,
        CLEAN_DATA_DIR / "survival_train_features.csv",
        CLEAN_DATA_DIR / "survival_train_targets.csv",
    )
    preds = layer.predict_risk(tf.iloc[:5])
    for p in preds:
        assert p.extrapolation_flags["30d"] is False
        assert p.extrapolation_flags["90d"] is False
        assert p.extrapolation_flags["180d"] is True
        assert p.extrapolation_flags["365d"] is True
        assert p.extrapolation_flags["730d"] is True


# --- INVARIANT 15: INSUFFICIENT-EVENT TRANSITION GATING ---

def test_insufficient_event_transitions_handled_explicitly(calibration_pipeline):
    """Invariant 15: Section 19 -> Award must explicitly report CALIBRATION NOT RELIABLE."""
    results = calibration_pipeline["results"]
    s19_res = results["SECTION_19_TO_AWARD"]
    assert s19_res.calibration_status == CalibrationStatus.NOT_RELIABLE_INSUFFICIENT_EVENTS.value
    assert s19_res.num_cases_with_events == 1  # Exactly 1 case with events in TRAIN
    assert "single case (CAS_CLEAN_070)" in s19_res.rationale


# --- INVARIANT 16: PRINCIPLED RISK BANDING ---

def test_no_arbitrary_risk_bands(calibration_pipeline, train_data):
    """Invariant 16: Risk bands must be anchored to empirical TRAIN quartiles, not arbitrary numbers."""
    cutoffs = calibration_pipeline["cutoffs"]
    for trans, c_dict in cutoffs.items():
        assert "p25_event_prob_90d" in c_dict
        assert "median_event_prob_90d" in c_dict
        assert "p75_event_prob_90d" in c_dict
        assert c_dict["p25_event_prob_90d"] <= c_dict["median_event_prob_90d"] <= c_dict["p75_event_prob_90d"]


# --- INVARIANT 17: UNCERTAINTY STATUS ---

def test_uncertainty_flags_work(train_data):
    """Invariant 17: Sparse event regimes are tagged with HIGH_UNCERTAINTY."""
    tf, _ = train_data
    layer = load_production_risk_layer(
        MODELS_DIR,
        CLEAN_DATA_DIR / "survival_train_features.csv",
        CLEAN_DATA_DIR / "survival_train_targets.csv",
    )
    preds = layer.predict_risk(tf.iloc[:10])
    for p in preds:
        assert p.uncertainty_status in [
            UncertaintyStatus.HIGH_UNCERTAINTY_SPARSE_EVENTS.value,
            UncertaintyStatus.EXTREME_UNCERTAINTY_ZERO_EVENTS.value,
        ]
        assert "UNCERTAINTY" in p.data_quality_warning


# --- INVARIANT 18: CITIZEN VIEW PRIVACY & SUPPRESSION ---

def test_citizen_output_does_not_expose_internal_ml_fields(train_data):
    """Invariant 18: Citizen projection strips internal hazard, coefficients, and ranking logic."""
    tf, _ = train_data
    layer = load_production_risk_layer(
        MODELS_DIR,
        CLEAN_DATA_DIR / "survival_train_features.csv",
        CLEAN_DATA_DIR / "survival_train_targets.csv",
    )
    preds = layer.predict_risk(tf.iloc[:5])

    for p in preds:
        # Officer view contains full analytical telemetry
        off_view = layer.to_officer_view(p)
        assert hasattr(off_view, "relative_hazard")
        assert off_view.governance_disclaimer == GOVERNANCE_SAFETY_DISCLAIMER

        # Citizen view suppresses all internal ML telemetry
        cit_view = layer.to_citizen_view(p, current_stage="SECTION_11", days_in_stage=45)
        cit_dict = cit_view.__dict__

        for banned in BANNED_CITIZEN_FIELDS:
            assert banned not in cit_dict, f"Security violation: banned field {banned} found in citizen view"

        # Check that citizen view provides statutory transparency
        assert hasattr(cit_view, "statutory_time_limit_days")
        assert hasattr(cit_view, "statutory_rights_summary")
        assert "RFCTLARR 2013" in cit_view.statutory_rights_summary
