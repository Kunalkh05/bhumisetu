# BUGS FIXED DURING VALIDATION (LOOP 16)

During the autonomous human simulation and cross-role penetration testing of the **BHUMISETU** platform, two high-severity security authorization defects were discovered and remediated in the application backend.

---

## BUG-01: Session Cookie Leakage During Persona Switch

### Severity
**HIGH** (Authentication / Privilege Leakage)

### File Affected
[`bhumi-setu/apps/api/app/api/auth.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/apps/api/app/api/auth.py)

### Root Cause
When switching active personas via the `/api/auth/persona` development endpoint (e.g., from an Officer persona to a Citizen persona), the endpoint set the new `CITIZEN_SESSION_COOKIE` but failed to delete the existing `OFFICER_SESSION_COOKIE` or `CSRF_COOKIE`. Because `authenticate` in `app.security.access` checks for officer credentials first, the browser continued to present the officer session cookie, inadvertently granting the citizen persona full officer privileges.

### Resolution
Updated `login_persona` in `bhumi-setu/apps/api/app/api/auth.py` to explicitly delete opposite session and CSRF cookies whenever a persona login request is processed:
```python
if payload.isCitizen:
    response.delete_cookie(OFFICER_SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    bundle = backend.create_citizen_session(...)
    ...
else:
    response.delete_cookie(CITIZEN_SESSION_COOKIE, path="/")
    bundle = backend.create_officer_session(...)
    ...
```

### Verification & Regression
Tested in `tests_harness/test_citizen_journey.py` and `tests_harness/test_ml_deep_validation.py` (SEC-FIND-01):
- Citizen logging in after officer immediately loses officer privileges.
- Subsequent calls to `/api/officer/dashboard` return HTTP 403 `NOT_AUTHORISED`.

---

## BUG-02: Missing Officer Authorization on Officer Endpoints

### Severity
**CRITICAL** (Broken Access Control / Unauthorized Access)

### Files Affected
- [`bhumi-setu/apps/api/app/api/cases.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/apps/api/app/api/cases.py)
- [`bhumi-setu/apps/api/app/api/dashboard.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/apps/api/app/api/dashboard.py)

### Root Cause
While `GatedRoute` redacts sensitive fields on model serialization based on `Principal.kind`, the router endpoints themselves (`GET /api/officer/dashboard`, `GET /api/officer/cases`, `GET /api/officer/cases/{id}`, `GET /api/officer/cases/{id}/workspace`, `GET /api/officer/cases/{id}/timeline`, `POST /api/officer/cases/{id}/stage`) only declared `principal: Principal = Depends(authenticate)`. 
They did not verify `if principal.kind != "OFFICER": raise NotAuthorised()`. Consequently, a citizen possessing a valid citizen session cookie was able to execute officer business logic and query unredacted lists of cases.

### Resolution
Enforced explicit principal kind validation at the entrance of all officer endpoints in `cases.py` and `dashboard.py`:
```python
@officer_router.get("/dashboard", response_model=DashboardOut)
def dashboard(principal: Principal = Depends(authenticate)) -> DashboardOut:
    if principal.kind != "OFFICER":
        raise NotAuthorised()
    ...

@officer_router.get("/cases", response_model=list[CaseOut])
def list_cases(principal: Principal = Depends(authenticate)) -> list[Any]:
    if principal.kind != "OFFICER":
        raise NotAuthorised()
    ...
```

### Verification & Regression
Tested in `tests_harness/test_citizen_journey.py` and `tests_harness/test_ml_deep_validation.py` (SEC-FIND-02):
- Citizen attempting `GET /api/officer/dashboard` returns HTTP 403 `NOT_AUTHORISED`.
- Citizen attempting `GET /api/officer/cases` returns HTTP 403 `NOT_AUTHORISED`.
- Citizen attempting `GET /api/officer/cases/CASE-001/survival-risk` returns HTTP 403 `NOT_AUTHORISED`.
- Citizen attempting `POST /api/officer/survival-risk/predict` returns HTTP 403 `NOT_AUTHORISED`.

---

## BUG-03: Local Development CORS Origin Port Configuration

### Severity
**LOW** (Local Developer Experience)

### File Affected
[`bhumi-setu/apps/api/app/main.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/apps/api/app/main.py)

### Root Cause
Vite local frontend runs on port 5174 when port 5173 is in use or default configured. The backend CORS middleware allowed `http://localhost:5173` and `http://localhost:3000`, causing CORS preflight failures when the browser app made API requests from port 5174.

### Resolution
Added `http://localhost:5174` and `http://127.0.0.1:5174` to `cors_origins` in `main.py`.

### Verification & Regression
Verified through real browser execution in Chrome CDP tests connecting to `http://localhost:5174/officer/` communicating seamlessly with API at `http://localhost:8000`.
