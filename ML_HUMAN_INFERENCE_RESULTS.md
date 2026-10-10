# ML HUMAN INFERENCE RESULTS (LOOP 16)

## Test Harness Overview
The 5 standard human operational inference scenarios (Phases 9 & 10) were executed against the frozen Cox Proportional Hazards baseline models (`models/cox_baseline/`) using the live FastAPI endpoint `/api/officer/survival-risk/predict` and the internal `SurvivalService` layer.

All 5 scenarios were evaluated on snapshot date `2026-10-02` against transition `SECTION_11_TO_SECTION_19`.

---

## Scenario Breakdown

### ML-HUMAN-001: Standard Section 11 -> 19 Case
- **Description**: Typical proceeding in Solapur district with 45 elapsed days in stage, standard rural infrastructure project.
- **Input Features**:
  ```json
  {
    "derived_days_in_current_stage": 45.0,
    "district": "Solapur",
    "derived_project_type": "Rural Infrastructure",
    "current_stage": "SECTION_11",
    "derived_days_since_case_initiation": 60.0,
    "derived_notice_count": 1.0,
    "extension_count": 0.0,
    "has_statutory_extension": 0.0,
    "act_key": "RFCTLARR_2013",
    "derived_is_direct_purchase": 0.0
  }
  ```
- **Inference Results**:
  - **Linear Predictor ($\eta$)**: `-2.9472`
  - **Relative Hazard ($\text{HR}$)**: `0.0525`
  - **Risk Band (90-Day)**: `ADVISORY_MEDIAN_RELATIVE_HAZARD`
  - **Calibration Status**: `UNCALIBRATED_BASELINE_RETAINED`
  - **Uncertainty Status**: `HIGH_UNCERTAINTY_SPARSE_EVENTS`
  - **Horizon Predictions**:
    | Horizon | Survival Probability $S(t)$ | Event Probability $P(\text{event})$ | Extrapolated Flag |
    | :--- | :--- | :--- | :--- |
    | **30 Days** | 0.999684 | 0.000316 | `False` |
    | **90 Days** | 0.999120 | 0.000880 | `False` |
    | **180 Days** | 0.997230 | 0.002770 | `True` (>148d empirical limit) |
    | **365 Days** | 0.992140 | 0.007860 | `True` (>148d empirical limit) |
    | **730 Days** | 0.985400 | 0.014600 | `True` (>148d empirical limit) |
- **Explainability**:
  - Top factor decreasing hazard: `derived_days_in_current_stage=45.0` ($\beta = -0.006749$, contrib = -0.3037, mult = 0.738)
  - Top factor increasing hazard: `derived_notice_count=1.0` ($\beta = +0.1245$, contrib = +0.1245, mult = 1.133)

---

### ML-HUMAN-002: Stalled Case (>300 Days in Current Stage)
- **Description**: Stalled irrigation canal project in Pune district with 320 days elapsed in Section 11 stage.
- **Input Features**:
  ```json
  {
    "derived_days_in_current_stage": 320.0,
    "district": "Pune",
    "derived_project_type": "Irrigation / Canal",
    "current_stage": "SECTION_11",
    "derived_days_since_case_initiation": 450.0,
    "derived_notice_count": 3.0,
    "extension_count": 1.0,
    "has_statutory_extension": 1.0,
    "act_key": "RFCTLARR_2013",
    "derived_is_direct_purchase": 0.0
  }
  ```
- **Inference Results**:
  - **Linear Predictor ($\eta$)**: `-2.1593`
  - **Relative Hazard ($\text{HR}$)**: `0.1154`
  - **Risk Band (90-Day)**: `ADVISORY_MEDIAN_RELATIVE_HAZARD`
  - **Horizon Predictions**:
    | Horizon | Survival Probability $S(t)$ | Event Probability $P(\text{event})$ | Extrapolated Flag |
    | :--- | :--- | :--- | :--- |
    | **30 Days** | 0.999307 | 0.000693 | `False` |
    | **90 Days** | 0.998069 | 0.001931 | `False` |
    | **180 Days** | 0.993928 | 0.006072 | `True` |
    | **365 Days** | 0.982845 | 0.017155 | `True` |
    | **730 Days** | 0.968250 | 0.031750 | `True` |
- **Explainability**:
  - Higher relative hazard than baseline due to cumulative delay in project initiation and 3 issued notices.

---

### ML-HUMAN-003: Case with Statutory Extension
- **Description**: Yavatmal rural connectivity proceeding with 2 formal statutory timeline extensions granted under RFCTLARR Section 19 proviso.
- **Input Features**:
  ```json
  {
    "derived_days_in_current_stage": 180.0,
    "district": "Yavatmal",
    "derived_project_type": "Rural Infrastructure",
    "current_stage": "SECTION_11",
    "derived_days_since_case_initiation": 240.0,
    "derived_notice_count": 2.0,
    "extension_count": 2.0,
    "has_statutory_extension": 1.0,
    "act_key": "RFCTLARR_2013",
    "derived_is_direct_purchase": 0.0
  }
  ```
