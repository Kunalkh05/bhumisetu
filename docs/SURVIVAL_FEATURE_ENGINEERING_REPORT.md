# BHUMISETU Survival Feature Engineering Report (LOOP 4)

This report documents the feature engineering layer, point-in-time calculation rules, missingness preservation, leakage risk audit, and transition-specific feature distributions for the **Landmark Survival Snapshots** in BHUMISETU.

---

## 1. Executive Summary & Design Principles

The survival feature engineering layer builds and validates the predictor matrix $\mathbf{X}(T_{\text{snap}})$ evaluated at each historical snapshot date $T_{\text{snap}}$ across 1,063 landmark observations derived from 271 real Maharashtra land acquisition cases.

### Core Architectural Guarantees:
1. **Strict Temporal As-Of Isolation**: Every predictor feature is computed strictly using events and records satisfying:
   $$\text{occurrence\_time} \le T_{\text{snap}} \quad \text{AND} \quad \text{recording\_time} \le T_{\text{snap}}$$
   under `AsOfMode.KNOWABLE_AT`. No future notifications, extensions, or stage changes can leak into historical feature values.
2. **Complete Target & Metadata Separation**:
   - `TARGET_COLUMNS`: `duration_at_risk_days`, `event_observed`, `entry_date`, `snapshot_date`, `event_date`, `censoring_date`.
   - `IDENTIFIER_COLUMNS`: `case_id`, `snapshot_id`, `transition`.
   - Guaranteed by automated unit tests:
     $$\text{set}(\text{FEATURE\_COLUMNS}) \cap \text{set}(\text{TARGET\_COLUMNS}) = \emptyset$$
     $$\text{set}(\text{FEATURE\_COLUMNS}) \cap \text{set}(\text{IDENTIFIER\_COLUMNS}) = \emptyset$$
3. **Statutory Missingness Preservation (No NULL $\rightarrow$ 0 Coercion)**:
   Attributes not published in gazette text or unparsed schedule tables (`objection_count`, `parcel_count`, `open_issue_count`, `notified_area_hectares`, `affected_landowner_count`, `compensation_amount_inr`) remain strictly `NULL` / `NaN` with standardized `missing_reason` audit columns. Zero is NEVER fabricated.
4. **Physical Separation of Artifacts**:
   - [`data/real_data/clean/survival_feature_matrix.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_feature_matrix.csv): Predictor features only + index keys.
   - [`data/real_data/clean/survival_targets.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_targets.csv): Target outcomes + horizon dates + index keys.
   - [`data/real_data/clean/survival_features.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_features.csv): Predictor features + missingness audit reasons + index keys.
   - [`data/real_data/clean/survival_feature_manifest.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_feature_manifest.csv): Specification, availability rules, and leakage risk for all 22 candidate features.

---

## 2. Complete Feature Inventory & Specification

