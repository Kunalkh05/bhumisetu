# Data Retention Policy — BHUMISETU Platform

## Document Control
- **Version**: 1.0
- **Last Updated**: 2026-09-29
- **Owner**: BHUMISETU Data Protection Officer
- **Classification**: Internal

## 1. Purpose

This policy defines the data retention and disposal schedule for all
personal and operational data processed by the BHUMISETU land acquisition
platform, in compliance with:

- Information Technology Act, 2000
- IT (Reasonable Security Practices and Procedures) Rules, 2011
- Right to Fair Compensation and Transparency in Land Acquisition,
  Rehabilitation and Resettlement Act, 2013 (RFCTLARR)
- Digital Personal Data Protection Act, 2023 (DPDPA)

## 2. Scope

This policy covers all data categories collected and processed by BHUMISETU:
- Citizen personal data (names, Aadhaar numbers, contact information)
- Land parcel records and survey data
- Compensation and valuation records
- Case management documents
- Officer activity logs
- ML model training data and predictions

## 3. Retention Schedules

### 3.1 Active Case Data
| Data Category | Retention Period | Justification |
|---------------|-----------------|---------------|
| Case records | Duration of case + 15 years | RFCTLARR compliance |
| Land parcel data | Permanent | Revenue records requirement |
| Compensation records | 30 years | Audit and appeals period |
| Officer notes | Duration of case + 7 years | Administrative record |

### 3.2 Citizen Personal Data
| Data Category | Retention Period | Justification |
|---------------|-----------------|---------------|
| Aadhaar numbers | Duration of case + 2 years | KYC verification |
| Contact details | Duration of case + 5 years | Notification obligations |
| Financial details | Duration of case + 10 years | Payment reconciliation |
| Objection records | Duration of case + 15 years | Legal proceedings |

### 3.3 Operational Data
| Data Category | Retention Period | Justification |
|---------------|-----------------|---------------|
| Access logs | 2 years | Security audit |
| API request logs | 90 days | Performance monitoring |
| Error logs | 1 year | Debugging and analysis |
| ML model outputs | 5 years | Decision audit trail |

## 4. Data Disposal

### 4.1 Disposal Methods
- **Soft delete**: Mark records as deleted; retain for grace period
- **Hard delete**: Permanently remove from database and all backups
- **Anonymization**: Strip PII while retaining statistical utility

### 4.2 Disposal Process
1. Automated scheduler identifies records past retention period
2. Data Protection Officer reviews disposal batch
3. Disposal is logged with record count, categories, and method
4. Confirmation report generated and archived

## 5. Data Subject Rights

Under DPDPA 2023, data subjects (citizens) have the right to:
- **Access**: Request a copy of their personal data
- **Correction**: Request correction of inaccurate data
- **Erasure**: Request deletion (subject to legal retention obligations)
- **Grievance**: File a complaint about data handling

The platform implements these via the Data Subject Request (DSR) module
at `/api/v1/retention/dsr/`.

## 6. Exceptions

Data under active litigation, government audit, or RTI proceedings
is exempt from scheduled disposal until the matter is resolved.

## 7. Review

This policy shall be reviewed annually or when there are significant
changes to applicable legislation.
