# BHUMISETU System Architecture Map

**Classification**: Official System Architecture Map  
**Version**: 1.0.0 (Post-LOOP 15 Architecture Reconstruction)  
**Author**: Master Autonomous Validation Harness  
**Platform**: BHUMISETU National Land Acquisition Management & Decision Support Platform  

---

## 1. High-Level System Architecture & Invariant Chain

```
                    HUMAN (Citizen / Officer / Administrator)
                                       │
                                       ▼
                       FRONTEND / UI LAYER (React 19 / Jinja2)
                    ┌─────────────────────────────────────────┐
                    │ Citizen Portal (/)  & Officer (/officer)│
                    │ SwaaS Design System & SVG Risk Curves   │
                    └────────────────────┬────────────────────┘
                                         │ HTTP / REST / Cookie / Session
                                         ▼
                     AUTHENTICATION & ACCESS GATEWAY (FastAPI)
                    ┌─────────────────────────────────────────┐
                    │ Principal Resolution (OFFICER / CITIZEN)│
                    │ GatedRoute & ResponseGate Redaction     │
                    │ Redis Session Backend & CSRF Validation │
                    └────────────────────┬────────────────────┘
                                         │ Scoped Principal
                                         ▼
                       API / SERVICE DISPATCH LAYER
                    ┌─────────────────────────────────────────┐
                    │ /api/officer/*, /api/citizen/*, /c/*    │
                    │ Unified Error Envelope (DomainError)    │
                    │ CaseService, NoticeService, GisService  │
                    └────────────────────┬────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   │                                           │
                   ▼                                           ▼
      DATABASE / PERSISTENCE TIER                 ML SURVIVAL INFERENCE TIER
  ┌─────────────────────────────────┐         ┌─────────────────────────────────┐
  │ PostgreSQL 15 + ltree + PostGIS │         │ Point-in-Time Snapshot (T)      │
  │ Append-Only Event Log & Sourcing│         │ Feature Builder (15 Covariates) │
  │ Outbox Dispatcher (task_outbox) │         │ Purged Leakage Blacklist (7)    │
  │ DPDP 2023 Retention & Erasure   │         │ Frozen Cox Proportional Hazards │
  └─────────────────────────────────┘         │ Horizon Probabilities & Risk    │
                                              │ Additive Explainability Engine  │
                                              │ Audit Telemetry Buffer          │
                                              └────────────────┬────────────────┘
                                                               │
                                                               ▼
                                                  REDACTION & RESPONSE GATE
                                              ┌─────────────────────────────────┐
                                              │ Strip Sensitive(OFFICER_ONLY)   │
                                              │ Citizen: Plain Timeline Only    │
                                              │ Officer: Full Risk & Multipliers│
                                              └────────────────┬────────────────┘
                                                               │
                                                               ▼
                                                    HUMAN (Verified Output)
```

---

## 2. Architectural Tiers & Boundaries

### Tier 1: Presentation & User Interface
* **Web Portal (`apps/web`)**:
  * Single Page Application built on **React 19.0.1**, **TypeScript 5.8.2**, **Tailwind CSS 4**, and **Vite 6.2.3**.
  * SwaaS (Secure, Scalable and Accessible Indian Government Websites) 2026 design language compliant with multilingual support (EN / MR / HI), high-contrast accessibility mode, and responsive layout.
  * **Citizen Experience**:
    * Public root (`/`) with tabs for Case Search, Compensation Calculator, Gazette Notices, State Portal Directory, and BhuMitra AI Chat modal.
    * Server-rendered alternative surface (`/c/{case_id}`) powered by Jinja2 templates via `render_gated` (§9.2, §10).
  * **Officer Workspace (`/officer/`)**:
    * KPI Dashboard, Active Proceeding Management, Case Workspace with 8 functional tabs (Overview, Land Parcels & 7/12, RERA Cross-Ref, Statutory Notices, Sec 15 Objections, Awards & DBT Payouts, Validation Engine Rules, Survival Risk & ML Engine).
    * Specialized officer hubs: RERA Integration Hub, PostGIS Cadastral GIS Viewer, Document OCR Reviewer, Intervention Queue, Validation Hub, Model Observability Hub, Bulk Import Hub, DPDP Retention Hub, and Audit Log Viewer.
* **Frontend API Client (`apps/web/src/services/backendApi.ts` & `survivalRiskService.ts`)**:
  * Unified communication with FastAPI backend (`/api/*`).
  * In-memory caching and request deduplication to prevent stampedes.
  * Prominent, unmissable `DEGRADED / SIMULATION MODE` banners when offline or uncalibrated.

### Tier 2: Authentication & Boundary Security Gateway
* **Session Management (`app/security/auth.py` & `app/security/access.py`)**:
  * Dual-mode authentication:
    * **Officer**: Opaque token in Redis session store (`RedisOfficerSessionBackend`), falling back gracefully to `InMemorySessionBackend` in development/testing. CSRF double-submit token validation on mutative state requests.
    * **Citizen**: Ephemeral passcode authentication verifying case ownership (`Principal(kind="CITIZEN", case_id=...)`).
    * **Internal Services**: Cryptographic Bearer tokens verifying service identity (`Principal(kind="SERVICE")`).
