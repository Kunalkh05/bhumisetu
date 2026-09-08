"""Data subject access and correction request handling (task 25.5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.event_log import EventLog
from app.models.acquisition_case import AcquisitionCase
from app.models.case_parcel import CaseParcel
from app.models.data_subject_request import DataSubjectRequest
from app.models.ownership_record import OwnershipRecord
from app.retention.categories import CATEGORY_MAP, PERSONAL_DATA_CATEGORIES, category_of
from app.security.access import Principal, scoped
from app.services.policy import PolicyResolver

__all__ = [
    "DSAR_RESPONSE_WINDOW_KEY",
    "CorrectionSubmission",
    "DSARAccessResponse",
    "DSARAttribute",
    "DSARDisposal",
    "DSARRequestRow",
    "dispose_correction_request",
    "flag_overdue_requests",
    "list_dsar_requests",
    "serve_my_data",
    "submit_correction_request",
]

DSAR_RESPONSE_WINDOW_KEY = "dsar.response_window_days"


@dataclass(frozen=True)
class DSARAttribute:
    ownership_record_id: int
    attribute_name: str
    data_category: str
    value: Any


@dataclass(frozen=True)
class DSARAccessResponse:
    request_id: int
    case_id: int
    served_at: datetime
    attributes: tuple[DSARAttribute, ...]


@dataclass(frozen=True)
class CorrectionSubmission:
    ownership_record_id: int
    target_attribute: str
    asserted_value: Any


@dataclass(frozen=True)
class DSARRequestRow:
    id: int
    request_type: str
    subject_key: str
    case_id: int | None
    ownership_record_id: int | None
    target_attribute: str | None
    current_value: Any | None
    asserted_value: Any | None
    received_at: datetime
    due_at: datetime
    completed_at: datetime | None
    status: str
    routed_area_code: str | None
    disposal_outcome: str | None
    disposal_reasons: str | None
    deciding_officer_id: str | None


@dataclass(frozen=True)
class DSARDisposal:
    request_id: int
    outcome: str
    reasons: str
    decided_at: datetime


def _init_dsar_entity(self, request_id: int) -> None:
    self.id = request_id


_DSAREntity = type(
    "_DSAREntity",
    (),
    {"__tablename__": "data_subject_request", "__init__": _init_dsar_entity},
)


def serve_my_data(
    session: Session,
    *,
    principal: Principal,
    resolver: PolicyResolver,
    now: datetime | None = None,
) -> DSARAccessResponse:
    _require_citizen(principal)
    occurred = now or datetime.now(timezone.utc)
    due_at = _due_at(resolver, principal=principal, received_at=occurred)
    attributes = _personal_attributes_for_principal(session, principal)
    request = DataSubjectRequest(
        request_type="ACCESS",
        subject_key=principal.id,
        case_id=principal.case_id,
        received_at=occurred,
        due_at=due_at,
        completed_at=occurred,
        status="COMPLETED",
    )
    session.add(request)
    session.flush()
    event = EventLog.append(
        session,
        event_type="DATA_ACCESS_REQUEST_SERVED",
        entity=_DSAREntity(request.id),
        actor=principal,
        changes={
            "request_type": (None, "ACCESS"),
            "subject_key": (None, principal.id),
            "case_id": (None, principal.case_id),
            "attribute_count": (None, len(attributes)),
        },
        occurrence_time=occurred,
        case_id=principal.case_id,
    )
    request.created_event_id = event.id
    return DSARAccessResponse(
        request_id=request.id,
        case_id=int(principal.case_id),
        served_at=occurred,
        attributes=attributes,
    )


def submit_correction_request(
    session: Session,
    *,
    principal: Principal,
    data: CorrectionSubmission,
    resolver: PolicyResolver,
    now: datetime | None = None,
) -> DSARRequestRow:
    _require_citizen(principal)
    if data.ownership_record_id not in principal.owner_record_ids:
        raise LookupError("ownership record is not visible to this citizen session")
    current_value, area_code = _current_owner_value(
        session,
        principal=principal,
        ownership_record_id=data.ownership_record_id,
        target_attribute=data.target_attribute,
    )
    occurred = now or datetime.now(timezone.utc)
    request = DataSubjectRequest(
        request_type="CORRECTION",
        subject_key=principal.id,
        case_id=principal.case_id,
        ownership_record_id=data.ownership_record_id,
        target_attribute=data.target_attribute,
        current_value=current_value,
        asserted_value=data.asserted_value,
        received_at=occurred,
        due_at=_due_at(resolver, principal=principal, received_at=occurred),
        status="OPEN",
        routed_area_code=area_code,
    )
    session.add(request)
    session.flush()
    return _request_row(request)


def list_dsar_requests(session: Session, *, principal: Principal) -> tuple[DSARRequestRow, ...]:
    stmt = scoped(
        select(DataSubjectRequest)
        .outerjoin(AcquisitionCase, AcquisitionCase.id == DataSubjectRequest.case_id)
        .order_by(DataSubjectRequest.due_at, DataSubjectRequest.id),
        principal,
        area_col=DataSubjectRequest.routed_area_code,
        case_col=DataSubjectRequest.case_id,
    )
    return tuple(_request_row(row) for row in session.execute(stmt).scalars())


def dispose_correction_request(
    session: Session,
    *,
    principal: Principal,
    request_id: int,
    outcome: str,
    reasons: str,
    now: datetime | None = None,
) -> DSARDisposal:
    request = session.get(DataSubjectRequest, request_id, populate_existing=True)
    if request is None:
        raise LookupError(f"data subject request {request_id} does not exist")
    if not _request_visible_to_principal(session, principal=principal, request_id=request_id):
        raise LookupError(f"data subject request {request_id} is outside this principal's scope")
    occurred = now or datetime.now(timezone.utc)
    request.status = "COMPLETED"
    request.completed_at = occurred
    request.disposal_outcome = outcome
    request.disposal_reasons = reasons
    request.deciding_officer_id = principal.id
    event = EventLog.append(
        session,
        event_type="CORRECTION_REQUEST_DISPOSED",
        entity=_DSAREntity(request.id),
        actor=principal,
        changes={
            "outcome": (None, outcome),
            "reasons": (None, reasons),
            "deciding_officer_id": (None, principal.id),
            "disposal_time": (None, occurred.isoformat()),
        },
        occurrence_time=occurred,
        case_id=request.case_id,
    )
    request.disposed_event_id = event.id
    return DSARDisposal(
        request_id=request.id,
        outcome=outcome,
        reasons=reasons,
        decided_at=occurred,
    )


def flag_overdue_requests(
    session: Session,
    *,
    now: datetime | None = None,
) -> int:
    occurred = now or datetime.now(timezone.utc)
    rows = tuple(
        session.execute(
            select(DataSubjectRequest).where(
                DataSubjectRequest.completed_at.is_(None),
                DataSubjectRequest.due_at < occurred,
                DataSubjectRequest.status != "OVERDUE",
            )
        ).scalars()
    )
    for row in rows:
        row.status = "OVERDUE"
    return len(rows)


def _personal_attributes_for_principal(
    session: Session,
    principal: Principal,
) -> tuple[DSARAttribute, ...]:
    owner_ids = tuple(principal.owner_record_ids)
    if not owner_ids:
        return ()
    records = tuple(
        session.execute(
            select(OwnershipRecord)
            .where(
                OwnershipRecord.id.in_(owner_ids),
                OwnershipRecord.valid_to.is_(None),
            )
            .order_by(OwnershipRecord.id)
        ).scalars()
    )
    items: list[DSARAttribute] = []
    for record in records:
        row = _row_dict(record)
        for attribute_name, data_category in _ownership_personal_categories(row):
            value = getattr(record, attribute_name)
            items.append(
                DSARAttribute(
                    ownership_record_id=record.id,
                    attribute_name=attribute_name,
                    data_category=data_category,
                    value=_mask_if_required(attribute_name, value),
                )
            )
    return tuple(items)


def _ownership_personal_categories(row: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    items: list[tuple[str, str]] = []
    for (table_name, column_name), _entry in CATEGORY_MAP.items():
        if table_name != OwnershipRecord.__tablename__:
            continue
        data_category = category_of(table_name, column_name, row)
        if data_category in PERSONAL_DATA_CATEGORIES:
            items.append((column_name, data_category))
    return tuple(sorted(items))


def _current_owner_value(
    session: Session,
    *,
    principal: Principal,
    ownership_record_id: int,
    target_attribute: str,
) -> tuple[Any, str]:
    record, case = session.execute(
        select(OwnershipRecord, AcquisitionCase)
        .join(CaseParcel, CaseParcel.parcel_id == OwnershipRecord.parcel_id)
        .join(AcquisitionCase, AcquisitionCase.id == CaseParcel.case_id)
        .where(
            OwnershipRecord.id == ownership_record_id,
            AcquisitionCase.id == principal.case_id,
        )
    ).one()
    personal = dict(_ownership_personal_categories(_row_dict(record)))
    if target_attribute not in personal:
        raise ValueError(f"{target_attribute!r} is not a correctable personal attribute")
    return getattr(record, target_attribute), case.area_code


def _due_at(
    resolver: PolicyResolver,
    *,
    principal: Principal,
    received_at: datetime,
) -> datetime:
    window_days = resolver.get(
        DSAR_RESPONSE_WINDOW_KEY,
        state="*",
        act=None,
        as_of=received_at.date(),
    )
    return received_at + timedelta(days=int(window_days))


def _request_row(request: DataSubjectRequest) -> DSARRequestRow:
    return DSARRequestRow(
        id=request.id,
        request_type=request.request_type,
        subject_key=request.subject_key,
        case_id=request.case_id,
        ownership_record_id=request.ownership_record_id,
        target_attribute=request.target_attribute,
        current_value=request.current_value,
        asserted_value=request.asserted_value,
        received_at=request.received_at,
        due_at=request.due_at,
        completed_at=request.completed_at,
        status=request.status,
        routed_area_code=request.routed_area_code,
        disposal_outcome=request.disposal_outcome,
        disposal_reasons=request.disposal_reasons,
        deciding_officer_id=request.deciding_officer_id,
    )


def _request_visible_to_principal(
    session: Session,
    *,
    principal: Principal,
    request_id: int,
) -> bool:
    stmt = scoped(
        select(DataSubjectRequest.id).where(DataSubjectRequest.id == request_id),
        principal,
        area_col=DataSubjectRequest.routed_area_code,
        case_col=DataSubjectRequest.case_id,
    )
    return session.execute(stmt).scalar_one_or_none() is not None


def _mask_if_required(attribute_name: str, value: Any) -> Any:
    if attribute_name != "government_identifier" or value is None:
        return value
    text = str(value)
    if len(text) <= 4:
        return text
    return "\u2022" * (len(text) - 4) + text[-4:]


def _row_dict(record: OwnershipRecord) -> dict[str, Any]:
    return {column.name: getattr(record, column.name) for column in OwnershipRecord.__table__.columns}


def _require_citizen(principal: Principal) -> None:
    if principal.kind != "CITIZEN" or principal.case_id is None:
        raise ValueError("DSAR citizen operation requires a citizen principal with a case")
