# BHUMISETU Survival Feature Leakage Audit Report (LOOP 5)

This report details the final, independent audit and purging of the survival feature matrix prior to temporal train/evaluation splitting. 

---

## 1. Candidate Feature Audit & Classification Table

Every candidate feature was subjected to an independent audit against target correlation, point-in-time invariants, future event contamination, and distribution variance.

| Feature Name | Status | Audit Decision Reason | Point-in-Time Rule |
|---|---|---|---|
| `derived_days_since_case_initiation` | **SAFE** | Strictly backward-looking elapsed duration from earliest recorded notice. Cannot encode future milestone or event dates. | $T_{\text{snap}} - \min(T_{\text{notice}} \le T_{\text{snap}})$ |
| `derived_days_in_current_stage` | **SAFE** | Strictly backward-looking elapsed days in active statutory stage. Evaluated as of $T_{\text{snap}}$. Future stage transitions are completely masked. | $T_{\text{snap}} - T_{\text{current\_stage\_entry}}$ |
| `derived_days_since_latest_notice` | **SAFE** | Days since latest notice published on or before $T_{\text{snap}}$. Suppresses any notice occurring or recorded after $T_{\text{snap}}$. | $T_{\text{snap}} - \max(T_{\text{notice}} \le T_{\text{snap}})$ |
| `derived_notice_count` | **SAFE** | Cumulative count of valid notices knowable on or before $T_{\text{snap}}$. Future notices are masked. | $\text{count}(\text{notices where } t_{\text{occ}} \le T_{\text{snap}} \land t_{\text{rec}} \le T_{\text{snap}})$ |
| `derived_statutory_sec19_proximity_ratio` | **SAFE** | Elapsed fraction of statutory 365-day Section 11 window. Relies solely on Section 11 publication date ($\le T_{\text{snap}}$); does not encode actual Section 19 declaration date. | $\min(1.0, (T_{\text{snap}} - T_{\text{sec11}}).\text{days} / 365.0)$ |
| `extension_count` | **SAFE** | Cumulative count of extension orders published on or before $T_{\text{snap}}$. Future extension orders are masked. | $\text{count}(\text{extensions where } t_{\text{occ}} \le T_{\text{snap}} \land t_{\text{rec}} \le T_{\text{snap}})$ |
| `has_statutory_extension` | **SAFE** | Boolean indicator (`extension_count > 0`). Evaluated strictly as of $T_{\text{snap}}$. | $\text{extension\_count} > 0$ |
| `current_stage` | **SAFE** | Current statutory stage active as of $T_{\text{snap}}$. Replayed from event log up to $T_{\text{snap}}$. | $\text{stage active at } T_{\text{snap}}$ |
| `district` | **SAFE** | Jurisdictional Collectorate. Static administrative context established at case initiation. | Static case attribute |
| `taluka` | **SAFE** | Revenue taluka. Static administrative context established at case initiation. Unparsed entries remain empty string (never fabricated). | Static case attribute |
| `village` | **SAFE** | Revenue mouza/village. Static administrative context established at case initiation. | Static case attribute |
| `acquiring_authority` | **SAFE** | Acquiring governmental department. Static administrative context. | Static case attribute |
| `act_key` | **SAFE** | Legal statutory act governing the proceedings. Static administrative context. | Static case attribute |
| `derived_project_type` | **SAFE** | Project category extracted from public notice text published at case initiation. | Static case attribute |
| `derived_is_direct_purchase` | **SAFE** | Negotiation indicator extracted from initial public notice text. | Static case attribute |
| `award_recorded` | **PURGED (LEAKY RISK)** | Uniformly `False` (100.0%, 0 variance) in valid pre-event snapshots. If post-event observations were inadvertently admitted, it would represent instantaneous target leakage. Purged to eliminate leakage vulnerability. | Excluded from training set |
| `objection_count` | **PURGED (0% COVERAGE)** | Unpublished in gazette notices (100.0% missing). Purged from training predictors to avoid split contamination. | Excluded from training set |
| `parcel_count` | **PURGED (0% COVERAGE)** | Unpublished in structured data (100.0% missing). Purged from training predictors. | Excluded from training set |
| `open_issue_count` | **PURGED (0% COVERAGE)** | Internal collectorate tracker not published in real data (100.0% missing). Purged from training predictors. | Excluded from training set |
| `notified_area_hectares` | **PURGED (0% COVERAGE)** | Embedded in unparsed raster schedule tables (100.0% missing). Purged from training predictors. | Excluded from training set |
| `affected_landowner_count` | **PURGED (0% COVERAGE)** | Unpublished in structured data (100.0% missing). Purged from training predictors. | Excluded from training set |
| `compensation_amount_inr` | **PURGED (0% COVERAGE)** | Post-award compensation determination (100.0% missing pre-award). Purged from training predictors. | Excluded from training set |

