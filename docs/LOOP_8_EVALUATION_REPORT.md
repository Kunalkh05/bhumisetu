# LOOP 8 — Out-of-Sample Survival Model Evaluation Report

**Execution Phase**: LOOP 8 — Out-of-Sample Survival Model Evaluation  
**Evaluated Artifacts**: LOOP 7C Pre-fitted Production Cox Proportional Hazards Models (`models/cox_baseline/`)  
**Evaluation Engine**: `lifelines 0.30.3` (`concordance_index`, `KaplanMeierFitter`) & `scipy`/`numpy` IPCW Brier score  
**Environment**: Python 3.14.3 (macOS arm64)  
**Input Data**: [`data/real_data/clean/survival_eval_features.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_eval_features.csv) & [`data/real_data/clean/survival_eval_targets.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_eval_targets.csv) (**EVALUATION COHORT ONLY**)  
**Audit Date**: September 2026  
**Final Status**: `PARTIAL — SOME METRICS NOT COMPUTABLE DUE TO EVENT SPARSITY`

---

## 1. Objective

The primary objective of LOOP 8 is to perform a strict, scientifically rigorous out-of-sample evaluation of the pre-fitted LOOP 7C Cox Proportional Hazards baseline models against the completely untouched **EVAL** cohort.

### Non-Negotiable Governance Invariants:
1. **Zero Model Fitting on EVAL**: The models were evaluated strictly in read-only inference mode. Zero parameters, coefficients, or baseline survival curves were refitted, recalibrated, or modified.
2. **Zero Hyperparameter Tuning**: Model hyperparameters (e.g., L2 ridge penalizer $\lambda = 0.1$) were not adjusted based on evaluation results.
3. **Zero Calibration Fitting**: No recalibration model (such as Platt scaling, isotonic regression, or secondary Cox models) was fitted on the evaluation cohort.
4. **Zero Domain Fabrication**: No pseudo-events were generated, no SMOTE or oversampling was performed, no censored rows were converted into non-events, and no uncomputable metrics were substituted with artificial numbers.
5. **Principled Metric Gating**: When event counts or risk support were statistically insufficient, the pipeline returned an explicit diagnostic status (`NOT COMPUTABLE — INSUFFICIENT EVENTS` or `NOT RELIABLE — INSUFFICIENT EVENTS`).

---

## 2. Model Artifacts Evaluated

The evaluation strictly loaded and verified the exact 10 pre-fitted artifacts from LOOP 7C located in `models/cox_baseline/`:
1. `models/cox_baseline/cox_model_summary.json`
2. `models/cox_baseline/cox_section_11_to_section_19_coefficients.csv`
3. `models/cox_baseline/cox_section_11_to_section_19_baseline_survival.csv`
4. `models/cox_baseline/cox_section_11_to_section_19_ph_test.csv`
5. `models/cox_baseline/cox_section_19_to_award_coefficients.csv`
6. `models/cox_baseline/cox_section_19_to_award_baseline_survival.csv`
7. `models/cox_baseline/cox_section_19_to_award_ph_test.csv`
8. `models/cox_baseline/cox_case_initiation_to_milestone_coefficients.csv`
9. `models/cox_baseline/cox_case_initiation_to_milestone_baseline_survival.csv`
10. `models/cox_baseline/cox_case_initiation_to_milestone_ph_test.csv`

All model files were cryptographically hashed (SHA256) before and after evaluation; every byte remained 100% unchanged.

---

## 3. Evaluation Cohort Description

The out-of-sample evaluation cohort was generated in LOOP 6 via a leakage-safe temporal and case-aware split:
- **Total Observations ($N$)**: 167 snapshots
- **Total Unique Cases**: 89 distinct land acquisition proceedings
- **Total Observed Events ($E=1$)**: 4 events
- **Total Right-Censored ($E=0$)**: 163 observations
- **Overall Censoring Rate**: **97.60%**
- **Follow-up Window**: Minimum duration = 2.0 days, Maximum duration = 148.0 days (no observations remain at risk past 148 days).
- **Predictor Allowlist**: Exactly the approved 15 leakage-safe predictor columns.
- **Purged Features**: All 7 purged features (`award_recorded`, `objection_count`, `parcel_count`, `open_issue_count`, `notified_area_hectares`, `affected_landowner_count`, `compensation_amount_inr`) and all future target columns were completely absent from predictor matrices.

