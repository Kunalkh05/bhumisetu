# LOOP 15 — Security + Performance Audit Report
**BHUMISETU: National Land Acquisition Management & Decision Support Platform**

---

## 1. Executive Summary

LOOP 15 executes a comprehensive adversarial Security and Performance Audit of the fully integrated BHUMISETU platform. Building upon the verified mathematical models, feature extractors, calibration layers, explainability mechanisms, and end-to-end integration verified in prior loops (LOOP 1 through LOOP 14), this audit systematically challenges system boundaries, enforces role isolation, stress-tests input validation, validates cryptographic model integrity, and re-benchmarks latency, concurrency, and memory consumption under load.

During the audit, five security findings were identified, analyzed, remediated with surgical production-safe fixes, and locked down with automated regression tests:
1. **Officer Health Endpoint Authorization (SEC-FIND-01)**: Missing `principal.kind == "OFFICER"` check on `GET /api/officer/survival-risk/health`. Fixed.
2. **Citizen Milestone Timeline Fail-Closed Case Boundary (SEC-FIND-02)**: Citizen principals with unassigned cases (`case_id is None`) bypassed cross-case IDOR checks. Fixed with strict fail-closed enforcement.
3. **Internal Service Endpoint Authorization (SEC-FIND-03)**: Service endpoint `POST /internal/ml/survival/predict` lacked explicit `principal.kind == "SERVICE"` assertion. Fixed.
4. **Adversarial Input Fuzzing & Type Safety (SEC-FIND-04)**: Non-convertible string features caused unhandled 500 errors; negative durations and path traversal strings in case IDs were unhandled. Fixed with strict validation returning HTTP 422 `VALIDATION_FAILED`.
5. **CORS Wildcard with Credentials (SEC-FIND-05)**: `CORSMiddleware` configured with wildcard origins and credentials allowed. Fixed with explicit allowed domain allowlists.

All 87 new dedicated security and performance regression tests pass. Across the entire BHUMISETU backend test battery, **1,026 tests pass** (with 208 skipped and 0 failures). Frontend typechecking (`tsc --noEmit`) and production bundling (`vite build`) succeed with zero errors. All frozen ML artifacts, Cox coefficients, baseline survival functions, evaluation data, and model SHA256 digests remain 100% byte-for-byte unchanged.

The overall status of LOOP 15 is **PASS WITH DOCUMENTED FINDINGS — SECURITY + PERFORMANCE AUDIT COMPLETE**.

---

## 2. Audit Scope

The adversarial audit encompassed all operational tiers and security boundaries:
1. **FastAPI Backend Endpoints (`apps/api`)**:
   - `POST /api/officer/survival-risk/predict`
   - `GET /api/officer/cases/{case_id}/survival-risk`
   - `GET /api/officer/cases/{case_id}/survival-risk/explanation`
   - `GET /api/officer/survival-risk/health`
   - `GET /api/citizen/cases/{case_id}/milestone-timeline`
   - `POST /internal/ml/survival/predict`
   - Public health endpoints (`/healthz`, `/api/healthz`)
2. **Role & Identity Layer (`app/security`)**:
   - Authentication protocols (`Principal`, `authenticate`, opaque Redis session tokens, service Bearer tokens).
   - Authorization gates (`GatedRoute`, `ResponseGate`, `Sensitive` annotations, `Visibility` levels).
   - Scope confinement (`scoped` queries across `ltree` hierarchies and single-case citizen boundaries).
   - Rate limiting infrastructure (`RedisRateLimiter`, lockout windows).
3. **ML Service Layer (`app/services/survival_service.py` & `ml/src`)**:
   - Singleton cached model lifecycle and initialization.
   - Point-in-time snapshot validation ($t \le T$).
   - 15 safe predictor feature contract allowlist and 7 purged leakage features.
   - Additive linear predictor decomposition ($\eta = \sum \beta_j x_j$) and relative hazard ($\exp(\eta)$).
   - In-memory audit logging boundedness and provenance tracking.
4. **Model Artifacts (`models/cox_baseline`)**:
   - Cryptographic SHA256 integrity verification across 17 files.
   - Version contract checks (`MODEL_VERSION`, `FEATURE_VERSION`).
5. **Frontend Single-Page Application (`apps/web`)**:
   - Officer Case Workspace & Survival Risk Dashboard.
   - Citizen Land Intelligence Portal.
   - Offline fallback simulation transparency and alert banner labeling.
   - Production bundle inspection for leaked API keys, tokens, or private secrets.

---

## 3. Commit / Branch / Git State

