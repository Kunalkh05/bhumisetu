# BHUMISETU — Production Operations & Maintenance Runbook

**Audience**: DevOps Engineers, Site Reliability Engineers, Platform Administrators  
**Applicability**: Staging and Production Deployments of BHUMISETU  

---

## 1. Application Startup & Process Supervision

### 1.1 Backend REST API Container
Run the API container using `Dockerfile.production`:
```bash
docker run -d \
  --name bhumisetu-api \
  --restart always \
  -p 8000:8000 \
  --env-file .env.production \
  bhumisetu:production \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 1.2 Celery General Worker (Queues: `import`, `maintenance`, `ocr`, `ml`)
```bash
docker run -d \
  --name bhumisetu-worker-general \
  --restart always \
  --env-file .env.production \
  bhumisetu:production \
  celery -A app.workers.celery_app worker --loglevel=INFO --concurrency=4 -Q import,maintenance,ocr,ml
```

### 1.3 Celery Measurement Worker (Queue: `ocr_bulk` — R11.10 Isolated Credential)
```bash
docker run -d \
  --name bhumisetu-worker-measure \
  --restart always \
  --env-file .env.production.measure \
  bhumisetu:production \
  celery -A app.workers.celery_app worker --loglevel=INFO --concurrency=1 -Q ocr_bulk
```

### 1.4 Celery Beat Periodic Scheduler
```bash
docker run -d \
  --name bhumisetu-worker-beat \
  --restart always \
  --env-file .env.production \
  bhumisetu:production \
  celery -A app.workers.celery_app beat --loglevel=INFO --schedule=/var/lib/celery/celerybeat-schedule
```

### 1.5 Frontend Web Portal (Vercel / Edge CDN)
- Static build output directory: `bhumi-setu/apps/web/dist`
- Build command: `npm run build`
- Deploy command via Vercel CLI:
  ```bash
  vercel deploy --prod
  ```

---

## 2. Health & Readiness Probes

| Probe Type | Endpoint | Protocol | Interval | Timeout | Healthy Threshold | Failure Threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Liveness** | `/healthz` | HTTP | 10s | 2s | 1 | 3 |
| **Readiness** | `/api/healthz` | HTTP | 15s | 3s | 1 | 3 |
| **Model Health** | `/api/officer/survival-risk/health` | HTTPS (Bearer Auth) | 60s | 5s | 1 | 2 |

---

## 3. Database Migrations & PostGIS Maintenance

### 3.1 Initial Database Setup
Before applying Alembic migrations to a newly provisioned PostgreSQL instance, connect as administrative user and verify extensions:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS ltree;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### 3.2 Executing Migrations (Alembic)
Always test migrations against staging before running on production:
```bash
cd bhumi-setu/apps/api
# Check current migration revision
.venv/bin/alembic current

# Run migrations to head
.venv/bin/alembic upgrade head
```

### 3.3 Database Backup Procedure
Perform automated daily backups using PostgreSQL custom-format dumps:
```bash
BACKUP_FILE="bhumisetu_db_backup_$(date +%Y%m%d_%H%M%S).dump"

pg_dump \
  -d "$DATABASE_URL" \
  --format=custom \
  --blobs \
  --verbose \
  --file="$BACKUP_FILE"

# Upload encrypted backup to cold backup storage
aws s3 cp "$BACKUP_FILE" s3://bhumisetu-cold-backups/database/ --sse aws:kms
rm -f "$BACKUP_FILE"
```

### 3.4 Point-in-Time Recovery
To restore a backup into a disaster recovery database:
```bash
pg_restore \
  -d "$NEW_DATABASE_URL" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  "$BACKUP_FILE"
```

---

## 4. Rollback Procedures

### 4.1 Application Rollback (API & Workers)
If a release causes regressions:
1. Re-deploy the previous container image tag:
   ```bash
   aws ecs update-service --cluster bhumisetu-prod --service api --task-definition bhumisetu-api:<PREVIOUS_STABLE_REVISION>
   ```
2. For Vercel frontend, roll back instantaneously via the Vercel Dashboard or CLI:
   ```bash
   vercel rollback <PREVIOUS_DEPLOYMENT_URL>
   ```

### 4.2 Database Migration Rollback
If a newly applied migration needs to be reverted:
```bash
cd bhumi-setu/apps/api
.venv/bin/alembic downgrade -1
```

---

## 5. Incident Response & Troubleshooting Playbooks

### Playbook A: ML Model Inference Failure / Artifact Loss
* **Symptom**: `/api/officer/survival-risk/predict` returns HTTP 500 or degraded status warnings.
* **Diagnosis**:
  1. Inspect container logs for `ArtifactNotFound` or missing coefficient files in `models/cox_baseline/`.
  2. Verify SHA-256 hashes against `bhumisetu_deployment_harness/.state/ml_hashes.json`.
* **Resolution**:
  1. Re-mount or re-copy frozen model directory from release package.
  2. The system will automatically enter **safe-fallback mode**, returning statutory rule-based milestone dates with clear degraded mode labeling.

### Playbook B: Redis Connection Outage
* **Symptom**: User sessions log out unexpectedly; Celery tasks accumulate.
* **Diagnosis**:
  1. Test Redis connectivity: `redis-cli -u "$REDIS_URL" ping`.
  2. Inspect Redis memory and connection limits.
* **Resolution**:
  1. Restart managed Redis instance or fail over to read-replica.
  2. The API automatically falls back to ephemeral `InMemorySessionBackend` for emergency session continuity.

### Playbook C: Celery Worker Queue Backlog
* **Symptom**: Scanned document OCR processing remains in `PENDING` state for > 5 minutes.
* **Diagnosis**:
  1. Inspect active workers: `celery -A app.workers.celery_app inspect active`.
  2. Check queue depth in Redis: `redis-cli -u "$REDIS_URL" llen ocr`.
* **Resolution**:
  1. Scale worker containers horizontally from 1 to 4 replicas.
  2. Confirm Tesseract OCR system binary is operational within the container.

---

## 6. Secrets & Credential Management Policy

1. **Zero Secret Commits**: Passwords, connection strings, and JWT keys must **never** be committed to version control.
2. **Environment Injection**: Inject credentials at runtime via AWS Secrets Manager, HashiCorp Vault, or Vercel Environment Variables.
3. **Internal Token Restriction**: `JWT_SECRET` must **only** be supplied to the API container for internal service tokens. User sessions reside exclusively in Redis as opaque tokens.
4. **Holdout Credential Isolation (R11.10)**: `HOLDOUT_STORAGE_*` credentials must **never** be injected into `worker-ocr` or `worker-ml`. They may only be held by `worker-measure`.
