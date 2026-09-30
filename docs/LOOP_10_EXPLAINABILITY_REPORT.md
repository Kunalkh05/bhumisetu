# LOOP 10 — Survival Model Explainability & Auditable Risk Reasons Report

**Execution Phase**: LOOP 10 — Explainability and Auditable Risk Reasons  
**Evaluated Artifacts**: Pre-fitted Production Cox Proportional Hazards Baseline Models (`models/cox_baseline/`)  
**Explainability Engine**: Exact Additive Linear Decomposition ($\beta_j \cdot x_j$) & Non-Causal Associative Attribution  
**Environment**: Python 3.14.3 (macOS arm64)  
**Input Data**: `data/real_data/clean/survival_train_features.csv` (896 snapshots) & `survival_eval_features.csv` (167 snapshots)  
**Audit Date**: September 2026  
**Final Status**: `PASS — SURVIVAL EXPLAINABILITY COMPLETE`  
*(Operating with explicit statistical event-sparsity caveats documented in Loops 8 & 9)*

---

## 1. Objective

The primary objective of **LOOP 10** is to provide rigorous, point-in-time, auditable explanations of **why** the BHUMISETU Cox Proportional Hazards baseline models produced a particular relative-hazard multiplier and event-probability estimate for any given proceeding snapshot.

### Non-Negotiable Governance Invariants
1. **Zero Retraining or Parameter Modification**: The underlying Cox models fitted in Loop 7C were not retrained, tuned, or replaced.
2. **Zero Outcome Leakage**: Explanations were generated strictly using feature matrices without any reference to survival event targets ($E$) or durations ($T$), preserving complete EVAL isolation.
3. **Strict Associative Phrasing**: Model attributions describe **statistical model associations**, never causality. The engine strictly suppresses causal phrases such as *"caused the delay"* or *"caused the acquisition to progress"*.
4. **Transparent Categorical Mapping**: One-hot encoded indicators (e.g. `current_stage_SECTION_11`, `district_Solapur`) are decoded into clear, human-understandable administrative interpretations.
5. **Decoupled Role Projections**:
   - **Officer View**: Exhaustive analytical telemetry, exact log-hazard contributions, hazard multipliers, missing-data tracking, uncertainty flags, and legal governance disclaimers.
   - **Citizen View**: Plain-language, rights-centric status tracking under RFCTLARR 2013; strictly strips internal model coefficients, hazard scores, and case ranking logic.

---

## 2. Cox Explainability Methodology

Unlike opaque tree ensembles or deep neural networks that require sampling-based heuristic approximations (such as Perturbation or KernelSHAP), the Cox Proportional Hazards model possesses **exact analytical interpretability**.

The hazard function for an individual with covariate vector $x_i = (x_{i1}, \dots, x_{ip})$ is:
$$h(t \mid x_i) = h_0(t) \exp(\eta_i)$$

Where $\eta_i$ is the linear predictor (log-hazard ratio relative to baseline):
$$\eta_i = \sum_{j=1}^p \beta_j x_{ij}$$

And the relative hazard (hazard ratio) is:
$$\text{HR}_i = \exp(\eta_i) = \prod_{j=1}^p \exp(\beta_j x_{ij})$$

Because the log-hazard is strictly linear in the coefficients:
- The individual additive contribution of feature $j$ is **identically equal to $\beta_j x_{ij}$**.
- This formulation represents the exact Shapley value attribution for linear models on the log-hazard scale, eliminating estimation variance, monte carlo sampling noise, and computational overhead.

---

## 3. Mathematical Formulation & Invariant Proofs

For each proceeding snapshot $i$ and feature $j \in \{1, \dots, p\}$:

1. **Feature Contribution (Log-Hazard Scale)**:
   $$\text{contribution}_{ij} = \beta_j \cdot x_{ij}$$
2. **Feature Hazard Multiplier (Multiplicative Scale)**:
   $$\text{hazard\_multiplier}_{ij} = \exp(\text{contribution}_{ij}) = \exp(\beta_j \cdot x_{ij})$$
3. **Additive Invariant**:
   $$\sum_{j=1}^p \text{contribution}_{ij} = \eta_i \quad (\text{tolerance } < 10^{-5})$$
4. **Multiplicative Invariant**:
   $$\prod_{j=1}^p \text{hazard\_multiplier}_{ij} = \exp(\eta_i) = \text{relative\_hazard}_i \quad (\text{tolerance } < 10^{-4})$$
5. **Survival and Event Probabilities**:
   $$S_i(t \mid x_i) = \left[ S_0(t) \right]^{\exp(\eta_i)}, \quad P_i(\text{event by } t \mid x_i) = 1 - S_i(t \mid x_i)$$

