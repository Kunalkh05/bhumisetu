"""Officer validation issue endpoints (task 13.5)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from fastapi import Depends
from sqlalchemy import case as sql_case
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routers import officer_router
from app.db.session import get_engine, unit_of_work
from app.models.acquisition_case import AcquisitionCase
from app.models.validation_issue import ValidationIssue, ValidationIssueHistory
from app.schemas.validation import ValidationHistoryOut, ValidationIssueOut, WaiveIssueIn
from app.security.access import Principal, authenticate, scoped
from app.services.policy import PolicyResolver
from app.services.validation import SEVERITY_ORDER, ValidationEngine

__all__ = []


@contextmanager
def _read_session() -> Iterator[Session]:
    session = Session(bind=get_engine())
    try:
        yield session
    finally:
        session.close()


@officer_router.get("/issues", response_model=list[ValidationIssueOut])
def issue_queue(principal: Principal = Depends(authenticate)) -> list[ValidationIssue]:
    with _read_session() as session:
        severity_rank = sql_case(
            SEVERITY_ORDER,
            value=ValidationIssue.severity,
            else_=-1,
        )
        stmt = scoped(
            select(ValidationIssue)
            .join(AcquisitionCase, AcquisitionCase.id == ValidationIssue.case_id)
            .where(ValidationIssue.resolution_state == "OPEN")
            .order_by(severity_rank.desc(), ValidationIssue.detected_at.asc()),
            principal,
            area_col=AcquisitionCase.area_code,
            case_col=ValidationIssue.case_id,
        )
        return list(session.execute(stmt).scalars())


@officer_router.post("/issues/{issue_id}/waive", response_model=ValidationIssueOut)
def waive_issue(
    issue_id: int,
    body: WaiveIssueIn,
    principal: Principal = Depends(authenticate),
) -> ValidationIssue:
    occurred = datetime.now(timezone.utc)
    with unit_of_work() as session:
        _assert_issue_scoped(session, issue_id=issue_id, principal=principal)
        return ValidationEngine(resolver=PolicyResolver(session), rules=()).waive(
            session,
            issue_id=issue_id,
            actor=principal,
            reason=body.reason,
            occurrence_time=occurred,
            expected_version=body.expected_version,
        )


@officer_router.get(
    "/issues/{issue_id}/history",
    response_model=list[ValidationHistoryOut],
)
def issue_history(
    issue_id: int,
    principal: Principal = Depends(authenticate),
) -> list[ValidationIssueHistory]:
    with _read_session() as session:
        _assert_issue_scoped(session, issue_id=issue_id, principal=principal)
        stmt = (
            select(ValidationIssueHistory)
            .where(ValidationIssueHistory.issue_id == issue_id)
            .order_by(ValidationIssueHistory.occurrence_time, ValidationIssueHistory.id)
        )
        return list(session.execute(stmt).scalars())


def _assert_issue_scoped(
    session: Session,
    *,
    issue_id: int,
    principal: Principal,
) -> None:
    stmt = scoped(
        select(ValidationIssue.id)
        .join(AcquisitionCase, AcquisitionCase.id == ValidationIssue.case_id)
        .where(ValidationIssue.id == issue_id),
        principal,
        area_col=AcquisitionCase.area_code,
        case_col=ValidationIssue.case_id,
    )
    session.execute(stmt).scalar_one()
