# Performance Testing Runbook

## Overview
This runbook describes the performance testing procedures for the BHUMISETU
platform to ensure the system meets response time and throughput requirements
under expected production load.

## Performance Requirements

| Metric | Target | Maximum |
|--------|--------|---------|
| API response time (P50) | < 200ms | 500ms |
| API response time (P95) | < 500ms | 1000ms |
| API response time (P99) | < 1000ms | 2000ms |
| Page load time (First Contentful Paint) | < 1.5s | 3s |
| Search results response | < 300ms | 800ms |
| Document upload processing | < 5s | 15s |
| Concurrent users supported | 500 | 1000 |
| Throughput | 200 req/s | 500 req/s |

## Load Testing Tools

- **k6** — Primary load testing tool (JavaScript-based)
- **Apache Bench (ab)** — Quick endpoint benchmarks
- **Lighthouse** — Frontend performance auditing
- **pgbench** — Database-specific load testing

## Test Scenarios

### 1. Smoke Test
Quick sanity check with minimal load.

```bash
k6 run --vus 5 --duration 30s scripts/perf/smoke.js
```

### 2. Load Test
Normal expected production traffic.

```bash
k6 run --vus 100 --duration 5m scripts/perf/load.js
```

### 3. Stress Test
Push beyond normal capacity to find breaking point.

```bash
k6 run --vus 500 --duration 10m scripts/perf/stress.js
```

### 4. Soak Test
Extended duration to detect memory leaks and resource exhaustion.

```bash
k6 run --vus 50 --duration 2h scripts/perf/soak.js
```

## Key Endpoints to Test

| Endpoint | Method | Priority |
|----------|--------|----------|
| `/api/health` | GET | Baseline |
| `/api/v1/cases` | GET | High |
| `/api/v1/cases/{id}` | GET | High |
| `/api/v1/citizen/search` | GET | Critical |
| `/api/v1/parcels` | GET | Medium |
| `/api/v1/documents/upload` | POST | Medium |
| `/api/v1/predictions` | GET | Medium |
| `/api/v1/gis/parcels` | GET | High |
| `/api/v1/dashboard` | GET | High |

## Database Performance

### Query Optimization
```sql
-- Find slow queries
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Check index usage
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check table statistics
ANALYZE;
SELECT relname, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 10;
```

### Connection Pool Monitoring
```bash
# Check current connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check pool statistics
psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

## Frontend Performance

### Lighthouse Audit
```bash
npx lighthouse https://bhumisetu.gov.in --output=json --output-path=perf-report.json
```

### Bundle Size Analysis
```bash
cd bhumi-setu/apps/web
npx vite-bundle-visualizer
```

## Reporting

After each performance test run:
1. Save k6 output with `--out json=results.json`
2. Compare against previous baseline
3. Flag any regressions > 20% from baseline
4. Document findings in `docs/compliance/performance-reports/`
