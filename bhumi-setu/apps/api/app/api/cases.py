"""Officer case endpoints (task 8.3)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routers import officer_router
from app.db.event_log import AsOfMode, EventLog
from app.db.session import get_engine
from app.models.acquisition_case import AcquisitionCase
from app.schemas.cases import CaseOut, TimelineEventOut
from app.security.access import Principal, authenticate, scoped

__all__ = []


class _CaseEntity:
    def __init__(self, case_id: int) -> None:
        self.__tablename__ = "acquisition_case"
        self.id = case_id


@contextmanager
def _read_session() -> Iterator[Session]:
    session = Session(bind=get_engine())
    try:
        yield session
    finally:
        session.close()


@officer_router.get(
    "/cases",
    response_model=list[CaseOut],
)
def list_cases(principal: Principal = Depends(authenticate)) -> list[AcquisitionCase]:
    with _read_session() as session:
        stmt = scoped(
            select(AcquisitionCase).order_by(AcquisitionCase.id),
            principal,
            area_col=AcquisitionCase.area_code,
            case_col=AcquisitionCase.id,
        )
        return list(session.execute(stmt).scalars())


@officer_router.get(
    "/cases/{case_id}",
    response_model=CaseOut,
)
def get_case(
    case_id: int,
    principal: Principal = Depends(authenticate),
) -> AcquisitionCase:
    with _read_session() as session:
        stmt = scoped(
            select(AcquisitionCase).where(AcquisitionCase.id == case_id),
            principal,
            area_col=AcquisitionCase.area_code,
            case_col=AcquisitionCase.id,
        )
        return session.execute(stmt).scalar_one()


@officer_router.get(
    "/cases/{case_id}/timeline",
    response_model=list[TimelineEventOut],
)
def case_timeline(
    case_id: int,
    principal: Principal = Depends(authenticate),
) -> list[TimelineEventOut]:
    with _read_session() as session:
        scoped_case = scoped(
            select(AcquisitionCase.id).where(AcquisitionCase.id == case_id),
            principal,
            area_col=AcquisitionCase.area_code,
            case_col=AcquisitionCase.id,
        )
        session.execute(scoped_case).scalar_one()
        rows = EventLog.events(
            session,
            _CaseEntity(case_id),
            as_of=datetime.now(timezone.utc),
            mode=AsOfMode.OCCURRED_BY,
        )
        return [
            TimelineEventOut(
                id=row.id,
                event_type=row.event_type,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                occurrence_time=row.occurrence_time,
                recording_time=row.recording_time,
                payload=dict(row.payload),
            )
            for row in rows
        ]