| # | Feature Name | Classification | Data Type | Source | Calculation / Definition | Missing Reason | Leakage Risk | Allowed in Training? |
|---|---|---|---|---|---|---|---|---|
| 1 | `derived_days_since_case_initiation` | Dynamic Temporal | integer | Earliest Gazette Notice | $\max(0, (T_{\text{snap}} - T_{\text{init}}).\text{days})$ | `NONE` | **LOW** | **YES** |
| 2 | `derived_days_in_current_stage` | Dynamic Temporal | integer | Current Stage Entry Event | $\max(0, (T_{\text{snap}} - T_{\text{stage}}).\text{days})$ | `NONE` | **LOW** | **YES** |
| 3 | `derived_days_since_latest_notice` | Dynamic Temporal | float / integer | Gazette Notices $\le T_{\text{snap}}$ | $\max(0, (T_{\text{snap}} - T_{\text{latest\_notice}}).\text{days})$ | `NO_NOTICE_EVENT` | **LOW** | **YES** |
| 4 | `derived_notice_count` | Dynamic Temporal | integer | Notice Events $\le T_{\text{snap}}$ | $\text{count}(\text{notices} \le T_{\text{snap}})$ | `NONE` | **LOW** | **YES** |
| 5 | `derived_statutory_sec19_proximity_ratio` | Dynamic Statutory | float | Section 11 Notice Date | $\min(1.0, (T_{\text{snap}} - T_{\text{sec11}}).\text{days} / 365.0)$ | `NOT_APPLICABLE_PRE_SEC11` | **LOW** | **YES** |
| 6 | `extension_count` | Dynamic Statutory | integer | Extension Orders $\le T_{\text{snap}}$ | $\text{count}(\text{extensions} \le T_{\text{snap}})$ | `NONE` | **LOW** | **YES** |
| 7 | `has_statutory_extension` | Dynamic Statutory | boolean | Extension Orders $\le T_{\text{snap}}$ | $\text{extension\_count} > 0$ | `NONE` | **LOW** | **YES** |
| 8 | `award_recorded` | Dynamic Milestone | boolean | Award Events $\le T_{\text{snap}}$ | $\text{count}(\text{awards} \le T_{\text{snap}}) > 0$ | `NONE` | **MEDIUM** | **NO** (Zero variance; $100\%$ False in pre-event snapshots) |
| 9 | `current_stage` | Dynamic Categorical | string | Most recent stage $\le T_{\text{snap}}$ | Latest stage active at $T_{\text{snap}}$ | `NONE` | **LOW** | **YES** |
| 10 | `district` | Static Context | string | Collectorate Records | Revenue district jurisdiction | `NONE` | **LOW** | **YES** |
| 11 | `taluka` | Static Context | string | Collectorate Records | Revenue taluka / tehsil | `UNPARSED_SCHEDULE_TABLE` | **LOW** | **YES** |
| 12 | `village` | Static Context | string | Collectorate Records | Revenue village / mouza | `UNPARSED_SCHEDULE_TABLE` | **LOW** | **YES** |
| 13 | `acquiring_authority` | Static Context | string | Project Records | Acquiring administrative body | `NONE` | **LOW** | **YES** |
| 14 | `act_key` | Static Context | string | Gazette Citation | Legal governing statute | `NONE` | **LOW** | **YES** |
| 15 | `derived_project_type` | Static Context | string | Notice Description NLP | Inferred project sector | `NONE` | **LOW** | **YES** |
| 16 | `derived_is_direct_purchase` | Static Context | boolean | Notice Text Keywords | Private negotiation proceeding indicator | `NONE` | **LOW** | **YES** |
| 17 | `objection_count` | Missing Attribute | float / integer | Section 15 Register | Landowner objections filed | `NOT_PUBLISHED_IN_GAZETTE` | **LOW** | **NO** ($0\%$ coverage) |
| 18 | `parcel_count` | Missing Attribute | float / integer | Cadastral Schedule | Survey parcel count | `NOT_PUBLISHED_IN_STRUCTURED_DATA` | **LOW** | **NO** ($0\%$ coverage) |
| 19 | `open_issue_count` | Missing Attribute | float / integer | Administrative Tracker | Collectorate issues | `NOT_APPLICABLE_IN_REAL_DATA` | **LOW** | **NO** ($0\%$ coverage) |
| 20 | `notified_area_hectares` | Missing Attribute | float | Gazette Schedule Table | Notified area in hectares | `UNPARSED_SCHEDULE_TABLE` | **LOW** | **NO** ($0\%$ coverage) |
| 21 | `affected_landowner_count` | Missing Attribute | float / integer | Landowner Schedule Table | Distinct affected persons count | `NOT_PUBLISHED_IN_STRUCTURED_DATA` | **LOW** | **NO** ($0\%$ coverage) |
| 22 | `compensation_amount_inr` | Missing Attribute | float | Section 23 Award | Total compensation in INR | `NOT_APPLICABLE_PRE_AWARD` | **LOW** | **NO** ($0\%$ coverage) |

---

## 3. Transition-Specific Feature Coverage Breakdown

Coverage across each of the three statutory transitions (from 1,063 clean landmark snapshots):

