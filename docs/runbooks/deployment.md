# Deployment Runbook — BHUMISETU Platform

## Overview
This document describes the standard deployment procedure for the
BHUMISETU platform across development, staging, and production environments.

## Pre-Deployment Checklist

- [ ] All tests pass (`pytest` for API, `npm test` for web)
- [ ] Database migrations are reviewed and tested
- [ ] Environment variables are configured for target environment
- [ ] Docker images build successfully
- [ ] Security scan passes (no critical vulnerabilities)
- [ ] Changelog is updated

## Environment Configuration

### Development
```bash
# Start all services locally
cd bhumi-setu
./start.sh
```

### Staging
```bash
# Deploy to staging
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# Run smoke tests
curl -s https://staging.bhumisetu.gov.in/api/health
```

### Production
```bash
# Pull latest images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Apply database migrations first
docker-compose exec api alembic upgrade head

# Rolling restart (zero-downtime)
docker-compose up -d --no-deps --scale api=2 api
sleep 30
docker-compose up -d --no-deps --scale api=1 api
```

## Service Dependencies

```
┌─────────┐     ┌──────────┐     ┌──────────────┐
│  Nginx  │────▶│  API     │────▶│  PostgreSQL  │
│ (proxy) │     │ (FastAPI)│     │  + PostGIS   │
└─────────┘     └──────────┘     └──────────────┘
                     │
                     ├──────────▶ Redis
                     │
                     └──────────▶ Celery Workers
```

## Startup Order

1. **PostgreSQL** — Must be ready before API starts
2. **Redis** — Required for caching and task queue
3. **API (FastAPI)** — Depends on PostgreSQL and Redis
4. **Celery Workers** — Depends on Redis and PostgreSQL
5. **Nginx** — Depends on API being available

## Health Checks

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| API | `/api/health` | `{"status": "ok"}` |
| PostgreSQL | `pg_isready` | Exit code 0 |
| Redis | `redis-cli ping` | `PONG` |
| Nginx | `/` | HTTP 200 |

## Rollback Procedure

1. Stop the current deployment
2. Restore the previous Docker image tag
3. Downgrade database migrations if needed
4. Restart services
5. Verify health checks
6. Notify stakeholders

## Post-Deployment Verification

1. Check all health endpoints
2. Verify recent cases load correctly
3. Test citizen portal search functionality
4. Confirm officer login and dashboard access
5. Validate compensation calculator outputs
6. Review error logs for new exceptions
