# Non-Parametric Survival Analysis Baseline: Educational Kaplan-Meier Report

**Execution Phase**: LOOP 7B — EDUCATIONAL KAPLAN-MEIER IMPLEMENTATION  
**Module**: [`bhumi-setu/ml/src/educational_kaplan_meier.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/ml/src/educational_kaplan_meier.py)  
**Dataset Input**: [`data/real_data/clean/survival_train_targets.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/survival_train_targets.csv) (**TRAIN ONLY**)  
**Audit Date**: September 2026  
**Final Status**: `PASS — EDUCATIONAL KAPLAN-MEIER COMPLETE`

---

## 1. Executive Summary & Educational Disclaimer

> [!IMPORTANT]
> ### Educational Baseline Only — Not Production Survival Library
> This module is an educational, self-contained implementation of the non-parametric Kaplan-Meier estimator written strictly using the Python standard library (`csv`, `math`, `collections`, `dataclasses`, `typing`).
> - It contains **zero external scientific dependencies** (no `pandas`, `numpy`, `scipy`, or `lifelines`).
> - It does **NOT** implement semi-parametric Cox Proportional Hazards or a production survival pipeline.
> - It consumes **strictly the training cohort targets** (`survival_train_targets.csv`, $N = 896$ snapshots across 159 cases). The prospective evaluation cohort ($N = 167$ snapshots across 89 cases) remains completely untouched and unobserved.

---

## 2. Mathematical Formulation

The non-parametric Kaplan-Meier survival estimator is formulated as:

$$\hat{S}(t) = \prod_{t_i \le t} \left(1 - \frac{d_i}{n_i}\right)$$

Where:
- $t_i$: Unique, ordered event times where at least one transition event was observed ($d_i > 0$).
- $n_i$: Number of cases at risk immediately prior to event time $t_i$, defined as all cases with duration $\ge t_i$.
- $d_i$: Number of observed milestone transition events occurring at duration $t_i$.
- $c_i$: Number of observations right-censored in the half-open interval $[t_i, t_{i+1})$.

### Cumulative Hazard Function
$$\hat{H}(t) = -\ln \hat{S}(t)$$

### Greenwood's Formula for Standard Error
$$\widehat{\operatorname{Var}}(\hat{S}(t)) = \hat{S}(t)^2 \sum_{t_i \le t} \frac{d_i}{n_i (n_i - d_i)}, \quad \operatorname{SE}(\hat{S}(t)) = \sqrt{\widehat{\operatorname{Var}}(\hat{S}(t))}$$

---

## 3. Tie & Censoring Handling Conventions

1. **Tied Event Times ($d_i > 1$)**:
   Multiple cases completing a statutory milestone at the exact same duration $T$ are aggregated into $d_i$, all drawing against the shared risk set $n_i$ at duration $T$.
2. **Tied Event and Censoring ($d_i \ge 1$ and $c_i \ge 1$ at same duration $T$)**:
   Under the standard survival analysis convention (Kalbfleisch & Prentice 2002; Fleming & Harrington 1991):
   - Individuals censored at duration $T$ were under observation up to and including time $T$, so they are included in the risk set $n_i$ at time $T$.
   - The events $d_i$ are evaluated first at time $T$, reducing $\hat{S}(T)$.
   - The censored individuals exit the risk set immediately after time $T$, and are therefore excluded from risk sets for all future times $t > T$.
3. **Censoring Before an Event ($C < t_i$)**:
   Any cases censored at duration $C < t_i$ exit the risk set prior to $t_i$ and do not contribute to $n_i$.
4. **Exact Risk Set Balance Invariant**:
   For every consecutive event time interval $[t_i, t_{i+1})$, the conservation equation holds exactly:
   $$n_{i+1} = n_i - d_i - c_i$$

---

## 4. Real BhumiSetu Training Data Summary

| Cohort / Transition | Observations ($N$) | Observed Events ($E=1$) | Right-Censored ($E=0$) | Censoring Rate | Unique Event Times |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **All Transitions Combined** | 896 | 40 | 856 | 95.54% | 15 |
| **`SECTION_11_TO_SECTION_19`** | 84 | 16 | 68 | 80.95% | 7 |
| **`SECTION_19_TO_AWARD`** | 203 | 6 | 197 | 97.04% | 6 |
| **`CASE_INITIATION_TO_MILESTONE`** | 609 | 18 | 591 | 97.04% | 9 |

---

## 5. Survival Estimates at Statutory Milestone Horizons

$$\hat{S}(t) = \text{Probability that milestone transition has NOT yet occurred by day } t$$

| Transition | 30 Days | 90 Days | 180 Days | 365 Days (1 Year) | 730 Days (2 Years) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **All Transitions** | 0.9966 | 0.9649 | 0.9600 | 0.9528 | 0.9505 |
| **`SECTION_11_TO_SECTION_19`** | 0.9881 | 0.8301 | 0.8177 | **0.8034** | 0.8034 |
| **`SECTION_19_TO_AWARD`** | 0.9948 | 0.9948 | 0.9888 | **0.9635** | 0.9499 |
| **`CASE_INITIATION_TO_MILESTONE`** | 0.9984 | 0.9745 | 0.9710 | **0.9691** | 0.9691 |

### Statutory Interpretations:
1. **Section 11 $\rightarrow$ Section 19 (Statutory Window = 365 Days)**:
   - At day 365, $\hat{S}(365) = 0.8034$.
   - This indicates that **19.66%** of cases successfully progressed from preliminary notification to Section 19 declaration within 1 year, while **80.34%** of cases remained ongoing or stalled past the statutory window.
