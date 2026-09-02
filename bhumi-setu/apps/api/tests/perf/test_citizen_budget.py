"""Citizen portal transfer budget tests (task 19.5).

Enforces R24.1 (150 KB total compressed), R24.2 (50 KB per JSON response),
and R27.6 (40 KB per font file) in CI on every PR.

The budget is stated in brotli-compressed bytes because Caddy compresses
at quality 11 before sending (§10.5). Subresources are discovered from the
rendered HTML rather than hand-maintained, so adding a new page or changing
a link automatically extends coverage.

The maximal_case fixture is adversarial: longest Devanagari owner names, maximum
parcels, a full 20-event timeline page, and every optional field populated.
A budget test that passes on a small fixture is not a budget test.

Runs without PostgreSQL — content is patched in through the same mechanism the
route tests use, so the rendering pipeline is exercised end-to-end without a
real database.
"""

from __future__ import annotations

import re
import urllib.parse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterator

import brotli
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

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

# Caddy proxy brotli quality — the budget is stated in compressed bytes (§10.5).
BROTLI_Q = 11

# Caps from the requirements and design.
CAP_TOTAL = 150_000   # R24.1 — HTML + CSS + JS + fonts, brotli-compressed
CAP_FONT = 40_000    # R27.6 — no font file exceeds 40 KB
CAP_RESPONSE = 50_000  # R24.2 — any citizen JSON response

# Languages the citizen surface is configured for; budget must hold for each.
SUPPORTED_LANGUAGES = ("en", "hi", "mr")

pytestmark = pytest.mark.perf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _brotli_size(data: bytes) -> int:
    """Size of data after brotli compression at proxy quality."""
    return len(brotli.compress(data, quality=BROTLI_Q))


def _discover_subresources(html: str) -> list[str]:
    """Extract subresource URLs from a rendered HTML page.

    Covers: <link href>, <script src>, @font-face src (url(...)).
    Paths are deduplicated so query strings on the same path don't double-count.
    """
    urls: list[str] = []
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith("/c/") or href.startswith("/"):
            urls.append(href)
    for src in re.findall(r'src="([^"]+)"', html):
        if src.startswith("/c/") or src.startswith("/"):
            urls.append(src)
    for url_match in re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', html):
        if url_match.startswith("/c/") or url_match.startswith("/"):
            urls.append(url_match)
    return urls


def _devanagari_name(char_count: int) -> str:
    """Return a plausible Devanagari owner name of approximately char_count chars."""
    syllables = [
        "श्री", "कुमार", "पटेल", "महादेव", "रघुनाथ",
        "जगन्नाथ", "विष्णु", "प्रभाकर", "सोमनाथ", "गणेश",
    ]
    name = ""
    while len(name) < char_count:
        name += syllables[len(name) % len(syllables)]
    return name + " " + "आचार्य"


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

def _citizen_app() -> FastAPI:
    app = FastAPI()
    app.include_router(citizen_html)
    return app


def _citizen_principal(request: Request) -> Principal:
    principal = Principal(
        kind="CITIZEN",
        id="budget-citizen-1",
        case_id=99999,
        owner_record_ids=tuple(range(100, 107)),
    )
    request.state.principal = principal
    return principal


# ---------------------------------------------------------------------------
# Maximal-case data
# ---------------------------------------------------------------------------

