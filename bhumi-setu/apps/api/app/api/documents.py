"""Officer document endpoints (tasks 15.2 and 18.5)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from fastapi import Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routers import officer_router
from app.db.session import get_engine, unit_of_work
from app.models.acquisition_case import AcquisitionCase
from app.models.document import Document
from app.schemas.documents import DocumentGrantOut, DocumentOut
from app.security.access import Principal, authenticate, scoped
from app.services.document import (
    DOCUMENT_QUEUED,
    PRESIGN_TTL_SECONDS,
    DocumentService,
    build_minio_store,
)
from app.services.ocr import PROCESSING
from app.settings import get_object_storage_settings

__all__ = []

PROCESSING_STATES = (DOCUMENT_QUEUED, PROCESSING)


@contextmanager
def _read_session() -> Iterator[Session]:
    session = Session(bind=get_engine())
    try:
        yield session
    finally:
        session.close()


@officer_router.get(
    "/documents/processing",
    response_model=list[DocumentOut],
)
def processing_documents(
    principal: Principal = Depends(authenticate),
) -> list[Document]:
    with _read_session() as session:
        stmt = scoped(
            select(Document)
            .outerjoin(AcquisitionCase, AcquisitionCase.id == Document.case_id)
            .where(Document.processing_state.in_(PROCESSING_STATES))
            .order_by(Document.uploaded_at.desc(), Document.id.desc()),
            principal,
            area_col=AcquisitionCase.area_code,
            case_col=Document.case_id,
        )
        return list(session.execute(stmt).scalars())


@officer_router.get(
    "/documents/{document_id}/grant",
    response_model=DocumentGrantOut,
)
def document_grant(
    document_id: int,
    expires_in: int = Query(PRESIGN_TTL_SECONDS, ge=1, le=PRESIGN_TTL_SECONDS),
    principal: Principal = Depends(authenticate),
) -> DocumentGrantOut:
    with unit_of_work() as session:
        stmt = scoped(
            select(Document.id)
            .outerjoin(AcquisitionCase, AcquisitionCase.id == Document.case_id)
            .where(Document.id == document_id),
            principal,
            area_col=AcquisitionCase.area_code,
            case_col=Document.case_id,
        )
        session.execute(stmt).scalar_one()
        grant = DocumentService(
            store=build_minio_store(get_object_storage_settings())
        ).grant(
            session,
            document_id=document_id,
            actor=principal,
            expires_in=expires_in,
        )
        return DocumentGrantOut(
            document_id=grant.document_id,
            url=grant.url,
            expires_in=grant.expires_in,
        )
