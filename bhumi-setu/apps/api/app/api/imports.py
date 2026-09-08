"""Officer bulk import endpoints."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Query

from app.api.routers import officer_router
from app.db.session import unit_of_work
from app.schemas.imports import (
    ImportBatchDetailOut,
    ImportBatchOut,
    ImportRowIn,
    ImportSubmitIn,
)
from app.security.access import Principal, authenticate
from app.services.import_service import (
    ImportRowSubmission,
    get_import_batch_report,
    submit_import_batch,
)

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


@officer_router.get("/imports/{batch_id}", response_model=ImportBatchDetailOut)
def get_import_batch(
    batch_id: int,
    rule_id: str | None = Query(None),
    principal: Principal = Depends(authenticate),
) -> ImportBatchDetailOut:
    with unit_of_work() as session:
        try:
            report = get_import_batch_report(
                session,
                batch_id=batch_id,
                principal=principal,
                rule_id=rule_id,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return ImportBatchDetailOut.model_validate(report)


def _row(row: ImportRowIn) -> ImportRowSubmission:
    return ImportRowSubmission(
        ordinal=row.ordinal,
        entity_type=row.entity_type,
        payload=row.payload,
    )