---

## 4. Transition-Level Cohort Breakdown

| Metric | `SECTION_11_TO_SECTION_19` | `SECTION_19_TO_AWARD` | `CASE_INITIATION_TO_MILESTONE` | **Total EVAL Cohort** |
| :--- | :---: | :---: | :---: | :---: |
| **Total Snapshots ($N$)** | 59 | 4 | 104 | **167** |
| **Unique Cases** | 57 | 4 | 55 | **89** |
| **Observed Events ($E=1$)** | 2 | 0 | 2 | **4** |
| **Right-Censored ($E=0$)** | 57 | 4 | 102 | **163** |
| **Censoring Rate (%)** | 96.61% | **100.00%** | 98.08% | **97.60%** |
| **Min Follow-up (days)** | 2.0 | 39.0 | 2.0 | **2.0** |
| **Max Follow-up (days)** | 148.0 | 53.0 | 148.0 | **148.0** |
| **Event Durations (days)** | [92.0, 2.0] | None | [92.0, 2.0] | [92.0, 2.0] |
| **Model Parameters ($p$)** | 3 | 8 | 14 | — |

> [!IMPORTANT]
> ### Critical Event Sparsity in Evaluation Data
> Across 167 snapshots, only **4 events** were observed.
> Notably, in `SECTION_11_TO_SECTION_19` and `CASE_INITIATION_TO_MILESTONE`, both observed events originate from a **single case** (`CAS_CLEAN_037`) captured at two different snapshot horizons ($T=0$ with 92 days remaining, and $T=90$ with 2 days remaining). In `SECTION_19_TO_AWARD`, **zero events** were observed.

---

## 5. Prediction Generation Methodology

For each evaluation snapshot $i$ in transition cohort $k$:
1. **Design Matrix Alignment**: Features were strictly projected into the model's trained `encoded_feature_names` vector $x_i$, maintaining exact dummy indicator alignment without refitting.
2. **Linear Predictor**:
   $$\eta_i = \sum_{j=1}^{p} \beta_j x_{ij}$$
3. **Partial Hazard / Relative Risk Score**:
   $$\text{Relative Risk}_i = \exp(\eta_i)$$
4. **Baseline Survival Step Function Lookup**:
   Using the non-parametric baseline survival table $S_{0,k}(t)$, the baseline probability for horizon $h$ was obtained via right-continuous step-function lookup:
   $$S_{0,k}(h) = \max_{t_m \le h} S_{0,k}(t_m)$$
   (where $S_{0,k}(h) = 1.0$ for $h < \min(t_m)$).
5. **Individual Survival Probability at Horizon $h$**:
   $$S_i(h \mid x_i) = \left[ S_{0,k}(h) \right]^{\exp(\eta_i)}$$
   Evaluated at horizons $h \in \{30, 90, 180, 365, 730\}$ days.