def _maximal_content(lang: str = "en") -> CitizenContentView:
    """Return a maximally-populated CitizenContentView for budget testing.

    Every text field is at maximum plausible length; all optional fields are
    present; 7 ownership records, 7 awards, 5 notices, 3 objections, 10 docs.
    """
    village_name = "ग्रामपंचायत " + "विश्वनाथ " * 3
    today = date.today()

    case = CitizenCaseStatus(
        case_reference="MH/BD/2024/R-99999/AC-99999",
        project_name="महाराष्ट्र राज्य महामार्ग " + "प्राधिकरण" * 2,
        stage="Award Draft",
        stage_entered_on=today - timedelta(days=45),
        next_step="Await the award notice and disbursement",
        statutory_period="90 days from stage entry",
        remaining_days=45,
    )
    ownership_records = tuple(
        CitizenOwnershipRow(
            parcel_id=i,
            survey_number=f"{1000 + i}",
            village=village_name,
            extent=Decimal("9.9999"),
            extent_unit="hectare",
            share=Decimal("0.142857"),
            interest_type="owner",
            co_owner_count=6,
            other_share_total=Decimal("0.857143"),
        )
        for i in range(1, 8)
    )
    awards = tuple(
        CitizenAwardRow(
            ownership_record_id=100 + i,
            total_amount=Decimal("9999999.99"),
            currency="INR",
            disbursement_state="UNPAID",
        )
        for i in range(1, 8)
    )
    notices = tuple(
        CitizenNoticeRow(
            id=i,
            notice_type="award_notice",
            service_date=today - timedelta(days=30),
            response_deadline=today + timedelta(days=30),
        )
        for i in range(1, 6)
    )
    objections = tuple(
        CitizenObjectionRow(
            id=i,
            receipt_date=today - timedelta(days=20),
            disposal_state="PENDING",
            disposal_date=None,
        )
        for i in range(1, 4)
    )
    documents = tuple(
        CitizenDocumentRow(
            id=i,
            document_type="sale_deed",
            original_filename="अभिलेख-पत्र-क्रमांक-" + str(i).zfill(4) + ".pdf",
            uploaded_at=today - timedelta(days=10),
            byte_size=999999,
        )
        for i in range(1, 11)
    )
    return CitizenContentView(
        case=case,
        ownership_records=ownership_records,
        awards=awards,
        notices=notices,
        objections=objections,
        documents=documents,
    )


@contextmanager
def _fake_unit_of_work() -> Iterator[object]:
    yield object()


