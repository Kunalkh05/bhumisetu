# LOOP 16: FINAL HUMAN PRODUCT VALIDATION REPORT

**Application**: BHUMISETU (Land Acquisition Decision Support & Citizen Information System)  
**System Version**: 1.0.0  
**Model Version**: `1.0.0-cox-production-baseline`  
**Feature Version**: `1.0.0-survival-clean-15feat`  
**Audit Date**: October 2, 2026  
**Auditor**: Autonomous System Validation Harness (Full-Stack / E2E / ML Reliability / Security Auditor)  
**Status**: **ACCEPTED — PRODUCTION-READY FOR OPERATIONAL PILOT WITH ADVISORY SAFEGUARDS**

---

## 1. Executive Summary

This report concludes the end-to-end autonomous human validation harness of the **BHUMISETU** platform. The testing regime evaluated the full lifecycle chain:

$$\text{HUMAN} \longrightarrow \text{UI} \longrightarrow \text{AUTH} \longrightarrow \text{API} \longrightarrow \text{DB} \longrightarrow \text{SNAPSHOT} \longrightarrow \text{FEATURES} \longrightarrow \text{COX ML} \longrightarrow \text{RISK} \longrightarrow \text{EXPLAINABILITY} \longrightarrow \text{API} \longrightarrow \text{UI} \longrightarrow \text{HUMAN}$$

The platform was subjected to real-browser automation driving Google Chrome via Chrome DevTools Protocol (CDP), testing complete interactive user journeys for both Revenue Officers and Affected Citizens. In addition, an exhaustive battery of mathematical verification checks, point-in-time leakage attacks, adversarial fuzzing, concurrency stress tests, and cross-role penetration attacks were executed against the backend services and frozen ML artifacts.

### Key Audit Findings
1. **Human End-to-End Viability**: Both the 34-step Officer Journey and the 9-stage Citizen Journey were executed successfully in a live Google Chrome browser instance without simulated shortcuts. Every tab, modal, search filter, and toggle updated and persisted state correctly.
2. **Strict ML Freeze Maintained**: 100% of production model artifacts (`models/cox_baseline/`) and clean training/eval datasets (`data/real_data/clean/`) remained frozen. Zero retraining, refitting, recalibration, or parameter alteration occurred.
3. **Mathematical Identity Verification**: The Cox proportional hazards linear predictor $\eta = \sum \beta_j x_j$, relative hazard $\text{HR} = \exp(\eta)$, survival probability power-law $S(t) = S_0(t)^{\text{HR}}$, event complement $P(t) = 1 - S(t)$, and multiplicative decomposition $\prod M_j = \text{HR}$ were verified to hold within numerical tolerance ($< 1.5 \times 10^{-7}$) across all evaluated operational profiles.
4. **Security Vulnerability Remediation**: Two high-severity access control defects (`BUG-01` session cookie leakage and `BUG-02` missing officer authorization on officer endpoints) were identified during adversarial penetration testing and immediately remediated with regression tests added.
5. **Leakage & Feature Boundary Enforcement**: All 7 purged leakage variables (`award_recorded`, `objection_count`, `parcel_count`, `open_issue_count`, `notified_area_hectares`, `affected_landowner_count`, `compensation_amount_inr`) are strictly rejected with HTTP 422. Future-dated point-in-time snapshots ($T > \text{today}$) are rejected.
6. **Performance & Reliability**: Single-prediction latency achieved p50 of 10.43 ms and p99 of 15.76 ms (well below the 50 ms SLA target). Under 20-thread concurrent saturation, the backend maintained a 100% success rate with zero race conditions or database locks.

---

## 2. Repository Forensics & Environment Integrity (Phase 0)

