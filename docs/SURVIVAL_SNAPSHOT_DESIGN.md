# BHUMISETU Survival Snapshot Design (LOOP 3)

This document specifies the architecture, generation strategy, point-in-time feature extraction, and leakage safeguards for **Point-in-Time Survival Snapshots** in BHUMISETU.

---

## 1. Architectural Philosophy: "What did BHUMISETU know at time T?"

In land acquisition risk modeling, predictive models must evaluate cases at realistic administrative decision points during proceedings. To train survival models without future data leakage, we construct point-in-time snapshots under **Landmark Survival Analysis** semantics:

$$\text{Observation at } T_{\text{snap}} = \left( \mathbf{x}(T_{\text{snap}}), T_{\text{rem}}, E \right)$$

Where:
- $\mathbf{x}(T_{\text{snap}})$ represents the vector of features constructed **strictly** from information available on or before $T_{\text{snap}}$ (satisfying `occurrence_time <= T_snap` and `recording_time <= T_snap`).
- $T_{\text{rem}}$ is the **remaining survival duration at risk from the snapshot date**:
  - If the transition milestone is observed ($E = 1$): $T_{\text{rem}} = T_{\text{event}} - T_{\text{snap}} > 0$, strictly with $T_{\text{snap}} < T_{\text{event}}$.
  - If the case is right-censored ($E = 0$): $T_{\text{rem}} = T_{\text{cutoff}} - T_{\text{snap}} > 0$, strictly with $T_{\text{snap}} < T_{\text{cutoff}}$.
- $E$ is the event indicator ($1 = \text{observed milestone}$, $0 = \text{right-censored}$).

> [!IMPORTANT]
> **Landmark Semantics Correction (LOOP 3A)**:
> In earlier drafts, $T_{\text{risk}}$ was calculated from the case entry date ($T_{\text{event}} - T_{\text{entry}}$), which represented static overall case duration rather than remaining time-to-event from the prediction point. Measuring from $T_{\text{snap}}$ aligns directly with the predictive task: *"Given what BHUMISETU knows at reference date $T_{\text{snap}}$, how much longer until this milestone occurs or is censored?"*
> 
> Furthermore, **post-event and on-event snapshots ($T_{\text{snap}} \ge T_{\text{event}}$) are strictly excluded** from predictive training because an event that has already occurred cannot be predicted.

---

## 2. Snapshot Types & Transitions

Snapshots are partitioned into three non-overlapping statutory transitions:

### 1. `SECTION_11_TO_SECTION_19`
- **Entry**: Publication date of Preliminary Notification under Section 11(1) of RFCTLARR Act 2013.
- **Milestone Exit**: Declaration date under Section 19(1).
- **Statutory Window**: 365 days.
- **Snapshot Range**: $\text{entry\_date} \le T_{\text{snap}} < \min(\text{event\_date}, T_{\text{cutoff}})$.

### 2. `SECTION_19_TO_AWARD`
- **Entry**: Declaration date under Section 19(1).
- **Milestone Exit**: Final Award date under Section 23/25.
- **Statutory Window**: 365 days (subject to documented extension provisions).
- **Snapshot Range**: $\text{entry\_date} \le T_{\text{snap}} < \min(\text{award\_date}, T_{\text{cutoff}})$.

### 3. `CASE_INITIATION_TO_MILESTONE`
- **Entry**: First recorded gazette notice (e.g. `GENERAL_NOTICE`, `INTAKE`, `SECTION_11`).
- **Milestone Exit**: First statutory milestone reached (`SECTION_19` or `AWARD`).
- **Snapshot Range**: $\text{entry\_date} \le T_{\text{snap}} < \min(\text{milestone\_date}, T_{\text{cutoff}})$.

---

## 3. Snapshot Generation Strategy

Rather than generating arbitrary, redundant daily snapshots that blow up dataset size without adding predictive information, BHUMISETU generates snapshots at realistic operational decision points:

1. **Initiation Snapshot ($T_{\text{snap}} = \text{entry\_date}$)**:
   - Evaluated at Day 0 of the transition.
   - Represents the risk assessment when the notification/declaration is first published.
2. **Intermediate Event Snapshots ($T_{\text{snap}} = \text{event\_date}_i$)**:
   - Triggered whenever an intermediate administrative event occurs (e.g. an extension order, Section 21 claims notice, or corrigendum) strictly between $\text{entry\_date} < \text{event\_date}_i < \text{horizon\_end}$.
3. **Statutory Checkpoints**:
   - `SECTION_11_TO_SECTION_19`: Day 90 (post-objection review), Day 180 (mid-term review), Day 270 (statutory escalation).
   - `SECTION_19_TO_AWARD`: Day 90, Day 180, Day 270, Day 365.
   - `CASE_INITIATION_TO_MILESTONE`: Day 90, Day 180, Day 270, Day 365, Day 730.