2. **Section 19 $\rightarrow$ Award (Statutory Window = 365 Days)**:
   - At day 365, $\hat{S}(365) = 0.9635$.
   - Only **3.65%** reached the final award stage within 1 year; **96.35%** remained pending. By day 730 (2 years), $\hat{S}(730) = 0.9499$ (94.99% pending).

---

## 6. Complete Kaplan-Meier Lifecycle Tables (Train Only)

### Transition 1: `SECTION_11_TO_SECTION_19` ($N = 84$, Events = 16, Censored = 68)

| Time ($t$) | At Risk ($n_i$) | Events ($d_i$) | Censored ($c_i$) | $\hat{S}(t)$ | $\hat{H}(t)$ | Std Error | 95% CI Lower | 95% CI Upper |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 84 | 1 | 1 | 0.988095 | 0.011976 | 0.011835 | 0.964899 | 1.000000 |
| **59** | 82 | 1 | 0 | 0.976045 | 0.024246 | 0.016766 | 0.943183 | 1.000000 |
| **60** | 81 | 8 | 2 | 0.879646 | 0.128236 | 0.035887 | 0.809307 | 0.949984 |
| **80** | 71 | 1 | 0 | 0.867256 | 0.142421 | 0.037302 | 0.794145 | 0.940368 |
| **87** | 70 | 3 | 0 | 0.830088 | 0.186224 | 0.041178 | 0.749379 | 0.910798 |
| **91** | 67 | 1 | 9 | 0.817699 | 0.201261 | 0.042316 | 0.734760 | 0.900638 |
| **181** | 57 | 1 | 56 | 0.803353 | 0.218961 | 0.044036 | 0.717042 | 0.889664 |

---

### Transition 2: `SECTION_19_TO_AWARD` ($N = 203$, Events = 6, Censored = 197)

| Time ($t$) | At Risk ($n_i$) | Events ($d_i$) | Censored ($c_i$) | $\hat{S}(t)$ | $\hat{H}(t)$ | Std Error | 95% CI Lower | 95% CI Upper |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **25** | 192 | 1 | 25 | 0.994792 | 0.005222 | 0.005182 | 0.984635 | 1.000000 |
| **120** | 166 | 1 | 25 | 0.988799 | 0.011264 | 0.007675 | 0.973757 | 1.000000 |
| **210** | 140 | 1 | 13 | 0.981736 | 0.018432 | 0.010079 | 0.961981 | 1.000000 |
| **238** | 126 | 1 | 32 | 0.973945 | 0.026401 | 0.012497 | 0.949451 | 0.998438 |
| **300** | 93 | 1 | 21 | 0.963472 | 0.037213 | 0.016075 | 0.931965 | 0.994979 |
| **390** | 71 | 1 | 70 | 0.949902 | 0.051403 | 0.021021 | 0.908701 | 0.991103 |

*(Note: 11 observations were right-censored prior to $t = 25$ days, yielding $n(25) = 203 - 11 = 192$ cases at risk).*

---

### Transition 3: `CASE_INITIATION_TO_MILESTONE` ($N = 609$, Events = 18, Censored = 591)

| Time ($t$) | At Risk ($n_i$) | Events ($d_i$) | Censored ($c_i$) | $\hat{S}(t)$ | $\hat{H}(t)$ | Std Error | 95% CI Lower | 95% CI Upper |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 609 | 1 | 7 | 0.998358 | 0.001643 | 0.001641 | 0.995141 | 1.000000 |
| **35** | 601 | 1 | 7 | 0.996697 | 0.003309 | 0.002327 | 0.992135 | 1.000000 |
| **59** | 593 | 1 | 6 | 0.995016 | 0.004996 | 0.002863 | 0.989404 | 1.000000 |
| **60** | 586 | 8 | 8 | 0.981432 | 0.018742 | 0.005527 | 0.970599 | 0.992265 |
| **80** | 570 | 1 | 2 | 0.979710 | 0.020498 | 0.005786 | 0.968370 | 0.991050 |
| **87** | 567 | 3 | 0 | 0.974527 | 0.025803 | 0.006509 | 0.961769 | 0.987285 |
| **91** | 564 | 1 | 18 | 0.972799 | 0.027577 | 0.006734 | 0.959602 | 0.985997 |
| **125** | 545 | 1 | 26 | 0.971014 | 0.029415 | 0.006977 | 0.957339 | 0.984690 |
| **181** | 518 | 1 | 517 | 0.969139 | 0.031348 | 0.007248 | 0.954932 | 0.983345 |

---

## 7. Output Artifacts on Disk

The life tables have been saved as CSV artifacts in `models/kaplan_meier_baseline/`:
- `models/kaplan_meier_baseline/km_all_transitions.csv`
- `models/kaplan_meier_baseline/km_section_11_to_section_19.csv`
- `models/kaplan_meier_baseline/km_section_19_to_award.csv`
- `models/kaplan_meier_baseline/km_case_initiation_to_milestone.csv`

---

## 8. Limitations & Constraints

1. **Heavy Right-Censoring**:
   Overall censoring in the training data is **95.54%** (856 of 896 snapshots right-censored). For `SECTION_19_TO_AWARD`, censoring is **97.04%** (only 6 events across 203 snapshots).
2. **Support Truncation**:
   The maximum observed event time in `SECTION_11_TO_SECTION_19` is day 181. For horizons beyond day 181, $\hat{S}(t)$ remains constant at $\hat{S}(181) = 0.8034$ because no subsequent events were recorded in the training cohort.
3. **No Covariates**:
   Kaplan-Meier estimates are unconditioned marginal distributions. They do not account for administrative district, project type, statutory extensions, or land parcel size.
4. **Evaluation Set Completely Preserved**:
   The prospective evaluation cohort ($N = 167$) was strictly excluded from all calculations.
