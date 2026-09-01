"""Case creation and stage transition service tests (task 8.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.models.acquisition_case import AcquisitionCase
from app.services import case as case_service
from app.services.case import (
    BlockingIssuesOpen,
    CaseCreate,
    CaseService,
    FirstStageParcelRequired,
)
from app.services.stage_graph import StageTransitionInvalid
from tests.strategies import st_stage_graph


@dataclass(frozen=True)
class Actor:
    kind: str = "OFFICER"
    id: str = "officer-1"


class FakeResolver:
    def get(self, key: str, *, state: str, act: str | None, as_of: date):  # type: ignore[no-untyped-def]
        if key == "policy.stage_set":
            return {
                "stages": [
                    {
                        "key": "SURVEY",
                        "successors": ["NOTICE"],
                        "period_key": "period.survey",
                    },
                    {
                        "key": "NOTICE",
                        "successors": ["AWARD"],
                        "period_key": "period.notice",
                    },
                    {
                        "key": "AWARD",
                        "successors": [],
                        "period_key": None,
                        "terminal": True,
                    },
                ]
            }
        if key == "period.survey":
            return 5
        if key == "period.notice":
            return 7
        raise AssertionError(f"unexpected policy key {key}")


class FakeSession:
    def __init__(self, case: AcquisitionCase | None = None) -> None:
        self.case = case
        self.added: list[object] = []
        self.flushed = False
        self.events: list[tuple[str, str]] = []

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, AcquisitionCase):
            value.id = 101

    def flush(self) -> None:
        self.flushed = True

    def get(self, entity_type, entity_id, **kwargs):  # type: ignore[no-untyped-def]
        return self.case


def _service() -> CaseService:
    return CaseService(resolver=FakeResolver(), reference_factory=lambda state: f"{state}-0001")  # type: ignore[arg-type]


def _case(*, stage: str = "SURVEY", blocking: int = 0) -> AcquisitionCase:
    item = AcquisitionCase(
        id=101,
        case_reference="MH-0001",
        project_id=11,
        state_key="MH",
        act_key="RFCTLARR_2013",
        area_code="MH.PN",
        stage_key=stage,
        stage_set_effective_from=date(2024, 1, 1),
        stage_entered_on=date(2024, 1, 2),
        stage_deadline=date(2024, 1, 7),
        open_blocking_count=blocking,
        deadline_breached=False,
        is_terminal=False,
        entity_version=3,
    )
    return item


def test_create_case_assigns_reference_first_stage_deadline_and_event(monkeypatch) -> None:
    session = FakeSession()

    def _append(session_arg, *, event_type, entity, actor, changes, occurrence_time, **kw):  # type: ignore[no-untyped-def]
        assert session_arg is session
        session.events.append((event_type, changes["stage_key"][1]))

    monkeypatch.setattr("app.services.case.EventLog.append", _append)

    created = _service().create(
        session,  # type: ignore[arg-type]
        data=CaseCreate(
            project_id=11,
            state_key="MH",
            act_key="RFCTLARR_2013",
            area_code="MH.PN",
            stage_set_effective_from=date(2024, 1, 1),
            stage_entered_on=date(2024, 1, 2),
        ),
        actor=Actor(),
    )

    assert created.case_reference == "MH-0001"
    assert created.stage_key == "SURVEY"
    assert created.stage_deadline == date(2024, 1, 7)
    assert session.flushed
    assert session.events == [("CASE_CREATED", "SURVEY")]


def test_transition_rejects_target_not_in_successor_set() -> None:
    with pytest.raises(StageTransitionInvalid) as exc:
        _service().transition(
            FakeSession(_case()),  # type: ignore[arg-type]
            case_id=101,
            expected_version=3,
            expected_stage="SURVEY",
            target_stage="AWARD",
            occurrence_date=date(2024, 1, 3),
            actor=Actor(),
        )

    assert exc.value.details["permitted_successors"] == ["NOTICE"]


def test_transition_rejects_open_blocking_issues() -> None:
    with pytest.raises(BlockingIssuesOpen) as exc:
        _service().transition(
            FakeSession(_case(blocking=2)),  # type: ignore[arg-type]
            case_id=101,
            expected_version=3,
            expected_stage="SURVEY",
            target_stage="NOTICE",
            occurrence_date=date(2024, 1, 3),
            actor=Actor(),
            blocking_issue_ids=(8, 9),
        )

    assert exc.value.details == {"issue_ids": [8, 9], "open_blocking_count": 2}


def test_transition_rejects_leaving_first_stage_without_a_parcel(monkeypatch) -> None:
    monkeypatch.setattr(case_service, "_case_has_parcel", lambda session, case_id: False)

    with pytest.raises(FirstStageParcelRequired):
        _service().transition(
            FakeSession(_case()),  # type: ignore[arg-type]
            case_id=101,
            expected_version=3,
            expected_stage="SURVEY",
            target_stage="NOTICE",
            occurrence_date=date(2024, 1, 3),
            actor=Actor(),
        )


def test_transition_uses_versioned_repository_with_stage_predicate(monkeypatch) -> None:
    session = FakeSession(_case())
    monkeypatch.setattr(case_service, "_case_has_parcel", lambda session, case_id: True)
    calls: list[dict] = []

    def _update(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        assert session_arg is session
        calls.append(kwargs)
        updated = _case(stage=kwargs["changes"]["stage_key"])
        updated.stage_deadline = kwargs["changes"]["stage_deadline"]
        return updated

    monkeypatch.setattr("app.services.case.VersionedRepository.update", _update)

    updated = _service().transition(
        session,  # type: ignore[arg-type]
        case_id=101,
        expected_version=3,
        expected_stage="SURVEY",
        target_stage="NOTICE",
        occurrence_date=date(2024, 1, 3),
        actor=Actor(),
    )

    [call] = calls
    assert call["expected_version"] == 3
    assert call["expected_stage"] == "SURVEY"
    assert call["event_type"] == "CASE_STAGE_TRANSITIONED"
    assert call["changes"]["stage_key"] == "NOTICE"
    assert call["changes"]["stage_deadline"] == date(2024, 1, 10)
    assert updated.stage_key == "NOTICE"


class GraphResolver:
    def __init__(self, graph: dict) -> None:
        self.graph = graph

    def get(self, key: str, *, state: str, act: str | None, as_of: date):  # type: ignore[no-untyped-def]
        if key == "policy.stage_set":
            return self.graph
        if key.startswith("period."):
            return 1
        raise AssertionError(f"unexpected policy key {key}")


@given(graph=st_stage_graph(min_stages=3), data=st.data())
def test_property_stage_transition_accepts_exactly_declared_successors(
    graph: dict,
    data: st.DataObject,
    monkeypatch,
) -> None:
    stages = graph["stages"]
    current_index = data.draw(st.integers(min_value=0, max_value=len(stages) - 2))
    current = stages[current_index]["key"]
    permitted = stages[current_index]["successors"]
    valid = data.draw(st.booleans())
    if valid:
        target = permitted[0]
    else:
        invalid_targets = [
            stage["key"]
            for stage in stages
            if stage["key"] != current and stage["key"] not in permitted
        ]
        target = data.draw(st.sampled_from(invalid_targets))

    monkeypatch.setattr(case_service, "_case_has_parcel", lambda session, case_id: True)
    monkeypatch.setattr(
        "app.services.case.VersionedRepository.update",
        lambda session, **kwargs: _case(stage=kwargs["changes"]["stage_key"]),
    )
    service = CaseService(resolver=GraphResolver(graph))  # type: ignore[arg-type]

    if valid:
        updated = service.transition(
            FakeSession(_case(stage=current)),  # type: ignore[arg-type]
            case_id=101,
            expected_version=3,
            expected_stage=current,
            target_stage=target,
            occurrence_date=date(2024, 1, 4),
            actor=Actor(),
        )
        assert updated.stage_key == target
    else:
        with pytest.raises(StageTransitionInvalid) as exc:
            service.transition(
                FakeSession(_case(stage=current)),  # type: ignore[arg-type]
                case_id=101,
                expected_version=3,
                expected_stage=current,
                target_stage=target,
                occurrence_date=date(2024, 1, 4),
                actor=Actor(),
            )
        assert exc.value.details["permitted_successors"] == permitted