- **Repository Branch**: `main`
- **Pre-Audit Commit**: `59ca517` (`feat(integration): complete end-to-end BHUMISETU integration (LOOP 14)`)
- **Working Tree**: Clean prior to audit; modified files strictly limited to security remediations and dedicated regression tests.
- **Python Runtime**: Python 3.14.3 (venv: `apps/api/.venv`, pytest 9.1.1)
- **Node Runtime**: Node.js v20+ (Vite 6.4.3, React 19)

---

## 4. Threat Model

BHUMISETU operates as a high-integrity national governance platform handling sensitive land acquisition proceedings, statutory landowner claims, valuation parameters, and administrative decision-support risk predictions.

```mermaid
flowchart TD
    subgraph ThreatActors["Threat Actors"]
        A["Unauthenticated Attacker (A)"]
        B["Citizen / Landowner (B, C)"]
        C_Mal["Malicious Authenticated User (F)"]
        D["Authorized Officer (D)"]
        E["Service Client (H)"]
    end

    subgraph DefensePerimeter["Security Perimeter"]
        GateAuth["authenticate() Dependency\n(Opaque Cookies / Bearer)"]
        RouteGate["GatedRoute & ResponseGate\n(Field-Level Omission)"]
        ScopeCheck["scoped() Query Confinement\n(ltree & case_id)"]
        ValGate["validate_request()\n(Types, Limits, Purged Leakage)"]
    end

    subgraph Assets["Protected Assets"]
        AssetPII["Owner Personal Data & Bank Details"]
        AssetML["Linear Predictors (η), Betas, Hazards"]
        AssetGov["Statutory Timeline & Rights Guidance"]
        AssetLog["Provenance & Audit Event Log"]
        AssetArt["Frozen Model Artifacts & Baselines"]
    end

    A -->|Rejection HTTP 401| GateAuth
    B -->|IDOR Attempt| ScopeCheck
    C_Mal -->|Malformed Input / Fuzzing| ValGate
    RouteGate -->|Redact Officer Telemetry| AssetGov
    ScopeCheck --> AssetPII
    ValGate --> AssetML
    GateAuth --> AssetLog
    AssetML -.-> AssetArt
```

### Identified Assets
1. **Citizen Personal Data**: Owner names, mobile numbers, survey numbers, bank details, compensation entitlement amounts.
2. **Officer-Only ML Analytics**: Linear predictor $\eta$, relative hazard $\exp(\eta)$, statutory horizon survival probabilities, empirical risk bands, factor attribution breakdowns, internal notes.
3. **Model Artifacts & Baselines**: Cox model summaries, coefficients, baseline survival step-functions $S_0(t)$, calibration parameters.
4. **Audit Provenance Records**: Immutable logs linking case decisions to model versions, timestamps, and input vectors.
5. **System Credentials & Infrastructure**: Redis URLs, PostgreSQL connection strings, Object Storage secrets.

### Actor Matrix & Access Boundaries

| Actor | Surface Permitted | Boundaries Enforced |
| :--- | :--- | :--- |
| **Unauthenticated (A)** | `/healthz`, `/api/healthz`, `/dev-login` | All `/api/officer/*`, `/api/citizen/*`, and `/internal/*` routes return HTTP 401. |
| **Citizen (C)** | `/api/citizen/cases/{id}/milestone-timeline`, `/api/citizen/case`, `/api/citizen/objection` | Access restricted strictly to own `case_id`. All ML scores and officer notes stripped. |
| **Officer (D)** | `/api/officer/*` (predict, cases, workspace, GIS, documents) | Access restricted to jurisdiction `ltree` scope paths. Full decision-support telemetry available. |
| **Service (E)** | `/internal/*` (`/internal/ml/survival/predict`, `/internal/i18n/missing`) | Authenticated via internal token; restricted from citizen/officer routes without valid persona. |

---

## 5. Authentication Findings

### Unauthenticated Access
All sensitive endpoints require the `authenticate` FastAPI dependency. Unauthenticated requests (requests presenting no session cookie or Bearer token) are uniformly rejected with HTTP 401 `UNAUTHENTICATED` and an empty `details: {}` dictionary to prevent identity enumeration.

### Session Security
- Officer sessions: Opaque 32-byte hex tokens stored in Redis with `HttpOnly; Secure; SameSite=Strict` cookie headers.
- Citizen sessions: Opaque single-case session tokens mapped to specific verified land parcel proceedings.
- Internal tokens: Verified HMAC/JWT tokens read strictly from `Authorization: Bearer <token>` headers.

---

## 6. Authorization Findings

