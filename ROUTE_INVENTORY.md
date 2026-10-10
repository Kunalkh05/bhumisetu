# BHUMISETU Route Inventory

**Version**: 1.0.0 (Master Autonomous Validation Harness)  
**Date**: October 2026  
**Scope**: Full Discovery of Frontend SPA Views, Citizen HTML Routes, and FastAPI Backend Endpoints  

---

## 1. Frontend SPA Views (`bhumi-setu/apps/web`)

| Route / View ID | Role | Purpose | Backend Dependency | Authentication | Authorization | Expected Data | Interactive Elements | Test Status |
|:---|:---|:---|:---|:---|:---|:---|:---|:---:|
| `CITIZEN:HOME` | Public / Citizen | Landing page with platform overview, key statistics, quick search | `/api/healthz`, mockData | None | Public | Statistics, state portal links, quick links | Language toggle, Search input, Persona login trigger, AI chat trigger | **PASS** |
| `CITIZEN:TRACK_CASE` | Public / Citizen | Track land acquisition case status, view timeline and notices | `/api/citizen/cases/{id}/milestone-timeline` | Passcode / Public | Case-specific | Case milestone dates, current stage, public notices | Search by Case ID, village filter, view timeline button | **PASS** |
| `CITIZEN:CALCULATOR` | Public / Citizen | Interactive RFCTLARR 2013 compensation calculator | `/api/cases` (optional) | None | Public | Market value, factor (1-2), 100% solatium, 12% interest | Land type select (Urban/Rural), area input, market rate input, calculate button | **PASS** |
| `CITIZEN:NOTICES` | Public / Citizen | Search and view gazette notifications (Sec 11, 19, etc.) | `/api/officer/cases/{id}/notices` | None | Public | Gazette notification PDFs, dates, village, survey numbers | Search filter, district dropdown, PDF download button | **PASS** |
| `CITIZEN:DIRECTORY` | Public / Citizen | Official contacts and state portal direct links | None (Local directory) | None | Public | State revenue portals (MahaBhulekh, Bhulekh UP, etc.) | State links, contact cards, external redirects | **PASS** |
| `CITIZEN:CITIZEN_SERVICES` | Public / Citizen | Grievance filing, Section 15 objection guidance, FAQ | `/api/citizen/objection` | Ephemeral | Citizen | Rights guide, grievance categories, submission status | Objection form, file upload, category select, submit button | **PASS** |
| `OFFICER:DASHBOARD` | Officer | Executive overview of proceedings, risk alerts, KPI metrics | `/api/officer/dashboard` | Cookie / Bearer | `Principal(kind="OFFICER")` | Total cases, high risk count, pending awards, stage counts | Filter by district, case click navigates to workspace | **PASS** |
| `OFFICER:CASE_WORKSPACE` | Officer | In-depth case management with 8 dedicated functional tabs | `/api/officer/cases/{id}/*` | Cookie / Bearer | `Principal(kind="OFFICER")` | Case metadata, parcels, notices, objections, ML survival | 8 tabs (Overview, Parcels, RERA, Notices, Objections, Awards, Validation, AI ML) | **PASS** |
| `OFFICER:RERA_GATEWAY` | Officer | RERA cross-referencing and Section 11 conflict detection | RERA API / mockData | Cookie / Bearer | `Principal(kind="OFFICER")` | Active RERA projects, promoters, conflict flags | Search RERA ID, verify conflict, filter by status | **PASS** |
| `OFFICER:GIS_MAP` | Officer | PostGIS cadastral parcel visualizer with geodesic metrics | `/api/officer/gis/parcels` | Cookie / Bearer | `Principal(kind="OFFICER")` | GeoJSON polygons, ST_Area, parcel survey numbers | Leaflet map layer controls, zoom, click parcel to inspect, boundary overlay | **PASS** |
| `OFFICER:OCR_REVIEW` | Officer | Review uploaded scanned gazettes, OCR text, and entity tags | `/api/officer/documents/processing` | Cookie / Bearer | `Principal(kind="OFFICER")` | OCR text, confidence scores, extracted survey numbers | Accept/reject extraction, re-run OCR, compare original image | **PASS** |
| `OFFICER:INTERVENTION_QUEUE`| Officer | Proactive intervention queue prioritizing high-risk cases | `/api/officer/queue` | Cookie / Bearer | `Principal(kind="OFFICER")` | Recommended interventions, urgency, deadline days | Action disposition buttons (Approve, Defer, Reject), add note | **PASS** |
| `OFFICER:VALIDATION_QUEUE` | Officer | Automated data and legal consistency issue queue | `/api/officer/issues` | Cookie / Bearer | `Principal(kind="OFFICER")` | Open validation rules, severity (CRITICAL/WARNING) | Issue waiver modal, reason input, mark resolved | **PASS** |
| `OFFICER:MODEL_OBSERVABILITY`| Officer | Survival ML model diagnostics, drift metrics, calibration | `/api/officer/survival-risk/health` | Cookie / Bearer | `Principal(kind="OFFICER")` | Baseline hazard curves, Brier score, calibration warning | Transition selector, metric charts, export logs | **PASS** |
| `OFFICER:BULK_IMPORT` | Officer | Batch ingestion of land acquisition datasets | `/api/officer/imports` | Cookie / Bearer | `Principal(kind="OFFICER")` | Batch status, row count, validation errors | File dropzone (CSV/JSON), upload button, inspect errors | **PASS** |
| `OFFICER:DPDP_RETENTION` | Officer | DPDP Act 2023 compliance, DSR requests, erasure sweeps | `/api/officer/dsar` | Cookie / Bearer | `Principal(kind="OFFICER")` | DSR requests, retention schedules, erasure logs | Approve erasure button, view audit trail, filter by status | **PASS** |
| `OFFICER:AUDIT_LOG` | Officer | Immutable audit log viewer of all system actions | `/api/officer/cases/{id}/timeline` | Cookie / Bearer | `Principal(kind="OFFICER")` | Event timestamps, actor, action, previous/new state | Search by actor, filter event type, export log | **PASS** |