| Feature Name | SECTION_11_TO_SECTION_19 (N=143) | SECTION_19_TO_AWARD (N=207) | CASE_INITIATION_TO_MILESTONE (N=713) | Overall (N=1,063) |
|---|---|---|---|---|
| `derived_days_since_case_initiation` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `derived_days_in_current_stage` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `derived_days_since_latest_notice` | **100.0%** (143/143) | **100.0%** (207/207) | **98.5%** (702/713) | **99.0%** |
| `derived_notice_count` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `derived_statutory_sec19_proximity_ratio` | **100.0%** (143/143) | **37.7%** (78/207) | **22.9%** (163/713) | **36.1%** (384/1,063) |
| `extension_count` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `has_statutory_extension` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `award_recorded` | **100.0%** (all False) | **100.0%** (all False) | **100.0%** (all False) | **100.0%** |
| `current_stage` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `district` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `taluka` | **85.3%** (122/143) | **64.3%** (133/207) | **54.4%** (388/713) | **60.5%** (643/1,063) |
| `village` | **85.3%** (122/143) | **81.6%** (169/207) | **54.8%** (391/713) | **64.2%** (682/1,063) |
| `acquiring_authority` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `act_key` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `derived_project_type` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `derived_is_direct_purchase` | **100.0%** (143/143) | **100.0%** (207/207) | **100.0%** (713/713) | **100.0%** |
| `objection_count` | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) |
| `parcel_count` | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) |
| `open_issue_count` | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) |
| `notified_area_hectares` | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) |
| `affected_landowner_count` | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) |
| `compensation_amount_inr` | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) | **0.0%** (NULL) |

---

## 4. Descriptive Statistics & Distribution Audit (No Predictive Claims)

### Numerical Predictors:

| Feature Name | Transition | Count | Missing | Miss % | Min | Median | Mean | Max |
|---|---|---|---|---|---|---|---|---|
| `derived_days_since_case_initiation` | Overall | 1,063 | 0 | 0.0% | 0.0 | 90.0 | 154.3 | 730.0 |
| | Section 11 $\rightarrow$ 19 | 143 | 0 | 0.0% | 0.0 | 0.0 | 64.8 | 270.0 |
| | Section 19 $\rightarrow$ Award | 207 | 0 | 0.0% | 0.0 | 180.0 | 174.4 | 490.0 |
| | Case Initiation $\rightarrow$ Milestone | 713 | 0 | 0.0% | 0.0 | 90.0 | 166.4 | 730.0 |
| `derived_days_in_current_stage` | Overall | 1,063 | 0 | 0.0% | 0.0 | 90.0 | 144.3 | 730.0 |
| | Section 11 $\rightarrow$ 19 | 143 | 0 | 0.0% | 0.0 | 0.0 | 64.8 | 270.0 |
| | Section 19 $\rightarrow$ Award | 207 | 0 | 0.0% | 0.0 | 135.0 | 136.4 | 365.0 |
| | Case Initiation $\rightarrow$ Milestone | 713 | 0 | 0.0% | 0.0 | 90.0 | 162.6 | 730.0 |
| `derived_days_since_latest_notice` | Overall | 1,052 | 11 | 1.0% | 0.0 | 90.0 | 145.8 | 730.0 |
| | Section 11 $\rightarrow$ 19 | 143 | 0 | 0.0% | 0.0 | 0.0 | 64.8 | 270.0 |
| | Section 19 $\rightarrow$ Award | 207 | 0 | 0.0% | 0.0 | 135.0 | 136.4 | 365.0 |
| | Case Initiation $\rightarrow$ Milestone | 702 | 11 | 1.5% | 0.0 | 90.0 | 165.1 | 730.0 |
| `derived_notice_count` | Overall | 1,063 | 0 | 0.0% | 0.0 | 1.0 | 1.14 | 3.0 |
| | Section 11 $\rightarrow$ 19 | 143 | 0 | 0.0% | 1.0 | 1.0 | 1.0 | 1.0 |
| | Section 19 $\rightarrow$ Award | 207 | 0 | 0.0% | 1.0 | 1.0 | 1.63 | 3.0 |
| | Case Initiation $\rightarrow$ Milestone | 713 | 0 | 0.0% | 0.0 | 1.0 | 1.03 | 2.0 |
| `derived_statutory_sec19_proximity_ratio` | Overall | 384 | 679 | 63.9% | 0.0 | 0.24 | 0.29 | 1.0 |
| | Section 11 $\rightarrow$ 19 | 143 | 0 | 0.0% | 0.0 | 0.0 | 0.18 | 0.74 |
| | Section 19 $\rightarrow$ Award | 78 | 129 | 62.3% | 0.0 | 0.44 | 0.51 | 1.0 |
| | Case Initiation $\rightarrow$ Milestone | 163 | 550 | 77.1% | 0.0 | 0.0 | 0.28 | 1.0 |
| `extension_count` | Overall | 1,063 | 0 | 0.0% | 0.0 | 0.0 | 0.02 | 2.0 |
| | Section 11 $\rightarrow$ 19 | 143 | 0 | 0.0% | 0.0 | 0.0 | 0.0 | 0.0 |
| | Section 19 $\rightarrow$ Award | 207 | 0 | 0.0% | 0.0 | 0.0 | 0.05 | 2.0 |
| | Case Initiation $\rightarrow$ Milestone | 713 | 0 | 0.0% | 0.0 | 0.0 | 0.02 | 1.0 |