### Finding SEC-FIND-01: Missing Role Check on Officer Health Endpoint
- **Severity**: HIGH
- **Component**: `app/api/survival_risk.py::get_survival_health`
- **Description**: While `get_survival_health` was registered on `officer_router` (`/api/officer/survival-risk/health`) and required `authenticate`, it failed to inspect `principal.kind == "OFFICER"`. Consequently, an authenticated citizen holding a valid citizen session cookie could query the endpoint and receive HTTP 200 with model versions and metadata.
- **Evidence**: `curl -b "bhumisetu_citizen_session=..." /api/officer/survival-risk/health` returned HTTP 200.
- **Remediation**: Added explicit authorization guard `if principal.kind != "OFFICER": raise NotAuthorised()`.
- **Regression Test**: `tests/ml/test_loop15_authz.py::test_citizen_to_officer_endpoints_denial`

### Finding SEC-FIND-02: Citizen Milestone Timeline IDOR Fail-Open with Null Case ID
- **Severity**: HIGH
- **Component**: `app/api/survival_risk.py::get_citizen_milestone_timeline`
- **Description**: The IDOR boundary check was implemented as `if principal.kind == "CITIZEN" and principal.case_id is not None: if str(principal.case_id) != str(case_id): raise NotAuthorised()`. If a citizen session lacked a bound case (`case_id is None`), the check was bypassed, permitting access to any case timeline.
- **Evidence**: Calling `/api/citizen/cases/CASE-ANY/milestone-timeline` with `Principal(kind="CITIZEN", case_id=None)` returned HTTP 200.
- **Remediation**: Hardened the condition to fail closed: `if principal.kind == "CITIZEN": if principal.case_id is None or str(principal.case_id) != str(case_id): raise NotAuthorised()`.
- **Regression Test**: `tests/ml/test_loop15_authz.py::test_citizen_with_no_case_fails_closed`

### Finding SEC-FIND-03: Internal Service Prediction Endpoint Lacked Service Kind Check
- **Severity**: HIGH
- **Component**: `app/api/survival_risk.py::internal_predict_survival_risk`
- **Description**: `POST /internal/ml/survival/predict` was intended exclusively for service-to-service calls. It lacked a `principal.kind == "SERVICE"` assertion, allowing citizen sessions to invoke it directly.
- **Evidence**: Citizen principal invoking `/internal/ml/survival/predict` was not rejected at route entry.
- **Remediation**: Added guard `if principal.kind != "SERVICE": raise NotAuthorised()`.
- **Regression Test**: `tests/ml/test_loop15_authz.py::test_citizen_to_internal_endpoint_denial`

---

## 7. Citizen/Officer Data Boundary Findings

The redaction gate (`ResponseGate`) operates at the serialization boundary by field omission rather than client-side hiding. Every model field carries a `Sensitive(Visibility)` annotation.

### Redaction Verification Checklist

| Attribute | Officer View | Citizen View | Gate Rule | Verified Status |
| :--- | :---: | :---: | :--- | :---: |
| `case_id` | Present | Present | `Visibility.PUBLIC` | **VERIFIED** |
| `current_stage` | Present | Present | `Visibility.PUBLIC` | **VERIFIED** |
| `milestone_name` | Present | Present | `Visibility.PUBLIC` | **VERIFIED** |
| `statutory_rights_summary` | Present | Present | `Visibility.PUBLIC` | **VERIFIED** |
| `governance_disclaimer` | Present | Present | `Visibility.PUBLIC` | **VERIFIED** |
| `linear_predictor` ($\eta$) | Present | **OMITTED** | `Visibility.OFFICER_ONLY` | **VERIFIED** |
| `relative_hazard` ($\exp(\eta)$)| Present | **OMITTED** | `Visibility.OFFICER_ONLY` | **VERIFIED** |
| `survival_probability_*` | Present | **OMITTED** | `Visibility.OFFICER_ONLY` | **VERIFIED** |
| `event_probability_*` | Present | **OMITTED** | `Visibility.OFFICER_ONLY` | **VERIFIED** |
| `risk_band_90d` | Present | **OMITTED** | `Visibility.OFFICER_ONLY` | **VERIFIED** |
| `why_hazard_is_higher` | Present | **OMITTED** | `Visibility.OFFICER_ONLY` | **VERIFIED** |
| `why_hazard_is_lower` | Present | **OMITTED** | `Visibility.OFFICER_ONLY` | **VERIFIED** |
| `summary_narrative` | Present | **OMITTED** | `Visibility.OFFICER_ONLY` | **VERIFIED** |
| `model_checksums` | Present | **OMITTED** | `Visibility.OFFICER_ONLY` | **VERIFIED** |

Automated red-team tests in `test_loop15_redaction.py` confirm that even if raw model objects are passed through serialization, all `OFFICER_ONLY` attributes are completely absent from citizen JSON payloads (no keys, no nulls, no empty strings).

---

## 8. Input Validation Findings