---

## 2. Target Leakage Audit Results

An automated audit verified that target outcomes and horizon dates are completely separated from model predictors:

1. **Target Columns Never in Features**:
   $$\text{TARGET\_COLUMNS} = \{\text{duration\_at\_risk\_days}, \text{event\_observed}, \text{entry\_date}, \text{snapshot\_date}, \text{event\_date}, \text{censoring\_date}\}$$
   $$\text{SAFE\_PREDICTOR\_COLUMNS} \cap \text{TARGET\_COLUMNS} = \emptyset \quad (\text{Strictly Verified})$$
2. **Identifier Columns Never in Predictors**:
   $$\text{IDENTIFIER\_COLUMNS} = \{\text{case\_id}, \text{snapshot\_id}, \text{transition}\}$$
   $$\text{SAFE\_PREDICTOR\_COLUMNS} \cap \text{IDENTIFIER\_COLUMNS} = \emptyset \quad (\text{Strictly Verified})$$
3. **No Target Proxies**:
   None of the 15 safe predictors correlates perfectly with or encodes the remaining survival duration $\Delta T_{\text{risk}}$ or the binary indicator $E$.

---

## 3. Future-Event Adversarial Audit

Adversarial synthetic test cases were executed to guarantee that future administrative events do not perturb snapshot feature values:

| Adversarial Test | Scenario | Observed Feature Behavior | Verdict |
|---|---|---|---|
| **Future Section 19** | Snapshot: Day 120. Future Section 19 declaration at Day 181. | `current_stage` remains `SECTION_11`, `derived_notice_count` remains 1, `derived_statutory_sec19_proximity_ratio` is $120/365 \approx 0.3288$. | **PASS** |
| **Future Award** | Snapshot: Day 180 after Section 19. Future Award at Day 390. | `award_recorded` remains `False`, `current_stage` remains `SECTION_19`. | **PASS** |
| **Future Extension** | Snapshot: Month 6. Future statutory extension granted at Month 8. | `extension_count` remains 0, `has_statutory_extension` remains `False`. | **PASS** |
| **Future Section 21** | Snapshot: Month 2 after Section 19. Claims notice published at Month 4. | `derived_notice_count` does not increment; stays at 1. | **PASS** |
| **Future Corrigendum** | Snapshot: Month 4. Corrigendum notice published at Month 8. | `derived_days_since_latest_notice` measured from initial notice, not future corrigendum. | **PASS** |

---

## 4. Recording-Time Audit under `KNOWABLE_AT`

In administrative governance, official orders can have backdated execution dates prior to public gazette publication:
- **Rule**: Information is only available at $T_{\text{snap}}$ if:
  $$\text{occurrence\_time} \le T_{\text{snap}} \quad \text{AND} \quad \text{recording\_time} \le T_{\text{snap}}$$
- **Verification**: An extension order executed on March 1 but published in the gazette on June 1 is suppressed at snapshot date April 1. Under `AsOfMode.KNOWABLE_AT`, `extension_count = 0`. This prevents look-ahead leakage from backdated administrative filings.

---

## 5. Missingness Audit

1. **Strict Non-Coercion (`NULL != 0`)**:
   Missing attributes (`objection_count`, `parcel_count`, `open_issue_count`, `notified_area_hectares`, `affected_landowner_count`, `compensation_amount_inr`) are confirmed to be strictly `NULL` / empty strings. None have been coerced to zero.
2. **Missingness Reasons as Leaks**:
   Audit investigated whether `missing_reason` values could act as subtle target proxies (e.g. `NOT_APPLICABLE_PRE_AWARD`). All `missing_reason_*` columns have been **purged from `survival_training_features.csv`**. They exist exclusively as audit logs in `survival_features.csv`.

---

## 6. Case-Level Leakage & Multiple Snapshots

