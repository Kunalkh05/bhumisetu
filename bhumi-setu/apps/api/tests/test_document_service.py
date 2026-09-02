"""Document storage and grant tests (task 15)."""

from __future__ import annotations

import hashlib
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest
from fastapi.routing import APIRoute
from hypothesis import given
from hypothesis import strategies as st

from app.api.routers import officer_router
from app.errors import ErrorCode
from app.models.document import Document
from app.services import document as document_service
from app.services.document import (
    ACCEPTED_CONTENT_TYPES,
    DOCUMENT_QUEUED,
    MAX_UPLOAD_BYTES,
    PRESIGN_TTL_SECONDS,
    DocumentService,
    DuplicateDocument,
    UploadRejected,
    admit_upload,
    build_minio_store,
)
from app.settings import get_object_storage_settings


@dataclass(frozen=True)
class Actor:
    kind: str = "OFFICER"
    id: str = "00000000-0000-0000-0000-000000000001"


class FakeScalar:
    def __init__(self, value) -> None:  # type: ignore[no-untyped-def]
        self.value = value

    def scalar_one_or_none(self):  # type: ignore[no-untyped-def]
        return self.value


class FakeSession:
    def __init__(self, *, duplicate_id: int | None = None, document: Document | None = None) -> None:
        self.duplicate_id = duplicate_id
        self.document = document
        self.added: list[object] = []
        self.flushed = False

    def execute(self, stmt):  # type: ignore[no-untyped-def]
        return FakeScalar(self.duplicate_id)

    def add(self, value: object) -> None:
        if isinstance(value, Document) and value.id is None:
            value.id = 55
            value.entity_version = 1
        self.added.append(value)

    def flush(self) -> None:
        self.flushed = True

    def get(self, entity_type, entity_id, **kwargs):  # type: ignore[no-untyped-def]
        if entity_type is Document and self.document is not None:
            return self.document
        return None


class MemoryStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.presigned: list[tuple[str, int]] = []

    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        self.objects[key] = bytes(body)

    def get_object(self, *, key: str) -> bytes:
        return self.objects[key]

    def presigned_get(self, *, key: str, expires_in: int) -> str:
        self.presigned.append((key, expires_in))
        return f"https://storage.local/{key}?exp={expires_in}"


@given(
    content_type=st.sampled_from(sorted(ACCEPTED_CONTENT_TYPES) + ["text/plain"]),
    byte_size=st.integers(min_value=0, max_value=MAX_UPLOAD_BYTES + 2),
)
def test_property_upload_admission_matches_type_and_size(content_type: str, byte_size: int) -> None:
    accepted = content_type in ACCEPTED_CONTENT_TYPES and byte_size <= MAX_UPLOAD_BYTES

    if accepted:
        admit_upload(content_type=content_type, byte_size=byte_size)
    else:
        with pytest.raises(UploadRejected) as exc:
            admit_upload(content_type=content_type, byte_size=byte_size)
        if content_type not in ACCEPTED_CONTENT_TYPES:
            assert exc.value.details["accepted_content_types"] == sorted(ACCEPTED_CONTENT_TYPES)
        else:
            assert exc.value.details["max_bytes"] == MAX_UPLOAD_BYTES


