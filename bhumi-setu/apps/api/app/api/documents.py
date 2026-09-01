"""Officer document endpoints (task 15.2)."""

from __future__ import annotations

from fastapi import Depends, Query
from sqlalchemy import select

from app.api.routers import officer_router
from app.db.session import unit_of_work
from app.models.acquisition_case import AcquisitionCase
from app.models.document import Document
from app.schemas.documents import DocumentGrantOut
from app.security.access import Principal, authenticate, scoped
from app.services.document import (
    PRESIGN_TTL_SECONDS,
    DocumentService,
    build_minio_store,
)
from app.settings import get_object_storage_settings

__all__ = []


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
