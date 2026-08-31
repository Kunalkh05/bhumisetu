# BHUMISETU

A land acquisition management platform for Indian government departments.

Land acquisition cases move through statutory stages — social impact assessment,
preliminary notification, declaration, award, payout, possession — each with a
legally mandated deadline. Cases slip. When they slip, landowners wait years for
compensation and projects stall. The usual reason a case slips is that nobody
noticed it was about to.

BHUMISETU tracks cases end to end and predicts which ones are about to miss a
statutory deadline, so officers can intervene while intervening still helps.

## What it does

**For officers** — a case workspace holding parcels, ownership records, statutory
notices, objections, awards and payouts; a map of parcels shaded by delay risk;
a queue of cases ranked by urgency with recommended actions; a review screen for
correcting machine-read land records.

**For landowners** — a separate text-first surface for checking their own case
status, timeline, and documents. Built for a 400 kbps rural connection with a
150 KB total budget, because connectivity should not decide whether someone can
follow the acquisition of their own land.

**Underneath** — scanned land records are digitized by OCR with per-field
confidence scores; low-confidence extractions go to an officer rather than into
the record. A validation engine raises issues for missing fields, impossible date
orders, contradictions between documents, and duplicates. An append-only event
log records every state change, and doubles as both the citizen-visible timeline
and the feature source for delay prediction.

## Three things that shape the architecture

**The event log is a product feature, not a journal.** It is the only source of
the citizen timeline and of machine learning features, and it is append-only.
Every decision about state answers to it.

**Almost nothing legally significant is a constant.** Stage sets, statutory
periods, OCR thresholds, risk band cutoffs, retention periods, and the delay
label definition are all effective-dated configuration. The code does not contain
the numbers, and a lint fails the build if a period literal reaches date
arithmetic. This is what lets one deployment serve more than one state.

**The model advises, it never decides.** No stage transition, objection disposal,
award change, payout, or notice issue can be initiated by a risk score. Officers
see the explanation factors beside any score and can override on record.

## Documentation

Read in this order:

| Document | What it holds |
|---|---|
| [`.kiro/specs/bhumisetu/requirements.md`](.kiro/specs/bhumisetu/requirements.md) | 32 requirements, 297 acceptance criteria, and 11 open policy decisions |
| [`.kiro/specs/bhumisetu/design.md`](.kiro/specs/bhumisetu/design.md) | Architecture, data model, 88 correctness properties |
| [`.kiro/specs/bhumisetu/tasks.md`](.kiro/specs/bhumisetu/tasks.md) | 29 tasks / 136 sub-tasks in dependency order |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How work happens here, and how to pick something up |
| [`docs/local-setup.md`](docs/local-setup.md) | Running it on your machine |
| [`docs/commit-convention.md`](docs/commit-convention.md) | Commit format |

The spec is the source of truth. Where this README and the spec disagree, the
spec is right and the README is stale.

## Stack

Python 3.11 · FastAPI · SQLAlchemy 2.0 · Alembic · Celery on Redis ·
PostgreSQL + PostGIS · MinIO · React 18 + TypeScript + Vite (officer portal
only) · Jinja2 server-rendered (citizen portal) · XGBoost + SHAP

The citizen portal is deliberately not React. A React baseline is ~46 KB
gzipped before any application code, and the total budget for the case status
view is 150 KB.

## Layout

```
.kiro/specs/bhumisetu/     requirements, design, tasks
bhumi-setu/
  apps/api/                FastAPI: services, models, migrations
    app/citizen/           server-rendered citizen portal
  apps/web/                React officer portal
  ml/                      features, labelling, training
  workers/                 OCR and ML Celery workers
  deployment/              Caddy proxy, MinIO policies
docs/                      setup and conventions
```

## Status

Early. The spec is complete; implementation has started. Current state is in
[`tasks.md`](.kiro/specs/bhumisetu/tasks.md) — checked boxes are done.

Three policy decisions are unconfirmed and deliberately block related work:
the delay label definition (Q1), the governing act and its statutory periods
(Q8), and personal data retention periods (Q10). No statutory period is seeded
and personal data erasure ships disabled until Q8 and Q10 are answered.
