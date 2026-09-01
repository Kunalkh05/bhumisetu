"""Objection intake, disposal and overdue marking (task 11)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.db.versioned_repository import VersionedRepository
from app.errors import DomainError, ErrorCode
from app.models.acquisition_case import AcquisitionCase
from app.models.objection import Objection
from app.models.statutory_notice import StatutoryNotice
from app.services.policy import PolicyResolver

__all__ = [
    "DISPOSAL_MISSING_REASONS",
    "WINDOW_OUT_OF_WINDOW",
    "WINDOW_WITHIN",
    "DisposalMissingReasons",
    "ObjectionDisposal",
    "ObjectionIntake",
    "ObjectionService",
    "sweep_objection_overdue",
]

WINDOW_WITHIN = "WITHIN"
WINDOW_OUT_OF_WINDOW = "OUT_OF_WINDOW"
DISPOSAL_MISSING_REASONS = "disposal_reasons"


@dataclass(frozen=True)
class ObjectionIntake:
    case_id: int
    objector_name: str
    receipt_date: date
    grounds_category: str
    substance: str
    disposal_period_key: str
    ownership_record_id: int | None = None
    governing_notice_id: int | None = None


@dataclass(frozen=True)
class ObjectionDisposal:
    outcome: str
    disposal_date: date
    reasons: str
    deciding_officer_id: uuid.UUID


class DisposalMissingReasons(DomainError):
    code = ErrorCode.VALIDATION_FAILED
    status_code = 422

    def __init__(self) -> None:
        super().__init__(
            "Disposal reasons are required",
            details={"missing_fields": [DISPOSAL_MISSING_REASONS]},
        )


def _occurrence_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _advanced_by(value: date, days: int) -> date:
    return value.fromordinal(value.toordinal() + days)


class ObjectionService:
    def __init__(self, *, resolver: PolicyResolver) -> None:
        self._resolver = resolver

    def intake(
        self,
        session: Session,
        *,
        data: ObjectionIntake,
        actor: Actor,
    ) -> Objection:
        case = session.get(AcquisitionCase, data.case_id, populate_existing=True)
        if case is None:
            raise LookupError(f"case {data.case_id} does not exist")
        notice = (
            session.get(StatutoryNotice, data.governing_notice_id, populate_existing=True)
            if data.governing_notice_id is not None
            else None
        )
        window_state = (
            WINDOW_WITHIN
            if notice is None or data.receipt_date <= notice.response_deadline
            else WINDOW_OUT_OF_WINDOW
        )
        period_days = int(
            self._resolver.get(
                data.disposal_period_key,
                state=case.state_key,
                act=case.act_key,
                as_of=data.receipt_date,
            )
        )
        objection = Objection(
            case_id=data.case_id,
            objector_name=data.objector_name,
            ownership_record_id=data.ownership_record_id,
            receipt_date=data.receipt_date,
            grounds_category=data.grounds_category,
            substance=data.substance,
            governing_notice_id=data.governing_notice_id,
            window_state=window_state,
            disposal_deadline=_advanced_by(data.receipt_date, period_days),
            is_disposal_overdue=False,
        )
        session.add(objection)
        case.undisposed_objection_count = (case.undisposed_objection_count or 0) + 1
        session.flush()
        EventLog.append(
            session,
            event_type="OBJECTION_RECORDED",
            entity=objection,
            actor=actor,
            changes={
                "objector_name": (None, data.objector_name),
                "receipt_date": (None, data.receipt_date),
                "grounds_category": (None, data.grounds_category),
                "substance": (None, data.substance),
                "window_state": (None, window_state),
                "disposal_deadline": (None, objection.disposal_deadline),
            },
            occurrence_time=_occurrence_datetime(data.receipt_date),
            entity_version_after=objection.entity_version,
        )
        return objection

    def dispose(
        self,
        session: Session,
        *,
        objection_id: int,
        expected_version: int,
        data: ObjectionDisposal,
        actor: Actor,
    ) -> Objection:
        if not data.reasons.strip():
            raise DisposalMissingReasons()
        objection = session.get(Objection, objection_id, populate_existing=True)
        if objection is None:
            raise LookupError(f"objection {objection_id} does not exist")
        case = session.get(AcquisitionCase, objection.case_id, populate_existing=True)
        if case is not None and objection.disposal_date is None:
            case.undisposed_objection_count = max(case.undisposed_objection_count - 1, 0)

        updated = VersionedRepository.update(
            session,
            entity_type=Objection,
            entity_id=objection_id,
            expected_version=expected_version,
            submitted_prior={
                "disposal_outcome": objection.disposal_outcome,
                "disposal_date": objection.disposal_date,
                "disposal_reasons": objection.disposal_reasons,
                "deciding_officer_id": objection.deciding_officer_id,
            },
            changes={
                "disposal_outcome": data.outcome,
                "disposal_date": data.disposal_date,
                "disposal_reasons": data.reasons,
                "deciding_officer_id": data.deciding_officer_id,
            },
            actor=actor,
            occurrence_time=_occurrence_datetime(data.disposal_date),
            event_type="OBJECTION_DISPOSED",
        )
        return updated  # type: ignore[return-value]


@dataclass(frozen=True)
class _SystemActor:
    kind: str = "SYSTEM"
    id: str = "deadline-sweep"


def sweep_objection_overdue(
    session: Session,
    *,
    today: date,
    actor: Actor | None = None,
    objections: Iterable[Objection] | None = None,
) -> int:
    actor = actor or _SystemActor()
    candidates = list(objections) if objections is not None else _overdue_candidates(session, today=today)
    changed = 0
    for objection in candidates:
        if objection.disposal_date is not None:
            continue
        overdue = today > objection.disposal_deadline
        if overdue and not objection.is_disposal_overdue:
            objection.is_disposal_overdue = True
            EventLog.append(
                session,
                event_type="OBJECTION_DISPOSAL_OVERDUE",
                entity=objection,
                actor=actor,
                changes={"is_disposal_overdue": (False, True)},
                occurrence_time=_occurrence_datetime(today),
                entity_version_after=objection.entity_version,
            )
            changed += 1
    session.flush()
    return changed


def _overdue_candidates(session: Session, *, today: date) -> list[Objection]:
    return list(
        session.execute(
            select(Objection)
            .where(
                Objection.disposal_date.is_(None),
                Objection.disposal_deadline < today,
            )
            .order_by(Objection.id)
        ).scalars()
    )
