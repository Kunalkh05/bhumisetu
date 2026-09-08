"""Bulk import submission tests (task 26.1)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.import_batch import ImportBatch, ImportRow
from app.security.access import Principal
from app.services.import_service import ImportRowSubmission, submit_import_batch


class _Session:
    def __init__(self) -> None:
        self.added = []
        self.flushed = 0

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed += 1
        for index, obj in enumerate(self.added, start=1):
            if isinstance(obj, ImportBatch) and getattr(obj, "id", None) is None:
                obj.id = index


def _principal() -> Principal:
    return Principal(
        kind="OFFICER",
        id="officer-1",
        permissions=frozenset({"import.submit"}),
    )


def test_submit_import_batch_creates_batch_rows_and_event(monkeypatch) -> None:
    session = _Session()
    events = []

    def _append(session_arg, **kwargs):  # noqa: ANN001
        assert session_arg is session
        events.append(kwargs)
        return type("Event", (), {"id": 9, "import_batch_id": None})()

    monkeypatch.setattr("app.services.import_service.EventLog.append", _append)
    result = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_principal(),
        rows=(
            ImportRowSubmission(ordinal=2, entity_type="ownership_record", payload={"owner": "A"}),
            ImportRowSubmission(ordinal=1, entity_type="land_parcel", payload={"survey": "42"}),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    batch = session.added[0]
    rows = [obj for obj in session.added if isinstance(obj, ImportRow)]
    assert isinstance(batch, ImportBatch)
    assert batch.submitted_count == 2
    assert batch.state == "PENDING"
    assert result.batch_id == batch.id
    assert result.content_checksum == batch.content_checksum.hex()
    assert [row.ordinal for row in rows] == [1, 2]
    assert all(row.state == "PENDING" for row in rows)
    assert events[0]["event_type"] == "IMPORT_BATCH_CREATED"
    assert events[0]["actor"] == _principal()


def test_submit_import_batch_requires_import_permission() -> None:
    session = _Session()

    try:
        submit_import_batch(
            session,  # type: ignore[arg-type]
            principal=Principal(kind="OFFICER", id="officer-1"),
            rows=(),
        )
    except Exception as exc:
        assert exc.__class__.__name__ == "NotAuthorised"
    else:
        raise AssertionError("submit_import_batch accepted an officer without import.submit")