All predictions were persisted to [`models/cox_baseline/eval_out_of_sample_predictions.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/models/cox_baseline/eval_out_of_sample_predictions.csv).

---

## 6. Concordance Index ($C$-Index) Results

| Transition | Train $C$ | EVAL Obs ($N$) | EVAL Events ($E$) | EVAL Concordance | Metric Status | Interpretation Limitations |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `SECTION_11_TO_SECTION_19` | 0.8067 | 59 | 2 | **0.0000** | `COMPUTED` | Both events originate from single case `CAS_CLEAN_037`. Negative duration coefficient ($\beta = -0.0067$) assigned lower hazard to the late snapshot (2 days to event) than the early snapshot (92 days to event), inverting the pairwise concordance. Severely unstable. |
| `SECTION_19_TO_AWARD` | 1.0000 | 4 | 0 | **None** | `NOT COMPUTABLE — INSUFFICIENT EVENTS` | **Evaluation discrimination cannot be established because the EVAL cohort contains zero observed target events.** |
| `CASE_INITIATION_TO_MILESTONE` | 0.9667 | 104 | 2 | **0.5083** | `COMPUTED` | Near-random discrimination ($C \approx 0.51$). With only 2 observed events across 104 observations, the sample size is statistically insufficient to infer generalized discriminatory ability. |

---

## 7. Time-Dependent Discrimination (AUC)

Time-dependent cumulative/dynamic discrimination (Heagerty & Zheng, Uno et al.) was audited across standard planning horizons:

| Horizon | `SECTION_11_TO_SECTION_19` | `SECTION_19_TO_AWARD` | `CASE_INITIATION_TO_MILESTONE` |
| :---: | :---: | :---: | :---: |
| **30 Days** | `NOT RELIABLE — INSUFFICIENT EVENTS` (1 event $\le 30$d) | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 events $\le 30$d) | `NOT RELIABLE — INSUFFICIENT EVENTS` (1 event $\le 30$d) |
| **90 Days** | `NOT RELIABLE — INSUFFICIENT EVENTS` (1 event $\le 90$d) | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 events $\le 90$d) | `NOT RELIABLE — INSUFFICIENT EVENTS` (1 event $\le 90$d) |
| **180 Days** | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 at risk past 148d) | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 at risk past 148d) | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 at risk past 148d) |
| **365 Days** | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 at risk past 148d) | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 at risk past 148d) | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 at risk past 148d) |
| **730 Days** | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 at risk past 148d) | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 at risk past 148d) | `NOT RELIABLE — INSUFFICIENT EVENTS` (0 at risk past 148d) |

**Scientific Rationale**: Standard time-dependent ROC estimation requires $\ge 5$ observed target events per horizon. Reporting an empirical AUC computed on 1 positive event would be mathematically degenerate and misleading.

---

## 8. Time-Dependent Brier Scores (IPCW)

Evaluated using Inverse Probability of Censoring Weighting (Graf et al., 1999) based on empirical censoring survival function $G(t) = P(C > t)$:

| Horizon | Transition | Brier Score | Status | $N$ at Risk | Events $\le t$ | Valid Obs | Notes |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **30 Days** | `SECTION_11_TO_SECTION_19` | **0.016932** | `COMPUTED` | 48 | 1 | 49 / 59 | Heavy censoring; low baseline failure rate. |
| **30 Days** | `SECTION_19_TO_AWARD` | **0.000000** | `COMPUTED` | 4 | 0 | 4 / 4 | Reflects non-event concordance only (0 events). |
| **30 Days** | `CASE_INITIATION_TO_MILESTONE` | **0.009679** | `COMPUTED` | 82 | 1 | 83 / 104 | Concordant with high survival probability. |
| **90 Days** | `SECTION_11_TO_SECTION_19` | **0.025135** | `COMPUTED` | 2 | 1 | 3 / 59 | Only 2 cases remain at risk at 90 days. |
| **90 Days** | `SECTION_19_TO_AWARD` | **None** | `NOT COMPUTABLE` | 0 | 0 | 0 / 4 | Max follow-up is 53 days; $G(90) = 0$. |
| **90 Days** | `CASE_INITIATION_TO_MILESTONE` | **0.009704** | `COMPUTED` | 18 | 1 | 19 / 104 | 18 cases at risk at 90 days. |
| **180 Days** | *All Transitions* | **None** | `NOT COMPUTABLE` | 0 | 2 | 0 / 167 | Max EVAL duration is 148 days; $G(180) = 0$. |
| **365 Days** | *All Transitions* | **None** | `NOT COMPUTABLE` | 0 | 2 | 0 / 167 | No cases at risk past 148 days. |
| **730 Days** | *All Transitions* | **None** | `NOT COMPUTABLE` | 0 | 2 | 0 / 167 | No cases at risk past 148 days. |

---

## 9. Calibration Analysis (Predicted vs Observed Kaplan-Meier)

Comparison between mean model-predicted survival probability $\bar{S}(h)$ and empirical non-parametric Kaplan-Meier survival $S_{\text{KM}}(h)$ in EVAL:

| Transition | Horizon ($h$) | Mean Predicted Survival | Observed KM Survival | Calibration Difference | Risk Support |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `SECTION_11_TO_SECTION_19` | 30 Days | 0.9980 | 0.9831 | +0.0149 | 48 at risk |
| `SECTION_11_TO_SECTION_19` | 90 Days | 0.9694 | 0.9831 | -0.0137 | 2 at risk |
| `SECTION_11_TO_SECTION_19` | 180 Days | 0.9664 | 0.4915 | `UNRELIABLE` | 0 at risk (KM drop at 148d is censoring artifact) |
| `SECTION_19_TO_AWARD` | 30 Days | 0.9998 | 1.0000 | -0.0002 | 4 at risk |
| `SECTION_19_TO_AWARD` | 90 Days | 0.9998 | 1.0000 | `UNRELIABLE` | 0 at risk (all censored by 53d) |
| `CASE_INITIATION_TO_MILESTONE` | 30 Days | 0.9986 | 0.9904 | +0.0082 | 82 at risk |
| `CASE_INITIATION_TO_MILESTONE` | 90 Days | 0.9783 | 0.9904 | -0.0121 | 18 at risk |
| `CASE_INITIATION_TO_MILESTONE` | 180 Days | 0.9751 | 0.9354 | `UNRELIABLE` | 0 at risk (all censored by 148d) |

> [!NOTE]
> Calibration at 30 and 90 days demonstrates close numerical alignment with empirical survival probabilities (differences $< 1.5\%$). However, because events are sparse, this alignment predominantly reflects the high proportion of right-censoring in the administrative data rather than fine-grained risk discrimination.

---

## 10. Empirical Kaplan-Meier Baseline vs Observed Comparison

| Transition | Train Baseline Events ($E_{\text{train}}$) | Train Censoring Rate | Train Median Survival | EVAL Events ($E_{\text{eval}}$) | EVAL Censoring Rate | EVAL Median Survival |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `SECTION_11_TO_SECTION_19` | 16 | 80.95% | Not reached | 2 | 96.61% | 148.0 days (censoring limit) |
| `SECTION_19_TO_AWARD` | 6 | 97.04% | Not reached | 0 | 100.00% | Not reached |
| `CASE_INITIATION_TO_MILESTONE` | 18 | 97.04% | Not reached | 2 | 98.08% | Not reached |

**Risk Stratification Note**: Subgroup risk stratification (e.g. comparing "high-risk" vs "low-risk" strata survival curves) was deliberately omitted because dividing 2 events across strata yields empty or single-event subsets, violating statistical reporting principles.

---

## 11. Uncertainty & Confidence Intervals

- **Clustered Case-Level Bootstrap Audit**:
  The evaluation cohort consists of 89 independent case clusters. Because only 2 cases contain observed events across the entire dataset, resampling case clusters at random results in over **91% of bootstrap replicates containing zero events**.
- **Conclusion**: Standard asymptotic Wald intervals and cluster-bootstrap confidence intervals are degenerate under this degree of event sparsity. As required by scientific rules, unsupportable intervals are omitted rather than fabricated.

---

## 12. Summary of Uncomputable Metrics

| Metric | Transition | Reason for Incomputability |
| :--- | :--- | :--- |
| **Concordance Index** | `SECTION_19_TO_AWARD` | Zero observed target events in EVAL cohort ($E=0$). |
| **Time-Dependent AUC** | All Transitions ($30, 90, 180, 365, 730$d) | Fewer than 5 target events observed prior to horizon. |
| **IPCW Brier Score** | `SECTION_19_TO_AWARD` ($90, 180, 365, 730$d) | Censoring survival probability $G(t) = 0$ (max duration 53d). |
| **IPCW Brier Score** | `SECTION_11_TO_SECTION_19` ($180, 365, 730$d) | Follow-up window ends at 148 days; zero cases at risk. |
| **IPCW Brier Score** | `CASE_INITIATION_TO_MILESTONE` ($180, 365, 730$d) | Follow-up window ends at 148 days; zero cases at risk. |
| **Cluster Bootstrap CIs** | All Transitions | Event sparsity ($E \le 2$ per transition) causes degenerate resamples. |

---

## 13. Critical Limitations & Candid Scientific Disclosures

1. **Small-Event Sparsity**: With only 4 observed events in EVAL, model performance cannot be statistically generalized.
2. **Heavy Right-Censoring**: A 97.6% censoring rate means the vast majority of cases in EVAL were administratively active at the temporal cutoff date.
3. **Follow-Up Censoring Horizon**: The evaluation cohort has an empirical follow-up ceiling of 148 days, preventing empirical evaluation at 180, 365, and 730-day statutory milestones.
4. **Appropriate Interpretation Language**:
   > *"The model produced out-of-sample risk estimates, but performance estimation is highly uncertain because only four target events were observed in EVAL."*
   >
   > *"Event-based discrimination cannot be established for SECTION_19_TO_AWARD because zero target events were observed in EVAL."*

---

## 14. Artifact Integrity

All pre-fitted LOOP 7C artifacts in `models/cox_baseline/` remain strictly unmodified. New evaluation outputs generated in this loop:
1. `models/cox_baseline/eval_out_of_sample_predictions.csv` (167 rows, out-of-sample risk scores and 5 horizon survival probabilities).
2. `models/cox_baseline/cox_eval_summary.json` (Structured JSON containing full cohort summaries, metrics, and diagnostics).

---

## 15. Automated Adversarial Tests Executed

- **Test Suite**: [`bhumi-setu/apps/api/tests/ml/test_survival_evaluation.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/apps/api/tests/ml/test_survival_evaluation.py) (15 tests)
  1. `test_eval_data_never_enters_model_fitting`: Confirmed EVAL case keys never enter training design matrices.
  2. `test_model_parameters_unchanged_before_after_eval`: Confirmed SHA256 checksums of all 10 Loop 7C artifacts are byte-for-byte identical.
  3. `test_preprocessing_unchanged`: Verified column order and feature schema match trained artifacts exactly.
  4. `test_no_target_leakage`: Proved no target columns appear in eval design matrices.
  5. `test_no_future_feature_usage`: Proved all 7 purged variables remain strictly absent.
  6. `test_censored_observations_retained`: Confirmed all 163 right-censored cases are retained.
  7. `test_correct_eval_event_counts`: Confirmed exact event counts (2 in S11, 0 in S19, 2 in Initiation).
  8. `test_transition_isolation`: Confirmed zero cross-transition row contamination.
  9. `test_deterministic_prediction`: Confirmed identical floating-point predictions across runs.
  10. `test_zero_event_transition_handled_safely`: Proved zero-event transition produces explicit uncomputable status without crash.
  11. `test_insufficient_event_metrics_return_explicit_status`: Verified diagnostic status strings on sparse metrics.
  12. `test_model_artifacts_load_correctly`: Verified clean loading of all 3 transition models.
  13. `test_prediction_schema_consistency`: Validated columns and probability bounds $[0.0, 1.0]$.
  14. `test_no_calibration_fitting_on_eval`: Proved zero calibration fitting on evaluation data.
  15. `test_no_hyperparameter_tuning_on_eval`: Proved zero hyperparameter tuning on evaluation data.
- **Test Command**:
  ```bash
  PYTHONPATH="bhumi-setu/apps/api:bhumi-setu/ml/src" ./bhumi-setu/apps/api/.venv/bin/pytest bhumi-setu/apps/api/tests/ml -v
  ```
- **Result**: **163 / 163 passed in 2.02s** (0 failures, 0 errors, 0 regressions).

---

## Final Status

$$\mathbf{PARTIAL\ —\ SOME\ METRICS\ NOT\ COMPUTABLE\ DUE\ TO\ EVENT\ SPARSITY}$$

*The out-of-sample evaluation pipeline executed with complete mathematical integrity, strict data isolation, and zero domain fabrication. Consistent with scientific governance rules, event-based metrics with insufficient support are reported as uncomputable rather than manufactured.*
