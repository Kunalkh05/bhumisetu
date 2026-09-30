"""Survival Model Explainability & Auditable Risk Reasons (LOOP 10).

Provides:
- Exact additive feature contribution decomposition for Cox Proportional Hazards:
  linear_predictor eta = sum(beta_j * x_j)
  relative_hazard = exp(eta) = prod(exp(beta_j * x_j))
- Rigorous non-causal association interpretations (INCREASED_HAZARD vs DECREASED_HAZARD).
- Point-in-time snapshot auditability with SHA256 model coefficient hashes.
- Decoupled role projections: OfficerExplanationView (full auditability) vs CitizenExplanationView (sanitized rights-centric view).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from calibration.survival_calibration import (
    BANNED_CITIZEN_FIELDS,
    GOVERNANCE_SAFETY_DISCLAIMER,
    MAX_EVAL_OBSERVED_FOLLOWUP_DAYS,
    MODEL_VERSION,
    PURGED_LEAKAGE_FEATURES,
    CalibrationStatus,
    UncertaintyStatus,
    evaluate_train_calibration,
)
from evaluation.survival_evaluation import (
    DEFAULT_HORIZONS,
    load_trained_cox_models,
    prepare_eval_design_matrix,
)

logger = logging.getLogger(__name__)

FEATURE_VERSION = "1.0.0-survival-clean-15feat"

# Feature metadata: human readable name, description, and baseline interpretation
FEATURE_CATALOG: dict[str, dict[str, str]] = {
    "derived_days_in_current_stage": {
        "human_readable_name": "Elapsed Days in Current Procedural Stage",
        "description": "Duration elapsed since entering current statutory stage.",
    },
    "derived_days_since_case_initiation": {
        "human_readable_name": "Elapsed Days Since Case Initiation",
        "description": "Total duration since the proceeding was formally initiated.",
    },
    "derived_days_since_latest_notice": {
        "human_readable_name": "Elapsed Days Since Latest Notice",
        "description": "Time elapsed since the most recent statutory gazette notice was published.",
    },
    "derived_notice_count": {
        "human_readable_name": "Statutory Notice Publications",
        "description": "Number of formal gazette notices and corrigenda issued.",
    },
    "extension_count": {
        "human_readable_name": "Statutory Extension Count",
        "description": "Number of formal government timeline extensions granted.",
    },
    "has_statutory_extension": {
        "human_readable_name": "Statutory Extension Granted",
        "description": "Formal statutory timeline extension has been granted under Act provisions.",
    },
    "derived_is_direct_purchase": {
        "human_readable_name": "Direct Purchase / Consent Modality",
        "description": "Proceeding utilizes direct land purchase / negotiated consent rather than compulsory acquisition.",
    },
    "district_Pune": {
        "human_readable_name": "District: Pune",
        "description": "Land parcel is situated in Pune revenue district.",
    },
    "district_Solapur": {
        "human_readable_name": "District: Solapur",
        "description": "Land parcel is situated in Solapur revenue district.",
    },
    "district_Yavatmal": {
        "human_readable_name": "District: Yavatmal",
        "description": "Land parcel is situated in Yavatmal revenue district.",
    },
    "current_stage_INITIATION": {
        "human_readable_name": "Stage: Case Initiation",
        "description": "Case is in initial proposal and requisition phase.",
    },
    "current_stage_GENERAL_NOTICE": {
        "human_readable_name": "Stage: Preliminary Notification",
        "description": "Case is in preliminary notification and public review stage.",
    },
    "current_stage_SECTION_11": {
        "human_readable_name": "Stage: Section 11 Notification",
        "description": "Formal Section 11 preliminary notification published in gazette.",
    },
    "current_stage_SECTION_19": {
        "human_readable_name": "Stage: Section 19 Declaration",
        "description": "Formal Section 19 declaration of public purpose published.",
    },
    "current_stage_SECTION_21": {
        "human_readable_name": "Stage: Section 21 Notice",
        "description": "Section 21 public notice for claims and inquiry issued.",
    },
    "act_key_RFCTLARR_2013": {
        "human_readable_name": "Statutory Act: RFCTLARR 2013",
        "description": "Proceeding governed by the central Right to Fair Compensation Act 2013.",
    },
    "derived_project_type_Irrigation / Canal": {
        "human_readable_name": "Project Type: Irrigation / Canal",
        "description": "Acquisition project is for water resources, canal, or irrigation infrastructure.",
    },
    "derived_project_type_Rural Infrastructure": {
        "human_readable_name": "Project Type: Rural Infrastructure",
        "description": "Acquisition project is for rural roads, connectivity, or village infrastructure.",
    },
}


class ContributionDirection(str, Enum):
    """Direction of feature effect on the Cox model's hazard."""

    INCREASED_HAZARD = "INCREASED_HAZARD"
    DECREASED_HAZARD = "DECREASED_HAZARD"
    NEUTRAL_BASELINE = "NEUTRAL_BASELINE"


