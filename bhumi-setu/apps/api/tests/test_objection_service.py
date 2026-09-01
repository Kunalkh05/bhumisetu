"""Objection intake, disposal and overdue tests (task 11)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.models.acquisition_case import AcquisitionCase
from app.models.objection import Objection
from app.models.statutory_notice import StatutoryNotice
from app.services import objection as objection_service
from app.services.objection import (
    WINDOW_OUT_OF_WINDOW,
    WINDOW_WITHIN,
    DisposalMissingReasons,
    ObjectionDisposal,
    ObjectionIntake,
    ObjectionService,
    sweep_objection_overdue,
)


@dataclass(frozen=True)
class Actor:
    kind: str = "OFFICER"
    id: str = "officer-1"


class FakeResolver:
    def __init__(self, days: int) -> None:
        self.days = days

    def get(self, key, *, state, act, as_of):  # type: ignore[no-untyped-def]
        assert key == "period.objection.disposal"
        return self.days


class FakeSession:
    def __init__(
        self,
        *,
        case: AcquisitionCase | None = None,
        notice: StatutoryNotice | None = None,
        objection: Objection | None = None,
    ) -> None:
        self.case = case
        self.notice = notice
        self.objection = objection
        self.added: list[object] = []
        self.events: list[str] = []
        self.flushed = False

    def get(self, entity_type, entity_id, **kwargs):  # type: ignore[no-untyped-def]
        if entity_type is AcquisitionCase:
            return self.case
        if entity_type is StatutoryNotice:
            return self.notice
        if entity_type is Objection:
            return self.objection
        return None

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, Objection):
            value.id = 200 + len(self.added)

    def flush(self) -> None:
        self.flushed = True


def _case(count: int = 0) -> AcquisitionCase:
    return AcquisitionCase(
        id=10,
        case_reference="MH-10",
        project_id=1,
        state_key="MH",
        act_key="RFCTLARR_2013",
        area_code="MH.PN",
        stage_key="NOTICE",
        stage_set_effective_from=date(2024, 1, 1),
        stage_entered_on=date(2024, 2, 1),
        stage_deadline=None,
        deadline_breached=False,
        is_terminal=False,
        undisposed_objection_count=count,
        entity_version=1,
    )


def _notice(deadline: date) -> StatutoryNotice:
    return StatutoryNotice(
        id=5,
        case_id=10,
        notice_type="PRELIMINARY",
        issuing_authority="Collector",
        issue_date=date(2024, 2, 1),
        publication_mode="GAZETTE",
        response_deadline=deadline,
        policy_snapshot_hash="hash",
        breach_state="WITHIN",
        entity_version=1,
    )


def _objection(*, disposed: bool = False, overdue: bool = False) -> Objection:
    return Objection(
        id=9,
        case_id=10,
        objector_name="Asha",
        receipt_date=date(2024, 3, 1),
        grounds_category="extent",
        substance="Extent is wrong",
        window_state=WINDOW_WITHIN,
        disposal_deadline=date(2024, 3, 10),
        is_disposal_overdue=overdue,
        disposal_date=date(2024, 3, 5) if disposed else None,
        entity_version=4,
    )


def _patch_events(monkeypatch, session: FakeSession) -> None:
    def _append(session_arg, *, event_type, entity, actor, changes, occurrence_time, **kw):  # type: ignore[no-untyped-def]
        assert session_arg is session
        session.events.append(event_type)

    monkeypatch.setattr("app.services.objection.EventLog.append", _append)


def test_intake_sets_window_state_deadline_count_and_event(monkeypatch) -> None:
    case = _case(count=2)
    session = FakeSession(case=case, notice=_notice(date(2024, 3, 15)))
    _patch_events(monkeypatch, session)

    objection = ObjectionService(resolver=FakeResolver(20)).intake(
        session,  # type: ignore[arg-type]
        data=ObjectionIntake(
            case_id=10,
            objector_name="Asha",
            receipt_date=date(2024, 3, 10),
            grounds_category="extent",
            substance="Extent is wrong",
            governing_notice_id=5,
            disposal_period_key="period.objection.disposal",
        ),
        actor=Actor(),
    )

    assert objection.window_state == WINDOW_WITHIN
    assert objection.disposal_deadline == date(2024, 3, 30)
    assert case.undisposed_objection_count == 3
    assert session.events == ["OBJECTION_RECORDED"]


def test_intake_marks_out_of_window_after_notice_deadline(monkeypatch) -> None:
    session = FakeSession(case=_case(), notice=_notice(date(2024, 3, 15)))
    _patch_events(monkeypatch, session)

    objection = ObjectionService(resolver=FakeResolver(20)).intake(
        session,  # type: ignore[arg-type]
        data=ObjectionIntake(
            case_id=10,
            objector_name="Asha",
            receipt_date=date(2024, 3, 16),
            grounds_category="extent",
            substance="Extent is wrong",
            governing_notice_id=5,
            disposal_period_key="period.objection.disposal",
        ),
        actor=Actor(),
    )

    assert objection.window_state == WINDOW_OUT_OF_WINDOW


def test_disposal_requires_recorded_reasons() -> None:
    with pytest.raises(DisposalMissingReasons) as exc:
        ObjectionService(resolver=FakeResolver(1)).dispose(
            FakeSession(objection=_objection()),  # type: ignore[arg-type]
            objection_id=9,
            expected_version=4,
            data=ObjectionDisposal(
                outcome="accepted",
                disposal_date=date(2024, 3, 5),
                reasons=" ",
                deciding_officer_id=uuid.uuid4(),
            ),
            actor=Actor(),
        )

    assert exc.value.details == {"missing_fields": ["disposal_reasons"]}


def test_disposal_records_outcome_through_versioned_repository_and_decrements_count(
    monkeypatch,
) -> None:
    case = _case(count=1)
    objection = _objection()
    session = FakeSession(case=case, objection=objection)
    calls: list[dict] = []
    officer_id = uuid.uuid4()

    def _update(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        assert session_arg is session
        calls.append(kwargs)
        return objection

    monkeypatch.setattr("app.services.objection.VersionedRepository.update", _update)

    ObjectionService(resolver=FakeResolver(1)).dispose(
        session,  # type: ignore[arg-type]
        objection_id=9,
        expected_version=4,
        data=ObjectionDisposal(
            outcome="accepted",
            disposal_date=date(2024, 3, 5),
            reasons="Measurement corrected",
            deciding_officer_id=officer_id,
        ),
        actor=Actor(),
    )

    [call] = calls
    assert call["event_type"] == "OBJECTION_DISPOSED"
    assert call["changes"]["disposal_reasons"] == "Measurement corrected"
    assert call["changes"]["deciding_officer_id"] == officer_id
    assert case.undisposed_objection_count == 0


def test_sweep_marks_undisposed_overdue_once(monkeypatch) -> None:
    objection = _objection()
    session = FakeSession(objection=objection)
    _patch_events(monkeypatch, session)

    changed = sweep_objection_overdue(
        session,  # type: ignore[arg-type]
        today=date(2024, 3, 11),
        objections=[objection],
    )
    changed_again = sweep_objection_overdue(
        session,  # type: ignore[arg-type]
        today=date(2024, 3, 12),
        objections=[objection],
    )

    assert changed == 1
    assert changed_again == 0
    assert objection.is_disposal_overdue is True
    assert session.events == ["OBJECTION_DISPOSAL_OVERDUE"]


@given(
    notice_deadline=st.dates(min_value=date(2024, 1, 1), max_value=date(2024, 3, 1)),
    offset=st.integers(min_value=-10, max_value=10),
)
def test_property_window_state_follows_notice_response_deadline(
    notice_deadline: date,
    offset: int,
) -> None:
    receipt = notice_deadline.fromordinal(notice_deadline.toordinal() + offset)
    state = WINDOW_WITHIN if receipt <= notice_deadline else WINDOW_OUT_OF_WINDOW
    assert state == (WINDOW_WITHIN if offset <= 0 else WINDOW_OUT_OF_WINDOW)
