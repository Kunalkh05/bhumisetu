# BHUMISETU Survival Target Definition (LOOP 2)

This document formalizes the **Time-to-Event (Survival Analysis)** formulation for BHUMISETU, replacing restrictive binary classification with statutory milestone duration modeling under right-censoring.

---

## 1. Executive Rationale & Transition from Binary to Survival Modeling

In real-world government land acquisition (RFCTLARR Act 2013):
- Only a small fraction of acquisition cases in public gazettes have reached final completion (Award). In Maharashtra collectorate records, **91.1% (247 / 271)** of cases are active in-progress proceedings with preliminary statutory notifications.
- Traditional binary classification (`DELAYED` vs `NOT_DELAYED`) requires closed lifecycles, forcing the modeler either to drop 91% of available cases or to make ungrounded assumptions regarding active proceedings.
- **Survival Analysis (Time-to-Event Modeling)** solves this fundamental limitation. Every single acquisition proceeding provides actionable statistical information:
  - **Completed milestones ($E = 1$)** provide observed duration $T$.
  - **Ongoing proceedings ($E = 0$)** provide right-censored duration $T_{\text{censored}} = T_{\text{cutoff}} - T_{\text{entry}}$, informing the survival probability distribution $S(t) = P(T > t)$.

---

## 2. Survival Target Definitions

BHUMISETU implements three statutory time-to-event targets:

### Target 1: `SECTION_11_TO_SECTION_19`
- **Legal Basis**: Section 11(1) publication to Section 19(1) declaration under the RFCTLARR Act 2013.
- **Statutory Window**: **365 days (12 months)**. Under Section 19(1), if no declaration is published within 12 months from the date of the preliminary notification, the notification lapses.
- **Entry Event**: Date of publication of the Section 11 Preliminary Notification (`SECTION_11` or synthetic alias `PN`).
- **Exit Event**: Date of declaration under Section 19(1) (`SECTION_19` or synthetic alias `DECLARATION`).
- **Formulation**:
  - If Section 19 declaration is observed on or before observation cutoff $T_{\text{cutoff}}$:
    $$T = \text{Section19\_date} - \text{Section11\_date}, \quad E = 1$$
  - If Section 19 declaration has not occurred by observation cutoff $T_{\text{cutoff}}$:
    $$T = T_{\text{cutoff}} - \text{Section11\_date}, \quad E = 0 \quad (\text{Right-Censored})$$

### Target 2: `SECTION_19_TO_AWARD`
- **Legal Basis**: Section 19(1) declaration to Final Award under Section 23/25 of the RFCTLARR Act 2013.
- **Statutory Window**: **365 days (12 months)** from the date of declaration under Section 25.
- **Entry Event**: Date of publication of Section 19 Declaration (`SECTION_19` or synthetic alias `DECLARATION`).
- **Exit Event**: Date of Final Award (`AWARD`).
- **Formulation**:
  - If Award is recorded on or before observation cutoff $T_{\text{cutoff}}$:
    $$T = \text{Award\_date} - \text{Section19\_date}, \quad E = 1$$
  - If Award has not occurred by observation cutoff $T_{\text{cutoff}}$:
    $$T = T_{\text{cutoff}} - \text{Section19\_date}, \quad E = 0 \quad (\text{Right-Censored})$$

### Target 3: `CASE_INITIATION_TO_MILESTONE`
- **Legal Basis**: General duration formulation from initiation of land acquisition to target statutory milestone.
- **Entry Event**: Date of first recorded acquisition notification (e.g. `GENERAL_NOTICE`, `INTAKE`, or `SECTION_11`).
- **Exit Event**: Target statutory milestone (e.g. `SECTION_19` or `AWARD`).
- **Formulation**:
  - If milestone is reached by $T_{\text{cutoff}}$:
    $$T = \text{Milestone\_date} - \text{Initiation\_date}, \quad E = 1$$
  - If milestone has not occurred by $T_{\text{cutoff}}$:
    $$T = T_{\text{cutoff}} - \text{Initiation\_date}, \quad E = 0 \quad (\text{Right-Censored})$$

---

## 3. Mathematical Formulation & Outcome Types

The output of survival labelling maps directly to the codebase dataclass [`LabelOutcome`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/ml/src/labelling/definition.py):

```python
@dataclass(frozen=True)
class LabelOutcome:
    label: Literal["DELAYED", "NOT_DELAYED", "CENSORED"]
    time_to_event_days: int | None
    event_observed: bool | None
    reason: str
    label_definition_version: str
```

### Outcome Mapping Rules:
1. **Observed Transitions ($E = 1$)**:
   - `event_observed = True`
   - `time_to_event_days = T` where $T = \text{Exit Date} - \text{Entry Date} \ge 0$
   - `label = "DELAYED"` if $\text{Exit Date} > \text{Statutory Deadline}$, else `"NOT_DELAYED"`
   - `reason = "EXIT_AFTER_DEADLINE"` or `"EXITED_BY_DEADLINE"`