@dataclass(frozen=True)
class FeatureContribution:
    """Individual feature contribution to the Cox linear predictor."""

    feature_name: str
    human_readable_name: str
    raw_value: Any
    transformed_value: float
    coefficient: float
    contribution: float
    hazard_multiplier: float
    direction: str
    explanation_narrative: str


@dataclass(frozen=True)
class MissingFeatureInfo:
    """Information regarding missing or unavailable features in the input record."""

    feature_name: str
    human_readable_name: str
    was_missing: bool
    imputation_applied: str
    imputed_value: float


@dataclass(frozen=True)
class SnapshotExplanation:
    """Comprehensive point-in-time mathematical explanation of a Cox model prediction."""

    case_id: str
    snapshot_id: str
    snapshot_date: str
    transition: str
    model_version: str
    feature_version: str
    model_checksum: str
    prediction_timestamp: str
    linear_predictor: float
    relative_hazard: float
    top_positive_contributors: list[FeatureContribution]
    top_negative_contributors: list[FeatureContribution]
    all_contributions: list[FeatureContribution]
    missing_features: list[MissingFeatureInfo]
    uncertainty_status: str
    calibration_status: str
    extrapolation_status: dict[str, bool]
    data_quality_warning: str
    governance_disclaimer: str


@dataclass(frozen=True)
class OfficerExplanationView:
    """Audit-ready, analytical explanation view for authorized revenue officers."""

    case_id: str
    snapshot_date: str
    transition: str
    model_version: str
    relative_hazard: float
    linear_predictor: float
    summary_narrative: str
    why_hazard_is_higher: list[dict[str, Any]]
    why_hazard_is_lower: list[dict[str, Any]]
    missing_features: list[dict[str, Any]]
    uncertainty_status: str
    calibration_status: str
    extrapolation_status: dict[str, bool]
    data_quality_warning: str
    governance_disclaimer: str


@dataclass(frozen=True)
class CitizenExplanationView:
    """Sanitized, plain-language rights and progress view for citizens."""

    case_id: str
    current_stage: str
    milestone_name: str
    statutory_time_limit_days: int
    days_in_current_stage: int
    proceedings_status: str
    statutory_rights_summary: str
    citizen_procedural_explanation: str


def compute_model_checksum(coef_df: pd.DataFrame) -> str:
    """Generate SHA256 checksum of model coefficients for point-in-time auditability."""
    content = coef_df.sort_values("covariate").to_csv(index=False).encode("utf-8")
    return hashlib.sha256(content).hexdigest()[:16]


