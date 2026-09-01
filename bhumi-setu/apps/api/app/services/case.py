"""Acquisition case creation and stage transitions (task 8.2)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Protocol

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.db.versioned_repository import VersionedRepository
from app.errors import DomainError, ErrorCode
from app.models.acquisition_case import AcquisitionCase
from app.models.case_parcel import CaseParcel
from app.services.policy import PolicyResolver
from app.services.stage_graph import resolve_stage_graph, stage_deadline

__all__ = [
    "BlockingIssuesOpen",
    "CaseCreate",
    "CaseService",
    "FirstStageParcelRequired",
]


class BlockingIssuesOpen(DomainError):
    """A stage transition cannot proceed while blocking issues are open."""

    code = ErrorCode.BLOCKING_ISSUES_OPEN
    status_code = 409

    def __init__(self, *, issue_ids: tuple[int, ...], count: int) -> None:
        super().__init__(
            "Blocking validation issues are open",
            details={"issue_ids": list(issue_ids), "open_blocking_count": count},
        )


class FirstStageParcelRequired(DomainError):
    """A case may not leave the first stage until at least one parcel is linked."""

    code = ErrorCode.BLOCKING_ISSUES_OPEN
    status_code = 409

    def __init__(self, *, case_id: int) -> None:
        super().__init__(
            "A case cannot leave its first stage before a parcel is associated",
            details={"case_id": case_id, "issue_ids": ["FIRST_STAGE_PARCEL_REQUIRED"]},
        )


class CaseReferenceFactory(Protocol):
    def __call__(self, state_key: str) -> str:
        ...


@dataclass(frozen=True)
class CaseCreate:
    project_id: int
    state_key: str
    act_key: str
    area_code: str
    stage_set_effective_from: date
    stage_entered_on: date


def _default_reference(state_key: str) -> str:
    return f"{state_key.upper()}-{secrets.token_hex(6).upper()}"


def _occurrence_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


class CaseService:
    """Create cases and move them through the configured stage graph."""

    def __init__(
        self,
        *,
        resolver: PolicyResolver,
        reference_factory: CaseReferenceFactory = _default_reference,
    ) -> None:
        self._resolver = resolver
        self._reference_factory = reference_factory

    def create(
        self,
        session: Session,
        *,
        data: CaseCreate,
        actor: Actor,
        case_reference: str | None = None,
    ) -> AcquisitionCase:
        reference = case_reference or self._reference_factory(data.state_key)
        draft = AcquisitionCase(
            case_reference=reference,
            project_id=data.project_id,
            state_key=data.state_key,
            act_key=data.act_key,
            area_code=data.area_code,
            stage_key="",
            stage_set_effective_from=data.stage_set_effective_from,
            stage_entered_on=data.stage_entered_on,
        )
        graph = resolve_stage_graph(draft, resolver=self._resolver)
        draft.stage_key = graph.first_key
        draft.stage_deadline = stage_deadline(draft, resolver=self._resolver)
        draft.is_terminal = graph.is_terminal(draft.stage_key)

        session.add(draft)
        session.flush()
        EventLog.append(
            session,
            event_type="CASE_CREATED",
            entity=draft,
            actor=actor,
            changes={
                "case_reference": (None, draft.case_reference),
                "stage_key": (None, draft.stage_key),
            },
            occurrence_time=_occurrence_datetime(data.stage_entered_on),
            entity_version_after=draft.entity_version,
        )
        return draft

    def transition(
        self,
        session: Session,
        *,
        case_id: int,
        expected_version: int,
        expected_stage: str,
        target_stage: str,
        occurrence_date: date,
        actor: Actor,
        blocking_issue_ids: tuple[int, ...] = (),
    ) -> AcquisitionCase:
        case = session.get(AcquisitionCase, case_id, populate_existing=True)
        if case is None:
            raise LookupError(f"case {case_id} does not exist")
        if case.open_blocking_count:
            raise BlockingIssuesOpen(
                issue_ids=blocking_issue_ids,
                count=case.open_blocking_count,
            )

        graph = resolve_stage_graph(case, resolver=self._resolver)
        graph.assert_transition_permitted(current=case.stage_key, requested=target_stage)
        if case.stage_key == graph.first_key and not _case_has_parcel(session, case_id):
            raise FirstStageParcelRequired(case_id=case_id)

        stage_context = _StageContext(
            state_key=case.state_key,
            act_key=case.act_key,
            stage_key=target_stage,
            stage_set_effective_from=case.stage_set_effective_from,
            stage_entered_on=occurrence_date,
        )
        deadline = stage_deadline(stage_context, resolver=self._resolver)
        updated = VersionedRepository.update(
            session,
            entity_type=AcquisitionCase,
            entity_id=case_id,
            expected_version=expected_version,
            expected_stage=expected_stage,
            submitted_prior={
                "stage_key": case.stage_key,
                "stage_entered_on": case.stage_entered_on,
            },
            changes={
                "stage_key": target_stage,
                "stage_entered_on": occurrence_date,
                "stage_deadline": deadline,
                "deadline_breached": False,
                "is_terminal": graph.is_terminal(target_stage),
            },
            actor=actor,
            occurrence_time=_occurrence_datetime(occurrence_date),
            event_type="CASE_STAGE_TRANSITIONED",
        )
        return updated  # type: ignore[return-value]


@dataclass(frozen=True)
class _StageContext:
    state_key: str
    act_key: str
    stage_key: str
    stage_set_effective_from: date
    stage_entered_on: date


def _case_has_parcel(session: Session, case_id: int) -> bool:
    return bool(
        session.execute(
            select(exists().where(CaseParcel.case_id == case_id))
        ).scalar()
    )
