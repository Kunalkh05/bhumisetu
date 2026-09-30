# LOOP 9 — Survival Risk Calibration & Production Risk Layer Report

**Execution Phase**: LOOP 9 — Survival Risk Calibration & Production Risk Estimation  
**Evaluated Artifacts**: Pre-fitted Production Cox Proportional Hazards Models (`models/cox_baseline/`)  
**Calibration Engine**: `lifelines 0.30.3` & Case-Grouped K-Fold Cross-Validation  
**Environment**: Python 3.14.3 (macOS arm64)  
**Calibration Dataset**: `data/real_data/clean/survival_train_features.csv` & `survival_train_targets.csv` (**TRAIN ONLY**)  
**Holdout Dataset**: `data/real_data/clean/survival_eval_features.csv` & `survival_eval_targets.csv` (**EVAL ISOLATED / UNTOUCHED**)  
**Audit Date**: September 2026  
**Final Status**: `PARTIAL — CALIBRATION NOT RELIABLE DUE TO EVENT SPARSITY`

---

## 1. Objective

Following the successful out-of-sample evaluation in **LOOP 8**, **LOOP 9** investigates whether a statistically defensible survival risk calibration and production risk layer can be established for BHUMISETU while strictly upholding survival analysis semantics and data governance rules.

### Core Scientific Invariants
1. **Strict TRAIN-Only Calibration**: The EVAL cohort must remain a completely untouched final holdout. Zero calibration models, shrinkage parameters, or threshold selections were fitted or tuned using EVAL.
2. **Case-Level Dependence Control**: Snapshot records originating from the same land acquisition proceeding (`case_id`) must remain grouped together. Cross-validation folds must strictly preserve case boundaries to prevent intra-case information leakage.
3. **Rigorous Probability vs Hazard Semantics**:
   - The Cox partial hazard / relative risk score $\theta_i = \exp(\eta_i)$ is a unitless hazard ratio multiplier, **not a probability of delay**.
   - The predicted survival probability $S(t \mid x_i) = [S_0(t)]^{\exp(\eta_i)} \in [0.0, 1.0]$.
   - The cumulative incidence / event probability is defined as $P(\text{event by } t \mid x_i) = 1 - S(t \mid x_i) \in [0.0, 1.0]$.
4. **Principled Metric Gating**: If statistical event counts are insufficient to identify calibration parameters without overfitting, the system explicitly reports `CALIBRATION NOT RELIABLE — INSUFFICIENT EVENTS` rather than manufacturing unverified parameters.
5. **Decoupled Role Projections**:
   - **Officer Risk View**: Full analytical risk telemetry, horizon probabilities, calibration diagnostics, advisory quartiles, and statutory legal disclaimers.
   - **Citizen View**: Rights-oriented, plain-language milestone progress; strictly suppresses internal model coefficients, hazard scores, and internal administrative rankings.

---

## 2. Existing Cox Model Architecture

The pre-fitted baseline models from **LOOP 7C** represent three sequential statutory transitions under the RFCTLARR Act 2013:

1. **`SECTION_11_TO_SECTION_19`**:
   - **Covariates ($p=3$)**: `derived_days_in_current_stage`, `district_Solapur`, `derived_project_type_Rural Infrastructure`.
   - **Training Parameters**: Converged with $L_2$ ridge penalizer $\lambda = 0.01$. Baseline survival step-function $S_0(t)$ defined across 36 discrete event times (maximum follow-up: 945 days).
2. **`SECTION_19_TO_AWARD`**:
   - **Covariates ($p=8$)**: `derived_days_since_case_initiation`, `derived_days_in_current_stage`, `derived_notice_count`, `extension_count`, `has_statutory_extension`, `current_stage_SECTION_19`, `current_stage_SECTION_21`, `derived_project_type_Rural Infrastructure`.
   - **Training Parameters**: Converged with $\lambda = 0.01$. Baseline survival step-function $S_0(t)$ defined across 100 discrete event times (maximum follow-up: 1012 days).
3. **`CASE_INITIATION_TO_MILESTONE`**:
   - **Covariates ($p=14$)**: Encompasses stage indicators, district fixed effects, statutory notice frequency, direct purchase flags, and infrastructure project types.
   - **Training Parameters**: Converged with $\lambda = 0.01$. Baseline survival step-function $S_0(t)$ defined across 312 discrete event times (maximum follow-up: 2565 days).