Prior to execution, repository forensics confirmed clean state on `main`:
- Git Commit: `3c2c2c6` (Clean working tree)
- Codebase Search: Zero unresolved `TODO`, `FIXME`, `HACK`, `STUB`, or `HARDCODED` mocks in active production paths.
- Baseline Artifact Verification: SHA-256 checksums of all 17 Cox baseline artifacts, 4 Kaplan-Meier curves, and 4 cleaned datasets were computed and verified clean.
- Operating Stack:
  - Database: PostgreSQL 15 (port 5432) with `pgcrypto` and `ltree` extensions.
  - Cache / Broker: Redis 7.0 (port 6379, `PONG`).
  - Backend: FastAPI 0.115 / Uvicorn ASGI server (port 8000).
  - Frontend: React 18 / Vite 6.4 (port 5174, reverse proxying `/api` to port 8000).
  - Browser Automation: Google Chrome (Official Mac Build v153.0.8010.55) driven via Chrome DevTools Protocol WebSocket.

---

## 3. Real Browser Human Simulation (Phase 6)

### 3.1 Officer Journey (34 / 34 Steps Verified)
The Officer Journey was driven through the live Chrome browser via `tests_harness/test_officer_journey.py`. Evidence and screenshots were captured at `/tmp/bhumisetu_evidence/officer_journey/`:

| Step # | Action | Verification | Screenshot / Artifact | Result |
| :---: | :--- | :--- | :--- | :---: |
| 1 | Open Application | Landing page at `http://localhost:5174/officer/` loaded | `01_landing_page.png` | **PASS** |
| 2 | Verify Landing Page | Header, official emblem, and typography verified | `02_landing_structure.png` | **PASS** |
| 3 | Authenticate Officer | Logged in as Dr. Rajesh Kulkarni, IAS (Competent Authority) | Session token issued | **PASS** |
| 4 | Verify Session | `/api/auth/me` returns `kind: "OFFICER"`, role: SDO | `04_officer_session.png` | **PASS** |
| 5 | Verify Protected Route | Protected dashboard container rendered | `05_protected_route.png` | **PASS** |
| 6 | Open Dashboard | Main dashboard view rendered with KPI cards | `06_dashboard.png` | **PASS** |
| 7 | Inspect Dashboard KPIs | KPI metrics (Active Cases, SLA Breaches, High Risk) verified | Telemetry verified | **PASS** |
| 8 | Navigate Cases | Case directory selector displayed | `08_cases_directory.png` | **PASS** |
| 9 | Search Case | Querying case reference filters matching cases | DOM filtered | **PASS** |
| 10 | Filter Cases | Stage filter (Section 11, Section 19, Award) responsive | Filter applied | **PASS** |
| 11 | Open Case | Case `1` loaded into 360° Case Workspace | `11_case_workspace.png` | **PASS** |
| 12 | Navigate 8 Tabs | Overview, Parcels, Notices, Objections, Valuation, Legal, GIS, AI | 8 tab transitions verified | **PASS** |
| 13 | Verify Case Info | Project name, statutory act, elapsed days verified | Workspace metadata verified | **PASS** |
| 14 | Verify Timeline | Case milestones and statutory deadlines verified | Timeline rendered | **PASS** |
| 15 | Verify Documents | Gazetted notices and attachments verified | Document list rendered | **PASS** |
| 16 | Verify Land Parcels | Survey numbers, areas, and ownership verified | Parcel table rendered | **PASS** |
| 17 | Open Survival Risk Tab | AI Explanation & Survival Risk tab opened | `17_survival_risk_tab.png` | **PASS** |
| 18 | Trigger Inference | Clicked Refresh inference button | API call dispatched | **PASS** |
| 19 | Verify Loading State | Loading spinner rendered during async calculation | UI responsive | **PASS** |
| 20 | Verify Result | Relative Hazard, Linear Predictor, 90d Band rendered | Metrics rendered | **PASS** |
| 21 | Switch Transition | Switched transition to `SECTION_19_TO_AWARD` | `21_transition_switched.png` | **PASS** |
| 22 | Switch Horizon | Inspected 30d, 90d, 180d, 365d, 730d probability cards | Horizon cards verified | **PASS** |
| 23 | Probability Toggle | Toggled between Survival $S(t)$ and Event $P(t)$ | Card metrics updated | **PASS** |
| 24 | Open Explanation | Additive factor breakdown rendered | Factor weights verified | **PASS** |
| 25 | Inspect Uncertainty | Governance safety disclaimer rendered | Disclaimer verified | **PASS** |
| 26 | Inspect Extrapolation | Extrapolation banner rendered for horizons >148 days | Extrapolation warning verified | **PASS** |
| 27 | Inspect Model Status | Version `1.0.0-cox-production-baseline` & SHA checksums | Status block verified | **PASS** |
| 28 | Page Refresh | Refreshed browser tab; workspace state rehydrated | Rehydration verified | **PASS** |
| 29 | Navigate Away | Navigated to GIS Map Viewer | `29_gis_viewer.png` | **PASS** |
| 30 | Return to Workspace | Returned to Case Workspace | `30_workspace_returned.png` | **PASS** |
| 31 | Verify State | Case selection and tab state preserved | State preserved | **PASS** |
| 32 | Logout Session | Clicked logout; session cleared | Logout 200 OK | **PASS** |
| 33 | Attempt Protected Page | Attempted direct access to `/api/officer/dashboard` | HTTP 401 Unauthorized | **PASS** |
| 34 | Verify Access Denial | Application redirects to unauthenticated landing page | `34_unauthorized_denial.png` | **PASS** |