2. **Right-Censored Transitions ($E = 0$)**:
   - `event_observed = False`
   - `time_to_event_days = T` where $T = T_{\text{cutoff}} - \text{Entry Date} \ge 0$
   - **Crucial Rule**: `time_to_event_days` is **never set to `None`** for right-censored survival observations. It preserves the observed duration at risk.
   - `label = "CENSORED"` (Never coerced into `"NOT_DELAYED"` or `"DELAYED"`)
   - `reason = "RIGHT_CENSORED"`

---

## 4. Observation Cutoff ($T_{\text{cutoff}}$) & Temporal Integrity

The observation cutoff $T_{\text{cutoff}}$ (passed as `now: date` in `label_row`) defines the temporal boundary for survival analysis:

1. **Reusing Existing Architecture**:
   - The parameter `now: date` in `label_row(view, t, definition=..., deadline=..., now=...)` serves as the canonical observation cutoff.
   - When running inference or retrospective evaluations, $T_{\text{cutoff}}$ represents the historical snapshot date, preventing the model from knowing any events that transpired after that day.
2. **Leakage Safeguards**:
   - **Future Events Suppression**: If an exit event occurs on calendar date $D > T_{\text{cutoff}}$, it is strictly treated as unobserved at time $T_{\text{cutoff}}$. The observation is right-censored with $T = T_{\text{cutoff}} - T_{\text{entry}}$ and $E = 0$.
   - **Precedence Validation**: If $T_{\text{cutoff}} < T_{\text{entry}}$, the call raises `ValueError` ("Observation cutoff cannot precede stage entry date"). Negative durations are mathematically impossible.
   - **Contradiction Validation**: If an exit event is dated prior to entry date ($T_{\text{exit}} < T_{\text{entry}}$), `ValueError` is raised, guarding against contradictory source documents.

---

## 5. Statutory Extensions Handling

Under the Proviso to Section 25 of the RFCTLARR Act 2013, the appropriate Government may extend the 12-month period for making an award by up to 12 additional months.

**Handling Rule**:
- **Statutory extensions do NOT alter the observed survival duration $T$**.
- $T$ strictly measures physical elapsed calendar days from stage entry to exit (or cutoff).
- Extension orders are preserved as administrative features (e.g. `extension_count`, `has_statutory_extension`, `extension_duration_days`) in the feature store for downstream model training, rather than distorting true event arrival times.

---

## 6. Concrete Examples

### Example 1: Completed Section 11 $\rightarrow$ Section 19 (Nagpur Case `CAS_CLEAN_018`)
- Section 11 Publication: `2024-06-25`
- Section 19 Declaration: `2024-10-09`
- Statutory Deadline: `2025-06-25` (365 days)
- Observation Cutoff: `2026-09-29`
- **Outcome**:
  - $T = \text{2024-10-09} - \text{2024-06-25} = \mathbf{106 \text{ days}}$
  - $E = \mathbf{1 \text{ (True)}}$
  - `label = "NOT_DELAYED"`
  - `reason = "EXITED_BY_DEADLINE"`

### Example 2: Ongoing Section 11 Proceeding (Pune Case `CAS_CLEAN_001`)
- Section 11 Publication: `2024-03-01`
- Section 19 Declaration: None recorded in gazette
- Statutory Deadline: `2025-03-01` (365 days)
- Observation Cutoff: `2026-09-29`
- **Outcome**:
  - $T = \text{2026-09-29} - \text{2024-03-01} = \mathbf{942 \text{ days}}$
  - $E = \mathbf{0 \text{ (False)}}$
  - `label = "CENSORED"`
  - `reason = "RIGHT_CENSORED"`

### Example 3: Extended Proceeding with Final Award (Nagpur Case `CAS_CLEAN_130`)
- Section 19 Declaration: `2022-09-08`
- Final Award: `2023-10-03`
- Statutory Extension Orders: 2 documented extensions granted by Commissioner
- Observation Cutoff: `2026-09-29`
- **Outcome**:
  - $T = \text{2023-10-03} - \text{2022-09-08} = \mathbf{390 \text{ days}}$
  - $E = \mathbf{1 \text{ (True)}}$
  - `label = "DELAYED"` (statutory baseline 365 days without baseline override)
  - `reason = "EXIT_AFTER_DEADLINE"`
  - Note: Extensions are documented in features; true physical elapsed duration is 390 days.

---

## 7. Real Dataset Label Yield Summary

Evaluated on the 271 clean Maharashtra acquisition cases:

| Transition Target | Eligible Cases | Observed ($E=1$) | Right-Censored ($E=0$) | Mean Observed $T$ | Mean Censored $T$ |
|---|---|---|---|---|---|
| `SECTION_11_TO_SECTION_19` | 91 | 17 (18.7%) | 74 (81.3%) | 67.8 days | 167.9 days |
| `SECTION_19_TO_AWARD` | 47 | 1 (2.1%) | 46 (97.9%) | 390.0 days | 447.7 days |

**Zero observations dropped**. Survival analysis retains 100% of cases entering statutory milestones.