- **Finding**: Multiple snapshots belong to the same acquisition case (1,063 snapshots across 271 unique cases).
- **Hazard**: If snapshots from the same case are split randomly across train and test sets, the model could train on future snapshots of Case X and be evaluated on earlier snapshots of Case X, causing temporal data leakage.
- **Remedy**: **Random splitting is strictly forbidden.** Temporal splitting (LOOP 6) must partition cases either by historical entry cutoff date or by strict group-based temporal cutoff, ensuring that all evaluation observations lie chronologically in the future relative to all training observations.

---

## 7. Target Consistency Audit

Across all 1,063 observations in [`data/real_data/clean/survival_targets.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_targets.csv):
1. **Observed Cases ($E = 1$, N = 44)**:
   - `event_date` is strictly populated; `censoring_date` is empty string.
   - Strictly satisfies $\text{event\_date} > \text{snapshot\_date}$.
   - Strictly satisfies $\text{duration\_at\_risk\_days} = (\text{event\_date} - \text{snapshot\_date}).\text{days} > 0$.
2. **Censored Cases ($E = 0$, N = 1,019)**:
   - `censoring_date` is strictly populated; `event_date` is empty string.
   - Strictly satisfies $\text{censoring\_date} > \text{snapshot\_date}$.
   - Strictly satisfies $\text{duration\_at\_risk\_days} = (\text{censoring\_date} - \text{snapshot\_date}).\text{days} > 0$.
3. **Range Check**:
   - Zero negative durations.
   - Zero zero-durations ($\min(\text{duration}) = 1$ day).
   - Zero contradictory event/censoring flags.

---

## 8. Transition Isolation Audit

Confirmed that each of the three statutory transitions uses strictly its own transition milestone target:
- `SECTION_11_TO_SECTION_19`: Entry = Section 11 date. Milestone = Section 19 date. (Zero contamination from Award dates).
- `SECTION_19_TO_AWARD`: Entry = Section 19 date. Milestone = Award date. (Zero contamination from Section 11/19 dates).
- `CASE_INITIATION_TO_MILESTONE`: Entry = Earliest notice. Milestone = First statutory milestone reached.

---

## 9. Final Purged & Safe Feature Inventory

### Purged Features (7 features removed from training candidate set):
1. `award_recorded` (Zero variance; leakage vulnerability)
2. `objection_count` (0% coverage)
3. `parcel_count` (0% coverage)
4. `open_issue_count` (0% coverage)
5. `notified_area_hectares` (0% coverage)
6. `affected_landowner_count` (0% coverage)
7. `compensation_amount_inr` (0% coverage)

### Final Safe Predictor Features (15 features):
1. `derived_days_since_case_initiation` (Numerical - Temporal)
2. `derived_days_in_current_stage` (Numerical - Temporal)
3. `derived_days_since_latest_notice` (Numerical - Temporal)
4. `derived_notice_count` (Numerical - Temporal)
5. `derived_statutory_sec19_proximity_ratio` (Numerical - Statutory)
6. `extension_count` (Numerical - Statutory)
7. `has_statutory_extension` (Boolean - Statutory)
8. `current_stage` (Categorical - Stage)
9. `district` (Categorical - Administrative)
10. `taluka` (Categorical - Administrative)
11. `village` (Categorical - Administrative)
12. `acquiring_authority` (Categorical - Administrative)
13. `act_key` (Categorical - Administrative)
14. `derived_project_type` (Categorical - Administrative)
15. `derived_is_direct_purchase` (Boolean - Administrative)

---

## 10. Final Safe Training Artifacts Generated

1. [`data/real_data/clean/survival_training_features.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_training_features.csv)
   - Dimensions: **1,063 rows × 18 columns**
   - Columns: `case_id`, `snapshot_id`, `transition` + 15 safe predictor features.
   - Guaranteed zero target columns, zero purged features, zero metadata columns.
2. [`data/real_data/clean/survival_training_targets.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_training_targets.csv)
   - Dimensions: **1,063 rows × 5 columns**
   - Columns: `case_id`, `snapshot_id`, `transition`, `duration_at_risk_days`, `event_observed`.
   - Guaranteed zero predictor columns.

---

## 11. Final Audit Verdict

$$\mathbf{PASS} \quad \text{— READY FOR TEMPORAL SPLIT}$$