These mathematical identities were verified across all 1,063 historical snapshots (896 TRAIN + 167 EVAL).

---

## 4. Feature Contribution Methodology

To produce auditable explanations:
1. **Raw Value Ingestion**: Capture the raw feature value (numerical duration, count, or categorical string).
2. **Transformed Value Alignment**: Map the raw value into the design matrix representation $x_{ij} \in \mathbb{R}$.
3. **Exact Linear Product**: Multiply by the frozen model weight $\beta_j$.
4. **Multiplier Calculation**: Compute $\exp(\beta_j x_{ij})$.
5. **Human Translation**: Attach descriptive labels and explanatory narratives.

---

## 5. Positive and Negative Contribution Interpretation

To avoid misleading government officers, contributions are strictly categorized by direction:

| Direction Category | Mathematical Criterion | Hazard Multiplier | Mandatory Non-Causal Interpretation |
| :--- | :---: | :---: | :--- |
| **`INCREASED_HAZARD`** | $\beta_j x_{ij} > 0$ | $> 1.0$ | Feature contributed positively to the model's estimated hazard relative to baseline. |
| **`DECREASED_HAZARD`** | $\beta_j x_{ij} < 0$ | $< 1.0$ | Feature contributed negatively to the model's estimated hazard relative to baseline. |
| **`NEUTRAL_BASELINE`** | $\beta_j x_{ij} = 0$ | $= 1.0$ | Feature is at reference baseline level; zero contribution to estimated log-hazard. |

### Top Contributors Selection
For each snapshot, features are ranked by $|\text{contribution}|$:
- **Top 5 Positive Contributors**: Ranked highest positive $\beta_j x_{ij}$ first.
- **Top 5 Negative Contributors**: Ranked most negative $\beta_j x_{ij}$ first.

---

## 6. Categorical Feature Handling

One-hot encoded categorical dummies are automatically resolved into contextualized interpretations:

| Model Feature Column | One-Hot Encoding | Human-Readable Name | Decoded Interpretation Narrative |
| :--- | :---: | :--- | :--- |
| `current_stage_SECTION_11` | $x=1$ | Stage: Section 11 Notification | Formal Section 11 preliminary notification published in gazette. |
| `current_stage_SECTION_19` | $x=1$ | Stage: Section 19 Declaration | Formal Section 19 declaration of public purpose published. |
| `current_stage_SECTION_21` | $x=1$ | Stage: Section 21 Notice | Section 21 public notice for claims and inquiry issued. |
| `district_Solapur` | $x=1$ | District: Solapur | Land parcel is situated in Solapur revenue district. |
| `district_Yavatmal` | $x=1$ | District: Yavatmal | Land parcel is situated in Yavatmal revenue district. |
| `derived_project_type_Rural Infrastructure` | $x=1$ | Project Type: Rural Infrastructure | Acquisition is for rural roads, connectivity, or village infrastructure. |
| `derived_project_type_Irrigation / Canal` | $x=1$ | Project Type: Irrigation / Canal | Acquisition is for water resources, canal, or irrigation infrastructure. |
| `act_key_RFCTLARR_2013` | $x=1$ | Statutory Act: RFCTLARR 2013 | Governed by the Right to Fair Compensation Act 2013. |

---

## 7. Missing-Data Handling & Tracking

The BHUMISETU pipeline never silently drops missing values or assumes missing data is equivalent to zero without notification:
- **`MissingFeatureInfo`**: Tracks any predictor column where raw values were null or structurally missing.
- **Logged Properties**:
  - `feature_name`: Column identifier.
  - `human_readable_name`: Plain-language label.
  - `was_missing`: Boolean flag (`True`).
  - `imputation_applied`: Explicit disclosure (`zero_or_baseline_imputation`).
  - `imputed_value`: Value passed to model design matrix ($0.0$).

---

## 8. Point-in-Time Reproducibility & Auditability

Every explanation object (`SnapshotExplanation`) captures a cryptographic audit trail:
- **`case_id`**: Land acquisition proceeding identifier.
- **`snapshot_id`**: Point-in-time snapshot key.
- **`snapshot_date`**: Chronological date of observation.
- **`transition`**: Specific statutory milestone transition.
- **`model_version`**: `1.0.0-cox-production-baseline`.
- **`feature_version`**: `1.0.0-survival-clean-15feat`.
- **`model_checksum`**: 16-character SHA256 hash of sorted model coefficients:
  - `SECTION_11_TO_SECTION_19`: `d253f57aa18dcb20`
  - `SECTION_19_TO_AWARD`: `2493aa920caf664a`
  - `CASE_INITIATION_TO_MILESTONE`: `8dfb6510e4708ff1`
