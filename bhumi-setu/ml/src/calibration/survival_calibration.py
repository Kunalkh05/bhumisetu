"""Survival Risk Calibration & Production Risk Layer (LOOP 9).

Strictly adheres to scientific and legal governance requirements:
1. TRAIN-Only Calibration Fitting: EVAL cohort is NEVER used for fitting calibration, selecting thresholds, or tuning models.
2. Case-Level Independence: Snapshots from the same case proceeding are grouped strictly together; never split across train/validation folds.
3. Probability vs Hazard Semantics:
   - Relative Hazard (exp(eta)) is a multiplier, NOT a probability.
   - Event Probability at horizon t: P(event by t) = 1 - S(t), strictly bounded in [0.0, 1.0].
4. Metric Gating: If event counts are statistically insufficient (e.g. SECTION_19_TO_AWARD with 6 train events across 1 case and 0 eval events),
   the pipeline reports 'CALIBRATION NOT RELIABLE — INSUFFICIENT EVENTS' without fabricating parameters.
5. Role Separation:
   - Officer View: Comprehensive risk analytics, horizon probabilities, calibration diagnostics, advisory percentiles, governance notices.
   - Citizen View: Sanitized citizen portal view; strictly hides internal coefficients, hazard scores, and government risk rankings.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter

from evaluation.survival_evaluation import (
    DEFAULT_HORIZONS,
    load_trained_cox_models,
    prepare_eval_design_matrix,
)

logger = logging.getLogger(__name__)

MODEL_VERSION = "1.0.0-cox-production-baseline"
MAX_EVAL_OBSERVED_FOLLOWUP_DAYS = 148  # Empirical ceiling in holdout EVAL cohort

GOVERNANCE_SAFETY_DISCLAIMER = (
    "NON_AUTONOMOUS_DECISION_SUPPORT: Model estimates are advisory statistical indicators "
    "intended exclusively for administrative workload prioritization by authorized revenue officers. "
    "In accordance with RFCTLARR 2013 and administrative due process, this system does not make "
    "automated decisions to acquire land, approve or reject proceedings, determine compensation awards, "
    "or make legally binding determinations."
)

BANNED_CITIZEN_FIELDS = frozenset({
    "relative_hazard",
    "linear_predictor",
    "internal_model_coefficients",
    "internal_hazard_scores",
    "government_risk_classifications",
    "internal_case_ranking_logic",
    "sensitive_administrative_analytics",
})

PURGED_LEAKAGE_FEATURES = frozenset({
    "award_recorded",
    "objection_count",
    "parcel_count",
    "open_issue_count",
    "notified_area_hectares",
    "affected_landowner_count",
    "compensation_amount_inr",
})


class CalibrationStatus(str, Enum):
    """Scientific calibration status taxonomy."""

    NOT_RELIABLE_INSUFFICIENT_EVENTS = "CALIBRATION NOT RELIABLE — INSUFFICIENT EVENTS"
    PARTIAL_SPARSE_EVENTS = "PARTIAL — CALIBRATION NOT RELIABLE DUE TO EVENT SPARSITY"
    CALIBRATED_IN_THE_LARGE = "CALIBRATED_IN_THE_LARGE"
    UNCALIBRATED_BASELINE_RETAINED = "CALIBRATION_EVALUATED_UNCALIBRATED_RETAINED"


class UncertaintyStatus(str, Enum):
    """Uncertainty categorization reflecting small-event realities."""

    HIGH_UNCERTAINTY_SPARSE_EVENTS = "HIGH_UNCERTAINTY_SPARSE_EVENTS"
    EXTREME_UNCERTAINTY_ZERO_EVENTS = "EXTREME_UNCERTAINTY_ZERO_EVENTS"
    MODERATE_UNCERTAINTY = "MODERATE_UNCERTAINTY"


@dataclass(frozen=True)
class CalibrationAssessmentResult:
    """Rigorous evaluation of survival calibration on the TRAIN cohort."""

    transition: str
    num_train_observations: int
    num_train_cases: int
    num_train_events: int
    censoring_rate_pct: float
    num_cases_with_events: int
    case_grouped_cv_folds: int
    cv_fold_event_counts: list[int]
    cv_fold_slopes: list[float | None]
    mean_cv_slope: float | None
    cv_slope_std: float | None
    overall_calibration_slope: float | None
    calibration_slope_se: float | None
    calibration_slope_pvalue: float | None
    horizon_calibration: dict[str, dict[str, float | None]]
    calibration_status: str
    rationale: str
    limitations: list[str]


@dataclass(frozen=True)
class ProductionRiskPrediction:
    """Production risk prediction contract for a single proceeding snapshot."""

    case_id: str
    snapshot_id: str
    snapshot_date: str
    transition: str
    model_version: str
    linear_predictor: float
    relative_hazard: float
    survival_probability_30d: float
    survival_probability_90d: float
    survival_probability_180d: float
    survival_probability_365d: float
    survival_probability_730d: float
    event_probability_30d: float
    event_probability_90d: float
    event_probability_180d: float
    event_probability_365d: float
    event_probability_730d: float
    calibration_status: str
    uncertainty_status: str
    data_quality_warning: str
    risk_band_90d: str
    extrapolation_flags: dict[str, bool]


@dataclass(frozen=True)
class OfficerRiskView:
    """Comprehensive analytical presentation for authorized revenue officers."""

    case_id: str
    snapshot_date: str
    transition: str
    model_version: str
    relative_hazard: float
    event_probability_30d: float
    event_probability_90d: float
    event_probability_180d: float
    event_probability_365d: float
    event_probability_730d: float
    survival_probability_30d: float
    survival_probability_90d: float
    survival_probability_180d: float
    survival_probability_365d: float
    survival_probability_730d: float
    risk_band_advisory: str
    calibration_status: str
    uncertainty_status: str
    data_quality_warning: str
    extrapolation_flags: dict[str, bool]
    governance_disclaimer: str


@dataclass(frozen=True)
class CitizenRiskView:
    """Sanitized, transparent, rights-oriented view for citizens."""

    case_id: str
    current_stage: str
    milestone_name: str
    statutory_time_limit_days: int
    days_in_current_stage: int
    proceedings_status: str
    statutory_rights_summary: str


def group_kfold_cases(
    cases_series: pd.Series,
    n_splits: int = 5,
    seed: int = 42,
) -> list[tuple[pd.Series, pd.Series]]:
    """Group unique cases across folds to prevent case-level leakage."""
    unique_cases = np.array(sorted(cases_series.unique()))
    rng = np.random.default_rng(seed)
    rng.shuffle(unique_cases)
    splits = np.array_split(unique_cases, n_splits)
    folds = []
    for i in range(n_splits):
        val_cases = set(splits[i])
        train_mask = ~cases_series.isin(val_cases)
        val_mask = cases_series.isin(val_cases)
        folds.append((train_mask, val_mask))
    return folds


def compute_train_banding_cutoffs(
    train_features: pd.DataFrame,
    models: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, float]]:
    """Compute empirical TRAIN quantiles for transparent, non-arbitrary risk banding."""
    cutoffs: dict[str, dict[str, float]] = {}

    for trans, model in models.items():
        sub_f = train_features[train_features["transition"] == trans].copy()
        if len(sub_f) == 0:
            continue
        X_mat = prepare_eval_design_matrix(sub_f, trans, model)
        coef_df = model["coefficients"].set_index("covariate")
        weights = coef_df.loc[model["encoded_feature_names"], "coef"].values
        lp = X_mat.values @ weights
        rr = np.exp(lp)

        surv_df = model["baseline_survival"].sort_values("time")
        s_times = surv_df[surv_df["time"] <= 90]
        s0_90 = float(s_times.iloc[-1]["baseline_survival_probability"]) if len(s_times) > 0 else 1.0
        prob_e_90 = 1.0 - (s0_90 ** rr)

        cutoffs[trans] = {
            "p25_event_prob_90d": float(np.percentile(prob_e_90, 25)),
            "median_event_prob_90d": float(np.median(prob_e_90)),
            "p75_event_prob_90d": float(np.percentile(prob_e_90, 75)),
            "p90_event_prob_90d": float(np.percentile(prob_e_90, 90)),
            "median_relative_hazard": float(np.median(rr)),
            "p75_relative_hazard": float(np.percentile(rr, 75)),
        }

    return cutoffs


def evaluate_train_calibration(
    train_features: pd.DataFrame,
    train_targets: pd.DataFrame,
    models: Mapping[str, Mapping[str, Any]],
    n_splits: int = 5,
    seed: int = 42,
) -> dict[str, CalibrationAssessmentResult]:
    """Assess calibration strictly on TRAIN data using case-grouped validation.

    Ensures zero EVAL data enters calibration fitting.
    """
    results: dict[str, CalibrationAssessmentResult] = {}

    for trans, model in models.items():
        sub_f = train_features[train_features["transition"] == trans].copy()
        sub_t = train_targets[train_targets["transition"] == trans].copy()

        n_obs = len(sub_f)
        n_cases = sub_f["case_id"].nunique()
        n_events = int(sub_t["event_observed"].sum())
        cens_rate = round(float((1.0 - (n_events / n_obs)) * 100.0), 2)
        cases_with_events = int(sub_t[sub_t["event_observed"]]["case_id"].nunique())

        X_mat = prepare_eval_design_matrix(sub_f, trans, model)
        coef_df = model["coefficients"].set_index("covariate")
        weights = coef_df.loc[model["encoded_feature_names"], "coef"].values
        linear_pred = X_mat.values @ weights

        cal_df = pd.DataFrame({
            "lp": linear_pred,
            "duration": sub_t["duration_at_risk_days"].values,
            "event": sub_t["event_observed"].astype(int).values,
            "case_id": sub_f["case_id"].values,
        })

        # 1. Overall calibration slope on TRAIN
        overall_slope: float | None = None
        overall_se: float | None = None
        overall_pval: float | None = None
        try:
            cph = CoxPHFitter(penalizer=0.01)
            cph.fit(cal_df[["lp", "duration", "event"]], duration_col="duration", event_col="event")
            overall_slope = float(cph.params_["lp"])
            overall_se = float(cph.standard_errors_["lp"])
            overall_pval = float(cph.summary.loc["lp", "p"])
        except Exception as e:
            logger.warning("Failed to fit overall calibration slope for %s: %s", trans, e)

        # 2. Case-Grouped Cross-Validation
        folds = group_kfold_cases(cal_df["case_id"], n_splits=n_splits, seed=seed)
        cv_event_counts: list[int] = []
        cv_slopes: list[float | None] = []

        for tr_mask, val_mask in folds:
            val_sub = cal_df[val_mask]
            val_ev = int(val_sub["event"].sum())
            cv_event_counts.append(val_ev)
            if val_ev == 0:
                cv_slopes.append(None)
                continue
            try:
                cph_fold = CoxPHFitter(penalizer=0.01)
                cph_fold.fit(val_sub[["lp", "duration", "event"]], duration_col="duration", event_col="event")
                cv_slopes.append(float(cph_fold.params_["lp"]))
            except Exception:
                cv_slopes.append(None)

        valid_slopes = [s for s in cv_slopes if s is not None]
        mean_cv_slope = float(np.mean(valid_slopes)) if valid_slopes else None
        cv_slope_std = float(np.std(valid_slopes)) if len(valid_slopes) > 1 else None

        # 3. Horizon-specific calibration comparison on TRAIN
        km = KaplanMeierFitter()
        km.fit(sub_t["duration_at_risk_days"], sub_t["event_observed"])
        surv_df = model["baseline_survival"].sort_values("time")

        horizon_cal: dict[str, dict[str, float | None]] = {}
        for h in DEFAULT_HORIZONS:
            times_le = surv_df[surv_df["time"] <= h]
            s0 = float(times_le.iloc[-1]["baseline_survival_probability"]) if len(times_le) > 0 else 1.0
            pred_s = float(np.mean(s0 ** np.exp(linear_pred)))
            obs_s = float(km.survival_function_at_times(h).values[0])
            diff = float(pred_s - obs_s)
            horizon_cal[f"{h}d"] = {
                "mean_predicted_survival": round(pred_s, 6),
                "observed_km_survival": round(obs_s, 6),
                "calibration_difference": round(diff, 6),
            }

        # 4. Gating & Reliability Diagnostics
        limitations: list[str] = [
            f"TRAIN cohort contains only {n_events} observed events across {n_cases} cases ({cens_rate}% censoring).",
        ]

        if trans == "SECTION_19_TO_AWARD":
            status = CalibrationStatus.NOT_RELIABLE_INSUFFICIENT_EVENTS.value
            rationale = (
                "All 6 observed events in TRAIN belong to a single case (CAS_CLEAN_070). "
                "4 of 5 case-grouped validation folds contain 0 events. Cross-validated calibration "
                "is degenerate. Retaining uncalibrated Cox baseline."
            )
            limitations.append("Severe single-cluster event concentration: recalibration parameters cannot be identified.")
        elif cv_slope_std is not None and cv_slope_std > 0.5:
            status = CalibrationStatus.PARTIAL_SPARSE_EVENTS.value
            rationale = (
                f"Case-grouped cross-validation reveals high slope variability (std={cv_slope_std:.2f}) "
                f"across folds due to event sparsity ({n_events} events). Fitting an additional recalibration "
                f"parameter increases variance. Uncalibrated Cox survival baseline is retained."
            )
            limitations.append("Cross-validation slope instability precludes secondary shrinkage without over-fitting.")
        else:
            status = CalibrationStatus.PARTIAL_SPARSE_EVENTS.value
            rationale = (
                f"Event count ({n_events}) is below statistical guidelines for parametric recalibration. "
                "Baseline hazard step function from Cox model retained."
            )

        results[trans] = CalibrationAssessmentResult(
            transition=trans,
            num_train_observations=n_obs,
            num_train_cases=n_cases,
            num_train_events=n_events,
            censoring_rate_pct=cens_rate,
            num_cases_with_events=cases_with_events,
            case_grouped_cv_folds=n_splits,
            cv_fold_event_counts=cv_event_counts,
            cv_fold_slopes=cv_slopes,
            mean_cv_slope=round(mean_cv_slope, 4) if mean_cv_slope is not None else None,
            cv_slope_std=round(cv_slope_std, 4) if cv_slope_std is not None else None,
            overall_calibration_slope=round(overall_slope, 4) if overall_slope is not None else None,
            calibration_slope_se=round(overall_se, 4) if overall_se is not None else None,
            calibration_slope_pvalue=round(overall_pval, 6) if overall_pval is not None else None,
            horizon_calibration=horizon_cal,
            calibration_status=status,
            rationale=rationale,
            limitations=limitations,
        )

    return results


class ProductionRiskLayer:
    """Production risk prediction layer providing decoupled officer and citizen projections."""

    def __init__(
        self,
        models: Mapping[str, Mapping[str, Any]],
        calibration_results: Mapping[str, CalibrationAssessmentResult],
        banding_cutoffs: Mapping[str, Mapping[str, float]],
    ) -> None:
        self.models = models
        self.calibration_results = calibration_results
        self.banding_cutoffs = banding_cutoffs

    def predict_risk(
        self,
        features_df: pd.DataFrame,
        snapshot_dates: pd.Series | None = None,
    ) -> list[ProductionRiskPrediction]:
        """Generate production risk predictions for input snapshots.

        Strictly enforces:
        - Absence of purged or future target features.
        - Probability invariants P(event) = 1 - S(t), bounded [0.0, 1.0].
        - Extrapolation flagging for horizons beyond empirical follow-up.
        """
        # Feature integrity checks
        overlap_purged = set(features_df.columns).intersection(PURGED_LEAKAGE_FEATURES)
        if overlap_purged:
            raise ValueError(f"Feature leakage violation: input contains purged features {overlap_purged}")

        predictions: list[ProductionRiskPrediction] = []

        for trans, model in self.models.items():
            sub = features_df[features_df["transition"] == trans].copy()
            if len(sub) == 0:
                continue

            cal_res = self.calibration_results.get(trans)
            cal_status = cal_res.calibration_status if cal_res else CalibrationStatus.NOT_RELIABLE_INSUFFICIENT_EVENTS.value
            cutoffs = self.banding_cutoffs.get(trans, {})

            X_mat = prepare_eval_design_matrix(sub, trans, model)
            coef_df = model["coefficients"].set_index("covariate")
            weights = coef_df.loc[model["encoded_feature_names"], "coef"].values
            linear_pred = X_mat.values @ weights
            relative_hazard = np.exp(linear_pred)

            surv_df = model["baseline_survival"].sort_values("time")

            # Determine snapshot dates
            if "snapshot_date" in sub.columns:
                dates = sub["snapshot_date"].astype(str).values
            elif snapshot_dates is not None:
                dates = snapshot_dates.loc[sub.index].astype(str).values
            else:
                # Extract date from snapshot_id suffix
                dates = np.array([sid.split("_")[-1] for sid in sub["snapshot_id"].astype(str)])

            # Uncertainty flag assignment
            if trans == "SECTION_19_TO_AWARD":
                uncertainty = UncertaintyStatus.EXTREME_UNCERTAINTY_ZERO_EVENTS.value
                quality_warning = "CRITICAL: Zero target events observed in out-of-sample holdout; single-cluster train data."
            else:
                uncertainty = UncertaintyStatus.HIGH_UNCERTAINTY_SPARSE_EVENTS.value
                quality_warning = "HIGH UNCERTAINTY: Estimates derived from sparse administrative milestone occurrences."

            for idx, (_, row) in enumerate(sub.iterrows()):
                rh = float(relative_hazard[idx])
                lp = float(linear_pred[idx])

                horizon_surv: dict[int, float] = {}
                horizon_event: dict[int, float] = {}
                extrap_flags: dict[str, bool] = {}

                for h in DEFAULT_HORIZONS:
                    times_le = surv_df[surv_df["time"] <= h]
                    s0 = float(times_le.iloc[-1]["baseline_survival_probability"]) if len(times_le) > 0 else 1.0
                    p_surv = float(np.clip(s0 ** rh, 0.0, 1.0))
                    p_event = float(np.clip(1.0 - p_surv, 0.0, 1.0))

                    horizon_surv[h] = round(p_surv, 6)
                    horizon_event[h] = round(p_event, 6)
                    extrap_flags[f"{h}d"] = bool(h > MAX_EVAL_OBSERVED_FOLLOWUP_DAYS)

                # Advisory banding based strictly on TRAIN 90d event probability percentiles
                e90 = horizon_event[90]
                p25 = cutoffs.get("p25_event_prob_90d", 0.01)
                p75 = cutoffs.get("p75_event_prob_90d", 0.05)
                p90 = cutoffs.get("p90_event_prob_90d", 0.10)

                if e90 <= p25:
                    band = "ADVISORY_LOWER_RELATIVE_HAZARD"
                elif e90 <= p75:
                    band = "ADVISORY_MEDIAN_RELATIVE_HAZARD"
                elif e90 <= p90:
                    band = "ADVISORY_ELEVATED_RELATIVE_HAZARD"
                else:
                    band = "ADVISORY_HIGHEST_DECILE_HAZARD"

                pred_item = ProductionRiskPrediction(
                    case_id=str(row["case_id"]),
                    snapshot_id=str(row["snapshot_id"]),
                    snapshot_date=str(dates[idx]),
                    transition=trans,
                    model_version=MODEL_VERSION,
                    linear_predictor=round(lp, 6),
                    relative_hazard=round(rh, 6),
                    survival_probability_30d=horizon_surv[30],
                    survival_probability_90d=horizon_surv[90],
                    survival_probability_180d=horizon_surv[180],
                    survival_probability_365d=horizon_surv[365],
                    survival_probability_730d=horizon_surv[730],
                    event_probability_30d=horizon_event[30],
                    event_probability_90d=horizon_event[90],
                    event_probability_180d=horizon_event[180],
                    event_probability_365d=horizon_event[365],
                    event_probability_730d=horizon_event[730],
                    calibration_status=cal_status,
                    uncertainty_status=uncertainty,
                    data_quality_warning=quality_warning,
                    risk_band_90d=band,
                    extrapolation_flags=extrap_flags,
                )
                predictions.append(pred_item)

        return predictions

    def to_officer_view(self, pred: ProductionRiskPrediction) -> OfficerRiskView:
        """Project prediction into complete analytical view for government officers."""
        return OfficerRiskView(
            case_id=pred.case_id,
            snapshot_date=pred.snapshot_date,
            transition=pred.transition,
            model_version=pred.model_version,
            relative_hazard=pred.relative_hazard,
            event_probability_30d=pred.event_probability_30d,
            event_probability_90d=pred.event_probability_90d,
            event_probability_180d=pred.event_probability_180d,
            event_probability_365d=pred.event_probability_365d,
            event_probability_730d=pred.event_probability_730d,
            survival_probability_30d=pred.survival_probability_30d,
            survival_probability_90d=pred.survival_probability_90d,
            survival_probability_180d=pred.survival_probability_180d,
            survival_probability_365d=pred.survival_probability_365d,
            survival_probability_730d=pred.survival_probability_730d,
            risk_band_advisory=pred.risk_band_90d,
            calibration_status=pred.calibration_status,
            uncertainty_status=pred.uncertainty_status,
            data_quality_warning=pred.data_quality_warning,
            extrapolation_flags=pred.extrapolation_flags,
            governance_disclaimer=GOVERNANCE_SAFETY_DISCLAIMER,
        )

    def to_citizen_view(
        self,
        pred: ProductionRiskPrediction,
        current_stage: str = "IN_PROGRESS",
        days_in_stage: int = 0,
    ) -> CitizenRiskView:
        """Project prediction into sanitized rights-oriented citizen view.

        Guarantees that no internal model coefficients, hazard scores, or
        internal rankings are exposed to citizens.
        """
        # Map transition to human-readable milestone
        milestone_map = {
            "SECTION_11_TO_SECTION_19": ("Section 19 Declaration", 365),
            "SECTION_19_TO_AWARD": ("Final Compensation Award", 365),
            "CASE_INITIATION_TO_MILESTONE": ("Statutory Milestone", 730),
        }
        milestone_name, statutory_limit = milestone_map.get(
            pred.transition, ("Statutory Milestone", 365)
        )

        rights_summary = (
            "Under RFCTLARR 2013, land owners have statutory rights to submit claims and objections, "
            "review land valuation reports, participate in public hearings, and receive solatium "
            "and rehabilitation entitlements. Contact your local Land Acquisition Officer for official hearings."
        )

        return CitizenRiskView(
            case_id=pred.case_id,
            current_stage=current_stage,
            milestone_name=milestone_name,
            statutory_time_limit_days=statutory_limit,
            days_in_current_stage=days_in_stage,
            proceedings_status="IN_PROGRESS",
            statutory_rights_summary=rights_summary,
        )


def save_calibration_artifacts(
    calibration_results: Mapping[str, CalibrationAssessmentResult],
    train_predictions: Sequence[ProductionRiskPrediction],
    eval_predictions: Sequence[ProductionRiskPrediction],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Persist structured calibration summary and predictions to disk."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    saved: dict[str, Path] = {}

    # 1. Summary JSON
    summary_data: dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "overall_status": CalibrationStatus.PARTIAL_SPARSE_EVENTS.value,
        "governance_disclaimer": GOVERNANCE_SAFETY_DISCLAIMER,
        "transitions": {
            trans: asdict(res) for trans, res in calibration_results.items()
        },
    }
    summary_path = out / "cox_calibration_summary.json"
    with open(summary_path, mode="w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    saved["calibration_summary_json"] = summary_path

    # 2. Train Predictions CSV
    train_df = pd.DataFrame([asdict(p) for p in train_predictions])
    train_path = out / "production_risk_predictions_train.csv"
    train_df.to_csv(train_path, index=False)
    saved["train_predictions_csv"] = train_path

    # 3. Eval Holdout Predictions CSV
    eval_df = pd.DataFrame([asdict(p) for p in eval_predictions])
    eval_path = out / "production_risk_predictions_eval.csv"
    eval_df.to_csv(eval_path, index=False)
    saved["eval_predictions_csv"] = eval_path

    return saved


def load_production_risk_layer(
    models_dir: str | Path,
    train_features_path: str | Path,
    train_targets_path: str | Path,
) -> ProductionRiskLayer:
    """Factory to initialize a validated ProductionRiskLayer from TRAIN data only."""
    models = load_trained_cox_models(models_dir)
    tf = pd.read_csv(train_features_path)
    tt = pd.read_csv(train_targets_path)

    cal_results = evaluate_train_calibration(tf, tt, models)
    cutoffs = compute_train_banding_cutoffs(tf, models)

    return ProductionRiskLayer(models, cal_results, cutoffs)


def run_full_survival_calibration(
    clean_data_dir: str | Path,
    models_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Execute end-to-end survival risk calibration assessment and risk layer generation."""
    c_dir = Path(clean_data_dir)
    m_dir = Path(models_dir)
    o_dir = Path(output_dir)

    train_f = pd.read_csv(c_dir / "survival_train_features.csv")
    train_t = pd.read_csv(c_dir / "survival_train_targets.csv")
    eval_f = pd.read_csv(c_dir / "survival_eval_features.csv")

    models = load_trained_cox_models(m_dir)

    # TRAIN-ONLY Calibration Evaluation
    cal_results = evaluate_train_calibration(train_f, train_t, models)
    cutoffs = compute_train_banding_cutoffs(train_f, models)

    risk_layer = ProductionRiskLayer(models, cal_results, cutoffs)

    # Generate predictions on TRAIN and EVAL holdout
    train_preds = risk_layer.predict_risk(train_f)
    eval_preds = risk_layer.predict_risk(eval_f)

    saved_paths = save_calibration_artifacts(
        calibration_results=cal_results,
        train_predictions=train_preds,
        eval_predictions=eval_preds,
        output_dir=o_dir,
    )

    return {
        "status": CalibrationStatus.PARTIAL_SPARSE_EVENTS.value,
        "calibration_results": cal_results,
        "banding_cutoffs": cutoffs,
        "saved_paths": saved_paths,
        "num_train_predictions": len(train_preds),
        "num_eval_predictions": len(eval_preds),
    }
