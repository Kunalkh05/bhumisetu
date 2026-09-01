"""Notice endpoints (task 10.4)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routers import officer_router
from app.db.session import get_engine
from app.models.acquisition_case import AcquisitionCase
from app.schemas.notices import NoticeOut
from app.security.access import Principal, authenticate, scoped
from app.services.notice import notices_for_case

__all__ = []


@contextmanager
def _read_session() -> Iterator[Session]:
    session = Session(bind=get_engine())
    try:
        yield session
    finally:
        session.close()


@officer_router.get(
    "/cases/{case_id}/notices",
    response_model=list[NoticeOut],
)
def case_notices(
    case_id: int,
    principal: Principal = Depends(authenticate),
) -> list:
    with _read_session() as session:
        stmt = scoped(
            select(AcquisitionCase.id).where(AcquisitionCase.id == case_id),
            principal,
            area_col=AcquisitionCase.area_code,
            case_col=AcquisitionCase.id,
        )
        session.execute(stmt).scalar_one()
        return notices_for_case(session, case_id=case_id)
