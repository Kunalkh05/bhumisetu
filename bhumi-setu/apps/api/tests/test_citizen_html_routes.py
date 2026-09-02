"""Citizen HTML route and template tests (task 19.1)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.gated_route import GatedRoute
from app.api.routers import citizen_html
from app.citizen import routes as citizen_routes
from app.citizen.content import (
    CitizenAwardRow,
    CitizenCaseStatus,
    CitizenContentView,
    CitizenDocumentRow,
    CitizenNoticeRow,
    CitizenObjectionRow,
    CitizenOwnershipRow,
)
from app.security.access import Principal, authenticate


EXPECTED_ROUTES = {
    ("GET", "/c/"),
    ("POST", "/c/request-code"),
    ("POST", "/c/verify"),
    ("GET", "/c/case"),
    ("GET", "/c/timeline"),
    ("GET", "/c/documents"),
    ("GET", "/c/documents/{document_id}/confirm"),
    ("GET", "/c/documents/{document_id}"),
    ("GET", "/c/notices"),
    ("GET", "/c/objections"),
    ("POST", "/c/language"),
}


def test_required_citizen_html_routes_are_registered_on_gated_router() -> None:
    routes = {
        (method, route.path)
        for route in citizen_html.routes
        if isinstance(route, APIRoute)
        for method in (route.methods or ())
        if method not in {"HEAD", "OPTIONS"}
    }

    assert EXPECTED_ROUTES.issubset(routes)
    for route in citizen_html.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/c/"):
            assert isinstance(route, GatedRoute)


def test_home_page_is_text_first_without_image_font_or_script_subresources() -> None:
    app = FastAPI()
    app.include_router(citizen_html)

    with TestClient(app) as client:
        response = client.get("/c/")

    assert response.status_code == 200
    body = response.text
    assert "Request access" in body
    assert "<img" not in body
    assert "<script" not in body
    assert "@font-face" not in body
    assert "system-ui" in body


def test_timeline_pagination_uses_plain_links(monkeypatch) -> None:
    monkeypatch.setattr(citizen_routes, "load_citizen_content", lambda session, principal: _content())
    app = _citizen_app()
    with TestClient(app) as client:
        response = client.get("/c/timeline?page=2")

    assert response.status_code == 200
    assert 'href="/c/timeline?page=1"' in response.text
    assert 'href="/c/timeline?page=3"' in response.text
    assert "Showing up to 20 events per page." in response.text


def test_case_page_renders_citizen_status_ownership_and_awards(monkeypatch) -> None:
    monkeypatch.setattr(citizen_routes, "load_citizen_content", lambda session, principal: _content())
    app = _citizen_app()

    with TestClient(app) as client:
        response = client.get("/c/case")

    assert response.status_code == 200
    body = response.text
    assert "BS-2026-001" in body
    assert "Canal widening" in body
    assert "Award Draft" in body
    assert "Wadgaon / 42" in body
    assert "1.2500 hectare" in body
    assert "125000.00 INR" in body
    assert "Other Owner" not in body


def test_citizen_documents_notices_and_objections_render_owned_rows(monkeypatch) -> None:
    monkeypatch.setattr(citizen_routes, "load_citizen_content", lambda session, principal: _content())
    app = _citizen_app()

    with TestClient(app) as client:
        documents = client.get("/c/documents")
        notices = client.get("/c/notices")
        objections = client.get("/c/objections")

    assert "sale_deed" in documents.text
    assert 'href="/c/documents/44/confirm"' in documents.text
    assert "award_notice" in notices.text
    assert "Respond by 2026-04-01" in notices.text
    assert "PENDING" in objections.text


def _citizen_app() -> FastAPI:
    app = FastAPI()
    app.include_router(citizen_html)

    def _principal(request: Request) -> Principal:
        principal = Principal(
            kind="CITIZEN",
            id="citizen-1",
            case_id=9,
            owner_record_ids=(101,),
        )
        request.state.principal = principal
        return principal

    app.dependency_overrides[authenticate] = _principal
    return app


def _content() -> CitizenContentView:
    return CitizenContentView(
        case=CitizenCaseStatus(
            case_reference="BS-2026-001",
            project_name="Canal widening",
            stage="Award Draft",
            stage_entered_on=date(2026, 1, 1),
            next_step="Await the award notice",
            statutory_period="90 days from stage entry",
            remaining_days=12,
        ),
        ownership_records=(
            CitizenOwnershipRow(
                parcel_id=5,
                survey_number="42",
                village="Wadgaon",
                extent=Decimal("1.2500"),
                extent_unit="hectare",
                share=Decimal("0.500000"),
                interest_type="owner",
            ),
        ),
        awards=(
            CitizenAwardRow(
                ownership_record_id=101,
                total_amount=Decimal("125000.00"),
                currency="INR",
                disbursement_state="UNPAID",
            ),
        ),
        notices=(
            CitizenNoticeRow(
                id=8,
                notice_type="award_notice",
                service_date=date(2026, 3, 1),
                response_deadline=date(2026, 4, 1),
            ),
        ),
        objections=(
            CitizenObjectionRow(
                id=12,
                receipt_date=date(2026, 3, 8),
                disposal_state="PENDING",
                disposal_date=None,
            ),
        ),
        documents=(
            CitizenDocumentRow(
                id=44,
                document_type="sale_deed",
                uploaded_at=date(2026, 2, 1),
                byte_size=4096,
            ),
        ),
    )
