"""Retention and DSAR endpoints."""

from __future__ import annotations

from fastapi import Depends

from app.api.cases import _read_session
from app.api.routers import citizen_html, officer_router
from app.db.session import unit_of_work
from app.retention.dsar import (
    CorrectionSubmission,
    dispose_correction_request,
    list_dsar_requests,
    serve_my_data,
    submit_correction_request,
)
from app.retention.projection import ownership_retention_projection
from app.schemas.retention import (
    CorrectionRequestIn,
    DSARAccessOut,
    DSARDisposalIn,
    DSARDisposalOut,
    DSARRequestOut,
    OwnershipRetentionOut,
)
from app.security.access import Principal, authenticate
from app.security.permissions import require_permission
from app.services.policy import PolicyResolver

__all__ = []


@officer_router.get(
    "/retention/ownership-records/{ownership_record_id}",
    response_model=OwnershipRetentionOut,
)
def ownership_retention(
    ownership_record_id: int,
    principal: Principal = Depends(authenticate),
) -> OwnershipRetentionOut:
    with _read_session() as session:
        projection = ownership_retention_projection(
            session,
            ownership_record_id=ownership_record_id,
            principal=principal,
            resolver=PolicyResolver(session),
        )
        return OwnershipRetentionOut.model_validate(projection)


@citizen_html.get("/my-data", response_model=DSARAccessOut)
def citizen_my_data(
    principal: Principal = Depends(authenticate),
) -> DSARAccessOut:
    with unit_of_work() as session:
        result = serve_my_data(
            session,
            principal=principal,
            resolver=PolicyResolver(session),
        )
        return DSARAccessOut.model_validate(result)


@citizen_html.post("/correction", response_model=DSARRequestOut)
def citizen_correction(
    payload: CorrectionRequestIn,
    principal: Principal = Depends(authenticate),
) -> DSARRequestOut:
    with unit_of_work() as session:
        result = submit_correction_request(
            session,
            principal=principal,
            data=CorrectionSubmission(
                ownership_record_id=payload.ownership_record_id,
                target_attribute=payload.target_attribute,
                asserted_value=payload.asserted_value,
            ),
            resolver=PolicyResolver(session),
        )
        return DSARRequestOut.model_validate(result)


@officer_router.get("/dsar", response_model=list[DSARRequestOut])
def officer_dsar_queue(
    principal: Principal = Depends(authenticate),
) -> list[DSARRequestOut]:
    with unit_of_work() as session:
        require_permission(session, principal, "dsar.dispose")
        return [
            DSARRequestOut.model_validate(row)
            for row in list_dsar_requests(session, principal=principal)
        ]


@officer_router.post("/dsar/{request_id}/disposal", response_model=DSARDisposalOut)
def officer_dsar_disposal(
    request_id: int,
    payload: DSARDisposalIn,
    principal: Principal = Depends(authenticate),
) -> DSARDisposalOut:
    with unit_of_work() as session:
        require_permission(
            session,
            principal,
            "dsar.dispose",
            resource={"data_subject_request_id": request_id},
        )
        result = dispose_correction_request(
            session,
            principal=principal,
            request_id=request_id,
            outcome=payload.outcome,
            reasons=payload.reasons,
        )
        return DSARDisposalOut.model_validate(result)
