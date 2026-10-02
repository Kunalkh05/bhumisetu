# FEATURE FUNCTIONALITY MATRIX (LOOP 16)

This matrix documents the functional, API, ML, and security boundary status across all components of the **BHUMISETU** platform, validated via autonomous real-browser human simulations (Google Chrome via CDP) and deep integration test harnesses.

| Domain | Feature / Component / Route | Role | Expected Behavior | Observed Result | Evidence | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Auth** | Persona Switcher (`/api/auth/persona`) | Officer / Citizen | Sets appropriate session cookie and isolates opposing role | Cookies isolated properly; opposite cookie removed on switch | `tests_harness/test_citizen_journey.py` | **PASS** |
| **Auth** | Session Identity (`/api/auth/me`) | Officer | Returns authenticated officer subject ID, role, jurisdiction | 200 OK with IAS officer credentials | `04_officer_session.png` | **PASS** |
| **Auth** | Session Termination (`/api/auth/logout`) | Officer / Citizen | Clears session cookie and invalidates session | 200 OK; redirects to unauthenticated landing page | Step 32 in `test_officer_journey.py` | **PASS** |
| **Security** | Protected Route Denial | Anonymous | Direct access to `/officer/` without session blocked | HTTP 401 Unauthorized / UI renders unauthenticated state | Step 34 in `test_officer_journey.py` | **PASS** |
| **Security** | Cross-Role Access Denial | Citizen | Citizen accessing officer endpoints (`/api/officer/...`) strictly blocked | HTTP 403 Forbidden with `NOT_AUTHORISED` code | `citizen_journey_evidence.json` | **PASS** |
| **Security** | Redaction Gate | Citizen | Internal Cox telemetry (hazard, coefficients, beta) absent from citizen payload | Zero leaked keys in response payload | Step 8 in `test_citizen_journey.py` | **PASS** |
| **Security** | Leakage Protection | Officer | Snapshot date in the future ($T > \text{today}$) rejected | HTTP 422 Unprocessable Entity (`future information rejected`) | Phase 11 in `test_ml_deep_validation.py` | **PASS** |
| **Security** | Purged Variables Rejection | Officer | Sending any of 7 purged variables rejected | HTTP 422 Unprocessable Entity (`feature leakage violation`) | Phase 12 in `test_ml_deep_validation.py` | **PASS** |
| **Security** | Injection & Traversal Guard | Officer | Malicious case IDs (SQLi, path traversal, XSS) rejected | HTTP 422 Unprocessable Entity | Phase 16 in `test_ml_deep_validation.py` | **PASS** |
| **Officer UI**| Dashboard View | Officer | Renders KPI cards (Total Cases, Active, SLA breaches, Risk) | KPI cards render with live telemetry data | `06_dashboard.png` | **PASS** |
| **Officer UI**| Case Directory / Selector | Officer | Displays filterable case list with search bar and stage filters | Search filters by case ref; stage filter works | `08_cases_directory.png` | **PASS** |
| **Officer UI**| 360° Workspace Overview Tab | Officer | Shows case summary, statutory timeline, project details | Renders case details, elapsed days, SLA progress | `11_case_workspace.png` | **PASS** |
| **Officer UI**| Land Parcels Tab | Officer | Lists surveyed land parcels, survey numbers, areas, owners | Renders parcel table and ownership records | Step 16 in `test_officer_journey.py` | **PASS** |
| **Officer UI**| Notices & Documents Tab | Officer | Displays gazetted Section 11/19 notices and PDF attachments | Renders statutory notices and download links | Step 15 in `test_officer_journey.py` | **PASS** |
| **Officer UI**| Objections & Claims Tab | Officer | Lists Section 15 landowner objections and hearing dates | Objections table rendered with status | Step 12 in `test_officer_journey.py` | **PASS** |
| **Officer UI**| Compensation Matrix Tab | Officer | Displays land valuation, solatium (100%), and award breakdown | Compensation calculator and matrix render | Step 12 in `test_officer_journey.py` | **PASS** |
| **Officer UI**| Legal Validation Tab | Officer | Validates statutory compliance rules against RFCTLARR 2013 | Renders compliance checklist and rule passes | Step 12 in `test_officer_journey.py` | **PASS** |
| **Officer UI**| GIS / Map Viewer Tab | Officer | Renders cadastral map layers and boundary polygons | Map container rendered and responsive | `29_gis_viewer.png` | **PASS** |
| **Officer UI**| AI Explanation & Survival Tab| Officer | Embeds Cox Proportional Hazards analytical dashboard | Renders hazard ratio, 5 horizon cards, factor weights | `17_survival_risk_tab.png` | **PASS** |
| **Officer UI**| ML Horizon Cards | Officer | Displays 30d, 90d, 180d, 365d, 730d probability cards | All 5 cards render with event/survival rates | `21_transition_switched.png` | **PASS** |
| **Officer UI**| Probability Toggle | Officer | Switches display between Survival $S(t)$ and Event $P(t)$ | Interactive toggle updates card metrics instantly | Step 23 in `test_officer_journey.py` | **PASS** |
| **Officer UI**| Extrapolation Warning Notice | Officer | Displays warning banner for horizons exceeding 148 days | Explicit advisory banner rendered for 180d, 365d, 730d | Step 26 in `test_officer_journey.py` | **PASS** |
| **Officer UI**| Model Status & Checksums | Officer | Shows model version, SHA256 checksums, and safety disclaimer | Renders `1.0.0-cox-production-baseline` & SHA hashes | Step 27 in `test_officer_journey.py` | **PASS** |
| **Citizen UI**| Citizen Landing Page | Citizen | Plain-language view of acquisition proceeding and rights | Renders clean citizen banner and status overview | `01_citizen_landing.png` | **PASS** |
| **Citizen UI**| Milestone Timeline | Citizen | Displays past milestones, current stage, and statutory days left | Renders Section 11 stage, 365d limit, 45d elapsed | `timeline_response` in evidence | **PASS** |
| **Citizen UI**| Statutory Calculator Tab | Citizen | Public compensation estimator under RFCTLARR 2013 | Renders entitlement rules, solatium, and assistance | `04_statutory_calculator.png` | **PASS** |
| **Citizen UI**| Mobile Responsive Viewport | Citizen | Adapts layout seamlessly to mobile screens (375x667) | Main container, navigation, and cards scale cleanly | `05_mobile_viewport.png` | **PASS** |
| **Citizen UI**| Error State Handling | Citizen | Gracefully displays error for unowned or malformed case IDs | Renders 403/404 forbidden notice without crashing | Step 6 in `test_citizen_journey.py` | **PASS** |
| **ML Engine** | Cox Proportional Hazards | Backend | Point-in-time inference: $\eta = \sum \beta_j x_j$, $\text{HR} = \exp(\eta)$ | Exact floating-point mathematical identity verified | Phase 13 in `test_ml_deep_validation.py` | **PASS** |
| **ML Engine** | Power-Law Survival Curves | Backend | $S(t) = S_0(t)^{\text{HR}}$ across all 5 horizons | Verified against frozen Breslow baseline survival | Phase 13 in `test_ml_deep_validation.py` | **PASS** |
| **ML Engine** | Additive Explainer | Backend | Decomposes $\eta$ into exact additive feature contributions | $\sum \text{contrib} = \eta$ and $\prod \text{mult} = \text{HR}$ verified | Phase 13 in `test_ml_deep_validation.py` | **PASS** |
| **ML Engine** | Feature Sensitivity | Backend | Monotonic response to elapsed stage duration | Strictly linear in $\eta$ space ($\beta = -0.006749$) | Phase 14 in `test_ml_deep_validation.py` | **PASS** |
| **ML Engine** | Event Sparsity Gating | Backend | Gating flags insufficient events without fabricating metrics | `CALIBRATION NOT RELIABLE — INSUFFICIENT EVENTS` reported | Phase 17 in `test_ml_deep_validation.py` | **PASS** |
| **ML Engine** | Fail-Closed Architecture | Backend | Corrupted/missing model directory aborts cleanly | Raises `ArtifactNotFound` with HTTP 500 | Phase 18 in `test_ml_deep_validation.py` | **PASS** |
| **Telemetry** | Audit Trail Logging | Backend | Records timestamp, case ID, transition, latency, version | Audit trail active; 26 test requests recorded | Phase 24 in `test_ml_deep_validation.py` | **PASS** |
| **Performance**| Latency SLA (<50ms) | Backend | Single inference response latency under normal load | p50 = 10.43ms, p95 = 15.15ms, p99 = 15.76ms | Phase 19 in `test_ml_deep_validation.py` | **PASS** |
| **Performance**| Concurrency (20 threads) | Backend | Handles 20 simultaneous inference requests without locks | 100% success rate, p50 = 133.63ms, max = 148.38ms | Phase 19 in `test_ml_deep_validation.py` | **PASS** |
| **Reliability**| Determinism (0-Variance) | Backend | Identical inputs produce bit-for-bit identical outputs | 10 repeat inferences produced 0.000 variance | Phase 22 in `test_ml_deep_validation.py` | **PASS** |
