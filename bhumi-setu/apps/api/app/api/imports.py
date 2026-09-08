"""Officer bulk import endpoints."""

from __future__ import annotations

from fastapi import Depends

from app.api.routers import officer_router
from app.db.session import unit_of_work
from app.schemas.imports import ImportBatchOut, ImportRowIn, ImportSubmitIn
from app.security.access import Principal, authenticate
from app.services.import_service import ImportRowSubmission, submit_import_batch

__all__ = []


@officer_router.post("/imports", response_model=ImportBatchOut)
def submit_import(
    payload: ImportSubmitIn,
    principal: Principal = Depends(authenticate),
) -> ImportBatchOut:
    with unit_of_work() as session:
        result = submit_import_batch(
            session,
            principal=principal,
            rows=tuple(_row(row) for row in payload.rows),
        )
        return ImportBatchOut.model_validate(result)


def _row(row: ImportRowIn) -> ImportRowSubmission:
    return ImportRowSubmission(
        ordinal=row.ordinal,
        entity_type=row.entity_type,
        payload=row.payload,
    )

