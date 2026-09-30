# LOOP 11 — BHUMISETU ML/API PRODUCTION INTEGRATION REPORT

**Date**: September 30, 2026  
**System**: BHUMISETU Land Acquisition Decision Support System  
**Module**: Production Inference, Explainability & Public Redaction Gateway  
**Service**: FastAPI (`bhumi-setu/apps/api`)  
**ML Model**: Cox Proportional Hazards Production Baseline (`cox_baseline_v1`)  
**Feature Contract**: Temporal Clean 15-Feature Specification (`survival_features_v1`)  
**Calibration Governance**: Preserved from LOOP 9 (`CALIBRATION NOT RELIABLE DUE TO EVENT SPARSITY`)  
**Explainability Engine**: Preserved from LOOP 10 (`PASS — SURVIVAL EXPLAINABILITY COMPLETE`)  
**Final Status**: **PASS — ML/API INTEGRATION COMPLETE**

---

## 1. Existing API Architecture

The BHUMISETU FastAPI backend (`bhumi-setu/apps/api`) organizes its API surfaces by **consumer role** rather than arbitrary domain subsystems, adhering to statutory governance requirements (§8.2, §9):
- **`officer_router` (`/api/officer/*`)**: Authenticated officer portal JSON API. Requires active officer credentials (`Principal(kind="OFFICER")`), validated against live database permissions and jurisdiction scopes on every request.
- **`citizen_router` (`/api/citizen/*`)**: Authenticated single-case citizen portal JSON API (`Principal(kind="CITIZEN", case_id=...)`).
- **`citizen_html` (`/c/*`)**: Server-rendered citizen surface, passing context through `render_gated`.
- **`internal_router` (`/internal/*`)**: Service-to-service internal surface secured via bearer tokens.

Every router is constructed with `route_class=GatedRoute`. This structural guarantee ensures that **every response is automatically passed through the `ResponseGate` serialization layer**, stripping attributes marked `Sensitive(Visibility.OFFICER_ONLY)` whenever an unprivileged or citizen principal receives the payload.

---

## 2. ML Service Architecture

To maintain strict separation of concerns, zero model retraining, and sub-3ms latency, the survival ML integration was organized into a dedicated service layer:

```
┌──────────────────────────────────────────────────────────────┐
│                    ML Model Artifacts                        │
│   (cox_model_summary.json, fitted pipelines, baseline S₀(t)) │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                  SurvivalService (Singleton)                 │
│  - Loads & caches Cox models & explainer once at startup     │
│  - Enforces point-in-time constraints (snapshot <= today)    │
│  - Rejects purged leakage variables (e.g. award_recorded)    │
│  - In-memory structured audit logging                        │
└──────────────────────────────┬───────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│  Officer Analytical Surface  │    │  Citizen Procedural Surface  │
│  - Relative hazard           │    │  - Statutory stage limit     │
│  - S(t) & P(event by t)      │    │  - Elapsed days in stage     │
│  - Hazard decomposition      │    │  - Plain-language rights     │
│  - Advisory risk bands       │    │  - ZERO internal ML scores   │
└──────────────┬───────────────┘    └──────────────┬───────────────┘
               │                                   │
               ▼                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                  ResponseGate Serialization                  │
│       Strikes OFFICER_ONLY fields from Citizen Views         │
└──────────────────────────────────────────────────────────────┘
```

The singleton pattern in `get_survival_service()` guarantees that model artifacts are deserialized exactly once on application startup or first invocation, avoiding expensive per-request disk I/O.

---

## 3. Model Loading & Integrity

Artifact integrity is verified on service initialization:
- **Model Checksums**: SHA-256 hashes of all fitted baseline models (`SECTION_11_TO_SECTION_19`, `SECTION_19_TO_AWARD`, `CASE_INITIATION_TO_MILESTONE`) are loaded from `cox_model_summary.json`.
- **Concordance Verification**: Verifies baseline concordance indices ($0.8067$, $1.000$, $0.9667$).
- **Fail-Safe Startup**: If any artifact is missing or corrupted, the service raises `ArtifactNotFound` (HTTP 500) with diagnostic logging. **It strictly never silently trains a replacement model.**

