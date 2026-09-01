"""Parcel and ownership service tests (tasks 9.2-9.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.models.land_parcel import LandParcel
from app.models.ownership_record import OwnershipRecord
from app.services import parcel as parcel_service
from app.services.parcel import (
    DuplicateParcel,
    OwnershipCreate,
    ParcelCreate,
    ParcelIdentity,
    ParcelService,
)


@dataclass(frozen=True)
class Actor:
    kind: str = "OFFICER"
    id: str = "officer-1"


class FakeSession:
    def __init__(self, ownership: OwnershipRecord | None = None) -> None:
        self.ownership = ownership
        self.added: list[object] = []
        self.flushed = False
        self.events: list[str] = []

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, (LandParcel, OwnershipRecord)):
            value.id = 100 + len(self.added)

    def flush(self) -> None:
        self.flushed = True

    def get(self, entity_type, entity_id, **kwargs):  # type: ignore[no-untyped-def]
        return self.ownership


SECRET = b"parcel-test-secret"


def _identity(sub_division: str | None = None) -> ParcelIdentity:
    return ParcelIdentity(
        state_key="MH",
        district="Pune",
        tehsil="Mulshi",
        village="Lavale",
        survey_number="12",
        sub_division=sub_division,
    )


def _patch_events(monkeypatch, session: FakeSession) -> None:
    def _append(session_arg, *, event_type, entity, actor, changes, occurrence_time, **kw):  # type: ignore[no-untyped-def]
        assert session_arg is session
        session.events.append(event_type)

    monkeypatch.setattr("app.services.parcel.EventLog.append", _append)


def test_create_parcel_rejects_duplicate_identity_with_matching_identifier(monkeypatch) -> None:
    monkeypatch.setattr(parcel_service, "_matching_parcel_id", lambda session, identity: 88)
    service = ParcelService(key_secret=SECRET)

    with pytest.raises(DuplicateParcel) as exc:
        service.create_parcel(
            FakeSession(),  # type: ignore[arg-type]
            data=ParcelCreate(
                identity=_identity(),
                classification="agricultural",
                extent=Decimal("1.25"),
                extent_unit="hectare",
                area_code="MH.PN",
            ),
            actor=Actor(),
            occurrence_date=date(2024, 2, 1),
        )

    assert exc.value.details["matching_parcel_id"] == 88
    assert exc.value.details["identity"]["survey_number"] == "12"


def test_create_parcel_records_event_when_identity_is_new(monkeypatch) -> None:
    session = FakeSession()
    _patch_events(monkeypatch, session)
    monkeypatch.setattr(parcel_service, "_matching_parcel_id", lambda session, identity: None)

    parcel = ParcelService(key_secret=SECRET).create_parcel(
        session,  # type: ignore[arg-type]
        data=ParcelCreate(
            identity=_identity("A"),
            classification="agricultural",
            extent=Decimal("1.25"),
            extent_unit="hectare",
            area_code="MH.PN",
        ),
        actor=Actor(),
        occurrence_date=date(2024, 2, 1),
    )

    assert parcel.sub_division == "A"
    assert session.flushed
    assert session.events == ["LAND_PARCEL_CREATED"]


def test_create_ownership_hashes_mobile_and_records_event(monkeypatch) -> None:
    session = FakeSession()
    _patch_events(monkeypatch, session)

    record = ParcelService(key_secret=SECRET).create_ownership(
        session,  # type: ignore[arg-type]
        data=OwnershipCreate(
            parcel_id=7,
            owner_name="Asha",
            owner_identity_key="asha",
            government_identifier="ID-1234",
            contact_mobile="+919000000000",
            interest_type="owner",
            share=Decimal("1.0"),
            valid_from=date(2024, 1, 1),
        ),
        actor=Actor(),
        occurrence_date=date(2024, 2, 1),
    )

    assert record.contact_mobile == "+919000000000"
    assert record.contact_mobile_hash is not None
    assert b"+919000000000" not in record.contact_mobile_hash
    assert session.events == ["OWNERSHIP_RECORDED"]


def test_supersede_sets_old_valid_to_through_versioned_repository_and_keeps_replacement(
    monkeypatch,
) -> None:
    prior = OwnershipRecord(
        id=5,
        parcel_id=7,
        owner_name="Asha",
        interest_type="owner",
        share=Decimal("1.0"),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        entity_version=2,
    )
    session = FakeSession(prior)
    _patch_events(monkeypatch, session)
    calls: list[dict] = []

    def _update(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        assert session_arg is session
        calls.append(kwargs)
        return prior

    monkeypatch.setattr("app.services.parcel.VersionedRepository.update", _update)

    replacement = ParcelService(key_secret=SECRET).supersede_ownership(
        session,  # type: ignore[arg-type]
        ownership_record_id=5,
        expected_version=2,
        valid_to=date(2024, 3, 1),
        replacement=OwnershipCreate(
            parcel_id=7,
            owner_name="Asha",
            owner_identity_key="asha",
            government_identifier=None,
            contact_mobile=None,
            interest_type="owner",
            share=Decimal("1.0"),
            valid_from=date(2024, 3, 2),
        ),
        actor=Actor(),
        occurrence_date=date(2024, 3, 2),
    )

    [call] = calls
    assert call["event_type"] == "OWNERSHIP_SUPERSEDED"
    assert call["changes"] == {"valid_to": date(2024, 3, 1)}
    assert replacement.valid_from == date(2024, 3, 2)
    assert session.events == ["OWNERSHIP_RECORDED"]


@given(
    start=st.dates(min_value=date(2024, 1, 1), max_value=date(2024, 1, 20)),
    duration=st.integers(min_value=0, max_value=20),
    offset=st.integers(min_value=-5, max_value=30),
)
def test_property_temporal_ownership_membership_matches_inclusive_bounds(
    start: date, duration: int, offset: int
) -> None:
    end = start.fromordinal(start.toordinal() + duration)
    queried = start.fromordinal(start.toordinal() + offset)
    expected = start <= queried <= end

    assert _inclusive_contains(start, end, queried) is expected
    assert _inclusive_contains(start, None, queried) is (queried >= start)


def _inclusive_contains(start: date, end: date | None, queried: date) -> bool:
    if queried < start:
        return False
    return end is None or queried <= end
