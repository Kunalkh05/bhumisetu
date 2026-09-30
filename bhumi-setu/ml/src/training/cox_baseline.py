"""Production Cox Proportional Hazards Baseline for BHUMISETU (LOOP 7C).

Fits semi-parametric Cox Proportional Hazards regression using the verified
lifelines library on TRAIN ONLY data across land acquisition transitions:
- SECTION_11_TO_SECTION_19
- SECTION_19_TO_AWARD
- CASE_INITIATION_TO_MILESTONE

Guarantees:
1. Strict isolation of training cohort (EVAL cohort is never accessed or touched).
2. Proper right-censoring handling using (duration_at_risk_days, event_observed).
3. Zero domain fabrication for missing values.
4. Principled handling of zero-variance and transition-specific collinear attributes.
5. Extraction of coefficients, hazard ratios exp(coef), 95% CIs, p-values, and PH assumption tests.
6. Candid reporting of Events Per Variable (EPV) and small-sample limitations.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
from lifelines import CoxPHFitter
from lifelines.statistics import proportional_hazard_test

from features.survival_features import (
    IDENTIFIER_COLUMNS,
    SAFE_PREDICTOR_COLUMNS,
    TARGET_COLUMNS,
    TARGET_METADATA_COLUMNS,
)

__all__ = [
    "CoxModelArtifact",
    "fit_all_transition_cox_models",
    "fit_single_transition_cox_model",
    "load_cox_artifacts",
    "prepare_cox_design_matrix",
    "save_cox_artifacts",
]


@dataclass(frozen=True)
class CoxModelArtifact:
    """Fitted Cox Proportional Hazards model artifact and diagnostics."""

    transition: str
    num_observations: int
    num_events: int
    num_censored: int
    censoring_rate_pct: float
    predictor_columns_used: tuple[str, ...]
    encoded_feature_names: tuple[str, ...]
    num_parameters: int
    events_per_variable: float
    convergence_status: str
    log_likelihood: float
    concordance_index: float
    partial_aic: float
    coefficient_summary: tuple[dict[str, Any], ...]
    ph_test_summary: tuple[dict[str, Any], ...]
    baseline_survival: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]


def prepare_cox_design_matrix(
    train_features_path: str | Path,
    train_targets_path: str | Path,
    transition: str,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Construct leakage-free design matrix for a specific transition cohort.
    
    Returns:
        X_matrix: DataFrame containing encoded predictors, 'duration', and 'event'.
        retained_columns: Base feature columns included after pruning zero-variance/collinear features.
        warnings: List of diagnostic warnings (e.g. dropped zero-variance features).
    """
    f_path = Path(train_features_path)
    t_path = Path(train_targets_path)

    if not f_path.exists() or not t_path.exists():
        raise FileNotFoundError(f"Feature or target file not found: {f_path}, {t_path}")

    feats = pd.read_csv(f_path)
    targs = pd.read_csv(t_path)

    # Invariant: features must not contain target columns
    for tc in TARGET_COLUMNS:
        if tc in feats.columns:
            raise AssertionError(f"Target column '{tc}' found in feature matrix!")

    df = pd.merge(feats, targs, on=list(IDENTIFIER_COLUMNS))
    sub = df[df["transition"] == transition].copy()

    if len(sub) == 0:
        raise ValueError(f"No observations found for transition '{transition}' in training set.")

    warnings: list[str] = []

    # Nominal features with extreme high cardinality (causing complete separation with <= 18 events)
    excluded_high_cardinality = {"village", "taluka"}
    exclude_all = set(IDENTIFIER_COLUMNS) | set(TARGET_COLUMNS) | set(TARGET_METADATA_COLUMNS) | excluded_high_cardinality

    candidate_cols: list[str] = []
    for col in SAFE_PREDICTOR_COLUMNS:
        if col in exclude_all:
            continue
        if col not in sub.columns:
            continue
        # Drop columns with > 50% structural missingness in this transition
        missing_count = sub[col].isna().sum()
        if missing_count > 0.5 * len(sub):
            warnings.append(
                f"Feature '{col}' excluded from '{transition}' due to high structural missingness "
                f"({missing_count}/{len(sub)} = {missing_count/len(sub):.1%})."
            )
            continue
        # Check variance within this transition cohort
        if sub[col].nunique() <= 1:
            warnings.append(
                f"Feature '{col}' excluded from '{transition}' due to zero variance (constant within cohort)."
            )
            continue
        candidate_cols.append(col)

    # Prune 1:1 collinear authority when district is present
    if "acquiring_authority" in candidate_cols and "district" in candidate_cols:
        if sub.groupby("district")["acquiring_authority"].nunique().max() == 1:
            candidate_cols.remove("acquiring_authority")
            warnings.append(
                f"Feature 'acquiring_authority' excluded from '{transition}' because it is 1:1 collinear with 'district'."
            )

    # Prune redundant identical day counters (correlation > 0.98 with derived_days_in_current_stage)
    if "derived_days_in_current_stage" in candidate_cols:
        for redundant in ["derived_days_since_case_initiation", "derived_days_since_latest_notice", "derived_statutory_sec19_proximity_ratio"]:
            if redundant in candidate_cols:
                corr = sub["derived_days_in_current_stage"].corr(sub[redundant])
                if abs(corr) > 0.98:
                    candidate_cols.remove(redundant)
                    warnings.append(
                        f"Feature '{redundant}' excluded from '{transition}' due to collinearity with "
                        f"'derived_days_in_current_stage' (Pearson r = {corr:.3f})."
                    )

    # Prune redundant extension boolean if extension_count is present
    if "extension_count" in candidate_cols and "has_statutory_extension" in candidate_cols:
        corr = sub["extension_count"].corr(sub["has_statutory_extension"].astype(int))
        if abs(corr) > 0.98:
            candidate_cols.remove("has_statutory_extension")
            warnings.append(
                f"Feature 'has_statutory_extension' excluded from '{transition}' due to collinearity with "
                f"'extension_count' (Pearson r = {corr:.3f})."
            )

    # Prepare matrix
    X_df = sub[candidate_cols].copy()

    # Handle remaining minor numerical missingness with median imputation
    for col in X_df.columns:
        if X_df[col].isna().any():
            median_val = X_df[col].median()
            X_df[col] = X_df[col].fillna(median_val)
            warnings.append(
                f"Feature '{col}' had {sub[col].isna().sum()} missing values imputed with median ({median_val})."
            )

    # One-hot encode categoricals (drop first to prevent dummy variable trap)
    X_enc = pd.get_dummies(X_df, drop_first=True)
    for col in X_enc.columns:
        if X_enc[col].dtype == bool:
            X_enc[col] = X_enc[col].astype(int)

    # Add duration and binary event indicator
    X_enc["duration"] = sub["duration_at_risk_days"].values
    X_enc["event"] = sub["event_observed"].astype(int).values

    return X_enc, candidate_cols, warnings


