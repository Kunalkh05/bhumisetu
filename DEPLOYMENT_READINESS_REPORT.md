# BHUMISETU — Production Deployment Readiness Report

**Platform**: BHUMISETU National Land Acquisition Management & Decision Support Platform  
**Compliance Standard**: RFCTLARR Act 2013 Statutory Compliance & DPDP Act 2023 Data Privacy  
**Audit Baseline**: Loop 13 (E2E ML Audit) &rarr; Loop 14 (Product Integration) &rarr; Loop 15 (Adversarial Security Audit) &rarr; Loop 16 (Human Browser E2E Validation)  
**Final Status**: `BLOCKED — USER ACTION REQUIRED`

---

## 1. Executive Summary & Repository Audit

An exhaustive, non-destructive audit of the entire BHUMISETU repository was conducted prior to executing deployment validations. The repository contains the complete production-grade source code, database migrations, frozen statistical machine learning models, and dual-portal interfaces (Officer Case Management Workspace and Citizen Land Intelligence Portal).

### 1.1 Git State & Working Tree Audit
* **Branch**: `main` (tracked ahead of `origin/main` by 2 commits: `d32e934` "docs(validation): add loop 16 final human product validation deliverables" and `4323b2d` "fix(validation): harden human e2e and ml product validation").
* **Protected Branch Policy**: No automated pushes. Direct push to `main` is gated and requires explicit operator confirmation and pull request review.
* **Working Tree State**:
  - Tracked modifications:
    - `.gitignore` (safely ignoring deployment harness local state and reports).
    - `bhumi-setu/apps/web/src/App.tsx` (URL parameter deep-linking support for citizen portal tabs).
    - `bhumi-setu/apps/web/src/context/AppContext.tsx` (URL parameter routing for portal mode and officer tabs).
  - New deployment configuration artifacts:
    - `Dockerfile.production` (root standalone multi-tier production container manifest).
    - `bhumi-setu/apps/web/vercel.json` (Vercel edge rewrite and SPA routing manifest).
    - Harness artifacts (`bhumisetu_deployment_harness/`).

### 1.2 Frontend & Backend Manifests
* **Frontend (`bhumi-setu/apps/web/package.json`)**:
  - Engine: Vite 6.2.3, React 19.0.1, TypeScript 5.8.2.
  - Styling & UI: Tailwind CSS v4.1.14 (`@tailwindcss/vite`), Lucide React 0.546.0, Motion 12.23.24.
  - Spatial GIS: Leaflet 1.9.4 with `@types/leaflet`.
  - Typecheck validation: `tsc --noEmit` executed with **0 errors**.
  - Production build: `vite build` completed successfully (**1,730 modules compiled**, `dist/` bundle created with zero errors).
* **Backend API (`bhumi-setu/apps/api/requirements.txt`)**:
  - Engine: Python 3.11+ / FastAPI 0.115, Uvicorn, Pydantic v2, Pydantic Settings.
  - Database ORM & Migrations: SQLAlchemy 2.0, Alembic, `psycopg[binary]`.
  - Concurrency & Caching: Redis, Celery (distributed asynchronous worker queue).
  - Security & Cryptography: Argon2-cffi, PyJWT (internal service tokens only).
  - Scientific & Statistical ML: `lifelines` (Cox Proportional Hazards and Kaplan-Meier estimators), NumPy, Pandas, Scikit-learn.
  - Test Suite: Pytest with Hypothesis property-based testing framework.

### 1.3 Container & Orchestration Manifests
* **`bhumi-setu/docker-compose.yml`**: Defines the local multi-service development topology with services:
  - `postgres`: PostgreSQL 15 with PostGIS 3.3.
  - `redis`: Redis 7 Alpine (session store and Celery broker).
  - `minio`: S3-compatible storage with `minio-init` provisioning 3 isolated buckets.
  - `proxy`: Caddy edge reverse proxy with brotli quality 11 compression and HTTP/3 support.
  - `api`: FastAPI REST API gateway (`uvicorn app.main:app`).
  - `worker-ocr`, `worker-measure`, `worker-ml`, `worker-general`, `worker-beat`: Dedicated Celery worker roles.
  - `web`: Vite development server for Officer Portal.
* **`bhumi-setu/apps/api/Dockerfile`**: Dev container utilizing host bind-mounts for live reloading.
* **`Dockerfile.production`**: Standalone production container manifest copying API source, ML packages, clean reference datasets, and frozen models into `/app` with non-root security execution (`bhumisetu:10001`).