- **`prediction_timestamp`**: ISO-8601 UTC timestamp of explanation generation.

---

## 9. Officer Explanation Contract (`OfficerExplanationView`)

Authorized revenue officers receive full analytical transparency:
```json
{
  "case_id": "CAS_CLEAN_271",
  "snapshot_date": "20190921",
  "transition": "CASE_INITIATION_TO_MILESTONE",
  "model_version": "1.0.0-cox-production-baseline",
  "relative_hazard": 0.395089,
  "linear_predictor": -0.928645,
  "summary_narrative": "The model estimated a relative hazard of 0.40x relative to baseline (linear predictor: -0.9286). This estimate is mathematically driven by 1 positive feature associations and 4 negative feature associations. This reflects statistical model correlation, not causal delay.",
  "why_hazard_is_higher": [
    {
      "feature": "act_key_RFCTLARR_2013",
      "label": "Statutory Act: RFCTLARR 2013",
      "value": 1.0,
      "contribution": 0.200499,
      "hazard_multiplier": 1.222012,
      "narrative": "Statutory Act: RFCTLARR 2013 contributed +0.2005 to the model's estimated log-hazard (hazard multiplier: 1.222x relative to baseline)."
    }
  ],
  "why_hazard_is_lower": [
    {
      "feature": "current_stage_GENERAL_NOTICE",
      "label": "Stage: Preliminary Notification",
      "value": 1.0,
      "contribution": -0.455803,
      "hazard_multiplier": 0.633939,
      "narrative": "Stage: Preliminary Notification contributed -0.4558 to the model's estimated log-hazard (hazard multiplier: 0.634x relative to baseline)."
    },
    {
      "feature": "derived_notice_count",
      "label": "Statutory Notice Publications",
      "value": 1.0,
      "contribution": -0.290293,
      "hazard_multiplier": 0.748044,
      "narrative": "Statutory Notice Publications contributed -0.2903 to the model's estimated log-hazard (hazard multiplier: 0.748x relative to baseline)."
    }
  ],
  "uncertainty_status": "HIGH_UNCERTAINTY_SPARSE_EVENTS",
  "calibration_status": "PARTIAL — CALIBRATION NOT RELIABLE DUE TO EVENT SPARSITY",
  "extrapolation_status": {
    "30d": false,
    "90d": false,
    "180d": true,
    "365d": true,
    "730d": true
  },
  "data_quality_warning": "HIGH UNCERTAINTY: Estimates derived from sparse administrative milestone occurrences.",
  "governance_disclaimer": "NON_AUTONOMOUS_DECISION_SUPPORT: Model estimates are advisory statistical indicators intended exclusively for administrative workload prioritization..."
}
```

---

## 10. Citizen Explanation Contract (`CitizenExplanationView`)

In compliance with the Digital Personal Data Protection Act (DPDPA) 2023 and natural justice principles:
- **Strictly Suppressed Fields**:
  - `relative_hazard`
  - `linear_predictor`
  - `internal_model_coefficients`
  - `internal_hazard_scores`
  - `government_risk_classifications`
  - `internal_case_ranking_logic`
  - `sensitive_administrative_analytics`
- **Exposed Plain-Language Fields**:
  - `case_id`: Proceeding identifier.
  - `current_stage`: Current procedural stage (e.g. `SECTION_11`).
  - `milestone_name`: Next statutory milestone (e.g. `Section 19 Declaration`).
  - `statutory_time_limit_days`: Formal legal deadline under RFCTLARR 2013 (e.g. 365 days).
  - `days_in_current_stage`: Elapsed duration in days.
  - `proceedings_status`: Administrative status (`IN_PROGRESS`).
  - `statutory_rights_summary`: Guidance on rights to file claims and objections (Sec 15) and receive rehabilitation entitlements.
  - `citizen_procedural_explanation`: Plain-language explanation of stage progress and statutory time limits.

---

## 11. Uncertainty & Extrapolation Handling

Explanations rigorously integrate the uncertainty states established in Loops 8 & 9:
1. **`HIGH_UNCERTAINTY_SPARSE_EVENTS`**: Attached to all explanations for `SECTION_11_TO_SECTION_19` and `CASE_INITIATION_TO_MILESTONE`, reminding officers that estimates are derived from sparse administrative milestone occurrences.
2. **`EXTREME_UNCERTAINTY_ZERO_EVENTS`**: Attached to `SECTION_19_TO_AWARD`, disclosing that zero target events were observed in out-of-sample holdout data.
3. **`extrapolation_status`**: Explicitly flags horizons beyond the 148-day holdout follow-up window (`180d`, `365d`, `730d`).