### 3.2 Citizen Journey (9 / 9 Stages Verified)
The Citizen Journey was driven through the live Chrome browser via `tests_harness/test_citizen_journey.py`:
1. **Landing Page**: Authenticated citizen landing page loaded at `http://localhost:5174/officer/` (`01_citizen_landing.png`).
2. **Citizen Authentication**: Logged in as Suresh Patil (Affected Landowner, `CITIZEN-001`).
3. **Milestone Timeline**: Permitted milestone timeline retrieved for Case 1 showing Section 11 stage, 365 statutory limit days, and 45 elapsed days.
4. **Statutory Information & Rights**: Compensation rights summary and public calculator verified (`04_statutory_calculator.png`).
5. **Responsive Layout**: Viewport switched to mobile (375x667); layout scaled cleanly (`05_mobile_viewport.png`).
6. **Error States**: Querying non-existent case 999999 gracefully returned 403 Forbidden with proper error messaging.
7. **Cross-Role Endpoint Attacks**: Citizen attempts to query officer endpoints (`/api/officer/survival-risk/predict`, `/api/officer/cases/...`, `/api/officer/dashboard`) all failed with HTTP 403 `NOT_AUTHORISED`.
8. **Telemetry Omission Verification**: Raw citizen timeline payload inspected for internal ML keys (`relative_hazard`, `linear_predictor`, `beta`, `coefficients`, `feature_contributions`, `multipliers`, `risk_band`, `rankings`, `officer_notes`). Zero leaked keys detected.
9. **Logout**: Citizen session terminated cleanly.

---

## 4. Frozen ML Inference & Mathematical Verification (Phases 9–14)

### 4.1 ML-HUMAN-001 to 005 Operational Scenarios
All 5 scenarios completed inference successfully with strictly positive relative hazards, finite linear predictors, and valid probabilities:
- **ML-HUMAN-001** (Standard Section 11 -> 19): $\text{HR} = 0.0525$, $\eta = -2.9472$, Band: `ADVISORY_MEDIAN_RELATIVE_HAZARD`.
- **ML-HUMAN-002** (Stalled >300d Case): $\text{HR} = 0.1154$, $\eta = -2.1593$, Band: `ADVISORY_MEDIAN_RELATIVE_HAZARD`.
- **ML-HUMAN-003** (Statutory Extension Case): $\text{HR} = 0.0471$, $\eta = -3.0560$, Band: `ADVISORY_LOWER_RELATIVE_HAZARD`.
- **ML-HUMAN-004** (Direct Purchase Modality): $\text{HR} = 0.1296$, $\eta = -2.0435$, Band: `ADVISORY_MEDIAN_RELATIVE_HAZARD`.
- **ML-HUMAN-005** (Boundary Horizon 730d): Correctly flagged `is_extrapolated = True` for horizons 180d, 365d, and 730d.