---

## 2. Server-Rendered Citizen HTML Routes (`/c/*`)

| HTTP Method | Route | Role | Purpose | Authentication | Authorization | Expected Data | Interactive Elements | Test Status |
|:---|:---|:---|:---|:---|:---|:---|:---|:---:|
| `GET` | `/c/` | Citizen | Server-rendered citizen home | None | Public | Welcome text, case access code prompt | Request access code form | **PASS** |
| `POST` | `/c/request-code` | Citizen | Request SMS/email access code | None | Public | Status message | Mobile number input, Submit button | **PASS** |
| `POST` | `/c/verify` | Citizen | Verify access code and establish session | Form post | Public | Case session cookie | Code input, Verify button | **PASS** |
| `GET` | `/c/case` | Citizen | Single-case summary (redacted) | Citizen Cookie | Case-specific | Case number, village, status | Navigation links | **PASS** |
| `GET` | `/c/timeline` | Citizen | Milestone progress timeline | Citizen Cookie | Case-specific | Milestone events (dates, names) | Milestone list | **PASS** |
| `GET` | `/c/documents` | Citizen | Citizen document list | Citizen Cookie | Case-specific | Available public documents | Download links | **PASS** |
| `GET` | `/c/documents/{id}` | Citizen | View/download document | Citizen Cookie | Case-specific | PDF binary / metadata | Download button | **PASS** |
| `GET` | `/c/documents/{id}/confirm`| Citizen | Confirm receipt of notice | Citizen Cookie | Case-specific | Receipt acknowledgment form | Confirm button | **PASS** |
| `GET` | `/c/notices` | Citizen | Public statutory notices | Citizen Cookie | Case-specific | Notices issued for this case | Notice list | **PASS** |
| `GET` | `/c/objections` | Citizen | Objections filed for this case | Citizen Cookie | Case-specific | Hearing dates, objection status | Submit objection link | **PASS** |
| `POST` | `/c/correction` | Citizen | Submit record correction request | Citizen Cookie | Case-specific | Confirmation message | Textarea, Submit button | **PASS** |
| `GET` | `/c/my-data` | Citizen | DPDP personal data summary | Citizen Cookie | Case-specific | Name, survey numbers held | Export data button | **PASS** |
| `POST` | `/c/language` | Citizen | Switch display language | None | Public | Redirect response | Language select | **PASS** |
| `GET` | `/c/offline` | Citizen | Offline fallback page | None | Public | Offline service worker instructions | Retry connection button | **PASS** |
| `GET` | `/c/static/sw.js` | Citizen | Service worker for offline asset caching | None | Public | Javascript service worker | Browser worker registration | **PASS** |

---

## 3. Officer & ML API Routes (`/api/officer/*` & `/internal/*`)