def fit_single_transition_cox_model(
    train_features_path: str | Path,
    train_targets_path: str | Path,
    transition: str,
    *,
    penalizer: float = 0.1,
) -> CoxModelArtifact:
    """Fit Cox Proportional Hazards model on TRAIN data for one transition."""
    X_mat, retained_cols, warnings = prepare_cox_design_matrix(
        train_features_path, train_targets_path, transition
    )

    n_obs = len(X_mat)
    n_events = int(X_mat["event"].sum())
    n_censored = n_obs - n_events
    censoring_rate = round(n_censored / n_obs * 100.0, 2)

    cph = CoxPHFitter(penalizer=penalizer)
    convergence_status = "CONVERGED"
    try:
        cph.fit(X_mat, duration_col="duration", event_col="event")
    except Exception as e:
        convergence_status = f"FAILED: {e}"
        warnings.append(f"Model fitting failed: {e}")

    n_params = len(cph.params_) if hasattr(cph, "params_") else 0
    epv = round(n_events / n_params, 2) if n_params > 0 else 0.0

    if epv < 5.0:
        warnings.append(
            f"Severe small-event limitation: Events Per Variable (EPV = {epv:.2f}) is below "
            f"standard statistical guidelines (EPV >= 10). Model is susceptible to small-sample bias."
        )

    # Extract coefficient summary table
    summary_df = cph.summary.copy()
    coef_list: list[dict[str, Any]] = []
    for cov_name, row in summary_df.iterrows():
        coef_list.append({
            "covariate": str(cov_name),
            "coef": round(float(row["coef"]), 6),
            "hazard_ratio": round(float(row["exp(coef)"]), 6),
            "standard_error": round(float(row["se(coef)"]), 6),
            "coef_lower_95": round(float(row["coef lower 95%"]), 6),
            "coef_upper_95": round(float(row["coef upper 95%"]), 6),
            "hr_lower_95": round(float(row["exp(coef) lower 95%"]), 6),
            "hr_upper_95": round(float(row["exp(coef) upper 95%"]), 6),
            "z_score": round(float(row["z"]), 4),
            "p_value": round(float(row["p"]), 6),
        })

    # Proportional Hazards assumption test
    ph_list: list[dict[str, Any]] = []
    try:
        ph_res = proportional_hazard_test(cph, X_mat, time_transform="rank")
        for cov_name, row in ph_res.summary.iterrows():
            ph_list.append({
                "covariate": str(cov_name),
                "test_statistic": round(float(row["test_statistic"]), 4),
                "p_value": round(float(row["p"]), 6),
                "ph_satisfied": bool(row["p"] >= 0.05),
            })
    except Exception as e:
        warnings.append(f"Proportional hazards test encountered exception: {e}")

    # Baseline survival function
    baseline_surv = cph.baseline_survival_
    surv_list: list[dict[str, Any]] = []
    for t_val, s_row in baseline_surv.iterrows():
        surv_list.append({
            "time": int(t_val) if isinstance(t_val, (int, float)) and t_val == int(t_val) else float(t_val),
            "baseline_survival_probability": round(float(s_row.iloc[0]), 6),
        })

    encoded_feature_names = tuple(c for c in X_mat.columns if c not in ("duration", "event"))

    return CoxModelArtifact(
        transition=transition,
        num_observations=n_obs,
        num_events=n_events,
        num_censored=n_censored,
        censoring_rate_pct=censoring_rate,
        predictor_columns_used=tuple(retained_cols),
        encoded_feature_names=encoded_feature_names,
        num_parameters=n_params,
        events_per_variable=epv,
        convergence_status=convergence_status,
        log_likelihood=round(float(cph.log_likelihood_), 4),
        concordance_index=round(float(cph.concordance_index_), 4),
        partial_aic=round(float(cph.AIC_partial_), 4),
        coefficient_summary=tuple(coef_list),
        ph_test_summary=tuple(ph_list),
        baseline_survival=tuple(surv_list),
        warnings=tuple(warnings),
    )


