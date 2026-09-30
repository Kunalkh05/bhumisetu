# LOOP 12 — BHUMISETU OFFICER PORTAL FRONTEND INTEGRATION REPORT

**Date**: September 30, 2026  
**System**: BHUMISETU National Land Acquisition Management & Decision Support Platform  
**Module**: Officer Portal — Survival Risk, Horizon Projections & Auditable Explainability Surface  
**Technology**: React 19 / TypeScript 5.8 / Vite 6.4 / Tailwind CSS v4  
**Integrated Service**: FastAPI Backend (`/api/officer/survival-risk/*`, `/api/officer/cases/{case_id}/survival-risk/*`)  
**ML Model**: Cox Proportional Hazards Production Baseline (`cox_baseline_v1`)  
**Feature Contract**: Temporal Clean 15-Feature Specification (`survival_features_v1`)  
**Final Status**: **PASS — FRONTEND SURVIVAL INTEGRATION COMPLETE**

---

## 1. Executive Summary

LOOP 12 completes the officer-facing frontend integration of the BHUMISETU Survival Risk, Calibration, and Explainability Engine into the React 19 Officer Portal. 

The implementation replaces legacy synthetic AI delay factor cards with an interactive, auditable, and statutory governance-compliant analytical dashboard located under **Tab 7 ("Survival Risk & ML Engine (Cox PH)")** of the **Case Workspace** (`CaseWorkspace.tsx`).

Key capabilities delivered:
1. **Interactive Survival Risk Dashboard** (`SurvivalRiskDashboard.tsx`): Case-level point-in-time risk projection with dynamic statutory transition switching (`SECTION_11_TO_SECTION_19`, `SECTION_19_TO_AWARD`, `CASE_INITIATION_TO_MILESTONE`).
2. **Prominent Hazard vs. Probability Demarcation**: Rigorous visual distinction between Relative Hazard ratio ($\exp(\eta)$, reference cohort: $1.00\times$) and Transition Event Probability ($P(\text{event by } t) = 1 - S(t)$).
3. **Statutory Horizon Risk Matrix** (`HorizonRiskCards.tsx`): Multi-horizon risk projection cards across the 5 statutory horizons ($30$d, $90$d, $180$d, $365$d, $730$d), with clear empirical vs. extrapolated tags.
4. **Accessible SVG Survival Curve** (`SurvivalCurveChart.tsx`): Continuous visual representation of parametric survival $S(t) = S_0(t)^{\exp(\eta)}$, with an empirical cutoff boundary ($148$ days), toggles between $S(t)$ and $P(t)$, hover tooltips, and an accessible tabular data fallback.
5. **Auditable Explainability Engine** (`ExplainabilityPanel.tsx`): Additive decomposition of the linear predictor ($\eta = \sum \beta_j x_j$) into positive hazard contributors and negative hazard mitigators with strict non-causal terminology and missing feature audits.
6. **Multi-Tier Statistical Uncertainty & Governance Notices** (`UncertaintyNotice.tsx`): Automated alerts for extreme uncertainty (zero-event holdout cohorts), small-sample bias ($\text{EPV} < 10$), withheld calibration status, and mandatory non-autonomous decision support disclaimers.
7. **ML Subsystem Health & Telemetry** (`ModelStatusSection.tsx`): Live inspection of loaded model version, feature contract, statutory transitions, and artifact checksums.
8. **Resilient API Service Client** (`survivalRiskService.ts`): Typed REST client featuring query caching ($60$s TTL), in-flight request deduplication, structured error handling, and high-fidelity offline demonstration fallbacks based on real fitted Cox baseline parameters.

---

## 2. Frontend Architecture & Component Tree

The survival analysis subsystem is modularized inside `bhumi-setu/apps/web/src/components/officer/survival/`:

```
bhumi-setu/apps/web/src/
├── types/
│   └── survival.ts                    # TypeScript schemas for risk, explanation, health, horizons
├── services/
│   └── survivalRiskService.ts         # Singleton API client with caching, deduplication & fallback
└── components/
    └── officer/
        ├── CaseWorkspace.tsx          # Houses Sub-Tab 7 ("Survival Risk & ML Engine")
        └── survival/
            ├── SurvivalRiskDashboard.tsx  # Main coordinator & transition controller
            ├── HorizonRiskCards.tsx       # 5 Statutory horizon cards (30d, 90d, 180d, 365d, 730d)
            ├── SurvivalCurveChart.tsx     # Vector SVG survival curve with 148d cutoff line
            ├── ExplainabilityPanel.tsx    # Additive decomposition, hazard multipliers & narratives
            ├── UncertaintyNotice.tsx      # Multi-tier uncertainty, extrapolation & statutory disclaimers
            └── ModelStatusSection.tsx     # Subsystem health, model version & checksum inspection
```

---

## 3. Statutory Transition Support

The dashboard supports dynamic querying across all three validated statutory milestone transitions:

| Transition Key | Milestone Description | Primary Statutory Window | Holdout Event Context |
|---|---|---|---|
| `SECTION_11_TO_SECTION_19` | Preliminary Notification &rarr; Final Declaration | 365 days (RFCTLARR §19(1)) | 16 training events / 4 eval events |
| `SECTION_19_TO_AWARD` | Declaration &rarr; Compensation Award | 730 days (RFCTLARR §25) | 6 training events / 0 eval events (Zero-Event Warning) |
| `CASE_INITIATION_TO_MILESTONE` | Proceeding Initiation &rarr; First Statutory Milestone | Variable operational | 18 training events / 0 eval events |

