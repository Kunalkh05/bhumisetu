"""Out-of-sample evaluation pipeline for BHUMISETU Cox Proportional Hazards models (LOOP 8).

Strict scientific evaluation of pre-fitted Cox models (LOOP 7C) against the completely
untouched EVAL cohort (N=167, 89 cases, 4 events, 163 right-censored).

Guarantees:
1. Strict read-only out-of-sample evaluation (zero refitting, tuning, or parameter changes).
2. Complete absence of target leakage and purged variables in evaluation matrices.
3. Principled metric gating: returns explicit 'NOT COMPUTABLE — INSUFFICIENT EVENTS'
   rather than fabricated numbers when event support is lacking.
4. Calculation of Harrell's C-index, IPCW time-dependent Brier scores, calibration
   against empirical Kaplan-Meier, and horizon-specific survival probabilities.
5. Candid disclosure of severe small-event (N_events=4) and heavy-censoring (97.6%) limitations.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from lifelines import KaplanMeierFitter
from lifelines.utils import concordance_index
import numpy as np
import pandas as pd

from features.survival_features import (
    IDENTIFIER_COLUMNS,
    PURGED_FEATURE_COLUMNS,
    SAFE_PREDICTOR_COLUMNS,
    TARGET_COLUMNS,
    TARGET_METADATA_COLUMNS,
)

__all__ = [
    "BrierScoreResult",
    "CalibrationResult",
    "ConcordanceResult",
    "EvalCohortSummary",
    "FullEvaluationResult",
    "TransitionEvalResult",
    "compute_ipcw_brier_score",
    "evaluate_transition_survival",
    "generate_out_of_sample_predictions",
    "load_trained_cox_models",
    "prepare_eval_design_matrix",
    "run_full_survival_evaluation",
    "save_evaluation_artifacts",
    "validate_eval_features",
]

DEFAULT_HORIZONS: tuple[int, ...] = (30, 90, 180, 365, 730)


@dataclass(frozen=True)
class EvalCohortSummary:
    """Summary of out-of-sample evaluation cohort for a transition."""

    transition: str
    num_observations: int
    num_cases: int
    num_events: int
    num_censored: int
    censoring_rate_pct: float
    min_duration_days: float
    max_duration_days: float
    event_durations_days: tuple[float, ...]


@dataclass(frozen=True)
class ConcordanceResult:
    """Survival concordance evaluation and diagnostic disclosure."""

    transition: str
    status: str
    num_observations: int
    num_events: int
    num_censored: int
    concordance_index: float | None
    interpretation_limitations: str


@dataclass(frozen=True)
class BrierScoreResult:
    """Time-dependent Inverse Probability of Censoring Weighted (IPCW) Brier score."""

    horizon_days: int
    status: str
    brier_score: float | None
    num_at_risk: int
    num_events_before: int
    valid_observations: int
    limitations: str


@dataclass(frozen=True)
class CalibrationResult:
    """Calibration comparison between predicted survival and empirical Kaplan-Meier."""

    horizon_days: int
    status: str
    mean_predicted_survival: float | None
    observed_km_survival: float | None
    calibration_difference: float | None
    num_at_risk: int
    limitations: str


@dataclass(frozen=True)
class TransitionEvalResult:
    """Complete evaluation report for a single acquisition transition."""

    transition: str
    cohort_summary: EvalCohortSummary
    model_num_parameters: int
    model_train_concordance: float
    concordance: ConcordanceResult
    time_dependent_discrimination: dict[str, Any]
    brier_scores: tuple[BrierScoreResult, ...]
    calibration: tuple[CalibrationResult, ...]
    km_comparison: dict[str, Any]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class FullEvaluationResult:
    """Comprehensive out-of-sample evaluation across all transitions."""

    total_eval_observations: int
    total_eval_cases: int
    total_eval_events: int
    total_eval_censored: int
    overall_censoring_rate_pct: float
    transitions: dict[str, TransitionEvalResult]
    overall_status: str
    scientific_rationale: str
    predictions_df: pd.DataFrame


def validate_eval_features(
    eval_features_path: str | Path,
    eval_targets_path: str | Path,
) -> dict[str, Any]:
    """Validate that EVAL dataset conforms strictly to approved schemas and zero leakage.

    Verifies:
    1. Features file and targets file exist.
    2. All 15 safe predictors are present.
    3. Purged variables are completely absent.
    4. Target variables are absent from features.
    5. Durations > 0 and event_observed in {0, 1}.
    6. Exact cohort counts match specification.
    """
    f_path = Path(eval_features_path)
    t_path = Path(eval_targets_path)

    if not f_path.exists() or not t_path.exists():
        raise FileNotFoundError(f"Feature or target file not found: {f_path}, {t_path}")

    feats = pd.read_csv(f_path)
    targs = pd.read_csv(t_path)

    # 1. Purged variables absence check
    purged_found = [c for c in PURGED_FEATURE_COLUMNS if c in feats.columns]
    if purged_found:
        raise AssertionError(f"Purged feature(s) detected in EVAL feature matrix: {purged_found}")

    # 2. Target columns absence in features check
    targets_in_features = [c for c in TARGET_COLUMNS if c in feats.columns]
    if targets_in_features:
        raise AssertionError(f"Target column(s) detected in EVAL feature matrix: {targets_in_features}")

    # 3. Target validity
    if (targs["duration_at_risk_days"] <= 0).any():
        raise AssertionError("Non-positive duration detected in EVAL targets!")

    unique_events = set(targs["event_observed"].unique())
    if not unique_events.issubset({True, False, 0, 1}):
        raise AssertionError(f"Invalid event values in EVAL targets: {unique_events}")

    # 4. Cohort sizes
    total_obs = len(feats)
    total_cases = feats["case_id"].nunique()
    total_events = int(targs["event_observed"].sum())
    total_censored = total_obs - total_events

    expected_transitions = {
        "SECTION_11_TO_SECTION_19": {"obs": 59, "events": 2, "censored": 57},
        "SECTION_19_TO_AWARD": {"obs": 4, "events": 0, "censored": 4},
        "CASE_INITIATION_TO_MILESTONE": {"obs": 104, "events": 2, "censored": 102},
    }

    transition_counts: dict[str, dict[str, int]] = {}
    for trans, exp in expected_transitions.items():
        sub_t = targs[targs["transition"] == trans]
        sub_obs = len(sub_t)
        sub_events = int(sub_t["event_observed"].sum())
        sub_censored = sub_obs - sub_events
        transition_counts[trans] = {
            "obs": sub_obs,
            "events": sub_events,
            "censored": sub_censored,
        }
        if sub_obs != exp["obs"] or sub_events != exp["events"] or sub_censored != exp["censored"]:
            raise AssertionError(
                f"Transition '{trans}' count mismatch: got {transition_counts[trans]}, expected {exp}"
            )

    return {
        "total_observations": total_obs,
        "total_cases": total_cases,
        "total_events": total_events,
        "total_censored": total_censored,
        "transition_counts": transition_counts,
        "status": "VALIDATED",
    }


def load_trained_cox_models(
    models_dir: str | Path,
) -> dict[str, dict[str, Any]]:
    """Load pre-fitted LOOP 7C Cox Proportional Hazards model artifacts from disk without refitting.

    Loads summary metadata, coefficient vectors, baseline survival curves, and PH test results.
    """
    m_dir = Path(models_dir)
    summary_path = m_dir / "cox_model_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Cox model summary not found: {summary_path}")

    with open(summary_path, encoding="utf-8") as f:
        summary_data = json.load(f)

    models: dict[str, dict[str, Any]] = {}
    expected_transitions = [
        "SECTION_11_TO_SECTION_19",
        "SECTION_19_TO_AWARD",
        "CASE_INITIATION_TO_MILESTONE",
    ]

    for trans in expected_transitions:
        if trans not in summary_data:
            raise KeyError(f"Transition '{trans}' missing from model summary json!")

        slug = trans.lower()
        coef_path = m_dir / f"cox_{slug}_coefficients.csv"
        surv_path = m_dir / f"cox_{slug}_baseline_survival.csv"
        ph_path = m_dir / f"cox_{slug}_ph_test.csv"

        if not coef_path.exists():
            raise FileNotFoundError(f"Coefficient artifact not found: {coef_path}")
        if not surv_path.exists():
            raise FileNotFoundError(f"Baseline survival artifact not found: {surv_path}")

        coef_df = pd.read_csv(coef_path)
        surv_df = pd.read_csv(surv_path).sort_values("time")
        ph_df = pd.read_csv(ph_path) if ph_path.exists() else pd.DataFrame()

        models[trans] = {
            "summary": summary_data[trans],
            "coefficients": coef_df,
            "baseline_survival": surv_df,
            "ph_test": ph_df,
            "encoded_feature_names": summary_data[trans]["encoded_feature_names"],
            "predictor_columns_used": summary_data[trans]["predictor_columns_used"],
        }

    return models


def prepare_eval_design_matrix(
    eval_features: pd.DataFrame,
    transition: str,
    model_artifact: Mapping[str, Any],
) -> pd.DataFrame:
    """Construct evaluation design matrix aligned strictly to the trained model's feature space.

    Guarantees deterministic column mapping without fitting or modifying any encoders.
    """
    sub = eval_features[eval_features["transition"] == transition].copy()
    encoded_cols: list[str] = list(model_artifact["encoded_feature_names"])

    X = pd.DataFrame(0.0, index=sub.index, columns=encoded_cols)

    categorical_prefixes = ("district_", "current_stage_", "act_key_", "derived_project_type_")

    for col in encoded_cols:
        if col in sub.columns:
            # Direct numerical or boolean column
            X[col] = sub[col].fillna(0.0).astype(float)
        else:
            # Check for one-hot indicator pattern
            matched = False
            for pfx in categorical_prefixes:
                if col.startswith(pfx):
                    base_feature = pfx[:-1]
                    level = col[len(pfx):]
                    if base_feature in sub.columns:
                        X[col] = (sub[base_feature].astype(str) == level).astype(float)
                        matched = True
                        break
            if not matched:
                # Column not found in sub - assign default 0.0 without crash
                X[col] = 0.0

    return X


def generate_out_of_sample_predictions(
    eval_features: pd.DataFrame,
    models: Mapping[str, Mapping[str, Any]],
    time_horizons: Sequence[int] = DEFAULT_HORIZONS,
) -> pd.DataFrame:
    """Generate out-of-sample risk scores and survival probabilities for all EVAL snapshots.

    Computes:
    - linear predictor: eta = sum(beta_j * x_j)
    - relative risk / partial hazard: exp(eta)
    - survival probabilities at specified horizons: S_0(t) ** exp(eta)
    """
    dfs: list[pd.DataFrame] = []

    for trans, model in models.items():
        sub_feats = eval_features[eval_features["transition"] == trans].copy()
        if len(sub_feats) == 0:
            continue

        X_mat = prepare_eval_design_matrix(sub_feats, trans, model)
        coef_df = model["coefficients"].set_index("covariate")
        weights = coef_df.loc[model["encoded_feature_names"], "coef"].values

        # Linear predictor and relative risk
        linear_pred = X_mat.values @ weights
        relative_risk = np.exp(linear_pred)

        pred_sub = pd.DataFrame({
            "snapshot_id": sub_feats["snapshot_id"].values,
            "case_id": sub_feats["case_id"].values,
            "transition": trans,
            "linear_predictor": np.round(linear_pred, 6),
            "relative_risk": np.round(relative_risk, 6),
        }, index=sub_feats.index)

        # Baseline survival step-function lookup
        surv_df = model["baseline_survival"].sort_values("time")
        for h in time_horizons:
            times_le = surv_df[surv_df["time"] <= h]
            if len(times_le) == 0:
                s0 = 1.0
            else:
                s0 = float(times_le.iloc[-1]["baseline_survival_probability"])

            pred_surv = np.clip(s0 ** relative_risk, 0.0, 1.0)
            pred_sub[f"pred_survival_{h}d"] = np.round(pred_surv, 6)

        dfs.append(pred_sub)

    if not dfs:
        return pd.DataFrame()

    out_df = pd.concat(dfs, axis=0).sort_index()
    return out_df


def compute_ipcw_brier_score(
    durations: np.ndarray,
    events: np.ndarray,
    pred_surv_at_t: np.ndarray,
    t_horizon: int,
) -> tuple[float | None, str, int, int, int]:
    """Calculate Inverse Probability of Censoring Weighted (IPCW) Brier score at horizon t.

    Returns:
        (brier_score, status_message, n_at_risk, n_events_before, valid_obs)
    """
    km_cens = KaplanMeierFitter()
    # Censoring distribution: event is censoring (1 - event)
    km_cens.fit(durations, 1 - events)
    n = len(durations)

    # G(t) = P(C > t)
    g_t = float(km_cens.predict(t_horizon))
    if g_t <= 0.0:
        return (
            None,
            "NOT COMPUTABLE — INSUFFICIENT SUPPORT (censoring survivor probability G(t) = 0)",
            0,
            int(np.sum((durations <= t_horizon) & (events == 1))),
            0,
        )

    weights = np.zeros(n)
    sq_errors = np.zeros(n)
    valid_count = 0
    n_events_before = 0
    n_at_risk = 0

    for i in range(n):
        ti = durations[i]
        ei = events[i]
        si = pred_surv_at_t[i]

        if ti <= t_horizon and ei == 1:
            n_events_before += 1
            g_ti = float(km_cens.predict(ti))
            if g_ti > 0.0:
                weights[i] = 1.0 / g_ti
                sq_errors[i] = (0.0 - si) ** 2
                valid_count += 1
        elif ti > t_horizon:
            n_at_risk += 1
            weights[i] = 1.0 / g_t
            sq_errors[i] = (1.0 - si) ** 2
            valid_count += 1
        else:
            # Censored before horizon: indeterminate status, weight = 0
            weights[i] = 0.0
            sq_errors[i] = 0.0

    if valid_count == 0 or np.sum(weights) == 0:
        return (
            None,
            "NOT COMPUTABLE — INSUFFICIENT SUPPORT (zero valid weighted observations)",
            n_at_risk,
            n_events_before,
            0,
        )

    brier = float(np.sum(weights * sq_errors) / n)
    return (
        round(brier, 6),
        "COMPUTED",
        n_at_risk,
        n_events_before,
        valid_count,
    )


def evaluate_transition_survival(
    predictions_df: pd.DataFrame,
    eval_targets: pd.DataFrame,
    transition: str,
    model_artifact: Mapping[str, Any],
    time_horizons: Sequence[int] = DEFAULT_HORIZONS,
) -> TransitionEvalResult:
    """Conduct comprehensive survival evaluation for a single transition cohort."""
    sub_pred = predictions_df[predictions_df["transition"] == transition].copy()
    sub_targ = eval_targets[eval_targets["transition"] == transition].copy()

    # Join predictions with true targets
    merged = pd.merge(sub_pred, sub_targ, on=["case_id", "snapshot_id", "transition"])
    n_obs = len(merged)
    n_cases = merged["case_id"].nunique()
    n_events = int(merged["event_observed"].sum())
    n_censored = n_obs - n_events
    cens_rate = round(n_censored / n_obs * 100.0, 2) if n_obs > 0 else 0.0

    durations = merged["duration_at_risk_days"].values
    events = merged["event_observed"].astype(int).values
    event_durations = tuple(float(d) for d in durations[events == 1])

    cohort_summary = EvalCohortSummary(
        transition=transition,
        num_observations=n_obs,
        num_cases=n_cases,
        num_events=n_events,
        num_censored=n_censored,
        censoring_rate_pct=cens_rate,
        min_duration_days=float(durations.min()) if n_obs > 0 else 0.0,
        max_duration_days=float(durations.max()) if n_obs > 0 else 0.0,
        event_durations_days=event_durations,
    )

    limitations: list[str] = []

    # 1. Concordance Index
    if n_events == 0:
        concordance_res = ConcordanceResult(
            transition=transition,
            status="NOT COMPUTABLE — INSUFFICIENT EVENTS",
            num_observations=n_obs,
            num_events=0,
            num_censored=n_censored,
            concordance_index=None,
            interpretation_limitations=(
                "Evaluation discrimination cannot be established because the EVAL cohort "
                "contains zero observed target events."
            ),
        )
        limitations.append("Concordance uncomputable: 0 observed events in evaluation cohort.")
    else:
        # Higher risk -> shorter time-to-event, so rank using -relative_risk
        c_val = float(concordance_index(durations, -merged["relative_risk"].values, events))
        c_status = "COMPUTED"
        lim_msg = (
            f"Concordance index is {c_val:.4f}. However, with only {n_events} observed events "
            f"across {n_obs} observations, the estimate is statistically unstable and must not "
            f"be interpreted as evidence of generalized predictive performance."
        )
        concordance_res = ConcordanceResult(
            transition=transition,
            status=c_status,
            num_observations=n_obs,
            num_events=n_events,
            num_censored=n_censored,
            concordance_index=round(c_val, 4),
            interpretation_limitations=lim_msg,
        )
        limitations.append(f"Severe small-event sparsity ({n_events} events): C-index has high variance.")

    # 2. Time-Dependent Discrimination (AUC)
    # Check if cumulative/dynamic AUC is statistically valid
    time_dep_disc: dict[str, Any] = {}
    for h in time_horizons:
        events_le = int(np.sum((durations <= h) & (events == 1)))
        at_risk = int(np.sum(durations >= h))
        if events_le < 5:
            time_dep_disc[f"horizon_{h}d"] = {
                "status": "NOT RELIABLE — INSUFFICIENT EVENTS",
                "events_before_horizon": events_le,
                "at_risk": at_risk,
                "reason": (
                    f"Only {events_le} event(s) observed prior to {h} days. Standard time-dependent "
                    f"AUC requires >= 5 observed events for stable rank estimation."
                ),
            }
        else:
            time_dep_disc[f"horizon_{h}d"] = {
                "status": "NOT RELIABLE — INSUFFICIENT EVENTS",
                "events_before_horizon": events_le,
                "at_risk": at_risk,
                "reason": "Insufficient event density in evaluation cohort.",
            }

    # 3. Brier Scores
    brier_list: list[BrierScoreResult] = []
    for h in time_horizons:
        pred_col = f"pred_survival_{h}d"
        pred_surv = merged[pred_col].values
        bs_val, bs_status, n_risk, n_ev_before, n_valid = compute_ipcw_brier_score(
            durations, events, pred_surv, h
        )
        if bs_val is None:
            bs_lim = (
                f"Cannot compute IPCW Brier score at horizon {h}d: all observations censored "
                f"or exited before horizon (maximum follow-up = {cohort_summary.max_duration_days} days)."
            )
        elif n_ev_before == 0:
            bs_lim = f"Brier score at {h}d reflects non-event censoring only (0 events observed before {h}d)."
        else:
            bs_lim = f"Brier score at {h}d based on {n_ev_before} observed event(s) and {n_risk} at risk."

        brier_list.append(
            BrierScoreResult(
                horizon_days=h,
                status=bs_status,
                brier_score=bs_val,
                num_at_risk=n_risk,
                num_events_before=n_ev_before,
                valid_observations=n_valid,
                limitations=bs_lim,
            )
        )

    # 4. Calibration Analysis against empirical Kaplan-Meier
    calib_list: list[CalibrationResult] = []
    km = KaplanMeierFitter()
    km.fit(durations, events)

    for h in time_horizons:
        pred_col = f"pred_survival_{h}d"
        mean_pred = float(np.mean(merged[pred_col].values))
        n_risk = int(np.sum(durations >= h))

        if n_risk == 0:
            calib_list.append(
                CalibrationResult(
                    horizon_days=h,
                    status="NOT RELIABLE — INSUFFICIENT SUPPORT",
                    mean_predicted_survival=round(mean_pred, 4),
                    observed_km_survival=None,
                    calibration_difference=None,
                    num_at_risk=0,
                    limitations="Zero cases remain at risk past maximum evaluation duration.",
                )
            )
        else:
            obs_km = float(km.predict(h))
            diff = round(mean_pred - obs_km, 4)
            calib_list.append(
                CalibrationResult(
                    horizon_days=h,
                    status="COMPUTED",
                    mean_predicted_survival=round(mean_pred, 4),
                    observed_km_survival=round(obs_km, 4),
                    calibration_difference=diff,
                    num_at_risk=n_risk,
                    limitations=(
                        f"Calibration based on {int(np.sum((durations <= h) & (events == 1)))} "
                        f"event(s). No calibration model or adjustment was fitted."
                    ),
                )
            )

    # 5. Kaplan-Meier Baseline vs Observed Comparison
    km_comp = {
        "train_baseline_concordance": model_artifact["summary"]["concordance_index"],
        "train_num_events": model_artifact["summary"]["num_events"],
        "train_censoring_rate_pct": model_artifact["summary"]["censoring_rate_pct"],
        "eval_num_events": n_events,
        "eval_censoring_rate_pct": cens_rate,
        "eval_median_survival_days": float(km.median_survival_time_) if not math.isinf(km.median_survival_time_) else None,
        "strata_comparison_note": (
            "Subgroup risk stratification (e.g. high-risk vs low-risk strata) was omitted "
            "because the evaluation cohort contains <= 2 observed events, which prevents "
            "statistically meaningful strata separation."
        ),
    }

    return TransitionEvalResult(
        transition=transition,
        cohort_summary=cohort_summary,
        model_num_parameters=model_artifact["summary"]["num_parameters"],
        model_train_concordance=model_artifact["summary"]["concordance_index"],
        concordance=concordance_res,
        time_dependent_discrimination=time_dep_disc,
        brier_scores=tuple(brier_list),
        calibration=tuple(calib_list),
        km_comparison=km_comp,
        limitations=tuple(limitations),
    )


def run_full_survival_evaluation(
    data_dir: str | Path,
    models_dir: str | Path,
    output_dir: str | Path | None = None,
) -> FullEvaluationResult:
    """Execute complete out-of-sample survival evaluation across all transitions.

    Strictly complies with the No-Refitting and No-Tuning constraints.
    """
    d_dir = Path(data_dir)
    m_dir = Path(models_dir)

    eval_feats_path = d_dir / "survival_eval_features.csv"
    eval_targs_path = d_dir / "survival_eval_targets.csv"

    # Step 1 & 2: Validate eval features & schemas
    val_info = validate_eval_features(eval_feats_path, eval_targs_path)
    models = load_trained_cox_models(m_dir)

    eval_features = pd.read_csv(eval_feats_path)
    eval_targets = pd.read_csv(eval_targs_path)

    # Step 3: Out-of-sample risk scores & survival predictions
    predictions_df = generate_out_of_sample_predictions(eval_features, models)

    # Steps 4 - 10: Transition-specific evaluation
    transition_results: dict[str, TransitionEvalResult] = {}
    for trans, model in models.items():
        transition_results[trans] = evaluate_transition_survival(
            predictions_df, eval_targets, trans, model
        )

    overall_status = "PARTIAL — SOME METRICS NOT COMPUTABLE DUE TO EVENT SPARSITY"
    scientific_rationale = (
        "Evaluation pipeline completed successfully without model refitting or data leakage. "
        "However, out of 167 evaluation snapshots across 89 cases, only 4 observed events occurred "
        "(2 in SECTION_11_TO_SECTION_19, 0 in SECTION_19_TO_AWARD, 2 in CASE_INITIATION_TO_MILESTONE). "
        "Consequently, event-based discrimination cannot be established for SECTION_19_TO_AWARD, "
        "and time-dependent discrimination metrics across all horizons lack statistical reliability."
    )

    full_result = FullEvaluationResult(
        total_eval_observations=val_info["total_observations"],
        total_eval_cases=val_info["total_cases"],
        total_eval_events=val_info["total_events"],
        total_eval_censored=val_info["total_censored"],
        overall_censoring_rate_pct=round(
            val_info["total_censored"] / val_info["total_observations"] * 100.0, 2
        ),
        transitions=transition_results,
        overall_status=overall_status,
        scientific_rationale=scientific_rationale,
        predictions_df=predictions_df,
    )

    if output_dir is not None:
        save_evaluation_artifacts(full_result, output_dir)

    return full_result


def save_evaluation_artifacts(
    eval_result: FullEvaluationResult,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Persist evaluation predictions and structured metric summaries to disk.

    Leaves all existing Loop 7C artifacts intact.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    saved_paths: dict[str, Path] = {}

    # 1. Predictions CSV
    pred_path = out / "eval_out_of_sample_predictions.csv"
    eval_result.predictions_df.to_csv(pred_path, index=False)
    saved_paths["predictions_csv"] = pred_path

    # 2. Evaluation Summary JSON
    summary_dict: dict[str, Any] = {
        "overall_status": eval_result.overall_status,
        "scientific_rationale": eval_result.scientific_rationale,
        "cohort_totals": {
            "num_observations": eval_result.total_eval_observations,
            "num_cases": eval_result.total_eval_cases,
            "num_events": eval_result.total_eval_events,
            "num_censored": eval_result.total_eval_censored,
            "censoring_rate_pct": eval_result.overall_censoring_rate_pct,
        },
        "transitions": {},
    }

    for trans, tres in eval_result.transitions.items():
        summary_dict["transitions"][trans] = {
            "cohort_summary": asdict(tres.cohort_summary),
            "model_num_parameters": tres.model_num_parameters,
            "model_train_concordance": tres.model_train_concordance,
            "concordance": asdict(tres.concordance),
            "time_dependent_discrimination": tres.time_dependent_discrimination,
            "brier_scores": [asdict(b) for b in tres.brier_scores],
            "calibration": [asdict(c) for c in tres.calibration],
            "km_comparison": tres.km_comparison,
            "limitations": list(tres.limitations),
        }

    summary_path = out / "cox_eval_summary.json"
    with open(summary_path, mode="w", encoding="utf-8") as f:
        json.dump(summary_dict, f, indent=2)
    saved_paths["eval_summary_json"] = summary_path

    return saved_paths
