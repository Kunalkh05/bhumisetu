# BHUMISETU safe deployment task

Inspect the existing repository before changing anything. Deploy the existing application only; do not implement Smart Land Finder or other features.

1. Inspect Git state, frontend/backend manifests, Dockerfiles, env examples, migrations, PostgreSQL/PostGIS, Redis/Celery, document storage, map provider, model artifacts, auth, CORS, and health endpoints. Read LOOP 13–16 reports if present.
2. Report required environment-variable NAMES only; never print values.
3. Assess a possible topology: Vercel frontend, Docker/Python host for FastAPI, persistent worker service, managed PostgreSQL with verified PostGIS support, managed Redis, private object storage if required. Verify compatibility and costs; do not assume.
4. Make minimal, reversible deployment configuration changes and document startup, health/readiness, migrations, backup, rollback, and secrets.
5. Never retrain models, change Cox coefficients, regenerate or modify ML artifacts, change training/evaluation data, or change frozen model/feature versions.
6. Never weaken authentication, authorization, citizen/officer separation, validation, CORS, audit logging, or fail-closed behavior.
7. Never reset/drop a database, perform destructive migrations, commit secrets, or upload real landowner data to unapproved infrastructure.
8. Do not create paid resources, change DNS, or perform destructive provider actions without explicit user approval.
9. Run existing regression tests, frontend typecheck/build, and deployment checks. Verify frozen artifact SHA-256 hashes before/after.
10. If credentials are missing, prepare config and report exact user action needed. Do not fabricate deployment success.
11. After an authorized deployment, verify public HTTPS frontend/backend, database/PostGIS, Redis/workers, auth boundaries, ML loading, fallback labeling, and public response safety.
12. Generate DEPLOYMENT_READINESS_REPORT.md, DEPLOYMENT_ARCHITECTURE.md, PRODUCTION_SMOKE_TEST_REPORT.md, and PRODUCTION_RUNBOOK.md.
13. Final status must be DEPLOYED AND VERIFIED, DEPLOYED WITH DOCUMENTED LIMITATIONS, BLOCKED — USER ACTION REQUIRED, or BLOCKED — TECHNICAL ISSUE.
14. Do not automatically commit/push. Show diffs and ask before pushing to a protected branch.
