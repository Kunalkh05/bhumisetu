"""Authentication and persona management endpoints for the BHUMISETU UI/UX."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.security.access import (
    CITIZEN_SESSION_COOKIE,
    OFFICER_SESSION_COOKIE,
    Principal,
    authenticate,
    get_auth_backend,
)
from app.security.auth import CSRF_COOKIE, CSRF_HEADER

auth_router = APIRouter(tags=["auth"])

DEV_OFFICER_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")


class PersonaLoginRequest(BaseModel):
    userId: str
    name: str
    role: str
    jurisdiction: list[str] = ["Pune", "Haveli"]
    isCitizen: bool = False


class PersonaLoginResponse(BaseModel):
    sessionToken: str
    csrfToken: str
    role: str
    isCitizen: bool
    message: str


@auth_router.post("/api/auth/persona", response_model=PersonaLoginResponse)
def login_persona(payload: PersonaLoginRequest, response: Response) -> PersonaLoginResponse:
    backend = get_auth_backend()

    if payload.isCitizen:
        bundle = backend.create_citizen_session(
            subject_id=payload.userId,
            case_id=1,
            owner_record_ids=(1, 2),
        )
        response.set_cookie(
            key=CITIZEN_SESSION_COOKIE,
            value=bundle.session_token,
            httponly=False,
            samesite="lax",
            path="/",
        )
        return PersonaLoginResponse(
            sessionToken=bundle.session_token,
            csrfToken="",
            role="CITIZEN",
            isCitizen=True,
            message=f"Signed in as citizen: {payload.name}",
        )

    # Officer session
    bundle = backend.create_officer_session(DEV_OFFICER_ID)
    response.set_cookie(
        key=OFFICER_SESSION_COOKIE,
        value=bundle.session_token,
        httponly=False,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE,
        value=bundle.csrf_token,
        httponly=False,
        samesite="lax",
        path="/",
    )

    return PersonaLoginResponse(
        sessionToken=bundle.session_token,
        csrfToken=bundle.csrf_token,
        role=payload.role,
        isCitizen=False,
        message=f"Signed in as {payload.role}: {payload.name}",
    )


@auth_router.get("/api/auth/me")
def get_current_user(request: Request) -> dict:
    backend = get_auth_backend()
    bearer = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        bearer = auth_header.split(" ", 1)[1].strip()

    officer_token = request.cookies.get(OFFICER_SESSION_COOKIE) or (bearer if bearer and backend.officer_session(bearer) else None)
    if officer_token:
        officer = backend.officer_session(officer_token)
        if officer:
            return {
                "authenticated": True,
                "kind": "OFFICER",
                "officerId": str(officer.officer_id),
            }

    citizen_token = request.cookies.get(CITIZEN_SESSION_COOKIE) or (bearer if bearer and backend.citizen_session(bearer) else None)
    if citizen_token:
        citizen = backend.citizen_session(citizen_token)
        if citizen:
            return {
                "authenticated": True,
                "kind": "CITIZEN",
                "subjectId": citizen.subject_id,
                "caseId": citizen.case_id,
            }

    return {"authenticated": False, "kind": "ANONYMOUS"}


@auth_router.get("/dev-login")
def dev_login() -> RedirectResponse:
    backend = get_auth_backend()
    bundle = backend.create_officer_session(DEV_OFFICER_ID)
    res = RedirectResponse(url="/officer/", status_code=307)
    res.set_cookie(
        key=OFFICER_SESSION_COOKIE,
        value=bundle.session_token,
        httponly=False,
        samesite="lax",
        path="/",
    )
    res.set_cookie(
        key=CSRF_COOKIE,
        value=bundle.csrf_token,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return res


@auth_router.post("/api/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(OFFICER_SESSION_COOKIE, path="/")
    response.delete_cookie(CITIZEN_SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"message": "Logged out successfully"}