class SurvivalExplainer:
    """Explainability engine for production Cox Proportional Hazards baseline models."""

    def __init__(
        self,
        models: Mapping[str, Mapping[str, Any]],
        calibration_results: Mapping[str, Any] | None = None,
    ) -> None:
        self.models = models
        self.calibration_results = calibration_results or {}
        self.checksums: dict[str, str] = {
            trans: compute_model_checksum(model["coefficients"])
            for trans, model in models.items()
        }

    def explain_snapshot(
        self,
        snapshot_row: pd.Series | dict[str, Any],
        prediction_timestamp: str | None = None,
    ) -> SnapshotExplanation:
        """Decompose a single proceeding snapshot into exact additive Cox contributions.

        Enforces:
        - Sum of contributions == linear predictor (within 1e-5).
        - Product of hazard multipliers == relative hazard (within 1e-5).
        - Explicit non-causal association phrasing.
        - Absence of purged features.
        """
        if isinstance(snapshot_row, dict):
            row_s = pd.Series(snapshot_row)
        else:
            row_s = snapshot_row

        # Check for purged feature leakage
        overlap = set(row_s.index).intersection(PURGED_LEAKAGE_FEATURES)
        if overlap:
            raise ValueError(f"Feature leakage violation: snapshot contains purged features {overlap}")

        trans = str(row_s["transition"])
        if trans not in self.models:
            raise ValueError(f"Unknown transition: {trans}")

        model = self.models[trans]
        encoded_names: list[str] = list(model["encoded_feature_names"])
        coef_df = model["coefficients"].set_index("covariate")
        weights = coef_df.loc[encoded_names, "coef"].values

        # Build 1-row DataFrame for design matrix extraction
        single_df = pd.DataFrame([row_s])
        X_mat = prepare_eval_design_matrix(single_df, trans, model)
        transformed_vals = X_mat.values[0]

        contributions_arr = weights * transformed_vals
        linear_predictor = float(np.sum(contributions_arr))
        relative_hazard = float(np.exp(linear_predictor))

        # Track missing / imputed features
        missing_info: list[MissingFeatureInfo] = []
        for feat in model["predictor_columns_used"]:
            raw_val = row_s.get(feat, None)
            is_na = pd.isna(raw_val)
            meta = FEATURE_CATALOG.get(feat, {"human_readable_name": feat.replace("_", " ").title()})
            if is_na:
                missing_info.append(
                    MissingFeatureInfo(
                        feature_name=feat,
                        human_readable_name=meta["human_readable_name"],
                        was_missing=True,
                        imputation_applied="zero_or_baseline_imputation",
                        imputed_value=0.0,
                    )
                )

        # Build feature contribution objects
        all_contribs: list[FeatureContribution] = []
        for idx, feat_name in enumerate(encoded_names):
            coef = float(weights[idx])
            t_val = float(transformed_vals[idx])
            c_val = float(contributions_arr[idx])
            h_mult = float(np.exp(c_val))

            meta = FEATURE_CATALOG.get(
                feat_name, {"human_readable_name": feat_name.replace("_", " ").title()}
            )
            hr_name = meta["human_readable_name"]

            # Map raw value
            if feat_name in row_s:
                raw_v = row_s[feat_name]
            else:
                # One-hot encoded level
                raw_v = t_val

            if c_val > 1e-6:
                direction = ContributionDirection.INCREASED_HAZARD.value
                narrative = (
                    f"{hr_name} contributed +{c_val:.4f} to the model's estimated log-hazard "
                    f"(hazard multiplier: {h_mult:.3f}x relative to baseline)."
                )
            elif c_val < -1e-6:
                direction = ContributionDirection.DECREASED_HAZARD.value
                narrative = (
                    f"{hr_name} contributed {c_val:.4f} to the model's estimated log-hazard "
                    f"(hazard multiplier: {h_mult:.3f}x relative to baseline)."
                )
            else:
                direction = ContributionDirection.NEUTRAL_BASELINE.value
                narrative = f"{hr_name} is at baseline value; zero contribution to estimated log-hazard."

            all_contribs.append(
                FeatureContribution(
                    feature_name=feat_name,
                    human_readable_name=hr_name,
                    raw_value=raw_v,
                    transformed_value=round(t_val, 4),
                    coefficient=round(coef, 6),
                    contribution=round(c_val, 6),
                    hazard_multiplier=round(h_mult, 6),
                    direction=direction,
                    explanation_narrative=narrative,
                )
            )

        # Rank positive and negative contributors by absolute magnitude
        pos_contribs = sorted(
            [c for c in all_contribs if c.direction == ContributionDirection.INCREASED_HAZARD.value],
            key=lambda x: abs(x.contribution),
            reverse=True,
        )[:5]

        neg_contribs = sorted(
            [c for c in all_contribs if c.direction == ContributionDirection.DECREASED_HAZARD.value],
            key=lambda x: abs(x.contribution),
            reverse=True,
        )[:5]

        # Uncertainty and calibration status
        cal_res = self.calibration_results.get(trans)
        cal_status = (
            cal_res.calibration_status
            if hasattr(cal_res, "calibration_status")
            else (
                cal_res.get("calibration_status")
                if isinstance(cal_res, dict)
                else CalibrationStatus.NOT_RELIABLE_INSUFFICIENT_EVENTS.value
            )
        )

        if trans == "SECTION_19_TO_AWARD":
            uncertainty = UncertaintyStatus.EXTREME_UNCERTAINTY_ZERO_EVENTS.value
            quality_warning = "CRITICAL: Zero target events observed in out-of-sample holdout; single-cluster train data."
        else:
            uncertainty = UncertaintyStatus.HIGH_UNCERTAINTY_SPARSE_EVENTS.value
            quality_warning = "HIGH UNCERTAINTY: Estimates derived from sparse administrative milestone occurrences."

        # Extrapolation flags
        extrap_flags = {
            f"{h}d": bool(h > MAX_EVAL_OBSERVED_FOLLOWUP_DAYS) for h in DEFAULT_HORIZONS
        }

        # Snapshot date
        if "snapshot_date" in row_s and pd.notna(row_s["snapshot_date"]):
            s_date = str(row_s["snapshot_date"])
        else:
            sid = str(row_s["snapshot_id"])
            s_date = sid.split("_")[-1]

        timestamp = prediction_timestamp or datetime.now(timezone.utc).isoformat()

        return SnapshotExplanation(
            case_id=str(row_s["case_id"]),
            snapshot_id=str(row_s["snapshot_id"]),
            snapshot_date=s_date,
            transition=trans,
            model_version=MODEL_VERSION,
            feature_version=FEATURE_VERSION,
            model_checksum=self.checksums[trans],
            prediction_timestamp=timestamp,
            linear_predictor=round(linear_predictor, 6),
            relative_hazard=round(relative_hazard, 6),
            top_positive_contributors=pos_contribs,
            top_negative_contributors=neg_contribs,
            all_contributions=all_contribs,
            missing_features=missing_info,
            uncertainty_status=uncertainty,
            calibration_status=cal_status,
            extrapolation_status=extrap_flags,
            data_quality_warning=quality_warning,
            governance_disclaimer=GOVERNANCE_SAFETY_DISCLAIMER,
        )

    def explain_dataframe(self, df: pd.DataFrame) -> list[SnapshotExplanation]:
        """Generate explanations for an entire cohort DataFrame."""
        explanations: list[SnapshotExplanation] = []
        for _, row in df.iterrows():
            explanations.append(self.explain_snapshot(row))
        return explanations

    def to_officer_view(self, explanation: SnapshotExplanation) -> OfficerExplanationView:
        """Project explanation into full audit-ready analytical view for government officers."""
        pos_list = [
            {
                "feature": c.feature_name,
                "label": c.human_readable_name,
                "value": c.raw_value,
                "contribution": c.contribution,
                "hazard_multiplier": c.hazard_multiplier,
                "narrative": c.explanation_narrative,
            }
            for c in explanation.top_positive_contributors
        ]

        neg_list = [
            {
                "feature": c.feature_name,
                "label": c.human_readable_name,
                "value": c.raw_value,
                "contribution": c.contribution,
                "hazard_multiplier": c.hazard_multiplier,
                "narrative": c.explanation_narrative,
            }
            for c in explanation.top_negative_contributors
        ]

        miss_list = [
            {
                "feature": m.feature_name,
                "label": m.human_readable_name,
                "imputation": m.imputation_applied,
            }
            for m in explanation.missing_features
        ]

        # Generate non-causal summary narrative
        summary = (
            f"The model estimated a relative hazard of {explanation.relative_hazard:.2f}x relative to baseline "
            f"(linear predictor: {explanation.linear_predictor:+.4f}). "
            f"This estimate is mathematically driven by {len(pos_list)} positive feature associations "
            f"and {len(neg_list)} negative feature associations. This reflects statistical model correlation, "
            f"not causal delay."
        )

        return OfficerExplanationView(
            case_id=explanation.case_id,
            snapshot_date=explanation.snapshot_date,
            transition=explanation.transition,
            model_version=explanation.model_version,
            relative_hazard=explanation.relative_hazard,
            linear_predictor=explanation.linear_predictor,
            summary_narrative=summary,
            why_hazard_is_higher=pos_list,
            why_hazard_is_lower=neg_list,
            missing_features=miss_list,
            uncertainty_status=explanation.uncertainty_status,
            calibration_status=explanation.calibration_status,
            extrapolation_status=explanation.extrapolation_status,
            data_quality_warning=explanation.data_quality_warning,
            governance_disclaimer=GOVERNANCE_SAFETY_DISCLAIMER,
        )

    def to_citizen_view(
        self,
        explanation: SnapshotExplanation,
        current_stage: str = "IN_PROGRESS",
        days_in_stage: int = 0,
    ) -> CitizenExplanationView:
        """Project explanation into sanitized rights-oriented citizen view.

        Strictly hides internal model coefficients, hazard scores, and case ranking logic.
        """
        milestone_map = {
            "SECTION_11_TO_SECTION_19": ("Section 19 Declaration", 365),
            "SECTION_19_TO_AWARD": ("Final Compensation Award", 365),
            "CASE_INITIATION_TO_MILESTONE": ("Statutory Milestone", 730),
        }
        milestone_name, statutory_limit = milestone_map.get(
            explanation.transition, ("Statutory Milestone", 365)
        )

        rights_summary = (
            "Under RFCTLARR 2013, land owners have statutory rights to submit claims and objections (Sec 15), "
            "review land valuation reports, participate in public inquiry hearings, and receive solatium "
            "and rehabilitation entitlements. Contact your local Land Acquisition Officer for hearing dates."
        )

        procedural_expl = (
            f"Your land acquisition proceeding is currently at stage '{current_stage}'. "
            f"The next formal statutory milestone is '{milestone_name}'. "
            f"Under RFCTLARR 2013 provisions, the statutory time limit for this milestone is {statutory_limit} days. "
            f"Current elapsed time: {days_in_stage} days."
        )

        return CitizenExplanationView(
            case_id=explanation.case_id,
            current_stage=current_stage,
            milestone_name=milestone_name,
            statutory_time_limit_days=statutory_limit,
            days_in_current_stage=days_in_stage,
            proceedings_status="IN_PROGRESS",
            statutory_rights_summary=rights_summary,
            citizen_procedural_explanation=procedural_expl,
        )


