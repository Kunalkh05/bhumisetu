"""Statutory notice issue, service recording and deadline sweep (task 10)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.db.session import unit_of_work
from app.models.acquisition_case import AcquisitionCase
from app.models.event import Event
from app.models.notice_parcel import NoticeParcel
from app.models.notice_service_record import NoticeServiceRecord
from app.models.statutory_notice import StatutoryNotice
from app.services.policy import PolicyResolver
from app.workers.celery_app import celery_app

__all__ = [
    "APPROACHING_BOUNDARIES",
    "BREACH_STATE_BREACHED",
    "BREACH_STATE_WITHIN",
    "NoticeIssue",
    "NoticeService",
    "NoticeSummary",
    "ServiceRecordCreate",
    "deadline_sweep",
    "notice_response_deadline",
    "notices_for_case",
    "sweep_deadlines",
]

BREACH_STATE_WITHIN = "WITHIN"
BREACH_STATE_BREACHED = "BREACHED"
APPROACHING_BOUNDARIES: tuple[int, ...] = (30, 14, 7)


@dataclass(frozen=True)
class NoticeIssue:
    case_id: int
    notice_type: str
    issuing_authority: str
    issue_date: date
    publication_mode: str
    parcel_ids: tuple[int, ...]
    response_period_key: str


@dataclass(frozen=True)
class ServiceRecordCreate:
    notice_id: int
    ownership_record_id: int
    service_date: date
    service_mode: str
    service_location: str | None = None


@dataclass(frozen=True)
class NoticeSummary:
    id: int
    case_id: int
    notice_type: str
    issuing_authority: str
    issue_date: date
    publication_mode: str
    response_deadline: date
    service_date: date | None
    breach_state: str
    entity_version: int


def notice_response_deadline(
    *,
    issue_date: date,
    response_period_days: int,
) -> date:
    return issue_date.fromordinal(issue_date.toordinal() + response_period_days)


def _occurrence_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


class NoticeService:
    """Create notices and record service on interested persons."""

    def __init__(self, *, resolver: PolicyResolver) -> None:
        self._resolver = resolver

    def issue(
        self,
        session: Session,
        *,
        data: NoticeIssue,
        actor: Actor,
    ) -> StatutoryNotice:
        case = session.get(AcquisitionCase, data.case_id, populate_existing=True)
        if case is None:
            raise LookupError(f"case {data.case_id} does not exist")

        snapshot = self._resolver.snapshot(
            [data.response_period_key],
            state=case.state_key,
            act=case.act_key,
            as_of=data.issue_date,
        )
        deadline = notice_response_deadline(
            issue_date=data.issue_date,
            response_period_days=int(snapshot[data.response_period_key]),
        )
        notice = StatutoryNotice(
            case_id=data.case_id,
            notice_type=data.notice_type,
            issuing_authority=data.issuing_authority,
            issue_date=data.issue_date,
            publication_mode=data.publication_mode,
            response_deadline=deadline,
            policy_snapshot_hash=snapshot.content_hash,
            breach_state=BREACH_STATE_WITHIN,
        )
        session.add(notice)
        session.flush()
        for parcel_id in data.parcel_ids:
            session.add(NoticeParcel(notice_id=notice.id, parcel_id=parcel_id))
        EventLog.append(
            session,
            event_type="NOTICE_ISSUED",
            entity=notice,
            actor=actor,
            changes={
                "notice_type": (None, data.notice_type),
                "issuing_authority": (None, data.issuing_authority),
                "issue_date": (None, data.issue_date),
                "publication_mode": (None, data.publication_mode),
                "response_deadline": (None, deadline),
                "parcel_ids": (None, list(data.parcel_ids)),
            },
            occurrence_time=_occurrence_datetime(data.issue_date),
            entity_version_after=notice.entity_version,
        )
        return notice

    def record_service(
        self,
        session: Session,
        *,
        data: ServiceRecordCreate,
        actor: Actor,
    ) -> NoticeServiceRecord:
        record = NoticeServiceRecord(
            notice_id=data.notice_id,
            ownership_record_id=data.ownership_record_id,
            service_date=data.service_date,
            service_mode=data.service_mode,
            service_location=data.service_location,
        )
        session.add(record)
        session.flush()
        EventLog.append(
            session,
            event_type="NOTICE_SERVICE_RECORDED",
            entity=record,
            actor=actor,
            changes={
                "notice_id": (None, data.notice_id),
                "ownership_record_id": (None, data.ownership_record_id),
                "service_date": (None, data.service_date),
                "service_mode": (None, data.service_mode),
            },
            occurrence_time=_occurrence_datetime(data.service_date),
            entity_version_after=record.entity_version,
        )
        return record


def notices_for_case(session: Session, *, case_id: int) -> list[NoticeSummary]:
    rows = session.execute(
            select(StatutoryNotice)
            .add_columns(func.min(NoticeServiceRecord.service_date).label("service_date"))
            .outerjoin(NoticeServiceRecord, NoticeServiceRecord.notice_id == StatutoryNotice.id)
            .where(StatutoryNotice.case_id == case_id)
            .group_by(StatutoryNotice)
            .order_by(StatutoryNotice.issue_date, StatutoryNotice.id)
    ).all()
    return [
        NoticeSummary(
            id=notice.id,
            case_id=notice.case_id,
            notice_type=notice.notice_type,
            issuing_authority=notice.issuing_authority,
            issue_date=notice.issue_date,
            publication_mode=notice.publication_mode,
            response_deadline=notice.response_deadline,
            service_date=service_date,
            breach_state=notice.breach_state,
            entity_version=notice.entity_version,
        )
        for notice, service_date in rows
    ]


@dataclass(frozen=True)
class _SystemActor:
    kind: str = "SYSTEM"
    id: str = "deadline-sweep"


def sweep_deadlines(
    session: Session,
    *,
    today: date,
    actor: Actor | None = None,
    cases: Iterable[AcquisitionCase] | None = None,
) -> int:
    """Mark breached cases and append one approaching event per crossed boundary."""
    actor = actor or _SystemActor()
    candidates = list(cases) if cases is not None else _deadline_candidates(session, today=today)
    changed = 0
    for case in candidates:
        if case.stage_deadline is None or case.is_terminal:
            continue
        remaining_days = (case.stage_deadline - today).days
        for boundary in APPROACHING_BOUNDARIES:
            if 0 <= remaining_days <= boundary and not _has_deadline_event(
                session,
                case_id=case.id,
                event_type="DEADLINE_APPROACHING",
                remaining_days=boundary,
            ):
                EventLog.append(
                    session,
                    event_type="DEADLINE_APPROACHING",
                    entity=case,
                    actor=actor,
                    changes={"remaining_days": (None, boundary), "stage_key": (None, case.stage_key)},
                    occurrence_time=_occurrence_datetime(today),
                    entity_version_after=case.entity_version,
                )
                changed += 1
        if remaining_days <= 0 and not case.deadline_breached:
            case.deadline_breached = True
            EventLog.append(
                session,
                event_type="DEADLINE_BREACHED",
                entity=case,
                actor=actor,
                changes={"deadline_breached": (False, True), "stage_key": (None, case.stage_key)},
                occurrence_time=_occurrence_datetime(today),
                entity_version_after=case.entity_version,
            )
            changed += 1
    session.flush()
    return changed


@celery_app.task(name="app.services.notice.deadline_sweep")
def deadline_sweep() -> int:
    with unit_of_work() as session:
        today = date.today()
        changed = sweep_deadlines(session, today=today)
        from app.services.objection import sweep_objection_overdue

        changed += sweep_objection_overdue(session, today=today)
        return changed


def _deadline_candidates(session: Session, *, today: date) -> list[AcquisitionCase]:
    return list(
        session.execute(
            select(AcquisitionCase)
            .where(
                AcquisitionCase.stage_deadline.is_not(None),
                AcquisitionCase.is_terminal.is_(False),
            )
            .order_by(AcquisitionCase.id)
        ).scalars()
    )


def _has_deadline_event(
    session: Session,
    *,
    case_id: int,
    event_type: str,
    remaining_days: int | None = None,
) -> bool:
    rows = session.execute(
        select(Event.payload)
        .where(
            Event.entity_type == "acquisition_case",
            Event.entity_id == case_id,
            Event.event_type == event_type,
        )
    ).scalars()
    if remaining_days is None:
        return any(True for _ in rows)
    for payload in rows:
        if payload.get("remaining_days", {}).get("to") == remaining_days:
            return True
    return False