### 1.4 Database Migrations & PostgreSQL/PostGIS Support
* **Alembic Version History**: 21 linear migrations located in `bhumi-setu/apps/api/alembic/versions/`:
  - `0001_baseline.py`: Initializes mandatory PostgreSQL extensions:
    ```sql
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE EXTENSION IF NOT EXISTS ltree;
    CREATE EXTENSION IF NOT EXISTS pgcrypto;
    ```
    and creates the restricted `bhumisetu_app` role and administrative area triggers.
  - `0002_policy_config.py` through `0021_missing_translation.py`: Tables for event logging (`event`), personal datum encryption, task outbox, land parcels with spatial geometries (`geometry(MultiPolygon, 4326)`), ownership records, statutory notices, objections, awards, and retention tracking.
* **Zero Destructive Migrations**: All migrations preserve existing data. Dropping or resetting the production database is strictly prohibited.

### 1.5 Redis & Celery Worker Topology
* **Message Broker & Cache**: Redis 7+ (`REDIS_URL`).
* **Session Management**: Opaque server-side session tokens stored in Redis (`SESSION_STORE_URL`), enabling immediate token revocation (R1.5) and instant role change propagation (R2.6). JWTs are **never** used for citizen or officer sessions.
* **Worker Queue Segmentation**:
  - `ocr`: Interactive document text extraction.
  - `ocr_bulk`: Accuracy measurement against the holdout cohort (strictly isolated credentials).
  - `ml`: Asynchronous feature precomputation and risk scoring.
  - `import`: High-throughput cadastral parcel and gazette batch ingestion.
  - `maintenance`: Periodic SLA breach monitoring, outbox delivery, and DPDP retention sweeps.
* **Scheduler**: Celery Beat runs periodic tasks without serving HTTP traffic.

### 1.6 Document Storage & Map Provider
* **Storage Hierarchy**: S3-compatible private object storage with strict three-bucket separation:
  - `bhumisetu-documents`: Public/officer uploaded deed scans, 7/12 RoR records, and statutory gazette PDFs.
  - `bhumisetu-models`: Frozen model weights and calibration metadata.
  - `bhumisetu-holdout`: Isolated validation holdout dataset (inaccessible to training/tuning workers per statutory requirement R11.10).
* **Map & GIS Provider**:
  - Leaflet GIS visualizer configured with OpenStreetMap, Esri World Imagery, and OpenTopoMap base tiles.
  - Vector tile endpoint `/api/officer/gis/tiles/{z}/{x}/{y}.mvt` served by backend PostGIS spatial queries.

### 1.7 Frozen ML Artifact Integrity
* **Model Baseline**: Semi-parametric Cox Proportional Hazards baseline (`models/cox_baseline/`) and Kaplan-Meier non-parametric baselines (`models/kaplan_meier_baseline/`).
* **Model Version**: `1.0.0-cox-production-baseline`
* **Feature Contract Version**: `1.0.0-survival-clean-15feat` (15 safe point-in-time predictors; 7 purged future-leakage predictors permanently blocked).
* **Verification**: All **102 candidate ML files** across `models/` and `data/real_data/clean/` were cryptographically hashed using SHA-256 before and after verification. **102 / 102 hashes match baseline with zero byte drift**.

### 1.8 Authentication, Authorization, CORS & Health Endpoints
* **RBAC & Principal Boundary**: Three distinct security principals (`Principal.kind`):
  - `OFFICER`: Full case access within assigned administrative jurisdiction (`ltree` path scoping). Access to survival risk predictions, hazard ratios, and explainability decompositions.
  - `CITIZEN`: Strict IDOR-protected single-case boundary. Access to procedural rights, statutory milestones, and compensation calculators. **All PII and internal hazard scores ($\eta$) are redacted by default via `GatedRoute`**.
  - `SERVICE`: Internal automation principal authenticated via Bearer token (`JWT_SECRET`) for `/internal/*` routes only.
* **CORS Policy**: Configured in `app/main.py`. Development origins allow localhost; production mode defaults to `https://bhumisetu.gov.in` (configurable to operator frontend domain). Wildcard origins with credentials are strictly forbidden (SEC-FIND-05).
* **Health & Probes**:
  - `GET /healthz`: Public container liveness probe (HTTP 200 `{"status":"ok"}`).
  - `GET /api/healthz`: Public API readiness probe (HTTP 200 `{"status":"ok","app":"BHUMISETU","version":"1.0.0"}`).
  - `GET /api/officer/survival-risk/health`: Authenticated officer ML subsystem probe returning artifact checksums, versions, and governance disclaimers.

### 1.9 Loop 13–16 Validation History Summary
* **Loop 13**: Validated 6-tier ML data flow from raw gazettes to React dashboard; verified 15 safe features allowlist and 7 purged leakage variables.
* **Loop 14**: End-to-end integration across data ingestion, point-in-time snapshotting, survival inference, authorization gates, and UI presentation.
* **Loop 15**: Adversarial security and performance audit. Identified and remediated 6 security defects (`SEC-FIND-01` through `SEC-FIND-06`) and locked down with 87 regression tests.
* **Loop 16**: Human product validation in live Google Chrome browser via CDP. Verified 34-step Officer Journey and 9-stage Citizen Journey with zero defects.

