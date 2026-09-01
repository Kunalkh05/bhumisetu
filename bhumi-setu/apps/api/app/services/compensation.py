"""Award and payout tracking (task 12)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.db.versioned_repository import VersionedRepository
from app.errors import DomainError, ErrorCode
from app.models.acquisition_case import AcquisitionCase
from app.models.award import Award, AwardComponent
from app.models.case_parcel import CaseParcel
from app.models.ownership_record import OwnershipRecord
from app.models.payout import Payout

__all__ = [
    "AwardComponentInput",
    "AwardInput",
    "AwardTotalMismatch",
    "CompensationService",
    "DISBURSEMENT_FULLY_PAID",
    "DISBURSEMENT_PART_PAID",
    "DISBURSEMENT_UNPAID",
    "PayoutExceedsAward",
    "PayoutInput",
    "component_total_matches",
    "disbursement_state_for",
]

MONEY_TOLERANCE = Decimal("0.01")
DISBURSEMENT_UNPAID = "UNPAID"
DISBURSEMENT_PART_PAID = "PART_PAID"
DISBURSEMENT_FULLY_PAID = "FULLY_PAID"


@dataclass(frozen=True)
class AwardComponentInput:
    label: str
    amount: Decimal


@dataclass(frozen=True)
class AwardInput:
    ownership_record_id: int
    total_amount: Decimal
    currency: str
    determination_date: date
    determining_authority: str
    components: tuple[AwardComponentInput, ...]


@dataclass(frozen=True)
class PayoutInput:
    award_id: int
    amount: Decimal
    payout_date: date
    instrument_reference: str
    beneficiary: str


class AwardTotalMismatch(DomainError):
    code = ErrorCode.VALIDATION_FAILED
    status_code = 422

    def __init__(self, *, total: Decimal, component_total: Decimal) -> None:
        super().__init__(
            "Award total does not match itemised components",
            details={
                "field": "total_amount",
                "total_amount": str(total),
                "component_total": str(component_total),
                "tolerance": str(MONEY_TOLERANCE),
            },
        )


class PayoutExceedsAward(DomainError):
    code = ErrorCode.PAYOUT_EXCEEDS_AWARD
    status_code = 409

    def __init__(self, *, remaining: Decimal) -> None:
        super().__init__(
            "Payout exceeds remaining award amount",
            details={"remaining_disbursable_amount": str(remaining)},
        )


def component_total_matches(total: Decimal, components: Iterable[AwardComponentInput]) -> bool:
    component_total = sum((item.amount for item in components), Decimal("0.00"))
    return abs(total - component_total) <= MONEY_TOLERANCE


def disbursement_state_for(*, total: Decimal, paid: Decimal) -> str:
    if paid <= Decimal("0.00"):
        return DISBURSEMENT_UNPAID
    if paid >= total:
        return DISBURSEMENT_FULLY_PAID
    return DISBURSEMENT_PART_PAID


def _occurrence_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


class CompensationService:
    def record_award(
        self,
        session: Session,
        *,
        data: AwardInput,
        actor: Actor,
    ) -> Award:
        component_total = sum((item.amount for item in data.components), Decimal("0.00"))
        if not component_total_matches(data.total_amount, data.components):
            raise AwardTotalMismatch(total=data.total_amount, component_total=component_total)

        award = Award(
            ownership_record_id=data.ownership_record_id,
            total_amount=data.total_amount,
            currency=data.currency,
            determination_date=data.determination_date,
            determining_authority=data.determining_authority,
            disbursement_state=DISBURSEMENT_UNPAID,
        )
        session.add(award)
        session.flush()
        for component in data.components:
            session.add(
                AwardComponent(
                    award_id=award.id,
                    component_label=component.label,
                    amount=component.amount,
                )
            )
        case = _case_for_ownership(session, data.ownership_record_id)
        if case is not None:
            case.aggregate_awarded = (case.aggregate_awarded or Decimal("0.00")) + data.total_amount
        EventLog.append(
            session,
            event_type="AWARD_RECORDED",
            entity=award,
            actor=actor,
            changes={
                "ownership_record_id": (None, data.ownership_record_id),
                "total_amount": (None, data.total_amount),
                "currency": (None, data.currency),
                "determination_date": (None, data.determination_date),
                "determining_authority": (None, data.determining_authority),
            },
            occurrence_time=_occurrence_datetime(data.determination_date),
            entity_version_after=award.entity_version,
        )
        return award

    def record_payout(
        self,
        session: Session,
        *,
        data: PayoutInput,
        actor: Actor,
    ) -> Payout:
        award = session.get(Award, data.award_id, populate_existing=True)
        if award is None:
            raise LookupError(f"award {data.award_id} does not exist")
        paid_before = _paid_total(session, award_id=data.award_id)
        remaining = award.total_amount - paid_before
        if data.amount > remaining:
            raise PayoutExceedsAward(remaining=remaining)

        payout = Payout(
            award_id=data.award_id,
            amount=data.amount,
            payout_date=data.payout_date,
            instrument_reference=data.instrument_reference,
            beneficiary=data.beneficiary,
        )
        session.add(payout)
        session.flush()

        paid_after = paid_before + data.amount
        state = disbursement_state_for(total=award.total_amount, paid=paid_after)
        if state != award.disbursement_state:
            VersionedRepository.update(
                session,
                entity_type=Award,
                entity_id=award.id,
                expected_version=award.entity_version,
                submitted_prior={"disbursement_state": award.disbursement_state},
                changes={"disbursement_state": state},
                actor=actor,
                occurrence_time=_occurrence_datetime(data.payout_date),
                event_type="AWARD_DISBURSEMENT_STATE_UPDATED",
            )
        case = _case_for_ownership(session, award.ownership_record_id)
        if case is not None:
            case.aggregate_disbursed = (case.aggregate_disbursed or Decimal("0.00")) + data.amount
        EventLog.append(
            session,
            event_type="PAYOUT_RECORDED",
            entity=payout,
            actor=actor,
            changes={
                "award_id": (None, data.award_id),
                "amount": (None, data.amount),
                "payout_date": (None, data.payout_date),
                "instrument_reference": (None, data.instrument_reference),
                "beneficiary": (None, data.beneficiary),
            },
            occurrence_time=_occurrence_datetime(data.payout_date),
            entity_version_after=payout.entity_version,
        )
        return payout


def _paid_total(session: Session, *, award_id: int) -> Decimal:
    return session.execute(
        select(func.coalesce(func.sum(Payout.amount), Decimal("0.00"))).where(
            Payout.award_id == award_id
        )
    ).scalar_one()


def _case_for_ownership(session: Session, ownership_record_id: int) -> AcquisitionCase | None:
    return session.execute(
        select(AcquisitionCase)
        .join(CaseParcel, CaseParcel.case_id == AcquisitionCase.id)
        .join(OwnershipRecord, OwnershipRecord.parcel_id == CaseParcel.parcel_id)
        .where(OwnershipRecord.id == ownership_record_id)
    ).scalar_one_or_none()