### Categorical & Administrative Predictors:

| Feature Name | Distinct Count | Top 3 Modalities | Frequency & Percentage |
|---|---|---|---|
| `current_stage` | 6 | `GENERAL_NOTICE`<br>`SECTION_11`<br>`SECTION_19` | 426 (40.1%)<br>316 (29.7%)<br>145 (13.6%) |
| `district` | 5 | Nagpur<br>Pune<br>Yavatmal | 720 (67.7%)<br>283 (26.6%)<br>30 (2.8%) |
| `taluka` | 40 | *(Unparsed schedule)*<br>Kuhi<br>Hingna | 420 (39.5%)<br>234 (22.0%)<br>44 (4.1%) |
| `village` | 128 | *(Unparsed schedule)*<br>Ruyad<br>Nagpur (Khas) | 381 (35.8%)<br>25 (2.4%)<br>20 (1.9%) |
| `acquiring_authority` | 5 | Collectorate Nagpur<br>Collectorate Pune<br>Collectorate Yavatmal | 720 (67.7%)<br>283 (26.6%)<br>30 (2.8%) |
| `act_key` | 5 | `RFCTLARR_2013`<br>`LAND_ACQUISITION_ACT_1894`<br>`NATIONAL_HIGHWAYS_ACT_1956` | 1,038 (97.6%)<br>9 (0.8%)<br>8 (0.8%) |
| `derived_project_type` | 7 | Rural Infrastructure<br>Highway / Road Widening<br>Irrigation / Canal | 962 (90.5%)<br>66 (6.2%)<br>17 (1.6%) |
| `has_statutory_extension` | 2 | `False`<br>`True` | 1,046 (98.4%)<br>17 (1.6%) |
| `derived_is_direct_purchase` | 2 | `False`<br>`True` | 981 (92.3%)<br>82 (7.7%) |
| `award_recorded` | 1 | `False` | 1,063 (100.0%) |

---

## 5. Leakage Safeguard Audit & Rejection Decisions

### A. The `award_recorded` Evaluation
- **Analysis**: In predictive survival modeling, snapshots are evaluated strictly prior to the milestone horizon ($T_{\text{snap}} < \text{horizon\_end}$). For pre-Award transitions (`SECTION_11_TO_SECTION_19` and `SECTION_19_TO_AWARD`), an Award has not occurred yet. Therefore, `award_recorded` is uniformly `False` across all 1,063 valid snapshots.
- **Decision**: Classified as **MEDIUM** leakage risk and marked as **NOT ALLOWED FOR TRAINING** (`allowed_for_survival_training = FALSE`). If post-event observations were inadvertently fed into training, `award_recorded = True` would constitute instantaneous target leakage. Since it has zero variance (constant False) in valid pre-event data, excluding it prevents model confusion and leakage vulnerabilities.