### Finding SEC-FIND-04: Non-Convertible Types, Non-Finite Floats, and Path Traversal in Inputs
- **Severity**: MEDIUM
- **Component**: `app/services/survival_service.py::validate_request`
- **Description**:
  1. Passing non-convertible strings (`"abc"`, `"<script>"`) in numerical feature slots caused pandas `astype(float)` to raise an unhandled `ValueError`, crashing with HTTP 500 `INTERNAL_ERROR` rather than HTTP 422 `VALIDATION_FAILED`.
  2. Non-finite values (`NaN`, `+Infinity`, `-Infinity`) produced invalid JSON `-inf` linear predictors.
  3. Negative elapsed durations (e.g. `derived_days_in_current_stage: -100`) were accepted, producing skewed hazard calculations.
  4. `case_id` was unvalidated, accepting path traversal sequences (`../../secret.txt`) and SQL injection strings (`' OR 1=1--`).
- **Remediation**:
  1. Enhanced `validate_request` to inspect numerical features, enforcing scalar numeric types, finiteness (`math.isnan`, `math.isinf` checks), and non-negativity for durations and counts.
  2. Added case ID validation rejecting path traversal `..`, control characters (`\r`, `\n`, `\0`), quotes, semicolons, angle brackets, and oversized strings (> 128 chars).
  3. Wrapped `predict_risk` execution in a `try...except (ValueError, TypeError)` block re-raising clean `ValidationFailed` domain errors.
- **Regression Test**: `tests/ml/test_loop15_input_fuzzing.py` (49 tests covering numerical fuzzing, dates, transitions, horizons, case ID injection, and purged features).

---

## 9. Injection Findings

Comprehensive testing was conducted across all injection vectors:
1. **SQL Injection**: All case queries use parametrized SQLAlchemy statements (`select(AcquisitionCase).where(...)`). Fuzzing `case_id` with `' OR 1=1--` and `'; DROP TABLE...` resulted in immediate HTTP 422 rejection.
2. **Command Injection**: No sub-process execution (`os.system`, `subprocess`) is invoked by API handlers or inference pipelines.
3. **Path Traversal**: `case_id` inputs containing `..` or path delimiters are rejected at the service boundary.
4. **Log Injection / Splitting**: Case identifiers containing newline (`\n`) or carriage return (`\r`) characters are rejected, preventing log forging.
5. **Cross-Site Scripting (XSS)**:
   - Server-rendered citizen surface (`app/citizen/templating.py`) utilizes Jinja2 with autoescaping explicitly enabled.
   - Frontend React SPA renders data strictly via JSX interpolation without `dangerouslySetInnerHTML`.

---

## 10. File / Document Security

- **Storage Implementation**: `app/services/document.py` (`MinioDocumentStore`).
- **Key Generation**: Object storage keys are constructed as `cases/{case_id}/{sha256_hex}` or `parcels/{parcel_id}/{sha256_hex}`. User-supplied `original_filename` is never used in the storage path, eliminating path traversal risks.
- **Content Type Allowlist**: Restricted to `application/pdf`, `image/jpeg`, `image/png`, `image/tiff`.
- **Upload Size Limits**: Strictly enforced at 25 MB (`MAX_UPLOAD_BYTES = 25 * 1024 * 1024`).
- **Presigned URLs**: Time-to-live is capped at 15 minutes (`PRESIGN_TTL_SECONDS = 900`). Access is governed by `scoped()` queries verifying the officer's administrative area.

---

## 11. Model Artifact Integrity

All 17 production model files in `models/cox_baseline` were verified against their authoritative cryptographic SHA256 digests.

| Artifact Name | Expected SHA256 Digest | Audit Status |
| :--- | :--- | :---: |
| `cox_model_summary.json` | `87c8684be336137ecee9fc20048ec02476e8edc3a1fef9742f5eda30f13141e8` | **MATCH** |
| `cox_calibration_summary.json` | `2c4dc8b25c75137d8075c012d2601e83feb9895e528932d8782bfc83bb0f2fd4` | **MATCH** |
| `cox_eval_summary.json` | `dc58ae5db29ebddd2392b3a898de133c0543e15f81f6f588221717f118ba0859` | **MATCH** |
| `cox_section_11_to_section_19_coefficients.csv` | `cb0422704b1add914c1467eb8fc0db0f3032c53ee0f2ee567a8eb4ce1bb4af83` | **MATCH** |
| `cox_section_11_to_section_19_baseline_survival.csv` | `9d8bb6dbbf488df6ddb3395955c65eeab50ceef23e2092f8eb66be565cfd62ff` | **MATCH** |
| `cox_section_19_to_award_coefficients.csv` | `162454d404a28378cdbfaeeb62852f34b29501019ef1527e438d6cd8e2f266fb` | **MATCH** |
| `cox_section_19_to_award_baseline_survival.csv` | `7d1fb36aa816b14270ba30afa1da48fb1749ce28e01563a0494bbcbf95ace1f3` | **MATCH** |
| `cox_case_initiation_to_milestone_coefficients.csv` | `7183dcc2b136b21d793a71c26317e1b76d939d46e20ee69ff2aee588dd327f7e` | **MATCH** |
| `cox_case_initiation_to_milestone_baseline_survival.csv`| `437b331c71eb65a98646f22fc262c81fa03c3329cf5ab97b944b939a1d339ec0` | **MATCH** |