---

## 12. Non-Causal Explanation Guarantee

An automated AST and string scan across all generated narratives confirms:
- Zero occurrences of banned causal terms (`caused`, `causation`, `responsible for delay`, `caused the delay`, `caused progress`).
- Every narrative describes model associations:
  > *"Feature X contributed +Y.YYYY to the model's estimated log-hazard (hazard multiplier: Z.ZZZx relative to baseline)."*

---

## 13. Critical Limitations

1. **Model Association, Not Causation**: Feature contributions reflect linear partial correlation within historical administrative records. They do not demonstrate that altering a feature will causally alter proceeding duration.
2. **Small-Event Coefficient Instability**: With only 40 observed events across 896 training snapshots, individual coefficient estimates have wider confidence intervals than large-scale clinical survival datasets.
3. **Section 19 $\to$ Award Single-Case Cluster**: All 6 training events belong to `CAS_CLEAN_070`. Explanations for this transition reflect the historical characteristics of that single proceeding.
4. **Evaluation Holdout Ceiling**: The 148-day follow-up limit in the EVAL holdout prevents empirical out-of-sample verification of 1-year and 2-year statutory horizon contributions.

---

## 14. Adversarial Test Results

- **Test Suite**: [`bhumi-setu/apps/api/tests/ml/test_survival_explainability.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/apps/api/tests/ml/test_survival_explainability.py)
- **Tests Executed**: 18 adversarial tests covering all mathematical, data integrity, and privacy requirements:
  1. `test_sum_of_feature_contributions_equals_linear_predictor`: Passed ($\Delta < 10^{-6}$).
  2. `test_exp_linear_predictor_equals_relative_hazard`: Passed ($\Delta < 10^{-5}$).
  3. `test_no_future_features_used`: Passed (purged features raise ValueError).
  4. `test_no_eval_outcomes_used`: Passed (explanations operate strictly without targets).
  5. `test_explanation_uses_exact_snapshot_features`: Passed.
  6. `test_missing_values_handled_consistently`: Passed.
  7. `test_categorical_explanations_map_correctly`: Passed.
  8. `test_positive_contribution_classified_correctly`: Passed.
  9. `test_negative_contribution_classified_correctly`: Passed.
  10. `test_top_contributors_deterministic`: Passed.
  11. `test_artifact_save_load_preserves_explanations`: Passed.
  12. `test_model_hash_and_version_preserved`: Passed.
  13. `test_transition_isolation`: Passed.
  14. `test_citizen_projection_strips_internal_ml_fields`: Passed.
  15. `test_officer_projection_retains_permitted_analytical_fields`: Passed.
  16. `test_uncertainty_warnings_preserved`: Passed.
  17. `test_extrapolation_warnings_preserved`: Passed.
  18. `test_no_causal_language_in_explanation_engine`: Passed.
- **ML Suite Overall**: **199 / 199 tests passed in 5.04s** (0 failures, 0 regressions).

---

## 15. Generated Explanation Artifacts

| Artifact File | Size | Description |
| :--- | :---: | :--- |
| [`models/cox_baseline/survival_explanations.json`](file:///Users/sakshantwaghmare/Projects/bhumisetu/models/cox_baseline/survival_explanations.json) | 9.3 MB | Full audit-ready JSON containing complete mathematical decompositions for all 1,063 snapshots. |
| [`models/cox_baseline/survival_explanations.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/models/cox_baseline/survival_explanations.csv) | 533 KB | Flattened tabular export with top contributors and uncertainty statuses for database ingestion. |
| [`bhumi-setu/ml/src/explainability/survival_explainability.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/ml/src/explainability/survival_explainability.py) | 26 KB | Core explainability engine, `SurvivalExplainer`, and role projection functions. |
| [`bhumi-setu/apps/api/tests/ml/test_survival_explainability.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/apps/api/tests/ml/test_survival_explainability.py) | 12 KB | 18 automated adversarial integrity tests. |

---

## 16. Final Status

$$\mathbf{PASS\ —\ SURVIVAL\ EXPLAINABILITY\ COMPLETE}$$

### Candid Conclusion
The explainability engine fulfills all mathematical, software, and governance requirements with complete transparency. Every Cox relative-hazard estimate is fully decomposed into its exact linear components ($\beta_j x_j$), categorical features are mapped to administrative terms, causal language is strictly eliminated, and citizen views are protected against internal ML data leakage.
