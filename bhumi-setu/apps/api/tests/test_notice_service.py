"""Statutory notice service and deadline sweep tests (task 10)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import MappingProxyType

from hypothesis import given
from hypothesis import strategies as st

from app.models.acquisition_case import AcquisitionCase
from app.models.notice_parcel import NoticeParcel
from app.models.notice_service_record import NoticeServiceRecord
from app.models.statutory_notice import StatutoryNotice
from app.services import notice as notice_service
from app.services.notice import (
    APPROACHING_BOUNDARIES,
    BREACH_STATE_WITHIN,
    NoticeIssue,
    NoticeService,
    ServiceRecordCreate,
    notice_response_deadline,
    sweep_deadlines,
)
from app.services.policy import PolicySnapshot


@dataclass(frozen=True)
class Actor:
    kind: str = "OFFICER"
    id: str = "officer-1"


class FakeResolver:
    def __init__(self, days: int) -> None:
        self.days = days

    def snapshot(self, keys, *, state, act, as_of):  # type: ignore[no-untyped-def]
        [key] = list(keys)
        return PolicySnapshot(
            values=MappingProxyType({key: self.days}),
            resolved_at=as_of,
            content_hash=f"hash:{key}:{self.days}:{as_of.isoformat()}",
        )


class FakeSession:
    def __init__(self, case: AcquisitionCase | None = None) -> None:
        self.case = case
        self.added: list[object] = []
        self.flushed = False
        self.events: list[tuple[str, int]] = []

    def get(self, entity_type, entity_id, **kwargs):  # type: ignore[no-untyped-def]
        if entity_type is AcquisitionCase:
            return self.case
        return None

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, (StatutoryNotice, NoticeServiceRecord)):
            value.id = 100 + len(self.added)

    def flush(self) -> None:
        self.flushed = True


def _case(stage_deadline: date | None = None) -> AcquisitionCase:
    return AcquisitionCase(
        id=44,
        case_reference="MH-44",
        project_id=1,
        state_key="MH",
        act_key="RFCTLARR_2013",
        area_code="MH.PN",
        stage_key="NOTICE",
        stage_set_effective_from=date(2024, 1, 1),
        stage_entered_on=date(2024, 2, 1),
        stage_deadline=stage_deadline,
        deadline_breached=False,
        is_terminal=False,
        entity_version=3,
    )


def _patch_events(monkeypatch, session: FakeSession) -> None:
    def _append(session_arg, *, event_type, entity, actor, changes, occurrence_time, **kw):  # type: ignore[no-untyped-def]
        assert session_arg is session
        session.events.append((event_type, entity.id))

    monkeypatch.setattr("app.services.notice.EventLog.append", _append)


def test_issue_notice_freezes_deadline_and_policy_snapshot(monkeypatch) -> None:
    session = FakeSession(_case())
    _patch_events(monkeypatch, session)

    notice = NoticeService(resolver=FakeResolver(21)).issue(
        session,  # type: ignore[arg-type]
        data=NoticeIssue(
            case_id=44,
            notice_type="PRELIMINARY",
            issuing_authority="Collector",
            issue_date=date(2024, 3, 1),
            publication_mode="GAZETTE",
            parcel_ids=(7, 8),
            response_period_key="notice.response.preliminary",
        ),
        actor=Actor(),
    )

    assert notice.response_deadline == date(2024, 3, 22)
    assert notice.policy_snapshot_hash == "hash:notice.response.preliminary:21:2024-03-01"
    assert notice.breach_state == BREACH_STATE_WITHIN
    assert [type(item) for item in session.added].count(NoticeParcel) == 2
    assert session.events == [("NOTICE_ISSUED", notice.id)]


def test_record_service_captures_recipient_mode_date_and_event(monkeypatch) -> None:
    session = FakeSession()
    _patch_events(monkeypatch, session)

    record = NoticeService(resolver=FakeResolver(1)).record_service(
        session,  # type: ignore[arg-type]
        data=ServiceRecordCreate(
            notice_id=5,
            ownership_record_id=9,
            service_date=date(2024, 4, 1),
            service_mode="IN_PERSON",
            service_location="SRID=4326;POINT(73.8 18.5)",
        ),
        actor=Actor(),
    )

    assert record.notice_id == 5
    assert record.ownership_record_id == 9
    assert record.service_date == date(2024, 4, 1)
    assert record.service_mode == "IN_PERSON"
    assert session.events == [("NOTICE_SERVICE_RECORDED", record.id)]


def test_sweep_appends_approaching_and_breach_events_once(monkeypatch) -> None:
    case = _case(stage_deadline=date(2024, 5, 10))
    session = FakeSession(case)
    _patch_events(monkeypatch, session)
    seen: set[tuple[str, int | None]] = set()

    def _has_deadline_event(session_arg, *, case_id, event_type, remaining_days=None):  # type: ignore[no-untyped-def]
        key = (event_type, remaining_days)
        if key in seen:
            return True
        seen.add(key)
        return False

    monkeypatch.setattr(notice_service, "_has_deadline_event", _has_deadline_event)

    changed = sweep_deadlines(
        session,  # type: ignore[arg-type]
        today=date(2024, 5, 10),
        cases=[case],
    )
    changed_again = sweep_deadlines(
        session,  # type: ignore[arg-type]
        today=date(2024, 5, 10),
        cases=[case],
    )

    assert changed == len(APPROACHING_BOUNDARIES) + 1
    assert changed_again == 0
    assert case.deadline_breached is True
    assert [event[0] for event in session.events] == [
        "DEADLINE_APPROACHING",
        "DEADLINE_APPROACHING",
        "DEADLINE_APPROACHING",
        "DEADLINE_BREACHED",
    ]


@given(
    issue=st.dates(min_value=date(2024, 1, 1), max_value=date(2024, 3, 1)),
    earlier_days=st.integers(min_value=1, max_value=30),
    later_days=st.integers(min_value=31, max_value=60),
)
def test_property_notice_deadline_freezes_against_issue_date_policy(
    issue: date, earlier_days: int, later_days: int
) -> None:
    first_deadline = notice_response_deadline(
        issue_date=issue,
        response_period_days=earlier_days,
    )
    changed_policy_deadline = notice_response_deadline(
        issue_date=issue,
        response_period_days=later_days,
    )

    assert first_deadline == issue.fromordinal(issue.toordinal() + earlier_days)
    assert changed_policy_deadline == issue.fromordinal(issue.toordinal() + later_days)
    assert first_deadline != changed_policy_deadline