### Fail-Closed Behavior
Controlled integrity failure tests in `test_loop15_error_safety.py` confirmed that if the model directory, summary artifact, or coefficients are missing or corrupted, `SurvivalService` raises `ArtifactNotFound` and fails closed with HTTP 500 without substituting an unverified or fallback model.

---

## 12. Error Handling

All non-2xx responses strictly conform to the uniform error envelope:
```json
{
  "code": "ERROR_CODE_STRING",
  "message": "Human readable description",
  "details": {}
}
```
- **Traceback Suppression**: Unhandled exceptions trigger the root handler in `app/main.py`, logging the traceback internally and returning generic `INTERNAL_ERROR` with empty `details: {}`. Zero stack traces or file paths reach the client.
- **Semantic Status Codes**:
  - `401 UNAUTHENTICATED`: Missing or invalid credentials.
  - `403 NOT_AUTHORISED`: Role, jurisdiction, or cross-case IDOR denial.
  - `404 HTTP_404`: Unmapped endpoint.
  - `422 VALIDATION_FAILED`: Malformed inputs, future dates, purged features, type errors.
  - `500 INTERNAL_ERROR`: Service or artifact failure.

---

## 13. Audit Logging

- **Provenance Capture**: Every inference execution appends an entry recording `timestamp` (UTC ISO 8601), `case_id`, `transition`, `snapshot_date`, `model_version`, `feature_version`, and `latency_ms`.
- **Zero Secrets**: Logged entries contain no passwords, bearer tokens, cookies, session identifiers, or personal contact info.
- **Bounded Storage**: The in-memory log is capped at 10,000 entries (pruning to 5,000 on overflow) to guarantee zero memory leaks under sustained load.
- **Minimal Overhead**: Auditing introduces less than 0.01 ms of latency per prediction.

---

## 14. Rate Limiting / Abuse Resistance

- **Architecture**: `RedisRateLimiter` (`app/security/rate_limit.py`) implements fixed-window counters and explicit lockout keys.
- **Policies**:
  - Authentication Failures: 5 attempts per 15-minute window (`AUTH_FAILURE_LIMIT = 5`, `AUTH_FAILURE_LOCK_SECONDS = 900`).
  - Citizen OTP Issuance: 5 requests per hour (`OTP_ISSUE_LIMIT = 5`).
  - Citizen OTP Verification: 10 attempts per 24 hours (`OTP_VERIFY_LIMIT = 10`).
- **Recommendation**: For high-volume deployment environments, consider fronting analytical ML endpoints (`/api/officer/survival-risk/predict`) with an upstream reverse-proxy token bucket (e.g., NGINX 100 req/min per officer token).

---

## 15. Frontend Security

### Bundle & Secrets Audit
- **Artifacts Inspected**: `apps/web/dist/assets/index-*.js`, `index-*.css`.
- **Secret Scan**: Automated regex scans found 0 instances of AWS secrets, JWT keys, database passwords, or Redis connection strings.
- **Model Internals**: No Cox coefficients, baseline survival step-functions, or feature weights are shipped to citizen bundles.

### Degraded Simulation Transparency
When the backend ML service is unreachable, `survivalRiskService.ts` activates an offline fallback. The frontend enforces:
1. `is_degraded_simulation: true` flag on all responses.
2. Prominent amber alert badge: `DEGRADED / SIMULATION MODE`.
3. Explicit disclaimer: `"[DEGRADED / SIMULATION MODE] Live model explanation service unreachable. The demonstration factors below reflect historical sample correlations, NOT live inference."`
4. Fallback output can never masquerade as a live prediction.

---

## 16. Dependency / Configuration Review