---

## 4. Risk Endpoint Design

### `POST /api/officer/survival-risk/predict`
Accepts `SurvivalPredictIn` and returns `OfficerSurvivalRiskOut`:
```json
{
  "case_id": "CASE-101",
  "snapshot_date": "2026-03-01",
  "transition": "SECTION_11_TO_SECTION_19",
  "model_version": "1.0.0-cox-production-baseline",
  "linear_predictor": -2.9472,
  "relative_hazard": 0.052484,
  "survival_probability_30d": 0.999557,
  "survival_probability_90d": 0.992695,
  "survival_probability_180d": 0.957672,
  "survival_probability_365d": 0.892705,
  "survival_probability_730d": 0.825227,
  "event_probability_30d": 0.000443,
  "event_probability_90d": 0.007305,
  "event_probability_180d": 0.042328,
  "event_probability_365d": 0.107295,
  "event_probability_730d": 0.174773,
  "risk_band_90d": "ADVISORY_MEDIAN_RELATIVE_HAZARD",
  "calibration_status": "PARTIAL — CALIBRATION NOT RELIABLE DUE TO EVENT SPARSITY",
  "uncertainty_status": "HIGH_UNCERTAINTY_SMALL_SAMPLE_EPV_BELOW_10",
  "extrapolation_status": {
    "30d": false,
    "90d": false,
    "180d": true,
    "365d": true,
    "730d": true
  },
  "data_quality_warning": "Small-sample survival model: relative hazard estimates carry substantial variance due to 40 observed training events across 896 snapshots.",
  "governance_disclaimer": "NON-AUTONOMOUS DECISION-SUPPORT ADVISORY: Statistical relative hazard estimates and survival projections do NOT constitute autonomous legal determinations..."
}
```

### `GET /api/officer/cases/{case_id}/survival-risk`
Retrieves case-level survival risk projection by loading existing proceeding records from PostgreSQL or using default operational parameters when offline.

---

## 5. Explanation Endpoint Design

### `GET /api/officer/cases/{case_id}/survival-risk/explanation`
Integrates the complete LOOP 10 additive linear predictor decomposition ($\eta = \sum \beta_j x_j$) and returns `OfficerSurvivalExplanationOut`:
- **`summary_narrative`**: Plain-language synthesis explaining relative hazard relative to baseline cohort.
- **`why_hazard_is_higher`**: Top features contributing positive log-hazard (increasing hazard rate).
- **`why_hazard_is_lower`**: Top features contributing negative log-hazard (decreasing hazard rate).
- **`missing_features`**: Explicit audit of features unavailable at snapshot time.
- **Mathematical Invariant**: Sum of contributions equals linear predictor ($\sum \text{contrib}_j = \eta \pm 10^{-4}$).

---

## 6. Authentication & Authorization

Authentication leverages the core BHUMISETU identity system:
- Inbound requests resolve to an authenticated `Principal` via `Depends(authenticate)`.
- Officer endpoints verify `principal.kind == "OFFICER"`, raising HTTP 403 `NotAuthorised` (`ErrorCode.NOT_AUTHORISED`) for unauthorized callers.
- Unauthenticated requests raise HTTP 401 `Unauthenticated`.
- Citizen sessions are verified against `principal.case_id == case_id`.

---

## 7. Citizen / Officer Separation & Redaction Gate

Field separation is enforced at two distinct layers:
1. **Endpoint-Level Separation**:
   - Citizens interact only with `GET /api/citizen/cases/{case_id}/milestone-timeline`.
   - The response schema (`CitizenMilestoneTimelineOut`) contains solely statutory milestones, statutory time limits (e.g. Section 19 declaration limit = 365 days), elapsed days, and rights under RFCTLARR 2013 (Section 15 objections, rehabilitation entitlements).
2. **Build-Time ResponseGate Redaction**:
   - Every analytical field (`relative_hazard`, `linear_predictor`, `model_version`, `survival_probability_*`, `event_probability_*`, `risk_band_90d`) is annotated with `Sensitive(Visibility.OFFICER_ONLY)` on `GatedModel`.
   - If an officer model is serialized for a citizen principal, `ResponseGate.apply` strips all internal analytical fields, emitting only public statutory facts.

