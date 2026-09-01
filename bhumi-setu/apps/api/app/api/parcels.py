"""Parcel endpoints (task 9.3)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Iterator

from fastapi import Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routers import officer_router
from app.db.session import get_engine
from app.models.case_parcel import CaseParcel
from app.models.land_parcel import LandParcel
from app.schemas.ownership import OwnershipOut
from app.security.access import Principal, authenticate, scoped
from app.services.parcel import ownership_as_of

__all__ = []


@contextmanager
def _read_session() -> Iterator[Session]:
    session = Session(bind=get_engine())
    try:
        yield session
    finally:
        session.close()


@officer_router.get(
    "/parcels/{parcel_id}/ownership",
    response_model=list[OwnershipOut],
)
def parcel_ownership(
    parcel_id: int,
    on: date = Query(...),
    principal: Principal = Depends(authenticate),
) -> list:
    with _read_session() as session:
        scoped_parcel = scoped(
            select(LandParcel.id)
            .join(CaseParcel, CaseParcel.parcel_id == LandParcel.id)
            .where(LandParcel.id == parcel_id),
            principal,
            area_col=LandParcel.area_code,
            case_col=CaseParcel.case_id,
        )
        session.execute(scoped_parcel).scalar_one()
        return ownership_as_of(session, parcel_id=parcel_id, on=on)