---

## 2. Required Environment Variable Names (No Values Committed)

To deploy the BHUMISETU platform to staging or production infrastructure, the operator must provision the following environment variable names in the respective secrets manager or container environment.

### Backend REST API Service (`bhumi-setu/apps/api`)
* `APP_ENV` (e.g. `staging` or `production`)
* `LOG_LEVEL` (e.g. `INFO` or `WARNING`)
* `DATABASE_URL` (SQLAlchemy connection string with PostGIS: `postgresql+psycopg://...`)
* `REDIS_URL` (Redis broker and cache URL)
* `SESSION_STORE_URL` (Redis instance/database for opaque user sessions)
* `OBJECT_STORAGE_ENDPOINT` (S3/MinIO gateway endpoint URL)
* `OBJECT_STORAGE_ACCESS_KEY` (Application access key for documents bucket)
* `OBJECT_STORAGE_SECRET_KEY` (Application secret key for documents bucket)
* `OBJECT_STORAGE_BUCKET` (Bucket name for deed scans and gazettes)
* `OBJECT_STORAGE_MODELS_BUCKET` (Bucket name for model storage)
* `JWT_SECRET` (Cryptographic secret key for `/internal/*` service tokens only)
* `CORS_ORIGINS` (Allowed origins list for frontend domains)
* `PYTHONPATH` (Path configuration for imports)

### Celery Asynchronous Workers (`worker-general`, `worker-ocr`, `worker-ml`, `worker-beat`)
* `APP_ENV`
* `LOG_LEVEL`
* `DATABASE_URL`
* `REDIS_URL`
* `OBJECT_STORAGE_ENDPOINT`
* `OBJECT_STORAGE_ACCESS_KEY`
* `OBJECT_STORAGE_SECRET_KEY`
* `OBJECT_STORAGE_BUCKET`
* `OBJECT_STORAGE_MODELS_BUCKET`
* `PYTHONPATH`

### Celery Accuracy Measurement Worker (`worker-measure` Only)
* `HOLDOUT_STORAGE_BUCKET` (Statutorily isolated holdout bucket)
* `HOLDOUT_STORAGE_ACCESS_KEY` (Holdout read key; prohibited on `worker-ocr`)
* `HOLDOUT_STORAGE_SECRET_KEY` (Holdout secret key; prohibited on `worker-ocr`)

### Frontend Web Portal (`bhumi-setu/apps/web`)
* `VITE_API_URL` (Relative `/api` or absolute backend URL)

### Edge Proxy / Ingress (Caddy / Cloudflare / Nginx)
* `BHUMISETU_SITE_ADDRESS` (Domain name, e.g. `portal.bhumisetu.gov.in`)
* `BHUMISETU_TLS_DIRECTIVE` (ACME TLS directive, e.g. `tls admin@bhumisetu.gov.in`)

---

## 3. Production Topology & Compatibility Assessment

| Infrastructure Layer | Recommended Production Solution | Technical Feasibility & Compatibility | Estimated Monthly Cost |
| :--- | :--- | :--- | :--- |
| **Frontend Web Portal** | **Vercel** / **Cloudflare Pages** | **Compatible**. Static Vite/React 19 SPA. Bundle size: 1.16 MB JS (297 KB gzip), 160 KB CSS (27 KB gzip). Edge rewrites route `/api/*` to backend and `/officer/*` to SPA. | $0 – $20 / month (Hobby / Pro) |
| **Backend REST API** | **AWS ECS (Fargate)** / **Google Cloud Run** / **Render** | **Compatible**. Containerized Python 3.11/FastAPI service using `Dockerfile.production`. Stateless, horizontally scalable (2+ replicas recommended). Memory requirement: ~512 MB – 1 GB RAM per replica. | $25 – $60 / month |
| **Persistent Celery Workers** | **AWS ECS Service** / **Render Background Worker** | **Compatible**. Persistent worker running `celery -A app.workers.celery_app worker` and Celery Beat. Cannot run on serverless scale-to-zero compute due to active queue listeners. | $15 – $35 / month |
| **Database & Cadastral GIS** | **Managed PostgreSQL (AWS RDS / Supabase / Neon)** | **Compatible with verification**: Target database **must** support PostgreSQL 15+ and allow `CREATE EXTENSION IF NOT EXISTS postgis`, `ltree`, and `pgcrypto`. Serverless DBs without native C-extension support are incompatible. | $25 – $65 / month |
| **Session & Broker Store** | **Managed Redis (AWS ElastiCache / Upstash / Redis Cloud)** | **Compatible**. Standard Redis 7.0+ protocol required for Celery broker list operations and opaque session token key-value lookups. | $0 – $25 / month (Free tier to Small instance) |
| **Object Storage** | **AWS S3** / **Cloudflare R2** | **Compatible**. S3 API compatible private buckets. Low egress, high durability for statutory gazette documents and land deed scans. | $3 – $12 / month (Pay per usage) |
| **Total Estimated Cloud Infrastructure Cost** | — | — | **~$68 – $217 / month** |

