from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.services.intervention import (
    CounterSnapshot,
    attach_recommended_actions,
    counter_discrepancies,
    load_intervention_queue,
    record_action_disposition,
    remaining_days,
)
from app.security.access import Principal


NOW = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)
TODAY = date(2026, 3, 1)


class _Result:
    def __init__(self, rows) -> None:
        self._rows = rows

    def scalars(self):  # type: ignore[no-untyped-def]
        return iter(self._rows)


class _Session:
    def __init__(self, rows=()) -> None:
        self.rows = rows
        self.added = []
        self.flushed = False

    def execute(self, statement):  # type: ignore[no-untyped-def]
        return _Result(self.rows)

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed = True


class _Resolver:
    def get(self, key: str, *, state: str, act: str | None, as_of: date):
        assert key == "intervention.action_rules"
        return {
            "version": "actions-v1",
            "rules": [
                {
                    "id": "resolve-blocking-issues",
                    "label_key": "action.resolve_blocking_issues",
                    "reason_key": "action.reason.blocking_issues",
                    "severity": "BLOCKING",
                    "when": {"open_blocking_count_gt": 0},
                },
                {
                    "id": "dispose-objections",
                    "label_key": "action.dispose_objections",
                    "reason_key": "action.reason.undisposed_objections",
                    "severity": "WARNING",
                    "when": {"undisposed_objection_count_gt": 0},
                },
                {
                    "id": "deadline-followup",
                    "label_key": "action.deadline_followup",
                    "reason_key": "action.reason.deadline_near",
                    "severity": "WARNING",
                    "when": {"deadline_within_days": 3, "risk_band_in": ["HIGH", "CRITICAL"]},
                },
            ],
        }


@dataclass
class _Case:
    id: int = 42
    case_reference: str = "MH-42"
    stage_key: str = "AWARD"
    state_key: str = "IN-MH"
    act_key: str = "RFCTLARR-2013"
    area_code: str = "D1"
    risk_band: str | None = "HIGH"
    priority_score: Decimal | None = Decimal("88.000")
    priority_computed_at: datetime | None = NOW
    stage_deadline: date | None = date(2026, 3, 3)
    deadline_breached: bool = False
    open_blocking_count: int = 1
    undisposed_objection_count: int = 0
    pending_review_count: int = 2
    aggregate_awarded: Decimal = Decimal("1000.00")
    aggregate_disbursed: Decimal = Decimal("250.00")
    is_terminal: bool = False
    entity_version: int = 5


def _officer() -> Principal:
    return Principal(kind="OFFICER", id="officer-1", scope_paths=("IN.MH.D1",))


def test_load_intervention_queue_attaches_actions_for_returned_page_only() -> None:
    case = _Case()
    older = _Case(
        id=43,
        case_reference="MH-43",
        priority_score=Decimal("80.000"),
        priority_computed_at=NOW.replace(hour=9),
        open_blocking_count=0,
        undisposed_objection_count=1,
    )
    page = load_intervention_queue(
        _Session((case, older)),
        principal=_officer(),
        resolver=_Resolver(),
        limit=50,
        offset=0,
        today=TODAY,
    )

    assert [item.case_reference for item in page.items] == ["MH-42", "MH-43"]
    assert page.oldest_priority_computed_at == NOW.replace(hour=9)
    assert page.items[0].remaining_days == 2
    assert [action.action_id for action in page.items[0].recommended_actions] == [
        "resolve-blocking-issues",
        "deadline-followup",
    ]
    assert [action.action_id for action in page.items[1].recommended_actions] == [
        "dispose-objections",
        "deadline-followup",
    ]


def test_attach_recommended_actions_uses_denormalized_fields() -> None:
    actions = attach_recommended_actions(
        [_Case(open_blocking_count=0, pending_review_count=0)],
        rules=[
            {
                "id": "review-fields",
                "label_key": "action.review_fields",
                "reason_key": "action.reason.pending_review",
                "when": {"pending_review_count_gt": 0},
            }
        ],
        today=TODAY,
    )

    assert actions[42] == ()


def test_record_action_disposition_retains_officer_decision_as_event() -> None:
    session = _Session()
    event = record_action_disposition(
        session,
        case=_Case(),
        principal=_officer(),
        action_id="deadline-followup",
        disposition="ACCEPTED",
        reason="calling field office",
        occurrence_time=NOW,
        expected_version=5,
    )

    assert event.event_type == "RECOMMENDED_ACTION_DISPOSITION_RECORDED"
    assert event.actor_id == "officer-1"
    assert event.payload == {
        "action_id": "deadline-followup",
        "disposition": "ACCEPTED",
        "reason": "calling field office",
    }
    assert session.added == [event]
    assert session.flushed


def test_record_action_disposition_refuses_non_officer_or_stale_case_version() -> None:
    with pytest.raises(PermissionError):
        record_action_disposition(
            _Session(),
            case=_Case(),
            principal=Principal(kind="CITIZEN", id="citizen", case_id=42),
            action_id="x",
            disposition="ACCEPTED",
            reason=None,
        )

    with pytest.raises(ValueError, match="version"):
        record_action_disposition(
            _Session(),
            case=_Case(entity_version=6),
            principal=_officer(),
            action_id="x",
            disposition="ACCEPTED",
            reason=None,
            expected_version=5,
        )


def test_counter_discrepancies_report_stored_and_actual_values() -> None:
    discrepancies = counter_discrepancies(
        _Case(open_blocking_count=2),
        CounterSnapshot(
            open_blocking_count=1,
            undisposed_objection_count=0,
            pending_review_count=2,
            aggregate_awarded=Decimal("1000.00"),
            aggregate_disbursed=Decimal("250.00"),
        ),
    )

    assert discrepancies == {"open_blocking_count": {"stored": 2, "actual": 1}}


def test_remaining_days_uses_current_stage_deadline() -> None:
    assert remaining_days(_Case(stage_deadline=date(2026, 3, 5)), TODAY) == 4
    assert remaining_days(_Case(stage_deadline=None), TODAY) is None