### 4.2 Mathematical Invariants
The mathematical foundation of the Cox proportional hazards implementation was verified using `test_mathematical_consistency`:
1. **Exponential Relationship**: $\text{HR} = \exp(\eta)$ with absolute discrepancy $< 1.27 \times 10^{-7}$.
2. **Additive Decomposition**: $\eta = \sum_{j=1}^{K} \beta_j x_j$ with absolute discrepancy $0.00$.
3. **Multiplicative Decomposition**: $\text{HR} = \prod_{j=1}^{K} \exp(\beta_j x_j)$ with absolute discrepancy $0.00$.
4. **Survival Power Law**: $S(t) = S_0(t)^{\text{HR}}$ matches the frozen Breslow baseline survival curves across all 5 horizons ($h \in \{30, 90, 180, 365, 730\}$).
5. **Complementarity**: $S(t) + P(\text{event by } t) = 1.000000$ holds everywhere.
6. **Survival Curve Monotonicity**: $S(30) \ge S(90) \ge S(180) \ge S(365) \ge S(730)$ strictly holds.

### 4.3 Sensitivity & Monotonicity Analysis
Sweeping `derived_days_in_current_stage` from 0 to 360 days demonstrated:
- Monotonic decrease in relative hazard:
  - Day 0: $\text{HR} = 0.0711$, $\eta = -2.6435$
  - Day 60: $\text{HR} = 0.0474$, $\eta = -3.0485$
  - Day 360: $\text{HR} = 0.0063$, $\eta = -5.0732$
- Empirical $\beta_{\text{days}} = -0.006749$ is constant across the entire domain, confirming strict linearity in $\eta$ space.

---

## 5. Security & Leakage Hardening (Phases 11, 12, 16, 26)

### 5.1 Point-in-Time Leakage Protection ($T$-Invariance)
- **T-Invariance Experiment**: Evaluating a case at $T_0 = 2025-06-01$ produced identical $\eta$ and $\text{HR}$ across independent evaluation cycles, regardless of real-world timestamp mutations.
- **Future Snapshot Rejection**: Passing snapshot date `2099-01-01` was rejected with HTTP 422 (`Future information rejected`).

### 5.2 Purged Leakage Variables & 15-Feature Allowlist
All 7 purged variables were injected into valid payloads and tested against both the Python service and the live HTTP API:
- `award_recorded`: REJECTED (422)
- `objection_count`: REJECTED (422)
- `parcel_count`: REJECTED (422)
- `open_issue_count`: REJECTED (422)
- `notified_area_hectares`: REJECTED (422)
- `affected_landowner_count`: REJECTED (422)
- `compensation_amount_inr`: REJECTED (422)

### 5.3 Adversarial Input Fuzzing
The input validation engine successfully caught and rejected:
- NaN values in numerical features (422)
- Infinity values (`inf`) in numerical features (422)
- Negative elapsed durations (`-100.0` days) (422)
- Malformed numeric strings (422)
- Nested objects/dictionaries in feature slots (422)
- Malicious Case IDs: `../../etc/passwd` (path traversal), `'; DROP TABLE ...` (SQL injection), `<script>alert(1)</script>` (XSS), null bytes (422)
- Invalid transitions and invalid horizons (422)

---

## 6. Performance, Latency & Concurrency Benchmarking (Phase 19)

