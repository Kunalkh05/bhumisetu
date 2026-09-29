# Security Audit Checklist — BHUMISETU Platform

## Document Control
- **Version**: 1.0
- **Last Updated**: 2026-09-29
- **Audit Period**: Quarterly
- **Classification**: Confidential

## 1. Authentication & Authorization

- [ ] JWT tokens expire within configured TTL (default: 30 minutes)
- [ ] Refresh token rotation is enabled
- [ ] Password hashing uses bcrypt with cost factor ≥ 12
- [ ] Failed login attempts are rate-limited (max 5 per 15 minutes)
- [ ] Sign-in responses are indistinguishable for valid/invalid users
- [ ] RBAC matrix is enforced on all officer endpoints
- [ ] Citizen endpoints validate ownership before returning case data
- [ ] API key rotation schedule is documented and followed

## 2. Data Protection

- [ ] All PII fields are encrypted at rest (AES-256)
- [ ] Database connections use TLS 1.2+
- [ ] Aadhaar numbers are masked in API responses (show last 4 digits only)
- [ ] Data Subject Request (DSR) endpoint is functional
- [ ] Audit logs capture all data access events
- [ ] Backup encryption keys are stored in hardware security module (HSM)
- [ ] Cross-tenant data isolation is verified

## 3. Network Security

- [ ] HTTPS is enforced on all endpoints (HSTS enabled)
- [ ] CORS policy restricts origins to approved domains
- [ ] API rate limiting is active (configurable per endpoint)
- [ ] WebSocket connections require authentication
- [ ] Internal services communicate over private network only
- [ ] Database ports are not exposed to public internet
- [ ] Redis requires authentication

## 4. Application Security

- [ ] SQL injection prevention via parameterized queries (SQLAlchemy ORM)
- [ ] XSS prevention via output encoding in templates
- [ ] CSRF tokens are validated on state-changing operations
- [ ] File upload validation (type, size, content scanning)
- [ ] Dependency vulnerability scan (pip-audit, npm audit) clean
- [ ] No hardcoded secrets in source code (git-secrets scan)
- [ ] Error messages do not leak internal implementation details

## 5. Infrastructure Security

- [ ] Docker images use non-root user
- [ ] Container resource limits are configured
- [ ] Secrets are injected via environment variables (not config files)
- [ ] Log files do not contain PII or credentials
- [ ] Monitoring alerts are configured for anomalous patterns
- [ ] Disaster recovery plan is tested within last 90 days

## 6. Compliance

- [ ] Privacy impact assessment (PIA) is current
- [ ] Data processing register is maintained
- [ ] Third-party processor agreements are in place
- [ ] Data breach notification procedure is documented
- [ ] Right to Information (RTI) response workflow is tested
- [ ] Consent management records are auditable

## 7. ML / AI Security

- [ ] Model training data does not contain test/production PII
- [ ] Prediction explanations are logged for audit trail
- [ ] Model bias testing results are documented
- [ ] Feature inputs are validated and sanitized
- [ ] Model versioning tracks all deployed models

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Security Lead | | | |
| Data Protection Officer | | | |
| Engineering Lead | | | |
| Project Manager | | | |
