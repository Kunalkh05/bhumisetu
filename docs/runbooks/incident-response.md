# Incident Response Runbook

## Overview
This document outlines the incident response procedure for the BHUMISETU
land acquisition portal. All production incidents must be triaged, resolved,
and documented following this process.

## Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| SEV-1 | Platform completely down | 15 minutes | Database unreachable, API 500s |
| SEV-2 | Major feature broken | 1 hour | Compensation calculator failing |
| SEV-3 | Minor feature degraded | 4 hours | Slow search results |
| SEV-4 | Cosmetic / low impact | 24 hours | UI alignment issues |

## Incident Commander Responsibilities

1. **Acknowledge** the incident within the response time window
2. **Triage** to confirm severity and identify affected systems
3. **Communicate** status to stakeholders
4. **Coordinate** the technical response team
5. **Document** the timeline and resolution

## Diagnosis Steps

### API / Backend Issues

```bash
# Check API health
curl -s https://bhumisetu.gov.in/api/health | jq .

# Check recent logs
docker logs bhumisetu-api --tail 100

# Check database connectivity
docker exec bhumisetu-api python -c "from app.db import engine; engine.connect()"

# Check Redis / Celery
docker exec bhumisetu-redis redis-cli ping
docker exec bhumisetu-worker celery -A app.workers inspect active
```

### Frontend Issues

```bash
# Check Nginx proxy status
curl -I https://bhumisetu.gov.in

# Verify static assets are serving
curl -s https://bhumisetu.gov.in/officer/index.html | head -20

# Check for JavaScript errors in browser console
# (Manual step — open DevTools > Console)
```

### Database Issues

```bash
# Check connection count
SELECT count(*) FROM pg_stat_activity;

# Check for long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC
LIMIT 10;

# Check table bloat
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

## Recovery Procedures

### Restart Services
```bash
docker-compose restart api
docker-compose restart worker
docker-compose restart nginx
```

### Database Recovery
```bash
# Kill long-running queries
SELECT pg_cancel_backend(pid) FROM pg_stat_activity
WHERE duration > interval '5 minutes' AND state = 'active';

# Rebuild indexes if corrupted
REINDEX TABLE acquisition_cases;
```

### Rollback Deployment
```bash
# Revert to previous Docker image
docker-compose down
docker tag bhumisetu-api:latest bhumisetu-api:rollback
docker pull bhumisetu-api:previous
docker-compose up -d
```

## Post-Incident Review

After every SEV-1 or SEV-2 incident, conduct a blameless post-mortem:

1. **Timeline**: Minute-by-minute account of events
2. **Root Cause**: Technical root cause analysis
3. **Impact**: Users affected, data integrity, financial impact
4. **Action Items**: Preventive measures with owners and deadlines
5. **Lessons Learned**: What went well, what didn't

Document the review in `docs/compliance/incident-reports/`.