def fit_all_transition_cox_models(
    train_features_path: str | Path,
    train_targets_path: str | Path,
    *,
    penalizer: float = 0.1,
) -> dict[str, CoxModelArtifact]:
    """Fit Cox models for all three statutory acquisition transitions on TRAIN ONLY."""
    transitions = [
        "SECTION_11_TO_SECTION_19",
        "SECTION_19_TO_AWARD",
        "CASE_INITIATION_TO_MILESTONE",
    ]
    models: dict[str, CoxModelArtifact] = {}
    for t in transitions:
        models[t] = fit_single_transition_cox_model(
            train_features_path, train_targets_path, t, penalizer=penalizer
        )
    return models


def save_cox_artifacts(
    models: Mapping[str, CoxModelArtifact],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Save fitted model coefficients, baseline survival, and metadata to disk."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    saved_paths: dict[str, Path] = {}

    summary_metadata: dict[str, Any] = {}

    for t, m in models.items():
        slug = t.lower()
        coef_path = out / f"cox_{slug}_coefficients.csv"
        surv_path = out / f"cox_{slug}_baseline_survival.csv"
        ph_path = out / f"cox_{slug}_ph_test.csv"

        # 1. Coefficients CSV
        if m.coefficient_summary:
            with open(coef_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(m.coefficient_summary[0].keys()))
                writer.writeheader()
                for row in m.coefficient_summary:
                    writer.writerow(row)
            saved_paths[f"{slug}_coefficients"] = coef_path

        # 2. Baseline Survival CSV
        if m.baseline_survival:
            with open(surv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(m.baseline_survival[0].keys()))
                writer.writeheader()
                for row in m.baseline_survival:
                    writer.writerow(row)
            saved_paths[f"{slug}_baseline_survival"] = surv_path

        # 3. PH Test CSV
        if m.ph_test_summary:
            with open(ph_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(m.ph_test_summary[0].keys()))
                writer.writeheader()
                for row in m.ph_test_summary:
                    writer.writerow(row)
            saved_paths[f"{slug}_ph_test"] = ph_path

        summary_metadata[t] = {
            "num_observations": m.num_observations,
            "num_events": m.num_events,
            "num_censored": m.num_censored,
            "censoring_rate_pct": m.censoring_rate_pct,
            "num_parameters": m.num_parameters,
            "events_per_variable": m.events_per_variable,
            "convergence_status": m.convergence_status,
            "concordance_index": m.concordance_index,
            "log_likelihood": m.log_likelihood,
            "partial_aic": m.partial_aic,
            "predictor_columns_used": list(m.predictor_columns_used),
            "encoded_feature_names": list(m.encoded_feature_names),
            "warnings": list(m.warnings),
        }

    summary_path = out / "cox_model_summary.json"
    with open(summary_path, mode="w", encoding="utf-8") as f:
        json.dump(summary_metadata, f, indent=2)
    saved_paths["model_summary"] = summary_path

    return saved_paths


def load_cox_artifacts(
    output_dir: str | Path,
) -> dict[str, Any]:
    """Load Cox model summaries and coefficient tables from disk."""
    out = Path(output_dir)
    summary_path = out / "cox_model_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Model summary not found: {summary_path}")

    with open(summary_path, encoding="utf-8") as f:
        data = json.load(f)
    return data