All 10 original Loop 7C model files and Loop 8 evaluation files remain bit-identical before and after Loop 9 execution.

---

## 3. Calibration Methodologies Considered

Four standard survival calibration frameworks were investigated:

| Calibration Approach | Mathematical Formulation | Suitability for Administrative Cohort | Rejection / Adoption Reason |
| :--- | :--- | :--- | :--- |
| **Isotonic Regression on Survival Probabilities** | Non-parametric monotonic mapping $\hat{P}^* = \text{iso}(1 - \hat{S}(t))$ | **Unsuitable** | Assumes uncensored binary targets or horizon-specific pseudo-observations; severely overfits and collapses to step functions with $< 20$ events. |
| **Platt Scaling (Logistic on Pseudo-Obs)** | $\text{logit}(P) = \alpha + \beta \eta$ via Jackknife pseudo-values | **Unsuitable** | Pseudo-values require substantial sample size per cluster; extreme event sparsity in EVAL ($E=4$) and TRAIN ($E=40$) yields negative pseudo-values and numerical failure. |
| **Calibration-in-the-Large ($O/E$ Ratio)** | Ratio of total observed events to model cumulative expected hazard $\sum_i H_0(T_i) \exp(\eta_i)$ | **Evaluated** | Informative for baseline hazard scaling, but does not correct feature-specific discrimination slopes. |
| **Cox Recalibration (van Houwelingen / Royston-Altman)** | Univariate Cox model: $h(t) = h_0^*(t) \exp(\gamma \cdot \eta)$ where $\gamma$ is the calibration slope | **Selected for Evaluation** | Standard survival-analysis methodology that explicitly respects right-censoring without converting time-to-event outcomes into artificial binary classifications. |

---

## 4. Calibration Methodology Selected

The **Cox Recalibration** framework was adopted as the primary statistical probe:
- **Linear Predictor Evaluation**: For each snapshot $i$, compute $\eta_i = \sum_{j} \beta_j x_{ij}$ using frozen Loop 7C weights.
- **Univariate Recalibration Fit**: Fit a secondary Cox model:
  $$h_i(t) = h_0^*(t) \exp(\gamma \cdot \eta_i)$$
  where $\gamma$ is the calibration slope.
  - $\gamma = 1.0$: Perfect calibration slope (neither over-confident nor under-confident).
  - $\gamma < 1.0$: Over-fitting (predictions too extreme; requires shrinkage).
  - $\gamma > 1.0$: Under-fitting (predictions compressed).
- **Internal Validation**: Evaluated exclusively on TRAIN using 5-fold case-grouped cross-validation.

---

## 5. Why It Is Appropriate

1. **Survival Semantic Integrity**: Respects right-censoring durations ($T_i, E_i$) directly through partial likelihood, avoiding naive binarization.
2. **Leakage-Safe**: Does not require pseudo-observations computed across the entire cohort.
3. **Transparent Diagnostic**: Provides clear standard errors and p-values for $\gamma$, immediately exposing when event support is too weak to support recalibration.

---

## 6. TRAIN-Only Calibration Procedure

The calibration audit was performed strictly within the TRAIN cohort:
1. Load `survival_train_features.csv` (896 rows) and `survival_train_targets.csv` (896 rows).
2. Align design matrix $X_{\text{train}}$ to frozen model schemas.
3. Compute frozen linear predictor vector $\eta_{\text{train}}$.
4. Execute case-grouped 5-fold cross-validation.
5. Compute overall calibration slope and horizon-specific Kaplan-Meier calibration differences $\bar{S}(t) - S_{\text{KM}}(t)$.
6. Gate recalibration: if cross-validation reveals high fold variance or zero-event folds, retain uncalibrated baseline and report limitations.

---

## 7. Case-Level Validation Strategy

A primary vulnerability in temporal snapshot datasets is that multiple snapshots (e.g., $T=0, 90, 180$) originate from the same land acquisition proceeding (`case_id`).
- **Standard Random K-Fold**: Splitting snapshots randomly leaks case-level identity across folds, generating spuriously narrow confidence intervals and misleadingly optimistic calibration.
- **Implemented GroupKFold**: Folds were constructed strictly by partitioning the 159 unique `case_id`s in TRAIN into 5 non-overlapping subsets. All snapshots for any given proceeding were confined to exactly one fold.

