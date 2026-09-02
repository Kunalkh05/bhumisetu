"""Citizen HTML route and template tests (task 19.1)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.gated_route import GatedRoute
from app.api.routers import citizen_html
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


def test_timeline_pagination_uses_plain_links() -> None:
    app = FastAPI()
    app.include_router(citizen_html)

    def _principal(request: Request) -> Principal:
        principal = Principal(kind="CITIZEN", id="citizen-1", case_id=9)
        request.state.principal = principal
        return principal

    app.dependency_overrides[authenticate] = _principal
    with TestClient(app) as client:
        response = client.get("/c/timeline?page=2")

    assert response.status_code == 200
    assert 'href="/c/timeline?page=1"' in response.text
    assert 'href="/c/timeline?page=3"' in response.text
    assert "Showing up to 20 events per page." in response.text