* **Jurisdiction Confinement & RBAC**:
  * Hierarchical `ltree` queries (`IN.MH.PUNE.HAVELI <@ IN.MH`) preventing unauthorized inter-district queries.
  * Fail-closed access boundaries on case IDs preventing IDOR attacks.
* **Response Gate & Redaction (`app/security/gate.py` & `app/api/gated_route.py`)**:
  * Every router mounted via `GatedRoute`.
  * Field-level `@Sensitive(Visibility.OFFICER_ONLY)` metadata ensures that internal linear predictors ($\eta$), Cox coefficients, hazard multipliers, and case rankings are physically stripped before serialization to citizen or unauthenticated callers.

### Tier 3: API & Application Service Layer
* **FastAPI Modular Monolith (`apps/api/app/main.py`)**:
  * High-performance asynchronous API server.
  * Structured error envelope on every failure: `{"code": str, "message": str, "details": dict}`.
  * Routers divided by consumer surface:
    * `officer_router` (`/api/officer/*`)
    * `citizen_router` (`/api/citizen/*`)
    * `citizen_html` (`/c/*`)
    * `internal_router` (`/internal/*`)
* **Domain Services (`apps/api/app/services/`)**:
  * `CaseService`: Proceeding lifecycle and state graph transitions.
  * `NoticeService` & `ObjectionService`: Statutory Section 11/15/19 notifications and citizen hearings.
  * `CompensationService` & `compensation_calc.py`: RFCTLARR 2013 multiplier, solatium (100%), and 12% statutory interest computation.
  * `GisService`: GeoJSON boundary validation, geodesic ST_Area calculations, and cadastral spatial overlap detection.
  * `OcrService`: Asynchronous document text extraction, confidence scoring, and land record entity recognition.
  * `ValidationEngine`: Rule evaluation engine for legal compliance and data completeness.
  * `PolicyService`: Hierarchical policy override resolution.

### Tier 4: Database & State Persistence Tier
* **PostgreSQL 15 Engine**:
  * Append-only `event_log` table storing immutable sequence of business events.
  * Optimistic locking and version checking via `VersionedMixin`.
  * `task_outbox` table implementing the Transactional Outbox Pattern for reliable Celery asynchronous task execution.
  * Full DPDP Act 2023 compliance infrastructure: Personal Data classification, Data Subject Request (DSR) logging, retention period projection, and cryptographic erasure sweeps.

### Tier 5: Point-in-Time Snapshot & Feature Pipeline
* **Snapshot Engine (`ml/src/features/snapshots.py`)**:
  * Deterministic temporal slicing evaluated strictly as of timestamp $T$ using `AsOfMode.KNOWABLE_AT`.
  * Physical exclusion of all events, notices, objections, and milestones occurring at $t > T$, strictly eliminating data leakage.
* **15-Feature Production Contract**:
  * `derived_days_since_case_initiation`, `derived_days_in_current_stage`, `derived_days_since_latest_notice`
  * `derived_notice_count`, `extension_count`, `has_statutory_extension`, `statutory_time_limit_days`
  * `statutory_extension_proximity`, `project_type_*` (linear / infra / industrial), `district_*` (Solapur, etc.), `current_stage_*`
* **Permanent Purge Leakage Blacklist**:
  * Strict rejection/purging of forbidden variables: `award_recorded`, `objection_count`, `parcel_count`, `open_issue_count`, `notified_area_hectares`, `affected_landowner_count`, `compensation_amount_inr`.

### Tier 6: Frozen Statistical Machine Learning & Survival Engine
* **Frozen Model Artifacts (`models/cox_baseline/`)**:
  * Parametric Cox Proportional Hazards baseline models for statutory transitions:
    1. `SECTION_11_TO_SECTION_19` (3 covariates, $L_2$ regularized)
    2. `SECTION_19_TO_AWARD` (8 covariates, $L_2$ regularized)
    3. `CASE_INITIATION_TO_MILESTONE` (11 covariates)
  * Non-parametric Kaplan-Meier baseline survival curves (`models/kaplan_meier_baseline/`).
* **Mathematical Invariants**:
  * Linear predictor: $\eta = \sum_{j=1}^p \beta_j x_j$
  * Relative hazard ratio: $\theta = \exp(\eta) = \prod_{j=1}^p \exp(\beta_j x_j)$
  * Survival curve: $S(h \mid x) = [S_0(h)]^{\exp(\eta)}$
  * Milestone event probability: $P(\text{event by } h \mid x) = 1 - S(h \mid x)$ across discrete horizons $h \in \{30, 90, 180, 365, 730\}$ days.
* **Rigorous Calibration Governance**:
  * Explicit reporting of `CALIBRATION NOT RELIABLE DUE TO EVENT SPARSITY` rather than unverified parametric smoothing when events are sparse.

### Tier 7: Explainability, Uncertainty & Observability
* **Explainability Engine (`SurvivalExplainer`)**:
  * Exact additive linear decomposition attributing log-hazard variations to specific case attributes.
  * Strict suppression of causal language (using purely statistical associative phrasing).
* **Audit & Observability Buffer**:
  * Bounded sliding window in-memory telemetry buffer tracking inference requests, case IDs, transitions, horizons, and execution latencies without recording credentials or citizen PII.
