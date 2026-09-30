"""Survival Model Explainability & Auditable Risk Reasons (LOOP 10).

Provides:
- Exact mathematical additive attribution for Cox Proportional Hazards models (beta_j * x_j).
- Rigorous non-causal association interpretations (INCREASED_HAZARD vs DECREASED_HAZARD).
- Human-readable decoding of categorical indicators and district/stage context.
- Point-in-time snapshot auditability and SHA256 model coefficient tracking.
- Strict role separation: OfficerExplanationView (full auditability) vs CitizenExplanationView (sanitized rights-centric view).
"""

from .survival_explainability import (
    CitizenExplanationView,
    ContributionDirection,
    FeatureContribution,
    MissingFeatureInfo,
    OfficerExplanationView,
    SnapshotExplanation,
    SurvivalExplainer,
    explain_snapshot,
    generate_cohort_explanations,
    load_survival_explainer,
    run_full_survival_explainability,
    save_explanation_artifacts,
)

__all__ = [
    "CitizenExplanationView",
    "ContributionDirection",
    "FeatureContribution",
    "MissingFeatureInfo",
    "OfficerExplanationView",
    "SnapshotExplanation",
    "SurvivalExplainer",
    "explain_snapshot",
    "generate_cohort_explanations",
    "load_survival_explainer",
    "run_full_survival_explainability",
    "save_explanation_artifacts",
]
