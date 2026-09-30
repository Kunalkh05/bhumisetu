# Monitoring and Alerting Runbook

## Overview
This runbook documents the monitoring stack and alerting rules for the
BHUMISETU platform. Proactive monitoring prevents incidents before they
impact users.

## Monitoring Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| Metrics | Prometheus | System and application metrics |
| Visualization | Grafana | Dashboards and graphs |
| Logs | Loki / ELK | Centralized log aggregation |
| Alerts | Alertmanager | Alert routing and notification |
| APM | OpenTelemetry | Distributed tracing |

## Key Metrics

### Application Metrics
- `http_requests_total` — Total HTTP requests by method, path, status
- `http_request_duration_seconds` — Request latency histogram
- `active_cases_count` — Number of active acquisition cases
- `celery_tasks_total` — Total background tasks processed
- `celery_tasks_failed` — Failed background task count

### Infrastructure Metrics
- `node_cpu_seconds_total` — CPU usage per container
- `node_memory_usage_bytes` — Memory consumption
- `pg_stat_activity_count` — Active database connections
- `redis_connected_clients` — Redis client connections

## Alert Rules

### Critical (SEV-1)
| Alert | Condition | Action |
|-------|-----------|--------|
| API Down | `up{job="api"} == 0` for 2m | Page on-call engineer |
| DB Connection Pool Exhausted | `pg_stat_activity_count > 90` | Scale connections or restart |
| High Error Rate | `rate(http_requests_total{status=~"5.."}[5m]) > 0.05` | Investigate error logs |

### Warning (SEV-2)
| Alert | Condition | Action |
|-------|-----------|--------|
| High Latency | `histogram_quantile(0.95, http_request_duration_seconds) > 2s` | Profile slow endpoints |
| Disk Space Low | `node_filesystem_avail_bytes < 10%` | Clean up or expand storage |
| Celery Queue Backlog | `celery_tasks_pending > 100` | Scale workers |

### Info (SEV-3)
| Alert | Condition | Action |
|-------|-----------|--------|
| Certificate Expiry | `ssl_cert_expires_in_days < 30` | Renew certificate |
| Migration Pending | `alembic_head != alembic_current` | Apply pending migrations |

## Dashboard Setup

### Main Dashboard Panels
1. **Request Rate** — Requests per second over time
2. **Error Rate** — 4xx and 5xx error percentage
3. **Latency P50/P95/P99** — Response time percentiles
4. **Active Users** — Concurrent authenticated sessions
5. **Database Queries** — Query rate and duration
6. **Celery Tasks** — Task throughput and failure rate
7. **System Resources** — CPU, memory, disk across all nodes

## On-Call Schedule

- Primary on-call rotates weekly
- Secondary backup is always assigned
- Escalation to engineering lead after 30 minutes for SEV-1
- Handoff procedure: Update incident channel, share context