def test_store_writes_object_document_event_and_ocr_outbox(monkeypatch) -> None:
    session = FakeSession()
    store = MemoryStore()
    events: list[str] = []
    outbox: list[dict] = []

    def _append(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        events.append(kwargs["event_type"])

    def _enqueue(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        outbox.append(kwargs)
        return 1

    monkeypatch.setattr(document_service.EventLog, "append", _append)
    monkeypatch.setattr(document_service, "enqueue", _enqueue)

    body = b"immutable bytes"
    result = DocumentService(store=store).store(
        session,  # type: ignore[arg-type]
        case_id=9,
        parcel_id=None,
        document_type="award",
        original_filename="award.pdf",
        content_type="application/pdf",
        body=body,
        actor=Actor(),
        occurrence_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
    )

    assert result.document.processing_state == DOCUMENT_QUEUED
    assert result.checksum_sha256 == hashlib.sha256(body).digest()
    assert store.get_object(key=result.document.object_key) == body
    assert events == ["DOCUMENT_UPLOADED"]
    assert outbox[0]["queue"] == "ocr"
    assert outbox[0]["kwargs"] == {"document_id": 55}


@given(body=st.binary(min_size=0, max_size=4096))
def test_property_stored_object_checksum_survives_extraction_state_changes(
    monkeypatch,
    body: bytes,
) -> None:
    session = FakeSession()
    store = MemoryStore()

    monkeypatch.setattr(document_service.EventLog, "append", lambda *args, **kwargs: None)
    monkeypatch.setattr(document_service, "enqueue", lambda *args, **kwargs: 1)

    service = DocumentService(store=store)
    result = service.store(
        session,  # type: ignore[arg-type]
        case_id=9,
        parcel_id=None,
        document_type="notice",
        original_filename="notice.pdf",
        content_type="application/pdf",
        body=body,
        actor=Actor(),
    )
    document = result.document
    before = service.stored_checksum(document)

    document.processing_state = "EXTRACTED"
    document.detected_script = "dev"
    document.failure_reason = None
    after = service.stored_checksum(document)

    assert before == result.checksum_sha256 == hashlib.sha256(body).digest()
    assert after == before
    assert store.get_object(key=document.object_key) == body


def test_duplicate_document_rejected_before_object_write() -> None:
    store = MemoryStore()

    with pytest.raises(DuplicateDocument) as exc:
        DocumentService(store=store).store(
            FakeSession(duplicate_id=42),  # type: ignore[arg-type]
            case_id=9,
            parcel_id=None,
            document_type="award",
            original_filename="award.pdf",
            content_type="application/pdf",
            body=b"same",
            actor=Actor(),
        )

    assert exc.value.code == ErrorCode.DUPLICATE_DOCUMENT
    assert exc.value.details["existing_id"] == 42
    assert store.objects == {}


def test_grant_caps_ttl_and_records_event(monkeypatch) -> None:
    store = MemoryStore()
    document = Document(
        id=5,
        case_id=9,
        parcel_id=None,
        document_type="award",
        original_filename="award.pdf",
        byte_size=4,
        content_type="application/pdf",
        checksum_sha256=b"abcd",
        object_key="cases/9/abcd",
        uploaded_by=uuid.UUID(Actor().id),
        uploaded_at=datetime(2024, 5, 1, tzinfo=timezone.utc),
        processing_state=DOCUMENT_QUEUED,
        entity_version=1,
    )
    events: list[str] = []

    def _append(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        events.append(kwargs["event_type"])

    monkeypatch.setattr(document_service.EventLog, "append", _append)

    grant = DocumentService(store=store).grant(
        FakeSession(document=document),  # type: ignore[arg-type]
        document_id=5,
        actor=Actor(),
        expires_in=PRESIGN_TTL_SECONDS + 100,
        occurrence_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
    )

    assert grant.expires_in == PRESIGN_TTL_SECONDS
    assert store.presigned == [("cases/9/abcd", PRESIGN_TTL_SECONDS)]
    assert events == ["DOCUMENT_GRANT_ISSUED"]


def test_officer_router_exposes_processing_documents_before_id_route() -> None:
    document_routes = [
        route.path
        for route in officer_router.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/officer/documents")
    ]

    assert "/api/officer/documents/processing" in document_routes
    assert document_routes.index("/api/officer/documents/processing") < document_routes.index(
        "/api/officer/documents/{document_id}/grant"
    )


def test_integration_minio_presigned_url_expires(clean_settings_cache) -> None:
    pytest.importorskip("minio")
    _skip_without_minio()

    settings = get_object_storage_settings()
    store = build_minio_store(settings)
    key = "tests/presign-expiry-check"
    body = b"expiry check"
    store.put_object(key=key, body=body, content_type="application/octet-stream")

    url = store.presigned_get(key=key, expires_in=1)
    with urlopen(url, timeout=2) as response:
        assert response.read() == body

    _wait_until_expired()
    with pytest.raises((HTTPError, URLError)):
        urlopen(url, timeout=2)


def _skip_without_minio() -> None:
    settings = get_object_storage_settings()
    host, port = _host_port(settings.endpoint)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        if sock.connect_ex((host, port)) != 0:
            pytest.skip("MinIO is not reachable on OBJECT_STORAGE_ENDPOINT")


def _host_port(endpoint: str) -> tuple[str, int]:
    host_port = endpoint.removeprefix("http://").removeprefix("https://").split("/", 1)[0]
    host, _, port_text = host_port.partition(":")
    return host, int(port_text or 443 if endpoint.startswith("https://") else port_text or 80)


def _wait_until_expired() -> None:
    import time

    time.sleep(2)
