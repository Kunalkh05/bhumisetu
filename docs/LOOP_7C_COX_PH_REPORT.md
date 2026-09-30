# LOOP 7C — Production Cox Proportional Hazards Baseline Report

**Execution Phase**: LOOP 7C — Production Cox PH Dependency Recovery & Model Fitting  
**Engine**: `lifelines 0.30.3` (`CoxPHFitter`, `proportional_hazard_test`)  
**Environment**: Python 3.14.3 (macOS arm64)  
**Input Data**: [`data/real_data/clean/survival_train_features.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_train_features.csv) & [`data/real_data/clean/survival_train_targets.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_train_targets.csv) (**TRAIN ONLY**)  
**Audit Date**: September 2026  
**Final Status**: `PASS — COX PROPORTIONAL HAZARDS BASELINE FITTED SUCCESSFULLY`

---

## 1. Executive Summary & Dependency Recovery

In this loop, the missing survival analysis dependency was successfully resolved and verified in the project virtual environment (`./bhumi-setu/apps/api/.venv`):
- **Core Library Installed**: `lifelines 0.30.3` (genuine, validated survival analysis library).
- **Supporting Scientific Stack**: `numpy 2.5.3`, `scipy 1.18.1`, `pandas 2.3.3`, `pytz 2026.4`, `matplotlib 3.11.2`, `autograd 1.9.1`, `autograd-gamma 0.5.0`, `formulaic 1.2.2`.
- **Validation**:
  ```python
  from lifelines import CoxPHFitter, KaplanMeierFitter
  # Verified importable and functional
  ```
- **Strict Compliance**:
  - No pseudo-Cox or custom optimizer was created.
  - Zero evaluation rows were accessed; the evaluation cohort ($N = 167$) remains strictly untouched.
  - All 15 safe predictor columns were evaluated across all three transitions.

---

## 2. Transition Modeling Overview (Train Cohort Only)

| Metric | `SECTION_11_TO_SECTION_19` | `SECTION_19_TO_AWARD` | `CASE_INITIATION_TO_MILESTONE` |
| :--- | :---: | :---: | :---: |
| **Total Observations ($N$)** | 84 | 203 | 609 |
| **Observed Events ($E=1$)** | 16 | 6 | 18 |
| **Right-Censored ($E=0$)** | 68 | 197 | 591 |
| **Censoring Rate** | 80.95% | 97.04% | 97.04% |
| **Model Parameters ($p$)** | 3 | 8 | 14 |
| **Events Per Variable (EPV)** | **5.33** | **0.75** (Severe Scarcity) | **1.29** (Low Event Density) |
| **Convergence Status** | **CONVERGED** | **CONVERGED** | **CONVERGED** |
| **Concordance on Train ($C$)** | 0.8067 | 1.0000 | 0.9667 |
| **Log-Likelihood** | -62.4692 | -9.7759 | -99.2133 |
| **Partial AIC** | 130.9385 | 35.5518 | 226.4266 |
| **PH Assumption Status** | **PASSED** (all $p \ge 0.54$) | **PASSED** (all $p \ge 0.59$) | **PASSED** (all $p \ge 0.85$) |

---

## 3. Transition 1: `SECTION_11_TO_SECTION_19`

- **Statutory Milestone**: Preliminary Notice $\rightarrow$ Declaration under RFCTLARR Act 2013 (365-day statutory window).
- **Training Cohort**: 84 observations, 16 observed events, 68 censored (80.95% censoring).
- **EPV**: 5.33 (moderate statistical stability).
- **Concordance on Train**: $C = 0.8067$.

### Coefficient & Hazard Ratio Summary

| Covariate | Coef ($\beta$) | Hazard Ratio ($\exp(\beta)$) | Std Error | 95% CI Lower | 95% CI Upper | $z$-score | $p$-value |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `derived_days_in_current_stage` | -0.0076 | 0.9924 | 0.0026 | 0.9873 | 0.9975 | -2.9360 | **0.0033** |
| `district_Solapur` | -0.9254 | 0.3964 | 1.3900 | 0.0261 | 6.0270 | -0.6658 | 0.5055 |
| `derived_project_type_Rural Infrastructure` | -1.8239 | 0.1614 | 1.0877 | 0.0192 | 1.3571 | -1.6769 | 0.0936 |

### Proportional Hazards Assumption Test (Rank Transformation)

| Covariate | Test Statistic ($\chi^2$) | $p$-value | PH Assumption Satisfied? |
| :--- | :---: | :---: | :---: |
| `derived_days_in_current_stage` | 0.3639 | 0.5462 | **True** ($p \ge 0.05$) |
| `district_Solapur` | 0.0022 | 0.9627 | **True** ($p \ge 0.05$) |
| `derived_project_type_Rural Infrastructure` | 0.0001 | 0.9915 | **True** ($p \ge 0.05$) |

---

## 4. Transition 2: `SECTION_19_TO_AWARD`

> [!WARNING]
> ### Transition with Severe Small-Event Scarcity (EPV = 0.75)
> For Section 19 $\rightarrow$ Award, the training cohort contains **only 6 observed events** across 203 observations (97.04% right-censoring).
> With 8 model parameters, $\text{EPV} = 6 / 8 = 0.75$, which is well below the standard statistical threshold ($\text{EPV} \ge 10$).
> While L2 ridge regularization (`penalizer=0.1`) enabled numerical convergence, the estimated hazard ratios have wide confidence intervals and must be interpreted with extreme caution.

### Coefficient & Hazard Ratio Summary

