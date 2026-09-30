# API Design Guidelines — BHUMISETU

## Versioning

All API endpoints are versioned under `/api/v1/`. Version uniformity is
enforced via automated tests (`test_version_uniformity.py`).

## Request/Response Format

### Standard Success Response
```json
{
  "version": "1.0",
  "data": { ... },
  "meta": {
    "timestamp": "2026-09-29T10:00:00Z",
    "request_id": "uuid"
  }
}
```

### Standard Error Response
```json
{
  "version": "1.0",
  "error": {
    "code": "CASE_NOT_FOUND",
    "message": "The requested case does not exist",
    "details": {}
  }
}
```

## Naming Conventions

- **Endpoints**: Use kebab-case for URLs (`/api/v1/case-workspaces/`)
- **Query Parameters**: Use snake_case (`?page_size=20&sort_by=created_at`)
- **Request Bodies**: Use snake_case for JSON field names
- **Response Bodies**: Use snake_case for JSON field names

## Authentication

All officer endpoints require a Bearer token:
```
Authorization: Bearer <jwt_token>
```

Citizen endpoints use a separate authentication flow with Aadhaar-based
KYC verification.

## Pagination

List endpoints support cursor-based pagination:
```
GET /api/v1/cases?cursor=abc123&page_size=20
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "def456",
    "has_more": true,
    "total_count": 150
  }
}
```

## Rate Limiting

Rate limits are enforced per-endpoint and per-user:

| Endpoint Category | Rate Limit |
|-------------------|------------|
| Authentication | 5 req/15min |
| Read operations | 100 req/min |
| Write operations | 20 req/min |
| File uploads | 5 req/min |
| Search | 30 req/min |

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1696000000
```

## Data Gating

Sensitive fields are automatically redacted based on the requesting
user's role and relationship to the data. The gating system is
implemented in `app/security/gate.py` and applied via `GatedRoute`
middleware.

### Gating Levels
- **FULL**: All fields visible (data owner, authorized officer)
- **REDACTED**: Sensitive fields masked (related parties)
- **MINIMAL**: Only public fields visible (general public)

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_REQUIRED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource does not exist |
| `VALIDATION_ERROR` | 422 | Request body validation failed |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `CASE_NOT_FOUND` | 404 | Case ID not found |
| `PARCEL_NOT_FOUND` | 404 | Land parcel not found |
| `DOCUMENT_TOO_LARGE` | 413 | Uploaded document exceeds size limit |
| `STAGE_TRANSITION_INVALID` | 422 | Invalid case stage transition |
