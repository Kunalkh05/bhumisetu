"""Citizen-visible content assembly (task 19.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.acquisition_case import AcquisitionCase
from app.models.award import Award
from app.models.document import Document
from app.models.land_parcel import LandParcel
from app.models.notice_service_record import NoticeServiceRecord
from app.models.objection import Objection
from app.models.ownership_record import OwnershipRecord
from app.models.project import Project
from app.models.statutory_notice import StatutoryNotice
from app.security.access import Principal

__all__ = [
    "CitizenAwardRow",
    "CitizenCaseStatus",
    "CitizenContentView",
    "CitizenDocumentRow",
    "CitizenNoticeRow",
    "CitizenObjectionRow",
    "CitizenOwnershipRow",
    "load_citizen_content",
]


@dataclass(frozen=True)
class CitizenCaseStatus:
    case_reference: str
    project_name: str
    stage: str
    stage_entered_on: date
    next_step: str
    statutory_period: str
    remaining_days: int | None


@dataclass(frozen=True)
class CitizenOwnershipRow:
    parcel_id: int
    survey_number: str
    village: str
    extent: Decimal
    extent_unit: str
    share: Decimal
    interest_type: str


@dataclass(frozen=True)
class CitizenAwardRow:
    ownership_record_id: int
    total_amount: Decimal
    currency: str
    disbursement_state: str


@dataclass(frozen=True)
class CitizenNoticeRow:
    id: int
    notice_type: str
    service_date: date
    response_deadline: date


@dataclass(frozen=True)
class CitizenObjectionRow:
    id: int
    receipt_date: date
    disposal_state: str
    disposal_date: date | None


@dataclass(frozen=True)
class CitizenDocumentRow:
    id: int
    document_type: str
    uploaded_at: date
    byte_size: int


@dataclass(frozen=True)
class CitizenContentView:
    case: CitizenCaseStatus
    ownership_records: tuple[CitizenOwnershipRow, ...]
    awards: tuple[CitizenAwardRow, ...]
    notices: tuple[CitizenNoticeRow, ...]
    objections: tuple[CitizenObjectionRow, ...]
    documents: tuple[CitizenDocumentRow, ...]


def _plain_stage(stage_key: str) -> str:
    return stage_key.replace("_", " ").title()


def _remaining_days(deadline: date | None) -> int | None:
    if deadline is None:
        return None
    return (deadline - date.today()).days


def _statutory_period(case: AcquisitionCase) -> str:
    if case.stage_deadline is None:
        return "No configured deadline for the current stage"
    days = (case.stage_deadline - case.stage_entered_on).days
    return f"{days} days from stage entry"


def load_citizen_content(session: Session, principal: Principal) -> CitizenContentView:
    if principal.kind != "CITIZEN" or principal.case_id is None:
        raise ValueError("citizen content requires a citizen principal with a case")

    case, project = session.execute(
        select(AcquisitionCase, Project)
        .join(Project, Project.id == AcquisitionCase.project_id)
        .where(AcquisitionCase.id == principal.case_id)
    ).one()

    owner_ids = tuple(principal.owner_record_ids)
    ownership_rows: tuple[CitizenOwnershipRow, ...] = ()
    awards: tuple[CitizenAwardRow, ...] = ()
    notices: tuple[CitizenNoticeRow, ...] = ()
    objections: tuple[CitizenObjectionRow, ...] = ()
    documents: tuple[CitizenDocumentRow, ...] = ()

    if owner_ids:
        ownership_result = session.execute(
            select(OwnershipRecord, LandParcel)
            .join(LandParcel, LandParcel.id == OwnershipRecord.parcel_id)
            .where(
                OwnershipRecord.id.in_(owner_ids),
                OwnershipRecord.valid_to.is_(None),
            )
            .order_by(LandParcel.village, LandParcel.survey_number, OwnershipRecord.id)
        ).all()
        ownership_rows = tuple(
            CitizenOwnershipRow(
                parcel_id=parcel.id,
                survey_number=parcel.survey_number,
                village=parcel.village,
                extent=parcel.extent,
                extent_unit=parcel.extent_unit,
                share=record.share,
                interest_type=record.interest_type,
            )
            for record, parcel in ownership_result
        )
        owned_parcel_ids = tuple(row.parcel_id for row in ownership_rows)

        awards = tuple(
            CitizenAwardRow(
                ownership_record_id=award.ownership_record_id,
                total_amount=award.total_amount,
                currency=award.currency,
                disbursement_state=award.disbursement_state,
            )
            for award in session.execute(
                select(Award)
                .where(Award.ownership_record_id.in_(owner_ids))
                .order_by(Award.determination_date.desc(), Award.id.desc())
            ).scalars()
        )
        notices = tuple(
            CitizenNoticeRow(
                id=notice.id,
                notice_type=notice.notice_type,
                service_date=service.service_date,
                response_deadline=notice.response_deadline,
            )
            for notice, service in session.execute(
                select(StatutoryNotice, NoticeServiceRecord)
                .join(NoticeServiceRecord, NoticeServiceRecord.notice_id == StatutoryNotice.id)
                .where(
                    StatutoryNotice.case_id == principal.case_id,
                    NoticeServiceRecord.ownership_record_id.in_(owner_ids),
                )
                .order_by(*service_date_order())
            ).all()
        )
        objections = tuple(
            CitizenObjectionRow(
                id=objection.id,
                receipt_date=objection.receipt_date,
                disposal_state=objection.disposal_outcome or "PENDING",
                disposal_date=objection.disposal_date,
            )
            for objection in session.execute(
                select(Objection)
                .where(
                    Objection.case_id == principal.case_id,
                    Objection.ownership_record_id.in_(owner_ids),
                )
                .order_by(Objection.receipt_date.desc(), Objection.id.desc())
            ).scalars()
        )
        documents = tuple(
            CitizenDocumentRow(
                id=document.id,
                document_type=document.document_type,
                uploaded_at=document.uploaded_at.date(),
                byte_size=document.byte_size,
            )
            for document in session.execute(
                select(Document)
                .where(Document.parcel_id.in_(owned_parcel_ids))
                .order_by(Document.uploaded_at.desc())
            ).scalars()
        )

    return CitizenContentView(
        case=CitizenCaseStatus(
            case_reference=case.case_reference,
            project_name=project.name,
            stage=_plain_stage(case.stage_key),
            stage_entered_on=case.stage_entered_on,
            next_step="Await the next recorded case event",
            statutory_period=_statutory_period(case),
            remaining_days=_remaining_days(case.stage_deadline),
        ),
        ownership_records=ownership_rows,
        awards=awards,
        notices=notices,
        objections=objections,
        documents=documents,
    )


def service_date_order():
    return NoticeServiceRecord.service_date.desc(), NoticeServiceRecord.id.desc()