### B. Missing Attributes ($0\%$ Coverage)
- **Analysis**: `objection_count`, `parcel_count`, `open_issue_count`, `notified_area_hectares`, `affected_landowner_count`, `compensation_amount_inr` are not published in gazette text schedules.
- **Decision**: Marked as `allowed_for_survival_training = FALSE`. They remain in `survival_features.csv` and `survival_feature_manifest.csv` as strictly `NULL` / `NaN` with explicit `missing_reason` entries to preserve the data provenance contract without contaminating GBDT split nodes with synthetic zeros.

### C. Case Identifiers
- **Analysis**: `case_id`, `snapshot_id`, and `snapshot_date` are identifying index keys.
- **Decision**: Strictly kept in `IDENTIFIER_COLUMNS` and segregated from `FEATURE_COLUMNS`.

---

## 6. Concrete Snapshot Feature Vectors

### Example 1: Section 11 Initiation Snapshot (Case `CAS_CLEAN_070`)
- **Snapshot ID**: `SNP_CAS_CLEAN_070_CASE_INITIATION_MILESTONE_20250214`
- **Snapshot Date**: `2025-02-14`
- **Transition**: `CASE_INITIATION_TO_MILESTONE`
- **Predictors**:
  - `derived_days_since_case_initiation`: `0`
  - `derived_days_in_current_stage`: `0`
  - `derived_days_since_latest_notice`: `0`
  - `derived_notice_count`: `1`
  - `derived_statutory_sec19_proximity_ratio`: `0.0`
  - `extension_count`: `0`
  - `has_statutory_extension`: `False`
  - `current_stage`: `SECTION_11`
  - `district`: `Nagpur`
  - `taluka`: `Kuhi`
  - `village`: `Mandhal`
  - `derived_project_type`: `Rural Infrastructure`
  - `derived_is_direct_purchase`: `False`
  - `objection_count`: `NULL` (`missing_reason = NOT_PUBLISHED_IN_GAZETTE`)
  - `parcel_count`: `NULL` (`missing_reason = NOT_PUBLISHED_IN_STRUCTURED_DATA`)
- **Target Outcome (Isolated in Targets File)**:
  - `duration_at_risk_days`: `125`
  - `event_observed`: `True`
  - `event_date`: `2025-06-19`

### Example 2: Section 19 Review at Day 90 (Case `CAS_CLEAN_070`)
- **Snapshot ID**: `SNP_CAS_CLEAN_070_S19_AWARD_20250917`
- **Snapshot Date**: `2025-09-17` (90 days after Section 19 declaration on `2025-06-19`)
- **Transition**: `SECTION_19_TO_AWARD`
- **Predictors**:
  - `derived_days_since_case_initiation`: `215` (from S11 on `2025-02-14`)
  - `derived_days_in_current_stage`: `90`
  - `derived_days_since_latest_notice`: `90`
  - `derived_notice_count`: `2`
  - `derived_statutory_sec19_proximity_ratio`: `0.589`
  - `extension_count`: `0`
  - `has_statutory_extension`: `False`
  - `current_stage`: `SECTION_19`
- **Target Outcome (Isolated in Targets File)**:
  - `duration_at_risk_days`: `300` (Remaining to Award on `2026-07-14`)
  - `event_observed`: `True`
  - `event_date`: `2026-07-14`

---

## 7. Verification Summary

All 104 tests in the ML test suite pass cleanly:
```bash
PYTHONPATH=bhumi-setu/apps/api:bhumi-setu/ml/src ./bhumi-setu/apps/api/.venv/bin/pytest bhumi-setu/apps/api/tests/ml -v
```
Disjointness, future event suppression, late-recording handling, non-negativity of temporal features, and strict missingness preservation are fully verified.
