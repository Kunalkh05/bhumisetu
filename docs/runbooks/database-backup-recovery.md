# Database Backup and Recovery Runbook

## Overview
This document covers the backup strategy and disaster recovery procedures
for the BHUMISETU PostgreSQL database, which stores all land acquisition
records, citizen data, and case management information.

## Backup Strategy

### Backup Types

| Type | Frequency | Retention | Method |
|------|-----------|-----------|--------|
| Full backup | Daily (2:00 AM IST) | 30 days | `pg_dump` |
| Incremental WAL | Continuous | 7 days | WAL archiving |
| Monthly archive | 1st of month | 2 years | `pg_dump` + compression |

### Backup Commands

#### Full Database Backup
```bash
# Compressed full backup
pg_dump -h localhost -U bhumisetu -Fc -f /backups/bhumisetu_$(date +%Y%m%d).dump bhumisetu_db

# Plain SQL backup (for readability)
pg_dump -h localhost -U bhumisetu -f /backups/bhumisetu_$(date +%Y%m%d).sql bhumisetu_db

# Schema-only backup
pg_dump -h localhost -U bhumisetu --schema-only -f /backups/schema_$(date +%Y%m%d).sql bhumisetu_db
```

#### Table-Specific Backup
```bash
# Backup critical tables individually
pg_dump -h localhost -U bhumisetu -t acquisition_cases -Fc -f /backups/cases_$(date +%Y%m%d).dump bhumisetu_db
pg_dump -h localhost -U bhumisetu -t land_parcels -Fc -f /backups/parcels_$(date +%Y%m%d).dump bhumisetu_db
pg_dump -h localhost -U bhumisetu -t personal_data -Fc -f /backups/pii_$(date +%Y%m%d).dump bhumisetu_db
```

### WAL Archiving
```bash
# postgresql.conf settings
archive_mode = on
archive_command = 'cp %p /wal_archive/%f'
wal_level = replica
```

## Recovery Procedures

### Point-in-Time Recovery (PITR)
```bash
# Stop PostgreSQL
pg_ctl stop -D /var/lib/postgresql/data

# Restore base backup
pg_restore -d bhumisetu_db /backups/bhumisetu_20260929.dump

# Configure recovery
cat > /var/lib/postgresql/data/recovery.conf << EOF
restore_command = 'cp /wal_archive/%f %p'
recovery_target_time = '2026-09-29 18:00:00+05:30'
EOF

# Start PostgreSQL
pg_ctl start -D /var/lib/postgresql/data
```

### Full Restore from Dump
```bash
# Create fresh database
dropdb bhumisetu_db
createdb bhumisetu_db

# Restore from dump
pg_restore -d bhumisetu_db -j 4 /backups/bhumisetu_20260929.dump

# Verify restoration
psql -d bhumisetu_db -c "SELECT count(*) FROM acquisition_cases;"
```

### Table-Level Recovery
```bash
# Restore specific table to a temporary database
createdb bhumisetu_recovery
pg_restore -d bhumisetu_recovery -t acquisition_cases /backups/bhumisetu_20260929.dump

# Copy recovered data back
pg_dump -t acquisition_cases bhumisetu_recovery | psql bhumisetu_db
dropdb bhumisetu_recovery
```

## Verification

### Daily Backup Verification
```bash
# Verify backup file exists and has reasonable size
ls -lh /backups/bhumisetu_$(date +%Y%m%d).dump

# Test restoration to verification database
createdb bhumisetu_verify
pg_restore -d bhumisetu_verify /backups/bhumisetu_$(date +%Y%m%d).dump
psql -d bhumisetu_verify -c "SELECT count(*) FROM acquisition_cases;"
dropdb bhumisetu_verify
```

### Monthly Integrity Check
```bash
# Full table integrity check
psql -d bhumisetu_db -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname='public';" | \
  while read schema table; do
    echo "Checking $table..."
    psql -d bhumisetu_db -c "SELECT count(*) FROM $table;"
  done
```

## Disaster Recovery Plan

### Recovery Time Objective (RTO): 4 hours
### Recovery Point Objective (RPO): 1 hour (with WAL archiving)

### Steps:
1. Assess the failure scope (single table vs. full database)
2. Identify the most recent clean backup
3. Determine if PITR is needed (to recover to a specific point)
4. Execute recovery procedure
5. Verify data integrity
6. Resume application services
7. Document the incident
