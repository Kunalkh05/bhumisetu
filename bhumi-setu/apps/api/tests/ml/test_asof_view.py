"""AsOfView replay tests (task 22.2)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from app.models.event import Event
from features.asof import build_as_of_view  # noqa: E402

NOW = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)


class _Result:
    def __init__(self, rows: tuple[Event, ...]) -> None:
        self._rows = rows

    def scalars(self) -> tuple[Event, ...]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: tuple[Event, ...], *, as_of: datetime) -> None:
        self.rows = rows
        self.as_of = as_of
        self.statements: list[str] = []

    def execute(self, statement) -> _Result:  # type: ignore[no-untyped-def]
        rendered = str(statement)
        self.statements.append(rendered)
        rows = [
            row
            for row in self.rows
            if row.case_id == 77 and row.occurrence_time <= self.as_of
        ]
        if "recording_time <=" in rendered:
            rows = [row for row in rows if row.recording_time <= self.as_of]
        return _Result(tuple(sorted(rows, key=lambda row: (row.occurrence_time, row.id))))


def _event(
    *,
    event_id: int,
    event_type: str,
    entity_type: str,
    entity_id: int,
    case_id: int = 77,
    occurrence_time: datetime = NOW,
    recording_time: datetime = NOW,
    payload: dict | None = None,
) -> Event:
    return Event(
        id=event_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        case_id=case_id,
        actor_type="SYSTEM",
        actor_id="ml-test",
        occurrence_time=occurrence_time,
        recording_time=recording_time,
        payload=payload or {},
        has_pd_refs=False,
    )


def test_build_as_of_view_filters_knowable_at_in_sql() -> None:
    on_time = _event(
        event_id=1,
        event_type="STAGE_ENTERED",
        entity_type="acquisition_case",
        entity_id=77,
        occurrence_time=NOW - timedelta(days=4),
        recording_time=NOW - timedelta(days=3),
        payload={"stage_key": {"to": "intake"}},
    )
    late_recorded = _event(
        event_id=2,
        event_type="OBJECTION_RECEIVED",
        entity_type="objection",
        entity_id=88,
        occurrence_time=NOW - timedelta(days=2),
        recording_time=NOW + timedelta(days=5),
        payload={"disposal_state": {"to": "PENDING"}},
    )
    session = _FakeSession((on_time, late_recorded), as_of=NOW)
    occurred = build_as_of_view(session, 77, NOW, "OCCURRED_BY")
    knowable = build_as_of_view(session, 77, NOW, "KNOWABLE_AT")

    assert on_time.id in occurred.consumed_event_ids
    assert late_recorded.id in occurred.consumed_event_ids
    assert on_time.id in knowable.consumed_event_ids
    assert late_recorded.id not in knowable.consumed_event_ids
    assert "recording_time <=" not in session.statements[0]
    assert "recording_time <=" in session.statements[1]


def test_build_as_of_view_orders_by_occurrence_time_then_id() -> None:
    later_inserted = _event(
        event_id=1,
        event_type="STAGE_ENTERED",
        entity_type="acquisition_case",
        entity_id=77,
        occurrence_time=NOW - timedelta(days=1),
        recording_time=NOW,
        payload={"stage_key": {"to": "award_draft"}},
    )
    earlier_backdated = _event(
        event_id=2,
        event_type="STAGE_ENTERED",
        entity_type="acquisition_case",
        entity_id=77,
        occurrence_time=NOW - timedelta(days=3),
        recording_time=NOW + timedelta(hours=1),
        payload={"stage_key": {"to": "preliminary_notice"}},
    )
    session = _FakeSession((later_inserted, earlier_backdated), as_of=NOW + timedelta(days=1))
    view = build_as_of_view(session, 77, NOW + timedelta(days=1), "OCCURRED_BY")

    assert view.consumed_event_ids == (earlier_backdated.id, later_inserted.id)
    assert [stage.stage_key for stage in view.stage_history] == [
        "preliminary_notice",
        "award_draft",
    ]


def test_fold_groups_case_domain_entities() -> None:
    session = _FakeSession(
        (
            _event(
                event_id=1,
                event_type="NOTICE_SERVED",
                entity_type="statutory_notice",
                entity_id=1,
                payload={"notice_type": {"to": "award_notice"}},
            ),
            _event(event_id=2, event_type="PARCEL_LINKED", entity_type="land_parcel", entity_id=2),
            _event(event_id=3, event_type="AWARD_RECORDED", entity_type="award", entity_id=3),
            _event(event_id=4, event_type="ISSUE_OPENED", entity_type="validation_issue", entity_id=4),
            _event(event_id=5, event_type="DOCUMENT_UPLOADED", entity_type="document", entity_id=5),
        ),
        as_of=NOW + timedelta(days=1),
    )

    view = build_as_of_view(session, 77, NOW + timedelta(days=1), "KNOWABLE_AT")

    assert [row.notice_id for row in view.notices] == [1]
    assert [row.parcel_id for row in view.parcels] == [2]
    assert [row.award_id for row in view.awards] == [3]
    assert [row.issue_id for row in view.issues] == [4]
    assert [row.document_id for row in view.documents] == [5]
