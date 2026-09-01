"""Document admission, storage, and short-lived grants (task 15)."""

from __future__ import annotations

import hashlib
from io import BytesIO
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.db.outbox import enqueue
from app.errors import DomainError, ErrorCode
from app.models.document import Document
from app.settings import ObjectStorageSettings

__all__ = [
    "ACCEPTED_CONTENT_TYPES",
    "DOCUMENT_QUEUED",
    "EXTRACT_DOCUMENT_TASK",
    "MAX_UPLOAD_BYTES",
    "PRESIGN_TTL_SECONDS",
    "DocumentGrant",
    "DocumentService",
    "DocumentStore",
    "DuplicateDocument",
    "StoredDocument",
    "UploadRejected",
    "admit_upload",
    "build_minio_store",
]

ACCEPTED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
    }
)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
PRESIGN_TTL_SECONDS = 900
DOCUMENT_QUEUED = "QUEUED"
EXTRACT_DOCUMENT_TASK = "app.services.ocr.extract_document"

assert PRESIGN_TTL_SECONDS <= 900


class DocumentStore(Protocol):
    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        ...

    def get_object(self, *, key: str) -> bytes:
        ...

    def presigned_get(self, *, key: str, expires_in: int) -> str:
        ...


class MinioDocumentStore:
    def __init__(self, settings: ObjectStorageSettings) -> None:
        try:
            from minio import Minio
        except ImportError as exc:  # pragma: no cover - exercised only in deployed env
            raise RuntimeError("minio package is required for object storage") from exc
        endpoint = settings.endpoint.removeprefix("http://").removeprefix("https://")
        secure = settings.endpoint.startswith("https://")
        self._bucket = settings.bucket
        self._client = Minio(
            endpoint,
            access_key=settings.access_key,
            secret_key=settings.secret_key.get_secret_value(),
            secure=secure,
        )

    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        self._client.put_object(
            self._bucket,
            key,
            BytesIO(body),
            length=len(body),
            content_type=content_type,
        )

    def get_object(self, *, key: str) -> bytes:
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def presigned_get(self, *, key: str, expires_in: int) -> str:
        from datetime import timedelta

        return self._client.presigned_get_object(
            self._bucket,
            key,
            expires=timedelta(seconds=expires_in),
        )


def build_minio_store(settings: ObjectStorageSettings) -> DocumentStore:
    return MinioDocumentStore(settings)


@dataclass(frozen=True)
class StoredDocument:
    document: Document
    checksum_sha256: bytes


@dataclass(frozen=True)
class DocumentGrant:
    document_id: int
    url: str
    expires_in: int


class UploadRejected(DomainError):
    code = ErrorCode.VALIDATION_FAILED
    status_code = 422


class DuplicateDocument(DomainError):
    code = ErrorCode.DUPLICATE_DOCUMENT
    status_code = 409

    def __init__(self, *, existing_id: int, checksum_sha256: bytes) -> None:
        super().__init__(
            "Document already exists for this case",
            details={
                "existing_id": existing_id,
                "checksum_sha256": checksum_sha256.hex(),
            },
        )


def admit_upload(*, content_type: str, byte_size: int) -> None:
    if content_type not in ACCEPTED_CONTENT_TYPES:
        raise UploadRejected(
            "Unsupported document content type",
            details={"accepted_content_types": sorted(ACCEPTED_CONTENT_TYPES)},
        )
    if byte_size > MAX_UPLOAD_BYTES:
        raise UploadRejected(
            "Document exceeds maximum size",
            details={"max_bytes": MAX_UPLOAD_BYTES, "actual_bytes": byte_size},
        )


class DocumentService:
    def __init__(self, *, store: DocumentStore) -> None:
        self._store = store

    def store(
        self,
        session: Session,
        *,
        case_id: int | None,
        parcel_id: int | None,
        document_type: str,
        original_filename: str,
        content_type: str,
        body: bytes,
        actor: Actor,
        occurrence_time: datetime | None = None,
    ) -> StoredDocument:
        if case_id is None and parcel_id is None:
            raise UploadRejected(
                "Document must be attached to a case or parcel",
                details={"missing_fields": ["case_id", "parcel_id"]},
            )
        admit_upload(content_type=content_type, byte_size=len(body))
        checksum = hashlib.sha256(body).digest()
        if case_id is not None:
            duplicate_id = _duplicate_document_id(session, case_id=case_id, checksum=checksum)
            if duplicate_id is not None:
                raise DuplicateDocument(existing_id=duplicate_id, checksum_sha256=checksum)

        object_key = _object_key(case_id=case_id, parcel_id=parcel_id, checksum=checksum)
        self._store.put_object(key=object_key, body=body, content_type=content_type)
        occurred = occurrence_time or datetime.now(timezone.utc)
        document = Document(
            case_id=case_id,
            parcel_id=parcel_id,
            document_type=document_type,
            original_filename=original_filename,
            byte_size=len(body),
            content_type=content_type,
            checksum_sha256=checksum,
            object_key=object_key,
            uploaded_by=uuid.UUID(str(actor.id)),
            uploaded_at=occurred,
            processing_state=DOCUMENT_QUEUED,
        )
        session.add(document)
        session.flush()
        EventLog.append(
            session,
            event_type="DOCUMENT_UPLOADED",
            entity=document,
            actor=actor,
            changes={
                "case_id": (None, case_id),
                "parcel_id": (None, parcel_id),
                "checksum_sha256": (None, checksum.hex()),
                "processing_state": (None, DOCUMENT_QUEUED),
            },
            occurrence_time=occurred,
            entity_version_after=document.entity_version,
        )
        enqueue(
            session,
            queue="ocr",
            task_name=EXTRACT_DOCUMENT_TASK,
            kwargs={"document_id": document.id},
            idempotency_key=f"extract:{document.id}",
        )
        return StoredDocument(document=document, checksum_sha256=checksum)

    def grant(
        self,
        session: Session,
        *,
        document_id: int,
        actor: Actor,
        expires_in: int = PRESIGN_TTL_SECONDS,
        occurrence_time: datetime | None = None,
    ) -> DocumentGrant:
        if expires_in > PRESIGN_TTL_SECONDS:
            expires_in = PRESIGN_TTL_SECONDS
        document = session.get(Document, document_id, populate_existing=True)
        if document is None:
            raise LookupError(f"document {document_id} does not exist")
        url = self._store.presigned_get(key=document.object_key, expires_in=expires_in)
        EventLog.append(
            session,
            event_type="DOCUMENT_GRANT_ISSUED",
            entity=document,
            actor=actor,
            changes={"expires_in": (None, expires_in)},
            occurrence_time=occurrence_time or datetime.now(timezone.utc),
            entity_version_after=document.entity_version,
        )
        return DocumentGrant(document_id=document.id, url=url, expires_in=expires_in)

    def stored_checksum(self, document: Document) -> bytes:
        return hashlib.sha256(self._store.get_object(key=document.object_key)).digest()


def _duplicate_document_id(session: Session, *, case_id: int, checksum: bytes) -> int | None:
    return session.execute(
        select(Document.id).where(
            Document.case_id == case_id,
            Document.checksum_sha256 == checksum,
        )
    ).scalar_one_or_none()


def _object_key(*, case_id: int | None, parcel_id: int | None, checksum: bytes) -> str:
    prefix = f"cases/{case_id}" if case_id is not None else f"parcels/{parcel_id}"
    return f"{prefix}/{checksum.hex()}"