---

## 8. Point-in-Time Protection

Point-in-time integrity is enforced programmatically before any model inference:
1. **Future Date Guard**: `snapshot_date > datetime.now(timezone.utc).date()` is rejected with HTTP 422 `VALIDATION_FAILED` (`Future information rejected`).
2. **Purged Feature Blacklist**: Features identified as target leakage in Loop 7B (`award_recorded`, `parcel_count`, `objection_count`, etc.) are actively checked against `PURGED_LEAKAGE_FEATURES`. If detected in the request payload, the call is rejected with HTTP 422 `VALIDATION_FAILED`.
3. **Transition Validation**: Only validated statutory transitions (`SECTION_11_TO_SECTION_19`, `SECTION_19_TO_AWARD`, `CASE_INITIATION_TO_MILESTONE`) are permitted.

---

## 9. Error Handling & Structured Envelopes

All errors conform to the platform error specification (§9.4) returning `ErrorEnvelope`:
- HTTP 401: `UNAUTHENTICATED` (no valid session)
- HTTP 403: `NOT_AUTHORISED` (unauthorized role/case)
- HTTP 422: `VALIDATION_FAILED` (malformed date, future snapshot, invalid transition, unsupported horizon, empty features, leakage features)
- HTTP 500: `INTERNAL_ERROR` (missing or corrupted model artifact)

---

## 10. Artifact Validation

On startup, `SurvivalService` inspects:
- `models/cox_baseline/cox_model_summary.json`
- `models/cox_baseline/models_cox_baseline.pkl`
- Clean feature manifest and baseline cumulative hazard tables.

Checksums and model metadata are logged and exposed to authorized officers via `GET /api/officer/survival-risk/health`.

---

## 11. Performance Measurements

Latency benchmarks measured over 100 consecutive API requests:
- **Warmup Latency**: 16.36 ms (initial singleton initialization)
- **Mean Latency**: **2.24 ms**
- **P50 Latency**: **2.07 ms**
- **P95 Latency**: **2.29 ms**
- **P99 Latency**: **16.36 ms**

Inference runs well within the platform SLA budget (< 50 ms).

---

## 12. Audit Logging

Every inference request records structured audit metadata:
```json
{
  "timestamp": "2026-09-30T02:34:25.102341+00:00",
  "case_id": "CASE-101",
  "transition": "SECTION_11_TO_SECTION_19",
  "snapshot_date": "2026-03-01",
  "model_version": "1.0.0-cox-production-baseline",
  "feature_version": "1.0.0-survival-clean-15feat",
  "latency_ms": 2.11
}
```
In-memory audit histories are accessible for verification via `service.get_audit_log()`.

---

## 13. Governance Constraints

Preserves the statutory non-autonomous decision support policy:
- **Mandatory Disclaimer**: Every response carries `GOVERNANCE_SAFETY_DISCLAIMER`.
- **Strict Non-Causal Phrasing**: Explanations use `"contributed to the model's estimated hazard"`. Causal phrases like `"caused the delay"` are strictly prohibited and enforced via automated test assertions.
- **Extrapolation Warnings**: Explicitly flags that horizons exceeding 148 days are statistical extrapolations beyond the empirical follow-up window.

---

## 14. Verification & Test Suite

The 25 test cases required by LOOP 11 were implemented in `bhumi-setu/apps/api/tests/ml/test_survival_api.py`:

