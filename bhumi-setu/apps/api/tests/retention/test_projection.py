"""Retention erasure-date projection tests (task 25.1)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.retention.categories import OWNER_CONTACT, OWNER_IDENTITY
from app.retention.projection import (
    _ownership_personal_categories,
    _project_attribute,
    retention_period_key,
)


class _Session:
    def __init__(self) -> None:
        self.added = []

    def add(self, obj) -> None:
        self.added.append(obj)


class _Resolver:
    def __init__(self, period_days=None) -> None:
        self.period_days = period_days
        self.calls = []

    def try_get(self, key: str, *, state: str, act: str | None, as_of: date):
        self.calls.append((key, state, act, as_of))
        return self.period_days


def test_ownership_projection_categories_follow_category_map() -> None:
    categories = dict(_ownership_personal_categories())

    assert categories["owner_name"] == OWNER_IDENTITY
    assert categories["government_identifier"] == OWNER_IDENTITY
    assert categories["contact_mobile"] == OWNER_CONTACT
    assert categories["contact_mobile_hash"] == OWNER_CONTACT


def test_erasure_date_uses_period_effective_at_retention_start() -> None:
    session = _Session()
    resolver = _Resolver(period_days=90)
    start = datetime(2026, 1, 15, 12, tzinfo=UTC)

    projection = _project_attribute(
        session,
        ownership_record_id=7,
        attribute_name="owner_name",
        data_category=OWNER_IDENTITY,
        retention_start=start,
        state_key="MH",
        act_key="RFCTLARR_2013",
        resolver=resolver,
    )

    assert resolver.calls == [
        ("retention.period.OWNER_IDENTITY", "MH", "RFCTLARR_2013", date(2026, 1, 15))
    ]
    assert projection.retention_start == "2026-01-15"
    assert projection.erasure_date == "2026-04-15"
    assert projection.withholding_reason is None
    assert session.added == []


def test_missing_retention_start_records_withholding() -> None:
    session = _Session()

    projection = _project_attribute(
        session,
        ownership_record_id=7,
        attribute_name="owner_name",
        data_category=OWNER_IDENTITY,
        retention_start=None,
        state_key="MH",
        act_key="RFCTLARR_2013",
        resolver=_Resolver(period_days=90),
    )

    assert projection.erasure_date is None
    assert projection.withholding_reason == "RETENTION_START_UNDETERMINED"
    assert session.added[0].reason == "RETENTION_START_UNDETERMINED"


def test_missing_retention_period_records_policy_withholding() -> None:
    session = _Session()
    start = datetime(2026, 1, 15, 12, tzinfo=UTC)

    projection = _project_attribute(
        session,
        ownership_record_id=7,
        attribute_name="owner_name",
        data_category=OWNER_IDENTITY,
        retention_start=start,
        state_key="MH",
        act_key="RFCTLARR_2013",
        resolver=_Resolver(period_days=None),
    )

    assert projection.erasure_date is None
    assert projection.withholding_reason == "RETENTION_PERIOD_MISSING"
    assert session.added[0].policy_key == retention_period_key(OWNER_IDENTITY)