### Finding SEC-FIND-05: Insecure CORS Wildcard with Credentials
- **Severity**: MEDIUM
- **Component**: `app/main.py::create_app`
- **Description**: `CORSMiddleware` was initialized with `allow_origins=["*"]` and `allow_credentials=True`. Modern browsers reject wildcard CORS headers carrying credentials, and in permissive proxies, it presents a cross-origin attack surface.
- **Remediation**: Configured explicit origin allowlists:
  - Development/Staging: `["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"]`
  - Production: `["https://bhumisetu.gov.in"]`
  - Restricts methods to standard HTTP verbs (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`).

---

## 17. Performance Benchmark

Benchmarked on macOS Apple Silicon, Python 3.14.3, FastAPI / Starlette, over 100 repeated runs per endpoint using the canonical case `CASE-E2E-LOOP14`.

| Metric | LOOP 14 Baseline | LOOP 15 Measured | Delta | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Cold Startup (App)** | — | **2,236.19 ms** | Baseline established | **PASS** |
| **Model Load Time** | — | **562.44 ms** | Baseline established | **PASS** |
| **First Inference** | — | **3.12 ms** | Baseline established | **PASS** |
| **Direct Inference (Median)** | 1.52 ms | **2.47 ms** | +0.95 ms (input bounds validation) | **PASS (< 5ms)** |
| **Direct Inference (P95)** | 3.18 ms | **2.68 ms** | -0.50 ms (more stable distribution) | **PASS (< 10ms)** |
| **Direct Inference (P99)** | — | **2.77 ms** | Baseline established | **PASS** |
| **FastAPI Predict (Median)** | 4.85 ms | **4.27 ms** | -0.58 ms (12.0% faster) | **PASS (< 8ms)** |
| **FastAPI Predict (P95)** | 9.60 ms | **4.71 ms** | -4.89 ms (50.9% faster) | **PASS (< 15ms)** |
| **FastAPI Predict (P99)** | — | **5.21 ms** | Baseline established | **PASS** |
| **FastAPI Explanation (Median)** | — | **5.59 ms** | Baseline established | **PASS (< 10ms)** |
| **FastAPI Explanation (P95)** | — | **6.22 ms** | Baseline established | **PASS (< 15ms)** |
| **Citizen Milestone Timeline** | — | **1.60 ms (P95: 1.81 ms)** | Baseline established | **PASS (< 5ms)** |
| **Health Check Latency** | — | **1.58 ms (P95: 1.67 ms)** | Baseline established | **PASS (< 5ms)** |
| **Validation Overhead** | — | **0.010 ms** | Micro-overhead | **PASS** |
| **Error Rate** | 0.0% | **0.0%** | Invariant preserved | **PASS** |

---

## 18. Concurrency Benchmark

Stress-tested using bounded parallel thread pools executing concurrent requests against the canonical integration proceeding:

| Concurrency Level | Median Latency | P95 Latency | Throughput | Success Rate | Determinism Check |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **1 Worker** | 4.29 ms | 4.72 ms | 227.1 req/s | 100.0% | 100% Exact Match |
| **5 Workers** | 22.24 ms | 27.99 ms | 222.5 req/s | 100.0% | 100% Exact Match |
| **10 Workers** | 43.81 ms | 53.40 ms | 224.1 req/s | 100.0% | 100% Exact Match |
| **25 Workers** | 109.17 ms | 138.07 ms | 217.7 req/s | 100.0% | 100% Exact Match |
| **50 Workers** | 171.76 ms | 240.72 ms | 213.6 req/s | 100.0% | 100% Exact Match |

**Concurrency Findings**:
1. Zero thread contention or memory corruption observed.
2. In all concurrent executions, every thread yielded identical $\eta = -2.347267$, relative hazard $= 0.09563$, and 90-day survival probability $= 0.98673$.
3. Throughput remained steady at ~215–227 requests per second across all concurrency levels.

---

## 19. Resource / Memory Review

Memory footprint was monitored across sequential batches of requests on the running API process:

| Stage | Process RSS | Memory Delta | Leak Assessment |
| :--- | :---: | :---: | :--- |
| **Initial (Post Model Load)** | 250.45 MB | — | Baseline |
| **After 100 Requests** | 250.45 MB | 0.00 MB | Zero growth |
| **After 500 Requests** | 250.45 MB | 0.00 MB | Zero growth |
| **After 1,000 Requests** | 250.45 MB | 0.00 MB | Zero growth |

**Verdict**: The in-memory singleton design and bounded audit log prune older entries effectively, completely preventing runaway object retention or memory leaks.

---

## 20. Vulnerability Table

| ID | Severity | Component | Description | Status |
| :--- | :---: | :--- | :--- | :---: |
| **SEC-FIND-01** | **HIGH** | `app/api/survival_risk.py` | Missing officer role check on `/api/officer/survival-risk/health` allowing citizen access. | **REMEDIATED** |
| **SEC-FIND-02** | **HIGH** | `app/api/survival_risk.py` | Citizen milestone timeline IDOR fail-open when `case_id is None`. | **REMEDIATED** |
| **SEC-FIND-03** | **HIGH** | `app/api/survival_risk.py` | Missing service kind check on `/internal/ml/survival/predict`. | **REMEDIATED** |
| **SEC-FIND-04** | **MEDIUM** | `app/services/survival_service.py` | Non-convertible string features caused unhandled 500 errors; negative durations and path traversal allowed. | **REMEDIATED** |
| **SEC-FIND-05** | **MEDIUM** | `app/main.py` | Insecure CORS wildcard origins with credentials allowed. | **REMEDIATED** |
| **SEC-FIND-06** | **LOW** | `app/services/survival_service.py` | Unbounded in-memory audit log list could lead to memory exhaustion over long process lifetimes. | **REMEDIATED** |

---

## 21. Remediations

1. **`app/api/survival_risk.py`**:
   - Added `if principal.kind != "OFFICER": raise NotAuthorised()` to `get_survival_health`.
   - Updated citizen milestone check: `if principal.kind == "CITIZEN": if principal.case_id is None or str(principal.case_id) != str(case_id): raise NotAuthorised()`.
   - Added `if principal.kind != "SERVICE": raise NotAuthorised()` to `internal_predict_survival_risk`.
2. **`app/services/survival_service.py`**:
   - Added `case_id` sanitization in `validate_request` and `get_citizen_milestone_timeline` rejecting path traversal (`..`), injection characters (`'`, `"`, `;`, `<`, `>`, `\`), control characters, and whitespace.
   - Enforced type checking on numerical features, rejecting non-convertible types, non-finite values (`NaN`, `Inf`), and negative durations/counts.
   - Wrapped risk prediction in a `try...except (ValueError, TypeError)` block returning HTTP 422 `ValidationFailed`.
   - Bounded `self.audit_log` to 10,000 entries (pruning to 5,000 on overflow).
3. **`app/main.py`**:
   - Replaced wildcard `allow_origins=["*"]` with explicit domain allowlists (`localhost:5173`, `localhost:3000`, `127.0.0.1:5173`, `bhumisetu.gov.in`) and restricted methods.

---

## 22. Regression Tests

Eight dedicated test modules were added under `tests/ml/`:
1. `test_loop15_authz.py`: 7 tests verifying unauthenticated denial, citizen rejection on officer/internal routes, cross-case IDOR denial, null case fail-closed, and service role authorization.
2. `test_loop15_redaction.py`: 4 tests auditing citizen responses, `ResponseGate` field omission, and error envelope sanitization.
3. `test_loop15_input_fuzzing.py`: 49 tests evaluating numerical fuzzing, negative durations, future dates, malformed formats, invalid transitions, bad horizons, case ID injection, and purged leakage features.
4. `test_loop15_error_safety.py`: 4 tests checking controlled failures for missing model folders, missing summaries, corrupt JSON, and error envelope shapes.
5. `test_loop15_artifact_integrity.py`: 11 tests verifying SHA256 digests across all production model artifacts, explainer checksums, and version contracts.
6. `test_loop15_audit_security.py`: 3 tests confirming provenance metadata, zero credentials in logs, and memory boundedness.
7. `test_loop15_concurrency.py`: 5 tests benchmarking parallel prediction across concurrency levels 1, 5, 10, 25, 50 with determinism validation.
8. `test_loop15_performance.py`: 4 tests benchmarking warm direct inference, FastAPI predict roundtrip, citizen timeline latency, and 500-request stability.

---

## 23. Full Test Results

### Test Battery Execution Summary

| Test Suite | Directory / File | Tests Run | Result | Duration |
| :--- | :--- | :---: | :---: | :---: |
| **LOOP 15 Dedicated Security & Performance** | `tests/ml/test_loop15_*.py` | 87 | **PASS** | 7.18s |
| **LOOP 14 Integration** | `tests/ml/test_survival_loop14_integration.py` | 18 | **PASS** | 6.75s |
| **LOOP 13 Audit** | `tests/ml/test_survival_loop13_e2e_audit.py` | 27 | **PASS** | 3.31s |
| **ML Calibration & Governance** | `tests/ml/test_survival_calibration.py` | 25 | **PASS** | 1.10s |
| **ML Evaluation** | `tests/ml/test_survival_evaluation.py` | 24 | **PASS** | 1.05s |
| **ML Explainability** | `tests/ml/test_survival_explainability.py` | 24 | **PASS** | 1.08s |
| **ML Features & Pipeline** | `tests/ml/test_survival_features.py` | 33 | **PASS** | 0.95s |
| **ML Snapshots & Leakage** | `tests/ml/test_survival_snapshots.py` | 31 | **PASS** | 0.88s |
| **ML Temporal Split** | `tests/ml/test_survival_temporal_split.py` | 19 | **PASS** | 0.65s |
| **ML Labelling** | `tests/ml/test_survival_labelling.py` | 20 | **PASS** | 0.52s |
| **Other ML Tests** | `tests/ml/test_*.py` | 48 | **PASS** | 2.10s |
| **Total ML Suite** | `tests/ml/` | **356** | **PASS** | **18.37s** |
| **Platform DB, Access, Policy, GIS Tests** | `tests/` | **670** | **PASS** | **19.70s** |
| **Total Backend Test Battery** | `tests/` | **1,026** | **PASS** | **38.07s** |
| **Frontend Typecheck** | `apps/web: npm run typecheck` | — | **PASS** | 1.15s |
| **Frontend Production Build** | `apps/web: npm run build` | — | **PASS** | 2.29s |

---

## 24. Model Integrity Verification

- **Artifacts Changed**: 0
- **Retrained Models**: 0
- **Cox Coefficients Altered**: 0
- **Baseline Survival Altered**: 0
- **Evaluation Holdout Touched**: 0
- **Model Version**: `1.0.0-cox-production-baseline` (Verified invariant)
- **Feature Version**: `1.0.0-survival-clean-15feat` (Verified invariant)

---

## 25. LOOP 13 Regression Verification

All 27 invariants established in LOOP 13 remain verified and operational:
1. Complete data flow from clean CSV to snapshot to prediction is intact.
2. Temporal leakage protection ($t \le T$) is strictly enforced.
3. 7 purged features are rejected at all entry points.
4. Model artifact digests match canonical checksums.
5. Linear decomposition $\eta = \sum \beta_j x_j$ matches to machine precision ($0.000000$ error).
6. Non-causal association phrasing is strictly maintained.

---

## 26. LOOP 14 Regression Verification

All end-to-end integration flows verified in LOOP 14 against canonical case `CASE-E2E-LOOP14` remain valid:
- `linear_predictor`: `-2.347267` (Exact match)
- `relative_hazard`: `0.09563` (Exact match)
- `survival_probability_90d`: `0.98673` (Exact match)
- `risk_band_90d`: `ADVISORY_MEDIAN_RELATIVE_HAZARD` (Exact match)
- `calibration_status`: `UNRELIABLE_SPARSE_EVAL_EVENTS` (Exact match)

---

## 27. Known Limitations

1. **Evaluation Event Sparsity ($N=18$ holdout events)**: As documented in LOOP 8, 9, 13, and 14, calibration for sparse transitions remains flagged `UNRELIABLE_SPARSE_EVAL_EVENTS`.
2. **Decision Support Advisory Scope**: Survival model outputs are purely advisory statistical indicators for workload prioritization and cannot make legally binding acquisition decisions.
3. **In-Memory Rate Limiting in Development**: When Redis is inactive in offline development environments, rate limiting defaults to safe in-memory tracking.

---

## 28. Final Acceptance Status

| Criterion | Target | Measured | Result |
| :--- | :---: | :---: | :---: |
| No Critical/High Unresolved Vulnerabilities | 0 | 0 | **MET** |
| Officer/Citizen Authorization Boundary | Enforced | Verified HTTP 403 on Citizen Attempts | **MET** |
| IDOR / Cross-Case Protection | Enforced | Verified HTTP 403 on Cross-Case Retrieval | **MET** |
| Citizen Redaction Guarantee | 100% | Zero ML Telemetry in Citizen Responses | **MET** |
| Input Validation / Fuzzing Resistance | 100% | 49 Fuzzing Vectors Handled Cleanly (422) | **MET** |
| Error Leakage Prevention | 0 Leaks | Zero Tracebacks / Internal Details | **MET** |
| Model Artifact Integrity | 100% Match | All 17 SHA256 Hashes Verified | **MET** |
| Fail-Closed Model Loading | Enforced | Verified HTTP 500 on Missing Artifacts | **MET** |
| Concurrency Determinism | 100% | Verified at 1, 5, 10, 25, 50 Threads | **MET** |
| Direct Inference Latency (Median) | < 5 ms | **2.47 ms** | **MET** |
| FastAPI Roundtrip Latency (Median) | < 8 ms | **4.27 ms** | **MET** |
| Full Backend Test Suite | 100% Pass | **1,026 Passed (0 Failed)** | **MET** |
| Frontend Typecheck & Build | 100% Pass | **Clean Build** | **MET** |

---

# **PASS WITH DOCUMENTED FINDINGS — SECURITY + PERFORMANCE AUDIT COMPLETE**

All security boundaries, input fuzzing defenses, cryptographic model verifications, concurrency scaling profiles, and end-to-end regression guarantees have been audited, remediated, and verified.
The next authorized project step is:
**LOOP 16 — FINAL PROJECT VALIDATION**
