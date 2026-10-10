# BHUMISETU — Production Smoke Test Report

**Execution Timestamp**: 2026-10-09T22:40:00+05:30  
**Testing Regime**: Local Regression & Static Validation Battery + Cloud Production Verification Protocol  
**Current Status**: `VERIFIED (LOCAL SUITE) — CLOUD TARGET AWAITING OPERATOR CREDENTIALS`  

---

## 1. Local Baseline Smoke & Verification Battery

The automated test battery was executed against the existing repository components without modifying model weights or application features:

| ID | Test Category / Objective | Target Module or Command | Result Summary | Status |
| :---: | :--- | :--- | :--- | :---: |
| **SMK-01** | Backend Regression Suite | `pytest tests/` (in `bhumi-setu/apps/api`) | 1,026 passed, 208 skipped (PostGIS), 0 failed | **PASS** |
| **SMK-02** | Frontend Static Typecheck | `npm run typecheck` (`tsc --noEmit`) | 0 TypeScript errors across all source files | **PASS** |
| **SMK-03** | Frontend Production Build | `npm run build` (`vite build`) | 1,730 modules compiled into `dist/` | **PASS** |
| **SMK-04** | ML Candidate Artifact Hash Baseline | SHA-256 validation across 102 candidate files | 102 / 102 digests identical to frozen baseline | **PASS** |
| **SMK-05** | Public Liveness Probe | `GET /healthz` | HTTP 200 `{"status":"ok"}` | **PASS** |
| **SMK-06** | Public Readiness Probe | `GET /api/healthz` | HTTP 200 `{"status":"ok","app":"BHUMISETU","version":"1.0.0"}` | **PASS** |
| **SMK-07** | ML Health & Version Verification | `GET /api/officer/survival-risk/health` | HTTP 200 with model version & SHA-256 checksums | **PASS** |
| **SMK-08** | Authentication Persona Token | `POST /api/auth/persona` | Valid session token issued for demo persona | **PASS** |
| **SMK-09** | Survival Risk Inference | `POST /api/officer/survival-risk/predict` | Multi-horizon survival probabilities ($S_{30}\dots S_{730}$) | **PASS** |
| **SMK-10** | Mathematical Invariant Check | $\text{HR} = \exp(\eta)$, $S(t) = S_0(t)^{\text{HR}}$ | Numerical tolerance verified ($< 1.5 \times 10^{-7}$) | **PASS** |
| **SMK-11** | Future Leakage Protection | Point-in-time snapshot check ($t > T$) | HTTP 422 `VALIDATION_FAILED` | **PASS** |
| **SMK-12** | Purged Variable Rejection | 7 purged features (`award_recorded`, etc.) | HTTP 422 rejection across all 7 variables | **PASS** |
| **SMK-13** | DPDP Citizen Redaction Gate | `GET /api/citizen/cases/{id}/milestone-timeline` | Internal linear predictor ($\eta$) and PII masked | **PASS** |
| **SMK-14** | Adversarial Input Fuzzing | Path traversal, SQLi, NaNs, negative durations | HTTP 422 with structured `ErrorEnvelope` | **PASS** |

---

## 2. Post-Deployment Cloud Verification Protocol

Once the cloud infrastructure is provisioned and deployed by the operator, the following automated smoke tests must be executed against the live public HTTPS endpoints:

```bash
# In bhumisetu_deployment_harness/.env.harness:
FRONTEND_URL=https://portal.bhumisetu.gov.in
BACKEND_URL=https://api.bhumisetu.gov.in
HEALTH_PATH=/api/healthz

# Run automated smoke test:
./bhumisetu_deployment_harness/run.sh smoke
```

### 2.1 Verification Checklist for Live Cloud Target
- [ ] **HTTPS Transport**: Both `FRONTEND_URL` and `BACKEND_URL` must serve valid TLS certificates over `https://`.
- [ ] **Strict-Transport-Security (HSTS)**: Response headers must enforce HSTS (`max-age=31536000; includeSubDomains`).
- [ ] **CORS Configuration**:
  - Request from authorized frontend origin returns `Access-Control-Allow-Origin: https://portal.bhumisetu.gov.in`.
  - Request from unauthorized origin returns no `Access-Control-Allow-Origin` header or HTTP 403.
- [ ] **Public Liveness**: `GET https://api.bhumisetu.gov.in/healthz` returns HTTP 200 within 500 ms.
- [ ] **API Readiness**: `GET https://api.bhumisetu.gov.in/api/healthz` returns HTTP 200 with application identifier.
- [ ] **Officer Security Isolation**:
  - Unauthenticated `GET https://api.bhumisetu.gov.in/api/officer/survival-risk/health` returns HTTP 401.
  - Citizen-authenticated request to the same endpoint returns HTTP 403 (SEC-FIND-01).
- [ ] **Citizen PII Masking**:
  - Citizen case view returns masked landowner names (`Ra**** Ku****`) and zero linear predictor telemetry.
- [ ] **Database & PostGIS Extension**:
  - Cadastral parcel query succeeds without PostGIS extension errors:
    `GET https://api.bhumisetu.gov.in/api/officer/gis/parcels` returns GeoJSON spatial vectors.
- [ ] **Redis & Celery Workers**:
  - Submitting an asynchronous document analysis request creates a task with status transitioning from `PENDING` to `SUCCESS`.
- [ ] **Zero Hardcoded Secrets in Frontend**:
  - Inspect production JavaScript bundle to ensure no database passwords, Redis URLs, or JWT secrets are present in client-side code.
