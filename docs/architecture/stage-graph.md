# RFCTLARR Act 2013 — Stage Graph Documentation

## Overview
This document describes the case stage workflow graph implemented in
`app/services/stage_graph.py`. The stage graph enforces the legal
sequence of land acquisition proceedings under the RFCTLARR Act 2013.

## Stage Transitions

```
┌─────────────────┐
│  SIA Initiated  │
│   (Section 4)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SIA Completed  │
│   (Section 6)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Expert Review  │
│   (Section 7)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Govt Approval  │
│   (Section 8)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Section 11 Notification│◄──────── Public Notice
│  (Preliminary)          │          (Gazette + Local)
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Objection Hearing      │◄──────── 60 Working Days
│  (Section 15)           │          Deadline
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Section 19 Declaration │◄──────── Within 12 Months
│                         │          of Section 11
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Survey & Measurement   │
│  (Section 20)           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Valuation              │
│  (Section 26)           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Section 23 Award       │◄──────── Within 12 Months
│                         │          of Section 19
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Payment                │
│  (Section 31-34)        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Possession             │◄──────── 60 Days Notice
│  (Section 38)           │          Required
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Completed              │
│                         │
└─────────────────────────┘
```

## Transition Rules

### Forward Transitions
- Each stage can only transition to the immediately next stage
- Transitions require the current stage's mandatory actions to be completed
- Statutory timelines must not be exceeded

### Backward Transitions
- Allowed only in specific circumstances (court orders, remand)
- Must be logged with reason and authorizing officer
- Cannot reverse completed payments or possessions

### Parallel Tracks
- Multiple parcels within a case may be at different stages
- The case's overall stage reflects the earliest stage among all parcels
- Individual parcel stages can advance independently

## Validation Rules

| Transition | Pre-conditions |
|------------|---------------|
| SIA Initiated → SIA Completed | SIA report uploaded, expert committee formed |
| SIA Completed → Expert Review | Expert group members assigned |
| Expert Review → Govt Approval | Expert review report approved |
| Govt Approval → Section 11 | Government order issued |
| Section 11 → Objection Hearing | Notice published in gazette, 60-day window |
| Objection Hearing → Section 19 | All objections heard, report submitted |
| Section 19 → Survey | Declaration published |
| Survey → Valuation | Survey report with area measurements |
| Valuation → Section 23 Award | Market value assessed, solatium calculated |
| Section 23 → Payment | Award declared, bank details verified |
| Payment → Possession | Payment credited to landowner account |
| Possession → Completed | Physical possession taken, record updated |

## Implementation Notes

The stage graph is implemented as a directed graph in `stage_graph.py`.
Key functions:

- `is_valid_transition(from_stage, to_stage)` — Check if a transition is allowed
- `get_next_stages(current_stage)` — Get valid next stages
- `get_stage_requirements(stage)` — Get pre-conditions for entering a stage
- `validate_transition(case_id, target_stage)` — Full validation with database checks