def save_explanation_artifacts(
    explanations: Sequence[SnapshotExplanation],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Persist structured explanation JSON and CSV artifacts to disk."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    saved: dict[str, Path] = {}

    # 1. Full JSON artifact
    json_data = [asdict(e) for e in explanations]
    json_path = out / "survival_explanations.json"
    with open(json_path, mode="w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    saved["explanations_json"] = json_path

    # 2. Flattened CSV artifact
    flattened_rows: list[dict[str, Any]] = []
    for e in explanations:
        pos_names = "; ".join(f"{c.feature_name} (+{c.contribution:.4f})" for c in e.top_positive_contributors)
        neg_names = "; ".join(f"{c.feature_name} ({c.contribution:.4f})" for c in e.top_negative_contributors)
        row_dict = {
            "case_id": e.case_id,
            "snapshot_id": e.snapshot_id,
            "snapshot_date": e.snapshot_date,
            "transition": e.transition,
            "model_version": e.model_version,
            "model_checksum": e.model_checksum,
            "linear_predictor": e.linear_predictor,
            "relative_hazard": e.relative_hazard,
            "top_positive_contributors": pos_names,
            "top_negative_contributors": neg_names,
            "num_positive_contributors": len(e.top_positive_contributors),
            "num_negative_contributors": len(e.top_negative_contributors),
            "uncertainty_status": e.uncertainty_status,
            "calibration_status": e.calibration_status,
            "data_quality_warning": e.data_quality_warning,
        }
        flattened_rows.append(row_dict)

    csv_path = out / "survival_explanations.csv"
    pd.DataFrame(flattened_rows).to_csv(csv_path, index=False)
    saved["explanations_csv"] = csv_path

    return saved


def load_survival_explainer(
    models_dir: str | Path,
    clean_data_dir: str | Path | None = None,
) -> SurvivalExplainer:
    """Factory to initialize a validated SurvivalExplainer."""
    models = load_trained_cox_models(models_dir)

    cal_results = {}
    if clean_data_dir is not None:
        c_dir = Path(clean_data_dir)
        tf_path = c_dir / "survival_train_features.csv"
        tt_path = c_dir / "survival_train_targets.csv"
        if tf_path.exists() and tt_path.exists():
            tf = pd.read_csv(tf_path)
            tt = pd.read_csv(tt_path)
            cal_results = evaluate_train_calibration(tf, tt, models)

    return SurvivalExplainer(models, cal_results)


def explain_snapshot(
    snapshot_row: pd.Series | dict[str, Any],
    models_dir: str | Path,
    clean_data_dir: str | Path | None = None,
) -> SnapshotExplanation:
    """Convenience function to explain a single snapshot."""
    explainer = load_survival_explainer(models_dir, clean_data_dir)
    return explainer.explain_snapshot(snapshot_row)


def generate_cohort_explanations(
    df: pd.DataFrame,
    models_dir: str | Path,
    clean_data_dir: str | Path | None = None,
) -> list[SnapshotExplanation]:
    """Convenience function to explain a cohort DataFrame."""
    explainer = load_survival_explainer(models_dir, clean_data_dir)
    return explainer.explain_dataframe(df)


def run_full_survival_explainability(
    clean_data_dir: str | Path,
    models_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Execute end-to-end survival explainability for both TRAIN and EVAL snapshots."""
    c_dir = Path(clean_data_dir)
    m_dir = Path(models_dir)
    o_dir = Path(output_dir)

    train_f = pd.read_csv(c_dir / "survival_train_features.csv")
    eval_f = pd.read_csv(c_dir / "survival_eval_features.csv")

    explainer = load_survival_explainer(m_dir, c_dir)

    train_explanations = explainer.explain_dataframe(train_f)
    eval_explanations = explainer.explain_dataframe(eval_f)

    # Save all explanations
    saved_paths = save_explanation_artifacts(
        explanations=list(train_explanations) + list(eval_explanations),
        output_dir=o_dir,
    )

    return {
        "status": "PASS — SURVIVAL EXPLAINABILITY COMPLETE",
        "saved_paths": saved_paths,
        "num_train_explanations": len(train_explanations),
        "num_eval_explanations": len(eval_explanations),
        "explainer": explainer,
    }