---

## 8. Transition-Specific Event Counts in TRAIN

| Transition | Total Snapshots ($N$) | Unique Cases | Observed Events ($E$) | Censoring Rate | Unique Cases with Events |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `SECTION_11_TO_SECTION_19` | 84 | 32 | 16 | 80.95% | 14 |
| `SECTION_19_TO_AWARD` | 203 | 43 | **6** | 97.04% | **1** (`CAS_CLEAN_070`) |
| `CASE_INITIATION_TO_MILESTONE` | 609 | 131 | 18 | 97.04% | 15 |
| **Total TRAIN Cohort** | **896** | **159** | **40** | **95.54%** | **29** |

---

## 9. Calibration Results & Diagnostics

### A. Case-Grouped Cross-Validation Slopes ($\gamma_{\text{CV}}$)

| Transition | Overall Slope $\gamma$ | SE | $p$-value | CV Folds with Events | CV Slopes across Folds | Mean CV Slope | CV Slope Std | Calibration Assessment |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `SECTION_11_TO_SECTION_19` | 1.4431 | 0.3143 | $4.4 \times 10^{-6}$ | 5 / 5 | [2.68, 2.45, 1.03, 0.84, 3.22] | 2.0444 | **0.9420** | **High Variance / Unstable**. 4x swing in fold slopes precludes stable secondary shrinkage. |
| `SECTION_19_TO_AWARD` | 1.3531 | 0.3195 | $2.3 \times 10^{-5}$ | **1 / 5** | [None, 1.18, None, None, None] | 1.1798 | **None** | **Degenerate**. All 6 events are in 1 case; 4 of 5 validation folds have 0 events. |
| `CASE_INITIATION_TO_MILESTONE` | 1.9513 | 0.2743 | $< 10^{-12}$ | 5 / 5 | [1.61, 2.27, 2.83, 2.13, 1.54] | 2.0762 | **0.4718** | **High Censoring / Sparse**. Slope $> 1$ indicates compressed linear predictor; sample size too small for refitting. |

### B. Horizon-Specific Calibration Differences ($\bar{S}(t) - S_{\text{KM}}(t)$) on TRAIN

| Horizon | `SECTION_11_TO_SECTION_19` | `SECTION_19_TO_AWARD` | `CASE_INITIATION_TO_MILESTONE` |
| :---: | :---: | :---: | :---: |
| **30 Days** | $+0.0110$ (Pred: 0.999, KM: 0.988) | $+0.0018$ (Pred: 0.997, KM: 0.995) | $+0.0011$ (Pred: 0.999, KM: 0.998) |
| **90 Days** | $+0.1558$ (Pred: 0.986, KM: 0.830) | $+0.0018$ (Pred: 0.997, KM: 0.995) | $+0.0163$ (Pred: 0.991, KM: 0.975) |
| **180 Days** | $+0.1669$ (Pred: 0.985, KM: 0.818) | $+0.0038$ (Pred: 0.993, KM: 0.989) | $+0.0184$ (Pred: 0.989, KM: 0.971) |
| **365 Days** | $+0.1797$ (Pred: 0.983, KM: 0.803) | $+0.0098$ (Pred: 0.973, KM: 0.964) | $+0.0196$ (Pred: 0.989, KM: 0.969) |
| **730 Days** | $+0.1797$ (Pred: 0.983, KM: 0.803) | $+0.0147$ (Pred: 0.965, KM: 0.950) | $+0.0196$ (Pred: 0.989, KM: 0.969) |

---

## 10. Uncertainty Analysis

1. **Asymptotic Standard Errors**: For `SECTION_11_TO_SECTION_19` ($\text{SE} = 0.31$) and `CASE_INITIATION_TO_MILESTONE` ($\text{SE} = 0.27$), calibration slopes are nominally significant. However, case-grouped bootstrap iterations reveal that resampling clusters creates zero-event folds in up to 35% of resamples.
2. **Single-Cluster Failure**: In `SECTION_19_TO_AWARD`, cluster-level uncertainty cannot be computed because resampling cases omits `CAS_CLEAN_070` in $(1 - 1/43)^{43} \approx 36.4\%$ of bootstrap draws, reducing total observed events to zero.
3. **Assigned Uncertainty Status**:
   - `SECTION_19_TO_AWARD`: `EXTREME_UNCERTAINTY_ZERO_EVENTS`
   - `SECTION_11_TO_SECTION_19` & `CASE_INITIATION_TO_MILESTONE`: `HIGH_UNCERTAINTY_SPARSE_EVENTS`

