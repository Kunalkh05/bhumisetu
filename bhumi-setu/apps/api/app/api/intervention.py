"""Officer intervention queue endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import Depends, Query
from sqlalchemy import select

from app.api.cases import _read_session
from app.api.routers import officer_router
from app.db.session import unit_of_work
from app.models.acquisition_case import AcquisitionCase
from app.schemas.intervention import (
    ActionDispositionIn,
    ActionDispositionOut,
    InterventionQueueOut,
)
from app.security.access import Principal, authenticate, scoped
from app.services.intervention import load_intervention_queue, record_action_disposition
from app.services.policy import PolicyResolver

__all__ = []


@officer_router.get("/queue", response_model=InterventionQueueOut)
def intervention_queue(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(authenticate),
) -> InterventionQueueOut:
    with _read_session() as session:
        page = load_intervention_queue(
            session,
            principal=principal,
            resolver=PolicyResolver(session),
            limit=limit,
            offset=offset,
            today=date.today(),
        )
        return InterventionQueueOut.model_validate(page)


@officer_router.post(
    "/queue/{case_id}/actions/{action_id}/disposition",
    response_model=ActionDispositionOut,
)
def dispose_recommended_action(
    case_id: int,
    action_id: str,
    body: ActionDispositionIn,
    principal: Principal = Depends(authenticate),
) -> ActionDispositionOut:
    with unit_of_work() as session:
        case = session.execute(
            scoped(
                select(AcquisitionCase).where(AcquisitionCase.id == case_id),
                principal,
                area_col=AcquisitionCase.area_code,
                case_col=AcquisitionCase.id,
            )
        ).scalar_one()
        event = record_action_disposition(
            session,
            case=case,
            principal=principal,
            action_id=action_id,
            disposition=body.disposition,
            reason=body.reason,
            occurrence_time=body.occurrence_time,
            expected_version=body.expected_version,
        )
        return ActionDispositionOut(
            case_id=case.id,
            action_id=action_id,
            disposition=body.disposition,
            reason=body.reason,
            occurrence_time=event.occurrence_time,
        )
