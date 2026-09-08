"""Erasure property tests (task 25.4)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from hypothesis import given, strategies as st

from app.db.event_log import _ResolvedDatum, _resolve_reference
from app.db.base import all_metadata
from app.retention.categories import PERSONAL_DATA_CATEGORIES
from app.retention.projection import _project_attribute, retention_period_key
from app.retention.sweep import ErasableAttributeTarget, due_for_erasure


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


_TARGETS = tuple(due_for_erasure())


@given(target=st.sampled_from(_TARGETS))
def test_property_every_generated_target_is_nullable_erasable_personal_data(
    target: ErasableAttributeTarget,
) -> None:
    table = all_metadata().tables[target.table_name]

    assert target.data_category in PERSONAL_DATA_CATEGORIES
    assert table.c[target.column_name].nullable


@given(
    target=st.sampled_from(_TARGETS),
    start=st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31),
        timezones=st.just(UTC),
    ),
    period_days=st.integers(min_value=0, max_value=3650),
)
def test_property_erasure_date_uses_period_effective_at_retention_start(
    target: ErasableAttributeTarget,
    start: datetime,
    period_days: int,
) -> None:
    session = _Session()
    resolver = _Resolver(period_days=period_days)

    projection = _project_attribute(
        session,
        ownership_record_id=11,
        attribute_name=target.column_name,
        data_category=target.data_category,
        retention_start=start,
        state_key="MH",
        act_key="RFCTLARR_2013",
        resolver=resolver,
    )

    assert resolver.calls == [
        (
            retention_period_key(target.data_category),
            "MH",
            "RFCTLARR_2013",
            start.date(),
        )
    ]
    assert projection.retention_start == start.date().isoformat()
    assert projection.withholding_reason is None


@given(target=st.sampled_from(_TARGETS))
def test_property_non_terminal_records_undetermined_start_and_erases_nothing(
    target: ErasableAttributeTarget,
) -> None:
    session = _Session()

    projection = _project_attribute(
        session,
        ownership_record_id=11,
        attribute_name=target.column_name,
        data_category=target.data_category,
        retention_start=None,
        state_key="MH",
        act_key="RFCTLARR_2013",
        resolver=_Resolver(period_days=1),
    )

    assert projection.erasure_date is None
    assert projection.withholding_reason == "RETENTION_START_UNDETERMINED"
    assert len(session.added) == 1
    assert session.added[0].reason == "RETENTION_START_UNDETERMINED"


@given(
    category=st.sampled_from(sorted(PERSONAL_DATA_CATEGORIES)),
    erased_at=st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31),
        timezones=st.just(UTC),
    ),
)
def test_property_erased_payload_returns_marker_without_the_erased_value(
    category: str,
    erased_at: datetime,
) -> None:
    resolved = _resolve_reference(
        7,
        {
            7: _ResolvedDatum(
                value_ciphertext=None,
                key_version=1,
                erased_at=erased_at,
                data_category=category,
            )
        },
    )

    assert resolved == {"$erased": {"data_category": category, "erased_at": erased_at}}
    assert "value" not in resolved["$erased"]
    assert "value_ciphertext" not in resolved["$erased"]