---

## 4. Safety & Statutory Compliance Invariants

1. **Frozen ML Artifact Guarantee**: Zero model retraining, zero modification of Cox PH regression coefficients, zero recalibration refitting. Models operate strictly in deterministic inference mode.
2. **Citizen / Officer Security Isolation**: Citizen users cannot view internal linear predictors ($\eta$), unmasked Aadhaar or phone numbers, or administrative audit trails.
3. **DPDP Act 2023 Compliance**: Strict PII masking enforced at the API boundary using `GatedRoute` and `Sensitive` redaction fields.
4. **Statutory Fail-Closed Behavior**: When cadastral boundary overlaps or unresolved objections exist, workflow advancement is rejected with HTTP 422 `VALIDATION_FAILED`.
5. **No Destructive Database Operations**: Database drop, flush, or unversioned table alter commands are prohibited.
6. **No Secret Commits**: All configuration values are loaded from the execution environment. No plain text secrets are stored in version control.

---

## 5. Verification Test Suite Results

The complete automated test harness was executed prior to deployment assessment:

```
======================================================================
                 BHUMISETU PREFLIGHT VERIFICATION
======================================================================
1. Backend Unit & Integration Suite (Pytest):
   - Total Tests Executed: 1,234
   - Passed:               1,026
   - Skipped (PostGIS):      208  (Spatial tests skipped without live local DB)
   - Failed:                   0  (100% Pass Rate)
   - Execution Time:       20.04 seconds

2. Frontend Static Analysis & Typechecking:
   - Tool: TypeScript Compiler (`tsc --noEmit`)
   - Errors: 0 (PASS)

3. Frontend Production Build:
   - Tool: Vite 6.4.3 (`vite build`)
   - Modules Transformed: 1,730
   - Output: `dist/index.html`, `dist/assets/*.js`, `dist/assets/*.css`
   - Build Time: 1.31 seconds (PASS)

4. Cryptographic ML Artifact Integrity Check:
   - Candidate Files Hashed: 102
   - Baseline Mismatches:      0 (100% Match, PASS)
======================================================================
```

---

## 6. Exact User Action Required to Proceed with Deployment

The deployment task is currently paused at the authorization boundary per safety directives (Rule 8: *"Do not create paid resources, change DNS, or perform destructive provider actions without explicit user approval"* and Rule 10: *"If credentials are missing, prepare config and report exact user action needed. Do not fabricate deployment success"*).

To execute the deployment, the operator must complete the following steps:

1. **Select and Authorize Hosting Providers**:
   - Confirm selection of hosting topology (e.g. Vercel for Frontend, AWS ECS / Render for API & Workers, AWS RDS / Supabase for PostgreSQL with PostGIS, AWS ElastiCache / Redis Cloud for Redis, AWS S3 / Cloudflare R2 for Storage).
2. **Provision Managed Database with PostGIS**:
   - Provision PostgreSQL 15+ instance.
   - Run preliminary extension enabling query:
     ```sql
     CREATE EXTENSION IF NOT EXISTS postgis;
     CREATE EXTENSION IF NOT EXISTS ltree;
     CREATE EXTENSION IF NOT EXISTS pgcrypto;
     ```
3. **Configure Secrets**:
   - Populate environment variables in your cloud secrets manager or container configuration using the variable names listed in Section 2.
4. **Authorize Infrastructure Execution**:
   - In `bhumisetu_deployment_harness/.env.harness`, set:
     ```bash
     ALLOW_INFRA_CHANGES=1
     DEPLOY_FRONTEND_CMD="<your frontend deploy command, e.g. vercel deploy --prod>"
     DEPLOY_BACKEND_CMD="<your backend deploy command, e.g. aws ecs update-service ...>"
     DEPLOY_WORKERS_CMD="<your worker deploy command>"
     ```
5. **Run Verified Cloud Deployment & Smoke Suite**:
   - Execute deployment:
     ```bash
     ./bhumisetu_deployment_harness/run.sh deploy
     ```
   - Set public HTTPS URLs in `.env.harness` (`FRONTEND_URL` and `BACKEND_URL`).
   - Execute public smoke test verification:
     ```bash
     ./bhumisetu_deployment_harness/run.sh smoke
     ```
