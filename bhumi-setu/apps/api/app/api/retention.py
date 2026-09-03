"""Officer retention projection endpoints."""

from __future__ import annotations

from fastapi import Depends

from app.api.cases import _read_session
from app.api.routers import officer_router
from app.retention.projection import ownership_retention_projection
from app.schemas.retention import OwnershipRetentionOut
from app.security.access import Principal, authenticate
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