| Test Case | Description | Result |
|---|---|---|
| `test_1_valid_officer_prediction` | Officer receives complete analytical risk payload | **PASS** |
| `test_2_valid_citizen_request` | Citizen receives procedural milestone timeline | **PASS** |
| `test_3_officer_authorization_enforced` | Citizen denied access to officer prediction endpoint | **PASS** |
| `test_4_citizen_field_filtering_via_response_gate` | ResponseGate redacts all internal ML fields | **PASS** |
| `test_5_invalid_transition_rejection` | Rejects unknown statutory transitions with 422 | **PASS** |
| `test_6_invalid_horizon_rejection` | Rejects unsupported horizons with 422 | **PASS** |
| `test_7_missing_required_feature_rejection` | Rejects empty or missing required features | **PASS** |
| `test_8_malformed_snapshot_date_rejection` | Rejects invalid date strings with 422 | **PASS** |
| `test_9_future_information_rejected` | Rejects future dates (snapshot > today) | **PASS** |
| `test_10_missing_artifact_raises_safe_error` | Missing model dir fails safely with 500 | **PASS** |
| `test_11_corrupted_artifact_fails_safely_without_retraining` | Corrupted JSON fails safely without retraining | **PASS** |
| `test_12_model_loading_and_integrity` | Model versions and checksums load accurately | **PASS** |
| `test_13_model_caching_singleton_reuse` | Singleton caches models in memory | **PASS** |
| `test_14_deterministic_prediction` | Identical inputs produce bit-for-bit identical outputs | **PASS** |
| `test_15_auditable_explanation_generation` | Linear predictor equals sum of contributions | **PASS** |
| `test_16_uncertainty_propagation` | Small-sample uncertainty warnings propagated | **PASS** |
| `test_17_calibration_status_propagation` | Loop 9 uncalibrated status propagated | **PASS** |
| `test_18_extrapolation_flag_propagation` | Horizons > 148d marked extrapolated | **PASS** |
| `test_19_model_version_propagation` | Reports version `1.0.0-cox-production-baseline` | **PASS** |
| `test_20_feature_version_propagation` | Reports feature version `1.0.0-survival-clean-15feat` | **PASS** |
| `test_21_no_training_during_api_inference` | Training routines never called during inference | **PASS** |
| `test_22_no_eval_data_access_during_inference` | EVAL dataset access forbidden during inference | **PASS** |
| `test_23_no_causal_explanation_language` | Strict non-causal association wording verified | **PASS** |
| `test_24_structured_error_envelopes` | Error responses adhere to platform envelope | **PASS** |
| `test_25_no_sensitive_internal_fields_in_citizen_response` | Citizen response strictly free of ML parameters | **PASS** |

**Full Suite Result**:
- `test_survival_api.py`: **25 / 25 passed** (1.25s)
- Complete ML test battery (`tests/ml/`): **224 / 224 passed** (6.13s)
- Route-table security guard (`test_route_table.py`): **10 / 10 passed** (1.36s)
- Gated route HTTP test (`test_gated_route.py`): **15 / 15 passed** (1.17s)

---

## 15. API Documentation

All endpoints are registered on FastAPI routers with OpenAPI schemas:
- `GET /api/citizen/cases/{case_id}/milestone-timeline`
- `GET /api/officer/cases/{case_id}/survival-risk`
- `GET /api/officer/cases/{case_id}/survival-risk/explanation`
- `GET /api/officer/survival-risk/health`
- `POST /api/officer/survival-risk/predict`
- `POST /internal/ml/survival/predict`

Interactive Swagger documentation (`/docs`) and OpenAPI JSON (`/openapi.json`) expose the schemas and request/response specifications.

---

## 16. Limitations

1. **Small-Event Sparsity (Inherited from Loops 8 & 9)**: With only 40 observed events in TRAIN and 4 in EVAL, survival calibration remains uncalibrated (`PARTIAL — CALIBRATION NOT RELIABLE DUE TO EVENT SPARSITY`).
2. **Follow-Up Censoring Horizon**: Empirical follow-up ceases at 148 days. Predictions for 180, 365, and 730 days are extrapolated and flagged as such in `extrapolation_status`.
3. **Database Pre-computation**: Offline cases without PostgreSQL records fall back to standard operational profiles.

---

## 17. Final Status

**PASS — ML/API INTEGRATION COMPLETE**

All tasks for LOOP 11 have been completed and verified.
Zero model retraining occurred.
All previous model artifacts and evaluation results remain intact.
ML/API integration is verified.

---
*STOP: Execution concluded as mandated after LOOP 11.*