All snapshot dates must satisfy $T_{\text{snap}} < \text{horizon\_end}$. Any checkpoint on or after $\text{horizon\_end}$ is dropped.

---

## 4. Point-in-Time Feature Extraction & Availability Rules

All features are computed via [`compute_point_in_time_features`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/ml/src/features/snapshots.py) using events filtered under `AsOfMode.KNOWABLE_AT`:

$$\text{occurrence\_time} \le T_{\text{snap}} \quad \text{AND} \quad \text{recording\_time} \le T_{\text{snap}}$$

### Feature Set Specification:

| Feature Name | Source | Availability Rule | Data Type | Missing Reason | Safe? |
|---|---|---|---|---|---|
| `derived_days_since_case_initiation` | Earliest notice | $(T_{\text{snap}} - T_{\text{init}}).\text{days}$ | integer | NONE | YES |
| `derived_days_in_current_stage` | Current stage entry | $(T_{\text{snap}} - T_{\text{stage}}).\text{days}$ | integer | NONE | YES |
| `derived_days_since_latest_notice` | Notices $\le T_{\text{snap}}$ | $(T_{\text{snap}} - T_{\text{latest\_notice}}).\text{days}$ | integer | `NO_NOTICE_EVENT` | YES |
| `derived_notice_count` | Notice count $\le T_{\text{snap}}$ | Cumulative notices published by $T_{\text{snap}}$ | integer | NONE | YES |
| `derived_statutory_sec19_proximity_ratio` | Section 11 date | $\min(1.0, \text{days\_since\_s11} / 365.0)$ | float | `NOT_APPLICABLE_PRE_SEC11` | YES |
| `extension_count` | Extension orders $\le T_{\text{snap}}$ | Extensions granted by $T_{\text{snap}}$ | integer | NONE | YES |
| `has_statutory_extension` | Extension orders $\le T_{\text{snap}}$ | `extension_count > 0` | boolean | NONE | YES |
| `award_recorded` | Award events $\le T_{\text{snap}}$ | `True` only if Award $\le T_{\text{snap}}$ | boolean | NONE | YES |
| `district` | Case jurisdiction | Jurisdictional Collectorate | string | NONE | YES |
| `taluka` | Case jurisdiction | Sub-division administrative unit | string | NONE | YES |
| `village` | Case location | Revenue village / mouza | string | NONE | YES |
| `acquiring_authority` | Case metadata | Acquiring administrative body | string | NONE | YES |
| `act_key` | Case statute | Governing legal act | string | NONE | YES |
| `derived_project_type` | Notice text | Public project classification | string | NONE | YES |
| `derived_is_direct_purchase` | Notice text | Private negotiation indicator | boolean | NONE | YES |
| `objection_count` | Section 15 register | Landowner objections | integer | `NOT_PUBLISHED_IN_GAZETTE` | YES |
| `parcel_count` | Cadastral schedule | Survey numbers count | integer | `NOT_PUBLISHED_IN_STRUCTURED_DATA` | YES |
| `open_issue_count` | Issue tracker | Operational issues | integer | `NOT_APPLICABLE_IN_REAL_DATA` | YES |
| `notified_area_hectares` | Notice schedule | Notified area in hectares | float | `UNPARSED_SCHEDULE_TABLE` | YES |
| `compensation_amount_inr` | Award statement | Section 23 compensation | float | `NOT_APPLICABLE_PRE_AWARD` | YES |

---

## 5. Leakage Safeguards & Adversarial Verifications

Adversarial and landmark scenarios are verified by unit tests in [`test_survival_snapshots.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/apps/api/tests/ml/test_survival_snapshots.py):

1. **TEST A (Future Event Suppression)**:
   - An event occurring after $T_{\text{snap}}$ cannot alter `current_stage`, `derived_notice_count`, `extension_count`, or `award_recorded`.
2. **TEST B (Future Award Masking)**:
   - An Award published at $T = \text{2025-08-01}$ yields `award_recorded = False` for all snapshots prior to August 1, 2025.
3. **TEST C (Future Extension Masking)**:
   - An extension granted on $T = \text{2026-08-01}$ yields `extension_count = 0` and `has_statutory_extension = False` for snapshot $T = \text{2026-07-15}$.
4. **TEST D (Future Section 19 Masking)**:
   - Section 19 declaration occurring after $T_{\text{snap}}$ cannot alter Section 11 stage status or statutory proximity ratios prior to its publication date.
5. **TEST E (Late Recording Protection under `KNOWABLE_AT`)**:
   - An event occurring on Feb 1 but recorded in the gazette on May 1 is suppressed at snapshot $T = \text{March 1}$, preventing late-recording leakage.
6. **TEST F (Landmark Remaining Duration)**:
   - For Entry: 2025-01-01, Event: 2025-07-01, Snapshot: 2025-04-01, verifies `duration_at_risk_days = 91` (2025-07-01 - 2025-04-01), NOT 181.
7. **TEST G (Post-Event Exclusion)**:
   - For an event occurring at Day 59, checkpoints at Day 60 and Day 90 are excluded from training.

---

## 6. Real Dataset Snapshot Distribution (Landmark Aligned)

Generated from 271 clean Maharashtra cases ([`survival_snapshots.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_snapshots.csv)):