---

## 11. Production Risk-Output Contract

The production risk prediction engine (`ProductionRiskLayer`) exposes the following structured schema for each snapshot:

```json
{
  "case_id": "CAS_CLEAN_001",
  "snapshot_id": "SNP_CAS_CLEAN_001_SECTION_11_2024-01-01",
  "snapshot_date": "2024-01-01",
  "transition": "SECTION_11_TO_SECTION_19",
  "model_version": "1.0.0-cox-production-baseline",
  "linear_predictor": -0.405621,
  "relative_hazard": 0.666562,
  "survival_probability_30d": 0.994195,
  "survival_probability_90d": 0.903821,
  "survival_probability_180d": 0.893641,
  "survival_probability_365d": 0.893641,
  "survival_probability_730d": 0.893641,
  "event_probability_30d": 0.005805,
  "event_probability_90d": 0.096179,
  "event_probability_180d": 0.106359,
  "event_probability_365d": 0.106359,
  "event_probability_730d": 0.106359,
  "calibration_status": "PARTIAL — CALIBRATION NOT RELIABLE DUE TO EVENT SPARSITY",
  "uncertainty_status": "HIGH_UNCERTAINTY_SPARSE_EVENTS",
  "data_quality_warning": "HIGH UNCERTAINTY: Estimates derived from sparse administrative milestone occurrences.",
  "risk_band_90d": "ADVISORY_MEDIAN_RELATIVE_HAZARD",
  "extrapolation_flags": {
    "30d": false,
    "90d": false,
    "180d": true,
    "365d": true,
    "730d": true
  }
}
```

---

## 12. Risk-Band Methodology

Arbitrary probability band boundaries (e.g. naive $< 0.33$, $0.33-0.66$, $> 0.66$) were strictly rejected because they fail to correspond to empirical administrative realities.
- **Implemented Methodology**: Advisory bands are established strictly using **TRAIN-only empirical percentiles** of the 90-day event probability distribution:
  - `ADVISORY_LOWER_RELATIVE_HAZARD`: $P(\text{event by 90d}) \le P_{25}(\text{TRAIN})$
  - `ADVISORY_MEDIAN_RELATIVE_HAZARD`: $P_{25} < P(\text{event by 90d}) \le P_{75}(\text{TRAIN})$
  - `ADVISORY_ELEVATED_RELATIVE_HAZARD`: $P_{75} < P(\text{event by 90d}) \le P_{90}(\text{TRAIN})$
  - `ADVISORY_HIGHEST_DECILE_HAZARD`: $P(\text{event by 90d}) > P_{90}(\text{TRAIN})$
- **Advisory Flag**: The system explicitly documents that these bands represent relative ranking within historical Maharashtra proceedings, not calibrated absolute risk guarantees.

---

## 13. EVAL Isolation Verification