| Covariate | Coef ($\beta$) | Hazard Ratio ($\exp(\beta)$) | Std Error | 95% CI Lower | 95% CI Upper | $z$-score | $p$-value |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `derived_days_since_case_initiation` | 0.0007 | 1.0007 | 0.0010 | 0.9987 | 1.0028 | 0.6932 | 0.4882 |
| `derived_days_in_current_stage` | 0.0010 | 1.0010 | 0.0026 | 0.9959 | 1.0062 | 0.3846 | 0.7005 |
| `derived_notice_count` | -0.0216 | 0.9786 | 0.2594 | 0.5888 | 1.6263 | -0.0833 | 0.9336 |
| `extension_count` | 1.3788 | 3.9702 | 0.5930 | 1.2423 | 12.6881 | 2.3250 | **0.0201** |
| `has_statutory_extension` | 2.3276 | 10.2530 | 1.0169 | 1.3980 | 75.1979 | 2.2890 | **0.0221** |
| `current_stage_SECTION_19` | 0.0384 | 1.0392 | 0.4627 | 0.4196 | 2.5739 | 0.0830 | 0.9338 |
| `current_stage_SECTION_21` | -0.0191 | 0.9811 | 0.5042 | 0.3653 | 2.6353 | -0.0379 | 0.9697 |
| `derived_project_type_Rural Infrastructure` | -0.8197 | 0.4406 | 0.7434 | 0.1027 | 1.8906 | -1.1026 | 0.2703 |

### Proportional Hazards Assumption Test (Rank Transformation)

| Covariate | Test Statistic ($\chi^2$) | $p$-value | PH Assumption Satisfied? |
| :--- | :---: | :---: | :---: |
| `derived_days_since_case_initiation` | 0.1985 | 0.6559 | **True** |
| `derived_days_in_current_stage` | 0.2831 | 0.5946 | **True** |
| `derived_notice_count` | 0.0007 | 0.9783 | **True** |
| `extension_count` | 0.0089 | 0.9248 | **True** |
| `has_statutory_extension` | 0.2471 | 0.6193 | **True** |
| `current_stage_SECTION_19` | 0.0004 | 0.9847 | **True** |
| `current_stage_SECTION_21` | 0.0011 | 0.9736 | **True** |
| `derived_project_type_Rural Infrastructure` | 0.0510 | 0.8209 | **True** |

---

## 5. Transition 3: `CASE_INITIATION_TO_MILESTONE`

- **Statutory Milestone**: General Inception $\rightarrow$ First Statutory Notice/Milestone.
- **Training Cohort**: 609 observations, 18 observed events, 591 censored (97.04% censoring).
- **EPV**: 1.29.
- **Concordance on Train**: $C = 0.9667$.

### Key Significant Predictors:
- `current_stage_SECTION_11`: $\beta = +0.9702$, $\text{Hazard Ratio} = 2.6385$ ($95\%\text{ CI: } 1.4927 - 4.6635, p = 0.0007$). Cases currently in Section 11 experience a 2.64× higher rate of reaching the milestone declaration.
- `current_stage_GENERAL_NOTICE`: $\beta = -0.4552$, $\text{Hazard Ratio} = 0.6343$ ($p = 0.0597$). Cases lingering in general notice stage show lower rates of milestone exit.

### Proportional Hazards Assumption Test:
- All 14 covariates satisfy the PH assumption ($p$-values between $0.85$ and $0.99$, well above $0.05$).

---

## 6. Exported Model Artifacts on Disk

All model artifacts are stored in `models/cox_baseline/`:
1. `models/cox_baseline/cox_section_11_to_section_19_coefficients.csv`
2. `models/cox_baseline/cox_section_11_to_section_19_baseline_survival.csv`
3. `models/cox_baseline/cox_section_11_to_section_19_ph_test.csv`
4. `models/cox_baseline/cox_section_19_to_award_coefficients.csv`
5. `models/cox_baseline/cox_section_19_to_award_baseline_survival.csv`
6. `models/cox_baseline/cox_section_19_to_award_ph_test.csv`
7. `models/cox_baseline/cox_case_initiation_to_milestone_coefficients.csv`
8. `models/cox_baseline/cox_case_initiation_to_milestone_baseline_survival.csv`
9. `models/cox_baseline/cox_case_initiation_to_milestone_ph_test.csv`
10. `models/cox_baseline/cox_model_summary.json`

---

## 7. Automated Adversarial Tests Executed

- **Test Suite**: [`bhumi-setu/apps/api/tests/ml/test_cox_baseline.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/apps/api/tests/ml/test_cox_baseline.py) (10 tests)
  1. `test_train_only_fitting`: Strict isolation of training cohort from evaluation cases/keys.
  2. `test_censoring_retention`: Verified exact count of right-censored cases per transition (68, 197, 591).
  3. `test_binary_event_preservation`: Asserts event indicator remains strictly $\{0, 1\}$.
  4. `test_strictly_positive_durations`: Duration $> 0$ across all design matrices.
  5. `test_transition_isolation`: Ensures no cross-transition row contamination.
  6. `test_target_and_purged_leakage_prevention`: Proves no target or purged features enter model matrices.
  7. `test_deterministic_fitting`: Verifies identical coefficients across repeated runs.
  8. `test_artifact_loading_integrity`: Confirms all 10 artifacts reload from disk.
  9. `test_epv_diagnostics`: Validates automatic warning when EPV $< 5.0$.
  10. `test_ph_diagnostics`: Verifies execution of proportional hazards test.
- **Test Command**:
  ```bash
  PYTHONPATH=bhumi-setu/apps/api:bhumi-setu/ml/src ./bhumi-setu/apps/api/.venv/bin/pytest bhumi-setu/apps/api/tests/ml -v
  ```
- **Result**: **148 / 148 passed in 1.64s** (0 failures, 0 errors, 0 regressions).

---

## Final Status

$$\mathbf{PASS — BASELINE\ SURVIVAL\ MODELS\ FIT\ SUCCESSFULLY}$$