Transition switching in `SurvivalRiskDashboard.tsx` dynamically triggers parallel API requests (`survivalRiskService.getCaseSurvivalRisk` and `survivalRiskService.getCaseSurvivalExplanation`) with smooth loading states and zero layout shift.

---

## 4. Key UI/UX Innovations & Compliance Features

### 4.1 Hazard Ratio vs Event Probability Demarcation
To avoid cognitive confusion between hazard ratios and event probabilities:
- **Relative Hazard** is styled in slate monochrome with an explicit $\times$ suffix (e.g. `0.052x`), alongside a label explaining comparison against the baseline reference cohort.
- **Event Probability** is styled in distinct emerald green as an exact percentage (e.g. `0.73%`), explicitly labeled $P(\text{Event by } 90\text{d})$.
- Educational footnotes reinforce that relative hazard is a proportional intensity ratio ($\exp(\eta)$), *not* a percentage probability.

### 4.2 Empirical Follow-Up Ceiling & Extrapolation Visibility
Empirical follow-up in the historical dataset ceases at $148$ days:
- Horizons exceeding $148$ days ($180$d, $365$d, $730$d) display an amber `EXTRAPOLATED` badge and dashed borders.
- The `SurvivalCurveChart` renders empirical follow-up ($\le 148$d) as a solid deep navy curve (`#002642`) and transitions to a dashed sky blue curve (`#0284c7`) with shaded background past a vertical amber threshold line at $148$ days.

### 4.3 Auditable Explainability with Strict Non-Causal Policy
In compliance with ethical AI guidelines and statutory administrative law:
- All factor contributions use strict correlational phrasing: `"contributed +X.XXXX to the model's estimated log-hazard (hazard multiplier: X.XXx relative to baseline)"`.
- The interface strictly forbids causal assertions (e.g., `"caused the delay"` or `"responsible for proceedings stalling"`).
- Explanations display the exact linear predictor $\eta$, hazard multipliers ($\exp(\beta_j x_j)$), and list unavailable/imputed features in an explicit missing feature audit trail.

### 4.4 Multi-Tier Statistical Uncertainty Alerts
The UI dynamically renders contextual alerts based on the model's metadata:
1. **Zero-Event Warning**: If a transition has zero observed events in the evaluation cohort (e.g. `SECTION_19_TO_AWARD`), an amber warning advises extreme administrative caution.
2. **Small-Sample Sparsity**: For models with Events Per Variable (EPV) $< 10$, a small-sample advisory informs the officer that confidence intervals are wide.
3. **Calibration Governance**: Clarifies that empirical calibration curves were deliberately withheld in LOOP 9 to prevent overfitting to sparse data.
4. **Statutory Non-Autonomous Notice**: Reiterates that predictions are non-binding decision support aids; decisions remain the sole statutory responsibility of the competent authority.

---

## 5. Security, Authorization & Redaction

### 5.1 Role-Based Access Enforcement
- `SurvivalRiskDashboard` inspects `currentUser.role`. If a citizen user navigates to the component, it renders an `Unauthorized Access` security state (`Lock` icon), prohibiting display of internal ML parameters.
- Citizen users interact exclusively with the public procedural milestone surface (`PropertyTimelineView.tsx`), which consumes `/api/citizen/cases/{case_id}/milestone-timeline` and discloses statutory time limits and rights without internal model coefficients or risk bands.

### 5.2 API Error & Boundary Defense
- `survivalRiskService.ts` wraps all network requests, translating HTTP 401 (`UNAUTHENTICATED`), HTTP 403 (`NOT_AUTHORISED`), and HTTP 422 (`VALIDATION_FAILED`) into user-friendly error dialogs.
- Internal stack traces, SQL errors, or Python exceptions are never exposed to the client.

---

## 6. Verification & Quality Assurance

### 6.1 TypeScript Strict Compilation
```bash
npm run typecheck
```
**Result**: **PASS** (0 errors, 0 warnings across all files).

### 6.2 Production Asset Build
```bash
npm run build
```
**Result**: **PASS** (Vite v6.4.3 production bundle successfully emitted in 1.32s; assets verified in `dist/assets/`).

### 6.3 Live API Integration Verification
The frontend service was verified against the active FastAPI backend (`http://localhost:8000`):
- `POST /api/auth/persona` &rarr; Session token and CSRF issued (HTTP 200).
- `GET /api/officer/survival-risk/health` &rarr; Model `1.0.0-cox-production-baseline` reported healthy (HTTP 200).
- `GET /api/officer/cases/CASE-0042/survival-risk` &rarr; Analytical risk payload received (HTTP 200).
- `GET /api/officer/cases/CASE-0042/survival-risk/explanation` &rarr; Linear predictor $\eta = -2.9472$ with factor contributions received (HTTP 200).

### 6.4 Backend ML Test Suite
All 25 survival API unit tests in `apps/api/tests/ml/test_survival_api.py` and the complete ML battery of 224 tests pass cleanly.

---

## 7. Final Status

**PASS — FRONTEND SURVIVAL INTEGRATION COMPLETE**

All tasks for LOOP 12 have been executed and validated:
- TypeScript compilation is clean.
- Production bundle builds successfully.
- Officer portal Tab 7 fully operational.
- Citizen portal strictly redacted.
- Non-causal governance constraints preserved.
