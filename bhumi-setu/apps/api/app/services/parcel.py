"""Land parcel and ownership write/read paths (tasks 9.2-9.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.db.versioned_repository import VersionedRepository
from app.errors import DomainError, ErrorCode
from app.models.land_parcel import LandParcel
from app.models.ownership_record import OwnershipRecord
from app.security.rate_limit import hmac_key

__all__ = [
    "DuplicateParcel",
    "OwnershipCreate",
    "ParcelCreate",
    "ParcelIdentity",
    "ParcelService",
    "ownership_as_of",
]


@dataclass(frozen=True)
class ParcelIdentity:
    state_key: str
    district: str
    tehsil: str
    village: str
    survey_number: str
    sub_division: str | None = None

    def as_details(self) -> dict[str, str | None]:
        return {
            "state_key": self.state_key,
            "district": self.district,
            "tehsil": self.tehsil,
            "village": self.village,
            "survey_number": self.survey_number,
            "sub_division": self.sub_division,
        }


@dataclass(frozen=True)
class ParcelCreate:
    identity: ParcelIdentity
    classification: str
    extent: Decimal
    extent_unit: str
    area_code: str
    geom: str | None = None


@dataclass(frozen=True)
class OwnershipCreate:
    parcel_id: int
    owner_name: str | None
    owner_identity_key: str | None
    government_identifier: str | None
    contact_mobile: str | None
    interest_type: str
    share: Decimal
    valid_from: date
    valid_to: date | None = None


class DuplicateParcel(DomainError):
    code = ErrorCode.DUPLICATE_PARCEL
    status_code = 409

    def __init__(self, *, matching_parcel_id: int, identity: ParcelIdentity) -> None:
        super().__init__(
            "A parcel with this cadastral identity already exists",
            details={
                "matching_parcel_id": matching_parcel_id,
                "identity": identity.as_details(),
            },
        )


def _occurrence_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


class ParcelService:
    def __init__(self, *, key_secret: bytes) -> None:
        self._secret = key_secret

    def create_parcel(
        self,
        session: Session,
        *,
        data: ParcelCreate,
        actor: Actor,
        occurrence_date: date,
    ) -> LandParcel:
        duplicate_id = _matching_parcel_id(session, data.identity)
        if duplicate_id is not None:
            raise DuplicateParcel(matching_parcel_id=duplicate_id, identity=data.identity)

        identity = data.identity
        parcel = LandParcel(
            state_key=identity.state_key,
            district=identity.district,
            tehsil=identity.tehsil,
            village=identity.village,
            survey_number=identity.survey_number,
            sub_division=identity.sub_division,
            classification=data.classification,
            extent=data.extent,
            extent_unit=data.extent_unit,
            area_code=data.area_code,
            geom=data.geom,
        )
        session.add(parcel)
        session.flush()
        EventLog.append(
            session,
            event_type="LAND_PARCEL_CREATED",
            entity=parcel,
            actor=actor,
            changes={key: (None, value) for key, value in identity.as_details().items()},
            occurrence_time=_occurrence_datetime(occurrence_date),
            entity_version_after=parcel.entity_version,
        )
        return parcel

    def create_ownership(
        self,
        session: Session,
        *,
        data: OwnershipCreate,
        actor: Actor,
        occurrence_date: date,
    ) -> OwnershipRecord:
        record = OwnershipRecord(
            parcel_id=data.parcel_id,
            owner_name=data.owner_name,
            owner_identity_key=data.owner_identity_key,
            government_identifier=data.government_identifier,
            contact_mobile=data.contact_mobile,
            contact_mobile_hash=_mobile_hash(self._secret, data.contact_mobile),
            interest_type=data.interest_type,
            share=data.share,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
        )
        session.add(record)
        session.flush()
        EventLog.append(
            session,
            event_type="OWNERSHIP_RECORDED",
            entity=record,
            actor=actor,
            changes={
                "owner_name": (None, data.owner_name),
                "interest_type": (None, data.interest_type),
                "share": (None, data.share),
                "valid_from": (None, data.valid_from),
                "valid_to": (None, data.valid_to),
                "contact_mobile": (None, data.contact_mobile),
            },
            occurrence_time=_occurrence_datetime(occurrence_date),
            entity_version_after=record.entity_version,
        )
        return record

    def supersede_ownership(
        self,
        session: Session,
        *,
        ownership_record_id: int,
        expected_version: int,
        valid_to: date,
        replacement: OwnershipCreate,
        actor: Actor,
        occurrence_date: date,
    ) -> OwnershipRecord:
        prior = session.get(OwnershipRecord, ownership_record_id, populate_existing=True)
        if prior is None:
            raise LookupError(f"ownership record {ownership_record_id} does not exist")
        VersionedRepository.update(
            session,
            entity_type=OwnershipRecord,
            entity_id=ownership_record_id,
            expected_version=expected_version,
            submitted_prior={"valid_to": prior.valid_to},
            changes={"valid_to": valid_to},
            actor=actor,
            occurrence_time=_occurrence_datetime(occurrence_date),
            event_type="OWNERSHIP_SUPERSEDED",
        )
        return self.create_ownership(
            session,
            data=replacement,
            actor=actor,
            occurrence_date=occurrence_date,
        )


def ownership_as_of(
    session: Session, *, parcel_id: int, on: date
) -> list[OwnershipRecord]:
    return list(
        session.execute(
            select(OwnershipRecord)
            .where(
                OwnershipRecord.parcel_id == parcel_id,
                OwnershipRecord.validity.op("@>")(on),
            )
            .order_by(OwnershipRecord.id)
        ).scalars()
    )


def _matching_parcel_id(session: Session, identity: ParcelIdentity) -> int | None:
    return session.execute(
        select(LandParcel.id).where(
            LandParcel.state_key == identity.state_key,
            LandParcel.district == identity.district,
            LandParcel.tehsil == identity.tehsil,
            LandParcel.village == identity.village,
            LandParcel.survey_number == identity.survey_number,
            LandParcel.sub_division.is_(None)
            if identity.sub_division is None
            else LandParcel.sub_division == identity.sub_division,
        )
    ).scalar_one_or_none()


def _mobile_hash(secret: bytes, mobile: str | None) -> bytes | None:
    if mobile is None:
        return None
    return bytes.fromhex(hmac_key(secret, mobile))