- **Zero EVAL Data in Calibration**: Confirmed by adversarial test `test_eval_never_enters_calibration_fitting`. The set of case IDs in calibration fitting and the set of case IDs in EVAL are strictly disjoint.
- **Zero EVAL Targets in Calibration**: Confirmed by `test_eval_outcomes_never_enter_calibration_fitting`. Total training events ($E=40$) exactly equals historical training event sums.
- **Frozen Holdout Predictions**: Predictions on the EVAL holdout ([`models/cox_baseline/production_risk_predictions_eval.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/models/cox_baseline/production_risk_predictions_eval.csv)) were generated strictly after all calibration diagnostics and cutoffs were locked.

---

## 14. Governance & Role Separation

### A. Officer Portal Presentation (`OfficerRiskView`)
Authorized revenue officers receive full analytical insight:
- Individual relative hazard score $\exp(\eta)$.
- Multi-horizon event and survival probabilities ($30, 90, 180, 365, 730$ days).
- Calibration diagnostics and data quality alerts.
- Extrapolation warning flags for horizons exceeding the 148-day holdout follow-up window.
- Mandatory statutory governance disclaimer.

### B. Citizen Portal Presentation (`CitizenRiskView`)
In compliance with DPDPA 2023 and administrative transparency:
- **Strictly Suppressed**:
  - `relative_hazard`
  - `linear_predictor`
  - Internal model coefficients ($\beta$)
  - Internal case-ranking percentiles / risk bands
  - Sensitive administrative analytics
- **Exposed to Citizen**:
  - Current stage and plain-language milestone description.
  - Statutory RFCTLARR time limit (e.g. 365 days for Section 19 declaration).
  - Elapsed days in current stage.
  - Plain-language summary of citizen rights (filing objections under Section 15, entitlement to solatium and R&R benefits).

### C. Safety & Non-Autonomous Decision Invariant
The platform communicates through code and UI:
> *Model estimates are decision-support signals only. Under no circumstances does the system automate approval/rejection of land acquisitions, compute final legal compensation awards, or make legally binding administrative determinations.*

---

## 15. Critical Transition Limitation: Section 19 $\to$ Award

- **TRAIN Reality**: Only 6 events occurred across 203 observations (97.04% censored). Crucially, **all 6 events originate from a single case (`CAS_CLEAN_070`)**.
- **EVAL Reality**: 0 events occurred across 4 observations (100% censored).
- **Statistical Consequence**: Fitting a secondary calibration slope or recalibrating the baseline hazard is scientifically invalid because cross-validation cannot partition a single event-bearing cluster.
- **Gated Status**: `CALIBRATION NOT RELIABLE — INSUFFICIENT EVENTS`.

---

## 16. Heavy Censoring Limitations

1. **95.5% Censoring in TRAIN, 97.6% Censoring in EVAL**: The overwhelming majority of proceedings in the administrative dataset are administratively ongoing.
2. **Horizon Extrapolation**: The empirical follow-up window in the EVAL holdout ceases at 148 days. Predictions for 180d, 365d, and 730d cannot be claimed as validated against out-of-sample holdout data.

---

## 17. Adversarial Test Results

- **Test Suite**: [`bhumi-setu/apps/api/tests/ml/test_survival_calibration.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/apps/api/tests/ml/test_survival_calibration.py)
- **Tests Executed**: 18 adversarial tests covering all architectural invariants:
  1. `test_eval_never_enters_calibration_fitting`: Passed.
  2. `test_eval_outcomes_never_enter_calibration_fitting`: Passed.
  3. `test_case_level_separation_during_internal_calibration`: Passed.
  4. `test_no_future_information`: Passed.
  5. `test_no_purged_features`: Passed.
  6. `test_transition_isolation`: Passed.
  7. `test_correct_survival_probability_calculation`: Passed.
  8. `test_event_probability_equals_one_minus_survival`: Passed.
  9. `test_probability_bounds`: Passed.
  10. `test_deterministic_predictions`: Passed.
  11. `test_artifact_save_load`: Passed.
  12. `test_calibration_artifact_integrity`: Passed.
  13. `test_model_version_tracking`: Passed.
  14. `test_unsupported_horizons_handled_safely`: Passed.
  15. `test_insufficient_event_transitions_handled_explicitly`: Passed.
  16. `test_no_arbitrary_risk_bands`: Passed.
  17. `test_uncertainty_flags_work`: Passed.
  18. `test_citizen_output_does_not_expose_internal_ml_fields`: Passed.
- **ML Suite Overall**: **181 / 181 tests passed in 4.81s** (0 failures, 0 regressions).

---

## 18. Final Status

$$\mathbf{PARTIAL\ —\ CALIBRATION\ NOT\ RELIABLE\ DUE\ TO\ EVENT\ SPARSITY}$$

### Candid Scientific Conclusion
The production risk layer functions with complete software correctness, mathematical rigor, and strict role-based data governance. However, because target transition events are sparse (only 40 observed events across 896 training snapshots, with Section 19 $\to$ Award concentrated in a single proceeding), parametric recalibration cannot be reliably fitted without inflating model variance. 

In accordance with scientific rules, the uncalibrated Cox survival estimates are retained as the baseline, and the status is accurately reported as **PARTIAL — CALIBRATION NOT RELIABLE DUE TO EVENT SPARSITY**.
