"""Citizen HTML route and template tests (task 19.1)."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterator

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
from app.schemas.citizen import CitizenParcelOut
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
    _patch_citizen_data(monkeypatch)
    app = _citizen_app()
    with TestClient(app) as client:
        response = client.get("/c/timeline?page=2")

    assert response.status_code == 200
    assert 'href="/c/timeline?page=1"' in response.text
    assert 'href="/c/timeline?page=3"' in response.text
    assert "Showing up to 20 events per page." in response.text


def test_case_page_renders_citizen_status_ownership_and_awards(monkeypatch) -> None:
    _patch_citizen_data(monkeypatch)
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
    assert "Co-owners" in body
    assert "2 · other share 0.500000" in body
    assert "125000.00 INR" in body
    assert "Other Owner" not in body


def test_citizen_documents_notices_and_objections_render_owned_rows(monkeypatch) -> None:
    _patch_citizen_data(monkeypatch)
    app = _citizen_app()

    with TestClient(app) as client:
        documents = client.get("/c/documents")
        notices = client.get("/c/notices")
        objections = client.get("/c/objections")

    assert "sale-deed.pdf" in documents.text
    assert "4096 bytes" in documents.text
    assert 'href="/c/documents/44/confirm"' in documents.text
    assert "award_notice" in notices.text
    assert "Respond by 2026-04-01" in notices.text
    assert "PENDING" in objections.text


def test_citizen_parcel_shape_contains_aggregates_not_other_owner_rows() -> None:
    fields = set(CitizenParcelOut.model_fields)

    assert {"co_owner_count", "other_share_total"}.issubset(fields)
    assert "owners" not in fields
    assert "other_owners" not in fields
    assert "owner_name" not in fields


def test_document_confirm_presents_recorded_size_before_grant(monkeypatch) -> None:
    events = _patch_citizen_data(monkeypatch)
    app = _citizen_app()

    with TestClient(app) as client:
        response = client.get("/c/documents/44/confirm")

    assert response.status_code == 200
    assert "sale-deed.pdf" in response.text
    assert "4096 bytes" in response.text
    assert events[-1]["surface"] == "document_confirm"
    assert events[-1]["document_id"] == 44


def test_document_open_issues_grant_only_after_confirmation_click(monkeypatch) -> None:
    events = _patch_citizen_data(monkeypatch)
    grants: list[int] = []

    class FakeDocumentService:
        def __init__(self, *, store: object) -> None:
            self.store = store

        def grant(self, session: object, *, document_id: int, **kwargs: object) -> FakeGrant:
            grants.append(document_id)
            return FakeGrant(url="https://storage.example/granted", expires_in=900)

    monkeypatch.setattr(citizen_routes, "DocumentService", FakeDocumentService)
    monkeypatch.setattr(citizen_routes, "build_minio_store", lambda settings: object())
    monkeypatch.setattr(citizen_routes, "get_object_storage_settings", lambda: object())
    app = _citizen_app()

    with TestClient(app) as client:
        confirm = client.get("/c/documents/44/confirm")
        opened = client.get("/c/documents/44", follow_redirects=False)

    assert grants == [44]
    assert confirm.status_code == 200
    assert opened.status_code == 303
    assert opened.headers["location"] == "https://storage.example/granted"
    assert events[-1]["surface"] == "document"
    assert events[-1]["document_id"] == 44


def test_citizen_data_retrieval_records_session_case_and_time(monkeypatch) -> None:
    events = _patch_citizen_data(monkeypatch)
    app = _citizen_app()

    with TestClient(app) as client:
        response = client.get("/c/case")

    assert response.status_code == 200
    assert events[-1]["event_type"] == "CITIZEN_DATA_RETRIEVED"
    assert events[-1]["actor_id"] == "citizen-1"
    assert events[-1]["case_id"] == 9
    assert events[-1]["surface"] == "case"


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
                co_owner_count=2,
                other_share_total=Decimal("0.500000"),
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
                original_filename="sale-deed.pdf",
                uploaded_at=date(2026, 2, 1),
                byte_size=4096,
            ),
        ),
    )


@dataclass(frozen=True)
class FakeGrant:
    url: str
    expires_in: int


def _patch_citizen_data(monkeypatch) -> list[dict[str, object]]:  # type: ignore[no-untyped-def]
    events: list[dict[str, object]] = []

    @contextmanager
    def _fake_unit_of_work() -> Iterator[object]:
        yield object()

    def _append(session: object, **kwargs: object) -> None:
        changes = kwargs["changes"]
        assert isinstance(changes, dict)
        events.append(
            {
                "event_type": kwargs["event_type"],
                "actor_id": getattr(kwargs["actor"], "id"),
                "surface": changes["surface"][1],
                "case_id": changes["case_id"][1],
                "document_id": changes["document_id"][1],
                "occurrence_time": kwargs["occurrence_time"],
            }
        )

    monkeypatch.setattr(citizen_routes, "unit_of_work", _fake_unit_of_work)
    monkeypatch.setattr(citizen_routes, "load_citizen_content", lambda session, principal: _content())
    monkeypatch.setattr(
        citizen_routes,
        "load_citizen_document",
        lambda session, principal, document_id: _content().documents[0],
    )
    monkeypatch.setattr(citizen_routes.EventLog, "append", _append)
    return events