- **Inference Results**:
  - **Linear Predictor ($\eta$)**: `-3.0560`
  - **Relative Hazard ($\text{HR}$)**: `0.0471`
  - **Risk Band (90-Day)**: `ADVISORY_LOWER_RELATIVE_HAZARD`
  - **Horizon Predictions**:
    | Horizon | Survival Probability $S(t)$ | Event Probability $P(\text{event})$ | Extrapolated Flag |
    | :--- | :--- | :--- | :--- |
    | **30 Days** | 0.999717 | 0.000283 | `False` |
    | **90 Days** | 0.999211 | 0.000789 | `False` |
    | **180 Days** | 0.997517 | 0.002483 | `True` |
    | **365 Days** | 0.992955 | 0.007045 | `True` |
    | **730 Days** | 0.986915 | 0.013085 | `True` |
- **Explainability**:
  - Statutory extension variables (`has_statutory_extension=1.0`, `extension_count=2.0`) accounted for explicitly without model degradation.

---

### ML-HUMAN-004: Direct Purchase / Consent Modality Case
- **Description**: Direct purchase proceeding in Pune district avoiding compulsory acquisition litigation.
- **Input Features**:
  ```json
  {
    "derived_days_in_current_stage": 30.0,
    "district": "Pune",
    "derived_project_type": "Rural Infrastructure",
    "current_stage": "SECTION_11",
    "derived_days_since_case_initiation": 40.0,
    "derived_notice_count": 1.0,
    "extension_count": 0.0,
    "has_statutory_extension": 0.0,
    "act_key": "RFCTLARR_2013",
    "derived_is_direct_purchase": 1.0
  }
  ```
- **Inference Results**:
  - **Linear Predictor ($\eta$)**: `-2.0435`
  - **Relative Hazard ($\text{HR}$)**: `0.1296`
  - **Risk Band (90-Day)**: `ADVISORY_MEDIAN_RELATIVE_HAZARD`
  - **Horizon Predictions**:
    | Horizon | Survival Probability $S(t)$ | Event Probability $P(\text{event})$ | Extrapolated Flag |
    | :--- | :--- | :--- | :--- |
    | **30 Days** | 0.999222 | 0.000778 | `False` |
    | **90 Days** | 0.997831 | 0.002169 | `False` |
    | **180 Days** | 0.993183 | 0.006817 | `True` |
    | **365 Days** | 0.980753 | 0.019247 | `True` |
    | **730 Days** | 0.964408 | 0.035592 | `True` |

---

### ML-HUMAN-005: Boundary Horizon Extrapolation Verification (Horizon=730)
- **Description**: Standard proceeding tested at the maximum 2-year statutory boundary horizon ($h = 730$ days).
- **Input Features**: Same as standard Solapur rural case (`derived_days_in_current_stage=90.0`).
- **Inference Results**:
  - **Linear Predictor ($\eta$)**: `-3.2510`
  - **Relative Hazard ($\text{HR}$)**: `0.0387`
  - **Risk Band (90-Day)**: `ADVISORY_LOWER_RELATIVE_HAZARD`
  - **Extrapolation Verification**:
    - Horizon 30d: `is_extrapolated = False`
    - Horizon 90d: `is_extrapolated = False`
    - Horizon 180d: `is_extrapolated = True` (Exceeds empirical 148-day holdout limit)
    - Horizon 365d: `is_extrapolated = True` (Exceeds empirical 148-day holdout limit)
    - Horizon 730d: `is_extrapolated = True` (Exceeds empirical 148-day holdout limit)
  - **Extrapolation Warning Notice**:
    > "Extrapolated horizon: 730 days exceeds empirical observed holdout window (148 days). Probability reflects model proportional hazards baseline extension."

---

## Mathematical Invariant Summary Across Scenarios
1. $\text{HR} = \exp(\eta)$ verified across all 5 cases (maximum absolute discrepancy $< 1.5 \times 10^{-7}$).
2. $\eta = \sum \beta_j x_j$ verified across all 5 cases (exact identity in floating point space).
3. $\text{HR} = \prod \exp(\beta_j x_j)$ verified across all 5 cases (maximum absolute discrepancy $< 5.0 \times 10^{-4}$).
4. $S(t) + P(\text{event by } t) = 1.000000$ verified across all 25 horizon predictions.
5. Monotonicity $S(30) \ge S(90) \ge S(180) \ge S(365) \ge S(730)$ strictly held in 100% of cases.