| Transition | Unique Cases | Total Snapshots | Observed ($E=1$) | Censored ($E=0$) | Earliest Snapshot | Latest Snapshot | Duplicate Snapshots |
|---|---|---|---|---|---|---|---|
| `SECTION_11_TO_SECTION_19` | 89 | 143 | 18 (12.6%) | 125 (87.4%) | 2024-02-27 | 2026-09-22 | **0** |
| `SECTION_19_TO_AWARD` | 47 | 207 | 6 (2.9%) | 201 (97.1%) | 2023-12-22 | 2026-09-26 | **0** |
| `CASE_INITIATION_TO_MILESTONE` | 217 | 713 | 20 (2.8%) | 693 (97.2%) | 2019-09-21 | 2026-09-27 | **0** |
| **Total Across Transitions** | **271** | **1,063** | **44 (4.1%)** | **1,019 (95.9%)** | **2019-09-21** | **2026-09-27** | **0** |

> [!NOTE]
> Under Landmark alignment, 88 post-event / on-event snapshots ($T_{\text{snap}} \ge T_{\text{event}}$) present in the unconstrained generation were excluded, reducing total observations from 1,151 down to **1,063**. All 1,063 observations satisfy `duration_at_risk_days > 0`.

---

## 7. Concrete Snapshot Examples

### Example 1: Section 11 Initiation Snapshot (Case `CAS_CLEAN_070`)
- `snapshot_id`: `SNP_CAS_CLEAN_070_CASE_INITIATION_MILESTONE_20250214`
- `snapshot_date`: `2025-02-14` (Day 0)
- `transition`: `CASE_INITIATION_TO_MILESTONE`
- `entry_date`: `2025-02-14`
- `current_stage`: `SECTION_11`
- `derived_days_in_current_stage`: `0`
- `derived_notice_count`: `1`
- `award_recorded`: `False`
- `duration_at_risk_days`: `125` (2025-06-19 - 2025-02-14)
- `event_observed`: `True`
- `event_date`: `2025-06-19`

### Example 2: Section 11 Follow-up Checkpoint at Day 90 (Case `CAS_CLEAN_070`)
- `snapshot_id`: `SNP_CAS_CLEAN_070_CASE_INITIATION_MILESTONE_20250515`
- `snapshot_date`: `2025-05-15` (Day 90 after Section 11 initiation)
- `transition`: `CASE_INITIATION_TO_MILESTONE`
- `entry_date`: `2025-02-14`
- `current_stage`: `SECTION_11`
- `derived_days_in_current_stage`: `90`
- `derived_notice_count`: `1`
- `award_recorded`: `False`
- `duration_at_risk_days`: `35` (Remaining days: 2025-06-19 - 2025-05-15 = 35 days, NOT 125 days)
- `event_observed`: `True`
- `event_date`: `2025-06-19`

### Example 3: Section 19 to Award Checkpoints (Case `CAS_CLEAN_070`)
- `entry_date`: `2025-06-19` (Section 19 Declaration)
- `award_date`: `2026-07-14` (Final Award)
- **Snapshot 1 (Day 0, 2025-06-19)**: `duration_at_risk_days` = **390** days remaining ($E = 1$)
- **Snapshot 2 (Day 90, 2025-09-17)**: `duration_at_risk_days` = **300** days remaining ($E = 1$)
- **Snapshot 3 (Day 180, 2025-12-16)**: `duration_at_risk_days` = **210** days remaining ($E = 1$)
- **Snapshot 4 (Day 270, 2026-03-16)**: `duration_at_risk_days` = **120** days remaining ($E = 1$)
- **Snapshot 5 (Day 365, 2026-06-19)**: `duration_at_risk_days` = **25** days remaining ($E = 1$)
- **Post-Event (2026-07-14)**: Excluded from training ($T_{\text{snap}} \ge T_{\text{event}}$).
