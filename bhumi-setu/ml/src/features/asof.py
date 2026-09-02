"""Point-in-time event replay for ML features (task 22.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.event_log import AsOfMode
from app.models.event import Event

__all__ = [
    "AsOfView",
    "AwardState",
    "DocumentState",
    "IssueState",
    "NoticeState",
    "ObjectionState",
    "ParcelState",
    "StageEntry",
    "build_as_of_view",
]


@dataclass(frozen=True)
class StageEntry:
    event_id: int
    stage_key: str
    occurrence_time: datetime


@dataclass(frozen=True)
class NoticeState:
    event_id: int
    notice_id: int
    event_type: str
    occurrence_time: datetime
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class ObjectionState:
    event_id: int
    objection_id: int
    event_type: str
    occurrence_time: datetime
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class ParcelState:
    event_id: int
    parcel_id: int
    event_type: str
    occurrence_time: datetime
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class AwardState:
    event_id: int
    award_id: int
    event_type: str
    occurrence_time: datetime
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class IssueState:
    event_id: int
    issue_id: int
    event_type: str
    occurrence_time: datetime
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class DocumentState:
    event_id: int
    document_id: int
    event_type: str
    occurrence_time: datetime
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class AsOfView:
    case_id: int
    t: datetime
    mode: AsOfMode
    stage_history: tuple[StageEntry, ...]
    notices: tuple[NoticeState, ...]
    objections: tuple[ObjectionState, ...]
    parcels: tuple[ParcelState, ...]
    awards: tuple[AwardState, ...]
    issues: tuple[IssueState, ...]
    documents: tuple[DocumentState, ...]
    consumed_event_ids: tuple[int, ...]


def build_as_of_view(
    session: Session,
    case_id: int,
    t: datetime,
    mode: AsOfMode | str,
) -> AsOfView:
    """Fetch case events under the requested SQL predicate, then fold in memory."""
    mode = AsOfMode(mode)
    clause = Event.occurrence_time <= t
    if mode == AsOfMode.KNOWABLE_AT:
        clause = and_(clause, Event.recording_time <= t)

    rows = tuple(
        session.execute(
            select(Event)
            .where(Event.case_id == case_id, clause)
            .order_by(Event.occurrence_time, Event.id)
        ).scalars()
    )
    return _fold(case_id=case_id, t=t, mode=mode, rows=rows)


def _fold(
    *,
    case_id: int,
    t: datetime,
    mode: AsOfMode,
    rows: Iterable[Event],
) -> AsOfView:
    stages: list[StageEntry] = []
    notices: list[NoticeState] = []
    objections: list[ObjectionState] = []
    parcels: list[ParcelState] = []
    awards: list[AwardState] = []
    issues: list[IssueState] = []
    documents: list[DocumentState] = []
    consumed: list[int] = []

    for row in rows:
        consumed.append(row.id)
        payload = row.payload if isinstance(row.payload, Mapping) else {}
        if row.entity_type == "acquisition_case":
            stage_key = _payload_value(payload, "stage_key")
            if stage_key is not None:
                stages.append(
                    StageEntry(
                        event_id=row.id,
                        stage_key=str(stage_key),
                        occurrence_time=row.occurrence_time,
                    )
                )
        elif row.entity_type == "statutory_notice":
            notices.append(_notice(row, payload))
        elif row.entity_type == "objection":
            objections.append(_objection(row, payload))
        elif row.entity_type in {"land_parcel", "case_parcel"}:
            parcels.append(_parcel(row, payload))
        elif row.entity_type in {"award", "payout"}:
            awards.append(_award(row, payload))
        elif row.entity_type == "validation_issue":
            issues.append(_issue(row, payload))
        elif row.entity_type in {"document", "extraction", "extracted_field"}:
            documents.append(_document(row, payload))

    return AsOfView(
        case_id=case_id,
        t=t,
        mode=mode,
        stage_history=tuple(stages),
        notices=tuple(notices),
        objections=tuple(objections),
        parcels=tuple(parcels),
        awards=tuple(awards),
        issues=tuple(issues),
        documents=tuple(documents),
        consumed_event_ids=tuple(consumed),
    )


def _payload_value(payload: Mapping[str, Any], key: str) -> Any | None:
    value = payload.get(key)
    if isinstance(value, Mapping):
        return value.get("to", value.get("value"))
    return value


def _notice(row: Event, payload: Mapping[str, Any]) -> NoticeState:
    return NoticeState(row.id, row.entity_id, row.event_type, row.occurrence_time, payload)


def _objection(row: Event, payload: Mapping[str, Any]) -> ObjectionState:
    return ObjectionState(row.id, row.entity_id, row.event_type, row.occurrence_time, payload)


def _parcel(row: Event, payload: Mapping[str, Any]) -> ParcelState:
    return ParcelState(row.id, row.entity_id, row.event_type, row.occurrence_time, payload)


def _award(row: Event, payload: Mapping[str, Any]) -> AwardState:
    return AwardState(row.id, row.entity_id, row.event_type, row.occurrence_time, payload)


def _issue(row: Event, payload: Mapping[str, Any]) -> IssueState:
    return IssueState(row.id, row.entity_id, row.event_type, row.occurrence_time, payload)


def _document(row: Event, payload: Mapping[str, Any]) -> DocumentState:
    return DocumentState(row.id, row.entity_id, row.event_type, row.occurrence_time, payload)
