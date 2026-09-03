"""DSAR access, correction, and disposal tests (task 25.5)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.data_subject_request import DataSubjectRequest
from app.models.ownership_record import OwnershipRecord
from app.retention.dsar import (
    CorrectionSubmission,
    dispose_correction_request,
    flag_overdue_requests,
    serve_my_data,
    submit_correction_request,
)
from app.security.access import Principal


class _Resolver:
    def get(self, key: str, *, state: str, act: str | None, as_of: date) -> int:
        assert key == "dsar.response_window_days"
        assert state == "*"
        assert act is None
        return 30


class _Session:
    def __init__(self, records=()) -> None:
        self.added = []
        self.flushed = 0
        self.records = tuple(records)

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed += 1
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                obj.id = index

    def execute(self, stmt):  # noqa: ANN001 - lightweight SQLAlchemy fake
        return _Result(self.records)


class _Result:
    def __init__(self, rows) -> None:
        self.rows = tuple(rows)

    def scalars(self):
        return iter(self.rows)


def _principal() -> Principal:
    return Principal(
        kind="CITIZEN",
        id="citizen:case-1",
        case_id=1,
        owner_record_ids=(7,),
    )


def _owner() -> OwnershipRecord:
    owner = OwnershipRecord(
        parcel_id=3,
        owner_name="Asha Patil",
        owner_identity_key="asha-patil",
        government_identifier="ABCDE12345",
        contact_mobile="9999999999",
        contact_mobile_hash=b"hash",
        interest_type="OWNER",
        share=Decimal("1"),
        valid_from=date(2024, 1, 1),
    )
    owner.id = 7
    return owner


def test_my_data_iterates_category_map_and_masks_government_identifier(monkeypatch) -> None:
    session = _Session([_owner()])
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    events = []

    def _append(session_arg, **kwargs):  # noqa: ANN001
        events.append(kwargs)
        return type("Event", (), {"id": 91})()

    monkeypatch.setattr("app.retention.dsar.EventLog.append", _append)

    response = serve_my_data(
        session,  # type: ignore[arg-type]
        principal=_principal(),
        resolver=_Resolver(),  # type: ignore[arg-type]
        now=now,
    )

    values = {item.attribute_name: item.value for item in response.attributes}
    assert values["owner_name"] == "Asha Patil"
    assert values["government_identifier"] == "\u2022" * 6 + "2345"
    assert values["contact_mobile"] == "9999999999"
    assert response.served_at == now
    assert session.added[0].request_type == "ACCESS"
    assert session.added[0].due_at == now + timedelta(days=30)
    assert session.added[0].completed_at == now
    assert session.added[0].created_event_id == 91
    assert events[0]["event_type"] == "DATA_ACCESS_REQUEST_SERVED"


def test_correction_records_request_without_mutating_owner(monkeypatch) -> None:
    owner = _owner()
    session = _Session()

    def _current_value(*args, **kwargs):  # noqa: ANN001
        return "Asha Patil", "RET"

    monkeypatch.setattr("app.retention.dsar._current_owner_value", _current_value)

    row = submit_correction_request(
        session,  # type: ignore[arg-type]
        principal=_principal(),
        data=CorrectionSubmission(
            ownership_record_id=7,
            target_attribute="owner_name",
            asserted_value="Asha P.",
        ),
        resolver=_Resolver(),  # type: ignore[arg-type]
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert owner.owner_name == "Asha Patil"
    assert row.request_type == "CORRECTION"
    assert row.current_value == "Asha Patil"
    assert row.asserted_value == "Asha P."
    assert row.routed_area_code == "RET"
    assert isinstance(session.added[0], DataSubjectRequest)


def test_disposal_records_completion_fields_and_event(monkeypatch) -> None:
    request = DataSubjectRequest(
        request_type="CORRECTION",
        subject_key="citizen",
        case_id=1,
        due_at=datetime(2026, 2, 1, tzinfo=UTC),
        received_at=datetime(2026, 1, 1, tzinfo=UTC),
        status="OPEN",
    )
    request.id = 4
    events = []

    class Session:
        def get(self, model, request_id, populate_existing=False):  # noqa: ANN001
            assert model is DataSubjectRequest
            assert request_id == 4
            return request

    def _append(session_arg, **kwargs):  # noqa: ANN001
        events.append(kwargs)
        return type("Event", (), {"id": 111})()

    monkeypatch.setattr("app.retention.dsar.EventLog.append", _append)
    monkeypatch.setattr("app.retention.dsar._request_visible_to_principal", lambda *a, **k: True)
    officer = Principal(
        kind="OFFICER",
        id="officer-1",
        permissions=frozenset({"dsar.dispose"}),
    )
    now = datetime(2026, 1, 5, tzinfo=UTC)

    result = dispose_correction_request(
        Session(),  # type: ignore[arg-type]
        principal=officer,
        request_id=4,
        outcome="ACCEPTED",
        reasons="Matches corrected record",
        now=now,
    )

    assert result.decided_at == now
    assert request.status == "COMPLETED"
    assert request.completed_at == now
    assert request.disposal_outcome == "ACCEPTED"
    assert request.disposal_reasons == "Matches corrected record"
    assert request.deciding_officer_id == "officer-1"
    assert request.disposed_event_id == 111
    assert events[0]["event_type"] == "CORRECTION_REQUEST_DISPOSED"


def test_flag_overdue_requests_marks_only_open_past_due() -> None:
    past = DataSubjectRequest(
        request_type="CORRECTION",
        subject_key="a",
        received_at=datetime(2026, 1, 1, tzinfo=UTC),
        due_at=datetime(2026, 1, 5, tzinfo=UTC),
        status="OPEN",
    )
    future = DataSubjectRequest(
        request_type="CORRECTION",
        subject_key="b",
        received_at=datetime(2026, 1, 1, tzinfo=UTC),
        due_at=datetime(2026, 2, 5, tzinfo=UTC),
        status="OPEN",
    )

    class Result:
        def scalars(self):
            return iter((past,))

    class Session:
        def execute(self, stmt):  # noqa: ANN001
            return Result()

    changed = flag_overdue_requests(
        Session(),  # type: ignore[arg-type]
        now=datetime(2026, 1, 10, tzinfo=UTC),
    )

    assert changed == 1
    assert past.status == "OVERDUE"
    assert future.status == "OPEN"


def test_citizen_package_imports_no_entity_mutation_paths() -> None:
    from pathlib import Path

    root = Path("app/citizen")
    forbidden = (
        "VersionedRepository",
        "app.db.versioned_repository",
        "app.services.case",
        "app.services.parcel",
        "app.services.compensation",
        "app.services.objection",
        "app.services.validation",
    )
    offences = []
    for path in root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for needle in forbidden:
            if needle in source:
                offences.append(f"{path}: {needle}")

    assert not offences, "citizen code can reach entity mutation paths: " + "; ".join(offences)
