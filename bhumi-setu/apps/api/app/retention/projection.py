"""Retention-start and erasure-date projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.acquisition_case import AcquisitionCase
from app.models.case_parcel import CaseParcel
from app.models.data_subject_request import RetentionWithholding
from app.models.ownership_record import OwnershipRecord
from app.retention.categories import CATEGORY_MAP, PERSONAL_DATA_CATEGORIES, category_of
from app.security.access import Principal, scoped
from app.services.policy import PolicyResolver

__all__ = [
    "RetentionAttributeProjection",
    "OwnershipRetentionProjection",
    "ownership_retention_projection",
    "retention_period_key",
]


@dataclass(frozen=True)
class RetentionAttributeProjection:
    attribute_name: str
    data_category: str
    retention_start: str | None
    erasure_date: str | None
    withholding_reason: str | None
    policy_key: str | None


@dataclass(frozen=True)
class OwnershipRetentionProjection:
    ownership_record_id: int
    case_id: int
    attributes: tuple[RetentionAttributeProjection, ...]


def ownership_retention_projection(
    session: Session,
    *,
    ownership_record_id: int,
    principal: Principal,
    resolver: PolicyResolver,
) -> OwnershipRetentionProjection:
    row = session.execute(
        scoped(
            select(
                OwnershipRecord.id.label("ownership_record_id"),
                AcquisitionCase.id.label("case_id"),
                AcquisitionCase.state_key,
                AcquisitionCase.act_key,
            )
            .join(CaseParcel, CaseParcel.parcel_id == OwnershipRecord.parcel_id)
            .join(AcquisitionCase, AcquisitionCase.id == CaseParcel.case_id)
            .where(OwnershipRecord.id == ownership_record_id),
            principal,
            area_col=AcquisitionCase.area_code,
            case_col=AcquisitionCase.id,
        ),
    ).mappings().one()
    retention_start = session.execute(
        text("SELECT retention_start FROM v_case_terminal WHERE case_id = :case_id"),
        {"case_id": row["case_id"]},
    ).scalar_one_or_none()

    attributes = tuple(
        _project_attribute(
            session,
            ownership_record_id=ownership_record_id,
            attribute_name=attribute_name,
            data_category=data_category,
            retention_start=retention_start,
            state_key=row["state_key"],
            act_key=row["act_key"],
            resolver=resolver,
        )
        for attribute_name, data_category in _ownership_personal_categories()
    )
    session.flush()
    return OwnershipRetentionProjection(
        ownership_record_id=int(row["ownership_record_id"]),
        case_id=int(row["case_id"]),
        attributes=attributes,
    )


def retention_period_key(data_category: str) -> str:
    return f"retention.period.{data_category}"


def _project_attribute(
    session: Session,
    *,
    ownership_record_id: int,
    attribute_name: str,
    data_category: str,
    retention_start,
    state_key: str,
    act_key: str | None,
    resolver: PolicyResolver,
) -> RetentionAttributeProjection:
    policy_key = retention_period_key(data_category)
    if retention_start is None:
        _record_withholding(
            session,
            ownership_record_id=ownership_record_id,
            attribute_name=attribute_name,
            data_category=data_category,
            reason="RETENTION_START_UNDETERMINED",
            retention_start=None,
            policy_key=policy_key,
        )
        return RetentionAttributeProjection(
            attribute_name=attribute_name,
            data_category=data_category,
            retention_start=None,
            erasure_date=None,
            withholding_reason="RETENTION_START_UNDETERMINED",
            policy_key=policy_key,
        )

    start_date = retention_start.date()
    period_days = resolver.try_get(
        policy_key,
        state=state_key,
        act=act_key,
        as_of=start_date,
    )
    if period_days is None:
        _record_withholding(
            session,
            ownership_record_id=ownership_record_id,
            attribute_name=attribute_name,
            data_category=data_category,
            reason="RETENTION_PERIOD_MISSING",
            retention_start=retention_start,
            policy_key=policy_key,
        )
        return RetentionAttributeProjection(
            attribute_name=attribute_name,
            data_category=data_category,
            retention_start=start_date.isoformat(),
            erasure_date=None,
            withholding_reason="RETENTION_PERIOD_MISSING",
            policy_key=policy_key,
        )

    erasure_date = start_date + timedelta(days=int(period_days))
    return RetentionAttributeProjection(
        attribute_name=attribute_name,
        data_category=data_category,
        retention_start=start_date.isoformat(),
        erasure_date=erasure_date.isoformat(),
        withholding_reason=None,
        policy_key=policy_key,
    )


def _ownership_personal_categories() -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for (table, column), _entry in CATEGORY_MAP.items():
        if table != OwnershipRecord.__tablename__:
            continue
        category = category_of(table, column, {})
        if category in PERSONAL_DATA_CATEGORIES:
            rows.append((column, category))
    return tuple(sorted(rows))


def _record_withholding(
    session: Session,
    *,
    ownership_record_id: int,
    attribute_name: str,
    data_category: str,
    reason: str,
    retention_start,
    policy_key: str,
) -> None:
    session.add(
        RetentionWithholding(
            entity_type=OwnershipRecord.__tablename__,
            entity_id=ownership_record_id,
            attribute_name=attribute_name,
            data_category=data_category,
            reason=reason,
            retention_start=retention_start,
            policy_key=policy_key,
        )
    )
