# BHUMISETU System Architecture

## Overview

BHUMISETU is a unified AI-powered land intelligence platform built for
transparent and efficient land acquisition under India's RFCTLARR Act 2013.

## Architecture Principles

1. **Separation of Concerns**: Backend API (FastAPI), Frontend SPA (React),
   and ML pipeline are independently deployable.
2. **Security by Default**: All endpoints enforce RBAC, rate limiting,
   and data gating.
3. **Regulatory Compliance**: Data retention, audit trails, and statutory
   timelines are first-class concerns.
4. **Multi-language Support**: Full i18n support for English, Hindi, and Marathi.

## High-Level Architecture

```
                    ┌─────────────────────────────────┐
                    │         Load Balancer            │
                    │          (Nginx)                 │
                    └──────────┬──────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼──────┐ ┌──────▼──────┐ ┌───────▼───────┐
     │  Citizen SPA  │ │ Officer SPA │ │   API Server  │
     │   (React)     │ │  (React)    │ │  (FastAPI)    │
     └───────────────┘ └─────────────┘ └───────┬───────┘
                                               │
                    ┌──────────────────────────┼──────────┐
                    │                          │          │
           ┌───────▼───────┐ ┌────────────────▼──┐ ┌────▼─────┐
           │  PostgreSQL   │ │   Redis           │ │  Celery  │
           │  + PostGIS    │ │   (Cache/Queue)   │ │  Workers │
           └───────────────┘ └───────────────────┘ └──────────┘
                                                         │
                                               ┌─────────▼──────┐
                                               │   ML Pipeline  │
                                               │  (Survival/    │
                                               │   Prediction)  │
                                               └────────────────┘
```

## Component Details

### API Server (FastAPI)
- **Location**: `bhumi-setu/apps/api/`
- **Port**: 8000
- **Responsibilities**: REST API, authentication, business logic,
  data validation, RBAC enforcement
- **Key Modules**:
  - `app/api/` — Route handlers
  - `app/services/` — Business logic
  - `app/models/` — SQLAlchemy ORM models
  - `app/schemas/` — Pydantic request/response schemas
  - `app/security/` — Auth, RBAC, rate limiting, data gating

### Web Frontend (React + Vite)
- **Location**: `bhumi-setu/apps/web/`
- **Port**: 5173 (dev), served via Nginx (prod)
- **Responsibilities**: Citizen portal, officer portal, dashboards,
  compensation calculator, document verification
- **Key Modules**:
  - `src/components/citizen/` — Citizen-facing views
  - `src/components/officer/` — Officer dashboard components
  - `src/components/calculator/` — Compensation calculator
  - `src/services/` — API client services
  - `src/i18n/` — Internationalization

### ML Pipeline
- **Location**: `bhumi-setu/ml/`
- **Responsibilities**: Case duration prediction, survival analysis,
  risk scoring, anomaly detection
- **Key Models**:
  - Kaplan-Meier survival baseline
  - Feature-engineered prediction models

### Database (PostgreSQL + PostGIS)
- **Version**: PostgreSQL 14+
- **Extensions**: PostGIS (geospatial), pg_trgm (text search)
- **Schema Management**: Alembic migrations

## Data Flow

### Case Creation Flow
1. Officer submits case via Officer Portal
2. API validates input against policy rules
3. Case record created in PostgreSQL
4. Celery task queued for document processing
5. Notifications sent to affected citizens

### Citizen Lookup Flow
1. Citizen searches by survey number or case ID
2. API checks access permissions (gated response)
3. PII is redacted based on citizen's relationship to case
4. Response served with appropriate data visibility