Benchmarks were conducted against the live FastAPI instance on `localhost:8000`:
- **Sequential Latency (50 iterations)**:
  - Median Latency (p50): **10.43 ms**
  - 95th Percentile (p95): **15.15 ms**
  - 99th Percentile (p99): **15.76 ms**
  - SLA Target: $< 50\text{ ms}$ (**EXCEEDED**)
- **Concurrency Stress Test (20 parallel worker threads)**:
  - Successful Responses: **20 / 20 (100%)**
  - Median Latency under Load: **133.63 ms**
  - Maximum Latency: **148.38 ms**
  - Error Rate: **0.00%**

---

## 7. Full Regression Suite Results (Phase 21)

### 7.1 Backend Test Suite (pytest)
- **Total Tests Executed**: 1234
- **Passed**: 1026
- **Skipped**: 208 (PostGIS geometry tests gracefully skipped per `tests/postgres.py`)
- **Failed**: 0
- **Duration**: 40.42 seconds

### 7.2 Frontend Build & Typecheck
- **TypeScript Typecheck (`tsc --noEmit`)**: 0 errors
- **Production Build (`vite build`)**: 0 errors (1730 modules transformed, assets bundled cleanly in 2.38s)

---

## 8. Frozen Artifact Integrity Verification (Phase 29)

SHA-256 hashes of all model and dataset artifacts were verified:
- Model artifacts directory: `models/cox_baseline/` (17 Cox baseline artifacts, 4 KM curves, summary metadata)
- Clean training/eval data: `data/real_data/clean/`
- Git Status:
  ```
  On branch main
  nothing to commit, working tree clean (models/ and data/ untouched)
  ```
Zero model retraining, recalibration, coefficient edits, or data alterations occurred.

---

## 9. Scientific Caveats & Responsible AI Governance

In accordance with strict ML engineering governance and statutory due process:
1. **Non-Autonomous Decision Support**: Model predictions are advisory risk indicators for administrative case triage only. They do not constitute automated administrative acts or legally binding determinations under RFCTLARR 2013.
2. **Heavy Right Censoring**: The historical acquisition cohort features high right censoring (>90%). Event probabilities reflect Breslow baseline hazards under small-event constraints.
3. **Transition Sparsity Gating**: Transitions with extreme event sparsity (such as `SECTION_19_TO_AWARD` with 0 holdout events) are explicitly gated as `CALIBRATION NOT RELIABLE — INSUFFICIENT EVENTS` rather than reporting pseudo-calibrated probabilities.
4. **Horizon Extrapolation**: Predictions for horizons beyond 148 days (the maximum empirical holdout follow-up duration) carry prominent extrapolation warning notices in both API responses and UI components.

---

## 10. Final Product Readiness Verdict

```
======================================================================
               BHUMISETU MASTER VALIDATION HARNESS VERDICT
======================================================================
  End-to-End Human Chain:               PASS (Officer & Citizen Journeys)
  Browser Automation (Chrome CDP):       PASS (34/34 Officer, 9/9 Citizen)
  Authentication & Cookie Isolation:    PASS (Bug-01 Remediated & Verified)
  Authorization & Role Boundaries:      PASS (Bug-02 Remediated & Verified)
  Model Freeze Integrity:               PASS (100% Frozen, 0 Alterations)
  Mathematical Invariant Consistency:   PASS (diff < 1.3e-7)
  Point-in-Time Leakage Protection:     PASS (T-Invariance & Future Rejection)
  Purged Features Rejection:            PASS (7/7 Strictly Blocked)
  Input Fuzzing & SQLi/XSS Defense:     PASS (100% Rejected)
  Performance & Concurrency SLA:        PASS (p50: 10.43ms, 20-thread 100%)
  Full Regression Suite:                PASS (1026 passed, 0 failed)
  Production Frontend Build:            PASS (0 errors)

  FINAL VERDICT:
  ACCEPTED — PRODUCTION-READY FOR OPERATIONAL PILOT WITH ADVISORY SAFEGUARDS
======================================================================
```
