# Privacy Impact Assessment — BHUMISETU Platform

## Document Control
- **Version**: 1.0
- **Last Updated**: 2026-09-29
- **Classification**: Confidential
- **Prepared By**: Data Protection Officer

## 1. Project Description

**BHUMISETU** is a unified AI-powered land intelligence platform for
managing land acquisition proceedings under the RFCTLARR Act 2013. The
platform processes personal data of landowners, affected families, and
government officers.

## 2. Data Collection Summary

### 2.1 Personal Data Collected

| Category | Data Elements | Legal Basis | Source |
|----------|--------------|-------------|--------|
| Identity | Name, Aadhaar, PAN | Statutory requirement | Citizen/Officer submission |
| Contact | Phone, email, address | Notification obligation | Citizen submission |
| Financial | Bank account, IFSC | Payment processing | Citizen submission |
| Property | Survey number, area, ownership | Case management | Revenue records |
| Location | GPS coordinates, addresses | GIS mapping | Survey / geocoding |
| Biometric | Photograph | Identification | Officer-captured |

### 2.2 Data Processing Activities

| Activity | Purpose | Retention | Volume |
|----------|---------|-----------|--------|
| Case management | Track acquisition proceedings | Case + 15 years | ~10,000 records/year |
| Compensation calculation | Determine fair compensation | 30 years | ~5,000/year |
| Document OCR | Extract data from scanned docs | Case + 7 years | ~50,000 docs/year |
| Notification dispatch | Send statutory notices | 2 years | ~100,000/year |
| ML prediction | Estimate case duration | 5 years | Model only |
| Audit logging | Track officer actions | 2 years | ~1M events/year |

## 3. Risk Assessment

### 3.1 Data Breach Risk

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SQL injection | Low | Critical | ORM-only queries, parameterized |
| Unauthorized access | Medium | High | RBAC, JWT, rate limiting |
| Data leakage via API | Medium | High | Response gating, PII masking |
| Insider threat | Low | Critical | Audit logs, access review |
| Backup exposure | Low | High | Encrypted backups, HSM keys |

### 3.2 Privacy Impact

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Excessive collection | Low | Medium | Data minimization policy |
| Purpose limitation breach | Low | Medium | Access controls per purpose |
| Retention violation | Medium | Medium | Automated disposal scheduler |
| Cross-border transfer | Low | High | No cross-border processing |
| Consent withdrawal | Medium | Medium | DSR endpoint, erasure support |

## 4. Data Protection Measures

### Technical Measures
- Encryption at rest (AES-256) for all PII fields
- TLS 1.2+ for all data in transit
- Field-level access control via data gating middleware
- Aadhaar masking (show last 4 digits only)
- Automated PII detection in logs (redaction)

### Organizational Measures
- Data Protection Officer designated
- Privacy training for all officers with system access
- Data processing register maintained
- Annual privacy audit conducted
- Incident response plan documented

## 5. Data Subject Rights

The platform supports:
- ✅ Right to access (via DSR endpoint)
- ✅ Right to correction (via DSR endpoint)
- ✅ Right to erasure (subject to statutory retention)
- ✅ Right to be informed (privacy notice on portal)
- ✅ Right to grievance redressal (complaint form)

## 6. Recommendation

Based on this assessment, the BHUMISETU platform processes personal data
in a manner consistent with:
- Digital Personal Data Protection Act, 2023
- IT (Reasonable Security Practices) Rules, 2011
- RFCTLARR Act, 2013 (data collection justification)

**Risk Level**: MEDIUM — mitigated by technical and organizational measures.

**Approval Status**: ✅ Approved for continued operation with annual review.
