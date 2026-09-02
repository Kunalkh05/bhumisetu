"""Server-rendered citizen routes (task 19.1)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from starlette.templating import _TemplateResponse

from app.api.routers import citizen_html
from app.citizen.content import load_citizen_content, load_citizen_document
from app.citizen.templating import render_gated
from app.db.event_log import EventLog
from app.db.session import get_engine
from app.db.session import unit_of_work
from app.security.access import Principal, authenticate
from app.services.document import PRESIGN_TTL_SECONDS, DocumentService, build_minio_store
from app.settings import get_object_storage_settings

__all__ = []

TIMELINE_PAGE_SIZE = 20
SUPPORTED_LANGUAGES = ("en", "hi", "mr")


class _CitizenCaseEntity:
    __tablename__ = "acquisition_case"

    def __init__(self, case_id: int) -> None:
        self.id = case_id


@contextmanager
def _read_session() -> Iterator[Session]:
    session = Session(bind=get_engine())
    try:
        yield session
    finally:
        session.close()


def _redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def _record_retrieval(
    session: Session,
    principal: Principal,
    *,
    surface: str,
    document_id: int | None = None,
) -> None:
    if principal.case_id is None:
        return
    EventLog.append(
        session,
        event_type="CITIZEN_DATA_RETRIEVED",
        entity=_CitizenCaseEntity(principal.case_id),
        actor=principal,
        changes={
            "surface": (None, surface),
            "session_id": (None, principal.id),
            "case_id": (None, principal.case_id),
            "document_id": (None, document_id),
        },
        occurrence_time=datetime.now(timezone.utc),
    )


async def _form_value(request: Request, key: str, default: str = "") -> str:
    form = await request.form()
    value = form.get(key, default)
    return str(value)


@citizen_html.get("/")
def citizen_home(request: Request) -> _TemplateResponse:
    return render_gated(
        request,
        "home.html",
        None,
        None,
        title="Citizen access",
        languages=SUPPORTED_LANGUAGES,
        selected_language=request.cookies.get("bhumisetu_citizen_language", "en"),
    )


@citizen_html.post("/request-code")
async def request_code(request: Request) -> RedirectResponse:
    await _form_value(request, "case_reference")
    await _form_value(request, "mobile")
    return _redirect("/c/?requested=1")


@citizen_html.post("/verify")
async def verify_code(request: Request) -> RedirectResponse:
    await _form_value(request, "case_reference")
    await _form_value(request, "passcode")
    return _redirect("/c/case")


@citizen_html.get("/case")
def citizen_case(
    request: Request,
    principal: Principal = Depends(authenticate),
) -> _TemplateResponse:
    with unit_of_work() as session:
        content = load_citizen_content(session, principal)
        _record_retrieval(session, principal, surface="case")
    return render_gated(
        request,
        "case.html",
        None,
        principal,
        title="Case status",
        case=content.case,
        ownership_records=content.ownership_records,
        awards=content.awards,
        languages=SUPPORTED_LANGUAGES,
        selected_language=request.cookies.get("bhumisetu_citizen_language", "en"),
    )


@citizen_html.get("/timeline")
def citizen_timeline(
    request: Request,
    page: int = 1,
    principal: Principal = Depends(authenticate),
) -> _TemplateResponse:
    page = max(1, page)
    with unit_of_work() as session:
        content = load_citizen_content(session, principal)
        _record_retrieval(session, principal, surface="timeline")
    return render_gated(
        request,
        "timeline.html",
        None,
        principal,
        title="Timeline",
        case=content.case,
        page=page,
        page_size=TIMELINE_PAGE_SIZE,
        previous_page=page - 1 if page > 1 else None,
        next_page=page + 1,
        languages=SUPPORTED_LANGUAGES,
        selected_language=request.cookies.get("bhumisetu_citizen_language", "en"),
    )


@citizen_html.get("/documents")
def citizen_documents(
    request: Request,
    principal: Principal = Depends(authenticate),
) -> _TemplateResponse:
    with unit_of_work() as session:
        content = load_citizen_content(session, principal)
        _record_retrieval(session, principal, surface="documents")
    return render_gated(
        request,
        "documents.html",
        None,
        principal,
        title="Documents",
        documents=content.documents,
        languages=SUPPORTED_LANGUAGES,
        selected_language=request.cookies.get("bhumisetu_citizen_language", "en"),
    )


@citizen_html.get("/documents/{document_id}/confirm")
def citizen_document_confirm(
    request: Request,
    document_id: int,
    principal: Principal = Depends(authenticate),
) -> _TemplateResponse:
    with unit_of_work() as session:
        document = load_citizen_document(session, principal, document_id)
        _record_retrieval(session, principal, surface="document_confirm", document_id=document_id)
    return render_gated(
        request,
        "document_confirm.html",
        None,
        principal,
        title="Confirm document",
        document=document,
        languages=SUPPORTED_LANGUAGES,
        selected_language=request.cookies.get("bhumisetu_citizen_language", "en"),
    )


@citizen_html.get("/documents/{document_id}")
def citizen_document(
    document_id: int,
    principal: Principal = Depends(authenticate),
) -> RedirectResponse:
    with unit_of_work() as session:
        load_citizen_document(session, principal, document_id)
        grant = DocumentService(
            store=build_minio_store(get_object_storage_settings())
        ).grant(
            session,
            document_id=document_id,
            actor=principal,
            expires_in=PRESIGN_TTL_SECONDS,
        )
        _record_retrieval(session, principal, surface="document", document_id=document_id)
    return _redirect(grant.url)


@citizen_html.get("/notices")
def citizen_notices(
    request: Request,
    principal: Principal = Depends(authenticate),
) -> _TemplateResponse:
    with unit_of_work() as session:
        content = load_citizen_content(session, principal)
        _record_retrieval(session, principal, surface="notices")
    return render_gated(
        request,
        "notices.html",
        None,
        principal,
        title="Notices",
        notices=content.notices,
        languages=SUPPORTED_LANGUAGES,
        selected_language=request.cookies.get("bhumisetu_citizen_language", "en"),
    )


@citizen_html.get("/objections")
def citizen_objections(
    request: Request,
    principal: Principal = Depends(authenticate),
) -> _TemplateResponse:
    with unit_of_work() as session:
        content = load_citizen_content(session, principal)
        _record_retrieval(session, principal, surface="objections")
    return render_gated(
        request,
        "objections.html",
        None,
        principal,
        title="Objections",
        objections=content.objections,
        languages=SUPPORTED_LANGUAGES,
        selected_language=request.cookies.get("bhumisetu_citizen_language", "en"),
    )


@citizen_html.post("/language")
async def citizen_language(request: Request) -> RedirectResponse:
    language = await _form_value(request, "language", "en")
    response = _redirect(request.headers.get("referer", "/c/"))
    response.set_cookie(
        "bhumisetu_citizen_language",
        language if language in SUPPORTED_LANGUAGES else "en",
        httponly=True,
        samesite="strict",
        secure=True,
    )
    return response