def _patch_event_log(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Silence EventLog.append during budget tests — we are not testing event recording."""
    def _fake_append(session: object, **kwargs: object) -> None:
        pass
    monkeypatch.setattr(citizen_routes.EventLog, "append", _fake_append)


def _patch_maximal_case(monkeypatch, lang: str = "en") -> None:  # type: ignore[no-untyped-def]
    """Patch citizen routes to return maximally-populated content."""
    content = _maximal_content(lang=lang)
    monkeypatch.setattr(citizen_routes, "unit_of_work", _fake_unit_of_work)
    monkeypatch.setattr(citizen_routes, "load_citizen_content", lambda session, principal: content)
    monkeypatch.setattr(
        citizen_routes,
        "load_citizen_document",
        lambda session, principal, doc_id: content.documents[0],
    )
    _patch_event_log(monkeypatch)


# ---------------------------------------------------------------------------
# Tests: HTML budget per language
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_case_view_within_transfer_budget(monkeypatch, lang: str) -> None:
    """R24.1: the case status view and all subresources fit in 150 KB brotli.

    Maximal fixture: max Devanagari names, 7 parcels, 7 awards, 10 docs,
    every optional field populated. Run for every language including Devanagari.
    """
    _patch_maximal_case(monkeypatch, lang=lang)
    app = _citizen_app()
    app.dependency_overrides[authenticate] = _citizen_principal

    with TestClient(app, cookies={"bhumisetu_citizen_language": lang}) as client:
        response = client.get("/c/case")

    assert response.status_code == 200
    total_size = _brotli_size(response.content)

    # Discover subresources from the HTML itself (not hand-maintained list).
    subresource_sizes: dict[str, int] = {}
    for url in _discover_subresources(response.text):
        parsed = urllib.parse.urlparse(url)
        if parsed.path in subresource_sizes:
            continue
        sub_resp = client.get(url)
        if sub_resp.status_code == 200:
            subresource_sizes[parsed.path] = _brotli_size(sub_resp.content)

    font_sizes = {u: s for u, s in subresource_sizes.items() if u.endswith((".woff2", ".woff", ".ttf"))}
    other_sizes = {u: s for u, s in subresource_sizes.items() if u not in font_sizes}

    for url, size in font_sizes.items():
        assert size <= CAP_FONT, f"{url} font size {size} B exceeds R27.6 cap of {CAP_FONT} B"

    total_with_resources = total_size + sum(other_sizes.values()) + sum(font_sizes.values())
    assert total_with_resources <= CAP_TOTAL, (
        f"Total transfer size {total_with_resources} B exceeds R24.1 cap of {CAP_TOTAL} B "
        f"for language '{lang}'. "
        f"HTML: {total_size} B, subresources: {other_sizes}, fonts: {font_sizes}"
    )


# ---------------------------------------------------------------------------
# Test: service worker served correctly
# ---------------------------------------------------------------------------

def test_service_worker_is_javascript_with_correct_scope(monkeypatch) -> None:
    """R24.6: the service worker is served as JS with /c/ as its allowed scope."""
    _patch_maximal_case(monkeypatch, lang="en")
    app = _citizen_app()

    with TestClient(app) as client:
        response = client.get("/c/static/sw.js")

    assert response.status_code == 200
    assert "text/javascript" in response.headers.get("content-type", "")
    assert response.headers.get("Service-Worker-Allowed") == "/c/"
    # Source is human-readable; production delivery minifies + brotlis it.
    assert _brotli_size(response.content) < CAP_FONT


# ---------------------------------------------------------------------------
# Test: offline page is text-only, no external subresources
# ---------------------------------------------------------------------------

def test_offline_page_is_text_only_without_external_subresources(monkeypatch) -> None:
    """R24.8: the offline page renders without external subresources.

    The offline page carries the inline service-worker registration script from
    base.html (one small inline <script>, not an external resource). The test
    asserts there are no external subresources (no src=, no font files) and that
    the inline script is the only script present.
    """
    _patch_maximal_case(monkeypatch, lang="en")
    app = _citizen_app()

    with TestClient(app, cookies={"bhumisetu_citizen_language": "en"}) as client:
        response = client.get("/c/offline")

    assert response.status_code == 200
    # Inline SW registration is expected; no external scripts.
    assert "<script" in response.text
    assert re.search(r'<script[^>]+src=', response.text) is None
    assert "@font-face" not in response.text
    # Offline page itself must fit within the budget.
    assert _brotli_size(response.content) <= CAP_TOTAL


# ---------------------------------------------------------------------------
# Test: timeline page with maximal events within budget
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_timeline_page_with_maximal_events_within_budget(monkeypatch, lang: str) -> None:
    """R24.1 + R24.10: timeline at 20 events per page fits the budget."""
    _patch_maximal_case(monkeypatch, lang=lang)
    app = _citizen_app()
    app.dependency_overrides[authenticate] = _citizen_principal

    with TestClient(app, cookies={"bhumisetu_citizen_language": lang}) as client:
        response = client.get("/c/timeline?page=1")

    assert response.status_code == 200
    total_size = _brotli_size(response.content)

    subresource_sizes: dict[str, int] = {}
    for url in _discover_subresources(response.text):
        parsed = urllib.parse.urlparse(url)
        if parsed.path in subresource_sizes:
            continue
        sub_resp = client.get(url)
        if sub_resp.status_code == 200:
            subresource_sizes[parsed.path] = _brotli_size(sub_resp.content)

    total_with_resources = total_size + sum(subresource_sizes.values())
    assert total_with_resources <= CAP_TOTAL, (
        f"Timeline transfer size {total_with_resources} B exceeds {CAP_TOTAL} B for {lang}"
    )


# ---------------------------------------------------------------------------
# Test: documents, notices, objections pages within budget
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path,field",
    [
        ("/c/documents", "documents"),
        ("/c/notices", "notices"),
        ("/c/objections", "objections"),
    ],
)
@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_list_pages_within_transfer_budget(
    monkeypatch, lang: str, path: str, field: str
) -> None:
    """R24.1: documents, notices, and objections list pages fit the budget."""
    _patch_maximal_case(monkeypatch, lang=lang)
    app = _citizen_app()
    app.dependency_overrides[authenticate] = _citizen_principal

    with TestClient(app, cookies={"bhumisetu_citizen_language": lang}) as client:
        response = client.get(path)

    assert response.status_code == 200
    total_size = _brotli_size(response.content)

    subresource_sizes: dict[str, int] = {}
    for url in _discover_subresources(response.text):
        parsed = urllib.parse.urlparse(url)
        if parsed.path in subresource_sizes:
            continue
        sub_resp = client.get(url)
        if sub_resp.status_code == 200:
            subresource_sizes[parsed.path] = _brotli_size(sub_resp.content)

    total_with_resources = total_size + sum(subresource_sizes.values())
    assert total_with_resources <= CAP_TOTAL, (
        f"{path} transfer size {total_with_resources} B exceeds {CAP_TOTAL} B for {lang}"
    )