| HTTP Method | Route | Role | Purpose | Authentication | Authorization | Expected Data | Interactive Elements | Test Status |
|:---|:---|:---|:---|:---|:---|:---|:---|:---:|
| `POST` | `/api/auth/persona` | Dev / Officer | Switch active persona for testing | None | Public / Dev | UserSession object + cookie | Persona select | **PASS** |
| `GET` | `/api/auth/me` | Officer / Citizen | Retrieve current authenticated user | Cookie / Bearer | Any valid principal | User session metadata | Refresh user state | **PASS** |
| `POST` | `/api/auth/logout` | All | Terminate active session | Cookie / Bearer | Any valid principal | Success envelope | Logout trigger | **PASS** |
| `GET` | `/api/officer/dashboard` | Officer | Dashboard summary KPIs and case counts | Cookie / Bearer | `OFFICER` | Case counts, risk breakdown | Dashboard widgets | **PASS** |
| `GET` | `/api/officer/cases` | Officer | Paginated case listing with filters | Cookie / Bearer | `OFFICER` (Jurisdiction) | Array of cases with stages and dates | Search, filter, pagination | **PASS** |
| `GET` | `/api/officer/cases/{id}` | Officer | Case detail record | Cookie / Bearer | `OFFICER` (Jurisdiction) | Full case entity | View case | **PASS** |
| `GET` | `/api/officer/cases/{id}/workspace`| Officer | Full workspace bundle (parcels, notices, etc.) | Cookie / Bearer | `OFFICER` | Aggregated case workspace payload | Switch tabs | **PASS** |
| `GET` | `/api/officer/cases/{id}/timeline` | Officer | Complete event history | Cookie / Bearer | `OFFICER` | Ordered event log records | Filter timeline | **PASS** |
| `POST` | `/api/officer/cases/{id}/stage` | Officer | Advance proceeding statutory stage | Cookie / Bearer + CSRF | `OFFICER` | Updated case entity | Stage select, Confirm transition | **PASS** |
| `GET` | `/api/officer/cases/{id}/survival-risk` | Officer | Cox model survival risk & probabilities | Cookie / Bearer | `OFFICER` (SEC-FIND-01) | Relative hazard, horizon probabilities, flags | Transition select, horizon toggles | **PASS** |
| `GET` | `/api/officer/cases/{id}/survival-risk/explanation`| Officer | Additive linear explanation ($\beta_j \cdot x_j$) | Cookie / Bearer | `OFFICER` | Top factors, multipliers, linear predictor $\eta$ | Inspect explanation modal | **PASS** |
| `GET` | `/api/officer/survival-risk/health` | Officer | ML model health & diagnostic status | Cookie / Bearer | `OFFICER` | Frozen model metadata, baseline hashes | Observability dashboard | **PASS** |
| `POST` | `/api/officer/survival-risk/predict` | Officer | On-demand survival prediction for arbitrary snapshot | Cookie / Bearer | `OFFICER` | Inferred hazard ratio, survival curve | Re-calculate button | **PASS** |
| `GET` | `/api/officer/gis/parcels` | Officer | Cadastral parcels within bounding box | Cookie / Bearer | `OFFICER` | GeoJSON FeatureCollection | Pan / Zoom map | **PASS** |
| `GET` | `/api/officer/gis/parcels/{id}/geometry` | Officer | High-fidelity polygon geometry | Cookie / Bearer | `OFFICER` | GeoJSON Polygon + ST_Area | Parcel inspector | **PASS** |
| `GET` | `/api/officer/queue` | Officer | Priority intervention recommendations | Cookie / Bearer | `OFFICER` | Ranked interventions | Disposition action buttons | **PASS** |
| `POST` | `/api/officer/queue/{case_id}/actions/{id}/disposition`| Officer | Record action taken on recommendation | Cookie / Bearer + CSRF | `OFFICER` | Updated intervention record | Resolve / Dismiss button | **PASS** |
| `POST` | `/api/officer/imports` | Officer | Upload batch land acquisition file | Cookie / Bearer | `OFFICER` | Import batch ID and status | File upload | **PASS** |
| `GET` | `/api/officer/issues` | Officer | List legal/data validation issues | Cookie / Bearer | `OFFICER` | Validation issue list | Filter by severity | **PASS** |
| `POST` | `/api/officer/issues/{id}/waive` | Officer | Waive non-critical validation issue | Cookie / Bearer + CSRF | `OFFICER` | Updated issue record | Waive with reason modal | **PASS** |
| `GET` | `/api/officer/dsar` | Officer | DPDP Data Subject Request queue | Cookie / Bearer | `OFFICER` | Pending DSR requests | Action queue | **PASS** |
| `POST` | `/api/officer/dsar/{id}/disposal` | Officer | Dispose DSR request (erasure/export) | Cookie / Bearer + CSRF | `OFFICER` | Disposal confirmation | Complete erasure button | **PASS** |
| `POST` | `/internal/ml/survival/predict` | Service | Internal microservice ML prediction | Bearer Token | `SERVICE` (SEC-FIND-03) | Model prediction payload | Service client call | **PASS** |
| `GET` | `/healthz` | Public | Process liveness probe | None | None | `{"status": "ok"}` | Automated monitoring | **PASS** |
| `GET` | `/api/healthz` | Public | API service health with version | None | None | `{"status": "ok", "app": "BHUMISETU", "version": "1.0.0"}` | Frontend probe | **PASS** |
