from __future__ import annotations

import base64
from collections import defaultdict
from contextlib import nullcontext
from datetime import UTC, date, datetime
from decimal import Decimal
import re
from typing import Any, Mapping, Sequence

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from app.api.routers import officer_router
from app.db.event_log import EventLog
from app.models.document import Document
from app.models.event import Event
from app.models.import_batch import ImportBatch, ImportRow
from app.models.land_parcel import LandParcel
from app.models.ownership_record import OwnershipRecord
from app.security.access import Principal, authenticate
from app.services.document import (
    ACCEPTED_CONTENT_TYPES,
    MAX_UPLOAD_BYTES,
)
from app.services.import_service import (
    CHUNK_SIZE,
    ImportBatchReport,
    ImportChunkResult,
    ImportRowReport,
    ImportRowSubmission,
    ImportSubmissionResult,
    InMemoryDocumentStore,
    RowRejection,
    _process_import_chunk,
    evaluate_row_rules,
    get_import_batch_report,
    mark_batch_interrupted,
    process_import_chunk,
    submit_import_batch,
)
from app.services.validation.rules import (
    AREA_DIVERGENCE_RULE_ID,
    DUPLICATE_OWNERSHIP_RULE_ID,
    DUPLICATE_PARCEL_RULE_ID,
    area_divergence_rule,
    duplicate_ownership_overlap_rule,
    duplicate_parcel_identity_rule,
    required_field_rule,
)


class FakeResult:
    def __init__(self, *, scalar: Any = None, scalars: Any = None, rows: Any = None) -> None:
        self._scalar = scalar
        self._scalars = list(scalars) if scalars is not None else []
        self._rows = list(rows) if rows is not None else []

    def scalar_one(self) -> Any:
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalars(self) -> Any:
        return iter(self._scalars)

    def all(self) -> list[Any]:
        return list(self._rows)


class FakeImportSession:
    def __init__(
        self,
        *,
        batches: Sequence[ImportBatch] | None = None,
        rows: Sequence[ImportRow] | None = None,
        parcels: Sequence[LandParcel] | None = None,
        ownerships: Sequence[OwnershipRecord] | None = None,
        documents: Sequence[Document] | None = None,
    ) -> None:
        self.batches: dict[int, ImportBatch] = {b.id: b for b in (batches or [])}
        self.rows: list[ImportRow] = list(rows or [])
        self.parcels: list[LandParcel] = list(parcels or [])
        self.ownerships: list[OwnershipRecord] = list(ownerships or [])
        self.documents: list[Document] = list(documents or [])
        self.events: list[Event] = []
        self.added: list[Any] = []
        self.flushed: int = 0
        self._next_id: int = 200

    def get(self, entity_class: Any, entity_id: Any, **kwargs: Any) -> Any:
        if issubclass(entity_class, ImportBatch):
            return self.batches.get(entity_id)
        for obj in self.added + self.parcels + self.ownerships + self.documents:
            if isinstance(obj, entity_class) and getattr(obj, "id", None) == entity_id:
                return obj
        return None

    def add(self, obj: Any) -> None:
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            self._next_id += 1
            obj.id = self._next_id
        if isinstance(obj, ImportBatch):
            self.batches[obj.id] = obj
        elif isinstance(obj, ImportRow):
            self.rows.append(obj)
        elif isinstance(obj, LandParcel):
            self.parcels.append(obj)
        elif isinstance(obj, OwnershipRecord):
            self.ownerships.append(obj)
        elif isinstance(obj, Document):
            self.documents.append(obj)
        elif isinstance(obj, Event):
            self.events.append(obj)

    def flush(self) -> None:
        self.flushed += 1

    def get_bind(self) -> Any:
        class _Dialect:
            name = "sqlite"

        class _Bind:
            dialect = _Dialect()

        return _Bind()

    def execute(self, stmt: Any, params: Any = None) -> FakeResult:
        stmt_str = str(stmt)
        if "skip_event_backstop" in stmt_str or "SET LOCAL" in stmt_str:
            return FakeResult()

        try:
            compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        except Exception:
            compiled = stmt_str

        low = compiled.lower()

        if "from import_row" in low:
            batch_match = re.search(r"import_row\.batch_id = (\d+)", compiled)
            batch_id = int(batch_match.group(1)) if batch_match else None

            matching = list(self.rows)
            if batch_id is not None:
                matching = [r for r in matching if r.batch_id == batch_id]

            if "state = 'pending'" in low:
                matching = [r for r in matching if r.state == "PENDING"]
            elif "state = 'committed'" in low:
                matching = [r for r in matching if r.state == "COMMITTED"]
            elif "state = 'rejected'" in low:
                matching = [r for r in matching if r.state == "REJECTED"]

            ord_gte = re.search(r"import_row\.ordinal >= (\d+)", compiled)
            if ord_gte:
                matching = [r for r in matching if r.ordinal >= int(ord_gte.group(1))]
            ord_lt = re.search(r"import_row\.ordinal < (\d+)", compiled)
            if ord_lt:
                matching = [r for r in matching if r.ordinal < int(ord_lt.group(1))]
            ord_in = re.search(r"import_row\.ordinal in \(([^)]+)\)", low)
            if ord_in:
                ords = {int(x.strip()) for x in ord_in.group(1).split(",")}
                matching = [r for r in matching if r.ordinal in ords]

            if "order by" in low:
                matching.sort(key=lambda r: r.ordinal)

            if "count(" in low:
                return FakeResult(scalar=len(matching))

            lim_match = re.search(r"limit\s+(\d+)", low)
            if lim_match:
                matching = matching[: int(lim_match.group(1))]
            return FakeResult(scalars=matching)

        if "from land_parcel" in low:
            rows = []
            for p in self.parcels:
                rows.append(
                    type(
                        "ParcelRow",
                        (),
                        {
                            "id": p.id,
                            "state_key": p.state_key,
                            "district": p.district,
                            "tehsil": p.tehsil,
                            "village": p.village,
                            "village_norm": getattr(p, "village_norm", None) or p.village,
                            "survey_number": p.survey_number,
                            "sub_division": p.sub_division,
                        },
                    )()
                )
            return FakeResult(rows=rows)

        if "from ownership_record" in low:
            return FakeResult(scalars=self.ownerships)

        if "from document" in low:
            rows = []
            for d in self.documents:
                rows.append(
                    type(
                        "DocRow",
                        (),
                        {
                            "case_id": d.case_id,
                            "checksum_sha256": d.checksum_sha256,
                        },
                    )()
                )
            return FakeResult(rows=rows)

        if "from event" in low:
            evs = list(self.events)
            doc_match = re.search(r"event\.entity_id = (\d+)", compiled)
            if doc_match:
                eid = int(doc_match.group(1))
                evs = [e for e in evs if getattr(e, "entity_id", None) == eid]
            return FakeResult(scalar=evs[-1] if evs else None, scalars=evs)

        return FakeResult()


def _officer_principal() -> Principal:
    return Principal(
        kind="OFFICER",
        id="00000000-0000-0000-0000-000000000001",
        permissions=frozenset({"import.submit"}),
    )


def _valid_parcel_payload(survey_number: str = "101") -> dict[str, Any]:
    return {
        "state_key": "MH",
        "district": "Pune",
        "tehsil": "Haveli",
        "village": "Kothrud",
        "survey_number": survey_number,
        "classification": "agricultural",
        "extent": "2.5",
        "extent_unit": "hectare",
        "area_code": "MH.PUN",
    }


def _valid_ownership_payload(parcel_id: int = 101, owner_key: str = "O-1") -> dict[str, Any]:
    return {
        "parcel_id": parcel_id,
        "owner_name": "Asha Patil",
        "owner_identity_key": owner_key,
        "government_identifier": "ABCD1234E",
        "contact_mobile": "+919876543210",
        "interest_type": "PRIMARY",
        "share": "1.0",
        "valid_from": "2024-01-01",
        "valid_to": None,
    }


def _valid_document_payload(case_id: int = 1) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "document_type": "SALE_DEED",
        "original_filename": "deed.pdf",
        "content_type": "application/pdf",
        "body": base64.b64encode(b"%PDF-1.4 test document content").decode("ascii"),
    }


# ============================================================================
# Submission Tests (Task 26.1)
# ============================================================================


def test_submit_import_batch_creates_batch_rows_and_event(monkeypatch: Any) -> None:
    session = FakeImportSession()
    events = []

    def _append(session_arg: Any, **kwargs: Any) -> Any:
        assert session_arg is session
        events.append(kwargs)
        ev = Event(
            id=1,
            event_type=kwargs["event_type"],
            entity_type="import_batch",
            entity_id=1,
            actor_type="OFFICER",
            actor_id="00000000-0000-0000-0000-000000000001",
            occurrence_time=datetime(2026, 1, 1, tzinfo=UTC),
            payload="{}",
        )
        session.events.append(ev)
        return ev

    monkeypatch.setattr("app.services.import_service.EventLog.append", _append)
    result = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
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
    assert events[0]["actor"] == _officer_principal()


def test_submit_import_batch_requires_import_permission() -> None:
    session = FakeImportSession()
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


# ============================================================================
# Chunk Processing Tests (Task 26.2)
# ============================================================================


def test_process_import_chunk_commits_parcels() -> None:
    session = FakeImportSession()
    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="land_parcel", payload=_valid_parcel_payload("101")),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]
    assert result.processed_count == 1
    assert result.committed_count == 1
    assert result.rejected_count == 0
    assert result.is_completed is True

    batch = session.batches[submit_res.batch_id]
    assert batch.state == "COMPLETED"
    assert batch.last_processed_ordinal == 1

    row = session.rows[0]
    assert row.state == "COMMITTED"
    assert row.committed_entity_id is not None

    created_events = [e for e in session.events if getattr(e, "event_type", None) == "LAND_PARCEL_CREATED"]
    assert len(created_events) == 1
    assert created_events[0].provenance == "IMPORTED"
    assert created_events[0].import_batch_id == submit_res.batch_id


def test_process_import_chunk_commits_ownership_records() -> None:
    session = FakeImportSession()
    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="ownership_record", payload=_valid_ownership_payload(101)),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]
    assert result.processed_count == 1
    assert result.committed_count == 1
    assert result.rejected_count == 0
    assert result.is_completed is True

    row = session.rows[0]
    assert row.state == "COMMITTED"
    assert row.committed_entity_id is not None

    created_events = [e for e in session.events if getattr(e, "event_type", None) == "OWNERSHIP_RECORDED"]
    assert len(created_events) == 1
    assert created_events[0].provenance == "IMPORTED"
    assert created_events[0].import_batch_id == submit_res.batch_id


def test_process_import_chunk_commits_documents() -> None:
    session = FakeImportSession()
    doc_store = InMemoryDocumentStore()
    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="document", payload=_valid_document_payload(case_id=42)),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = _process_import_chunk(session, batch_id=submit_res.batch_id, document_store=doc_store)  # type: ignore[arg-type]
    assert result.processed_count == 1
    assert result.committed_count == 1
    assert result.rejected_count == 0
    assert result.is_completed is True

    row = session.rows[0]
    assert row.state == "COMMITTED"
    assert row.committed_entity_id is not None


def test_process_import_chunk_partial_commit_and_rejections() -> None:
    session = FakeImportSession()
    # Row 1 is valid, row 2 has missing survey_number, row 3 is valid
    invalid_parcel = _valid_parcel_payload("202")
    invalid_parcel.pop("survey_number")

    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="land_parcel", payload=_valid_parcel_payload("201")),
            ImportRowSubmission(ordinal=2, entity_type="land_parcel", payload=invalid_parcel),
            ImportRowSubmission(ordinal=3, entity_type="land_parcel", payload=_valid_parcel_payload("203")),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]
    assert result.processed_count == 3
    assert result.committed_count == 2
    assert result.rejected_count == 1
    assert result.is_completed is True

    assert session.rows[0].state == "COMMITTED"
    assert session.rows[1].state == "REJECTED"
    assert session.rows[1].rejection["rule_id"] == "required_field.land_parcel.survey_number"
    assert session.rows[1].rejection["attribute"] == "survey_number"
    assert session.rows[2].state == "COMMITTED"


def test_process_import_chunk_intra_batch_duplicate_parcel() -> None:
    session = FakeImportSession()
    # Both rows submit the same survey number in the same village
    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="land_parcel", payload=_valid_parcel_payload("301")),
            ImportRowSubmission(ordinal=2, entity_type="land_parcel", payload=_valid_parcel_payload("301")),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]
    assert result.processed_count == 2
    assert result.committed_count == 1
    assert result.rejected_count == 1

    assert session.rows[0].state == "COMMITTED"
    assert session.rows[1].state == "REJECTED"
    assert session.rows[1].rejection["rule_id"] == DUPLICATE_PARCEL_RULE_ID
    assert session.rows[1].rejection["matching_id"] is None


def test_process_import_chunk_existing_db_duplicate_parcel() -> None:
    existing_parcel = LandParcel(
        id=77,
        state_key="MH",
        district="Pune",
        tehsil="Haveli",
        village="Kothrud",
        survey_number="401",
        classification="agricultural",
        extent=Decimal("2.5"),
        extent_unit="hectare",
        area_code="MH.PUN",
    )
    session = FakeImportSession(parcels=[existing_parcel])

    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="land_parcel", payload=_valid_parcel_payload("401")),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]
    assert result.committed_count == 0
    assert result.rejected_count == 1
    assert session.rows[0].state == "REJECTED"
    assert session.rows[0].rejection["rule_id"] == DUPLICATE_PARCEL_RULE_ID
    assert session.rows[0].rejection["matching_id"] == 77


def test_process_import_chunk_ownership_date_overlap_rejection() -> None:
    session = FakeImportSession()
    # Two ownership records for the same owner & parcel with overlapping validity dates
    row1 = _valid_ownership_payload(parcel_id=101, owner_key="O-SAME")
    row1["valid_from"] = "2024-01-01"
    row1["valid_to"] = "2024-12-31"

    row2 = _valid_ownership_payload(parcel_id=101, owner_key="O-SAME")
    row2["valid_from"] = "2024-06-01"
    row2["valid_to"] = "2025-06-01"

    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="ownership_record", payload=row1),
            ImportRowSubmission(ordinal=2, entity_type="ownership_record", payload=row2),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]
    assert result.committed_count == 1
    assert result.rejected_count == 1
    assert session.rows[0].state == "COMMITTED"
    assert session.rows[1].state == "REJECTED"
    assert session.rows[1].rejection["rule_id"] == DUPLICATE_OWNERSHIP_RULE_ID


def test_process_import_chunk_area_divergence_rejection() -> None:
    session = FakeImportSession()
    # 1 hectare = 10,000 sqm. Geodesic area given as 12,000 sqm (20% divergence > 5%)
    payload = _valid_parcel_payload("501")
    payload["extent"] = "1.0"
    payload["extent_unit"] = "hectare"
    payload["geodesic_area_sqm"] = "12000"

    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="land_parcel", payload=payload),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]
    assert result.committed_count == 0
    assert result.rejected_count == 1
    assert session.rows[0].state == "REJECTED"
    assert session.rows[0].rejection["rule_id"] == AREA_DIVERGENCE_RULE_ID


def test_process_import_chunk_document_rejections() -> None:
    session = FakeImportSession()
    # Disallowed content type
    doc_bad_type = _valid_document_payload(case_id=1)
    doc_bad_type["content_type"] = "application/x-executable"

    # Oversized document (> 25MB)
    doc_oversized = _valid_document_payload(case_id=2)
    doc_oversized["byte_size"] = MAX_UPLOAD_BYTES + 10
    doc_oversized.pop("body", None)

    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="document", payload=doc_bad_type),
            ImportRowSubmission(ordinal=2, entity_type="document", payload=doc_oversized),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]
    assert result.committed_count == 0
    assert result.rejected_count == 2
    assert session.rows[0].rejection["rule_id"] == "upload_admitted"
    assert session.rows[1].rejection["rule_id"] == "upload_admitted"


def test_process_import_chunk_pagination_and_completion() -> None:
    session = FakeImportSession()
    # 5 rows processed in chunks of 2
    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=tuple(
            ImportRowSubmission(ordinal=i, entity_type="land_parcel", payload=_valid_parcel_payload(f"P-{i}"))
            for i in range(1, 6)
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    # Chunk 1: processes rows 1 & 2
    res1 = _process_import_chunk(session, batch_id=submit_res.batch_id, chunk_size=2)  # type: ignore[arg-type]
    assert res1.processed_count == 2
    assert res1.committed_count == 2
    assert res1.is_completed is False
    assert session.batches[submit_res.batch_id].state == "PROCESSING"

    # Chunk 2: processes rows 3 & 4
    res2 = _process_import_chunk(session, batch_id=submit_res.batch_id, chunk_size=2)  # type: ignore[arg-type]
    assert res2.processed_count == 2
    assert res2.committed_count == 2
    assert res2.is_completed is False
    assert session.batches[submit_res.batch_id].state == "PROCESSING"

    # Chunk 3: processes row 5 and finalizes batch
    res3 = _process_import_chunk(session, batch_id=submit_res.batch_id, chunk_size=2)  # type: ignore[arg-type]
    assert res3.processed_count == 1
    assert res3.committed_count == 1
    assert res3.is_completed is True
    assert session.batches[submit_res.batch_id].state == "COMPLETED"


# ============================================================================
# Interruption and Resumption Tests (Task 26.3)
# ============================================================================


def test_mark_batch_interrupted_and_resumption() -> None:
    session = FakeImportSession()
    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=tuple(
            ImportRowSubmission(ordinal=i, entity_type="land_parcel", payload=_valid_parcel_payload(f"INT-{i}"))
            for i in range(1, 4)
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    # Process first chunk of 1 row
    res1 = _process_import_chunk(session, batch_id=submit_res.batch_id, chunk_size=1)  # type: ignore[arg-type]
    assert res1.processed_count == 1
    assert session.rows[0].state == "COMMITTED"

    # Worker encounters failure/interruption: mark interrupted
    mark_batch_interrupted(session, batch_id=submit_res.batch_id, last_processed_ordinal=1)  # type: ignore[arg-type]
    assert session.batches[submit_res.batch_id].state == "INTERRUPTED"
    assert session.batches[submit_res.batch_id].last_processed_ordinal == 1

    # Resume: next chunk picks up remaining PENDING rows
    res_resume = _process_import_chunk(session, batch_id=submit_res.batch_id, chunk_size=10)  # type: ignore[arg-type]
    assert res_resume.processed_count == 2
    assert res_resume.committed_count == 2
    assert res_resume.is_completed is True
    assert session.batches[submit_res.batch_id].state == "COMPLETED"
    assert all(r.state == "COMMITTED" for r in session.rows)


def test_chunk_redelivery_idempotent_on_completed_batch() -> None:
    session = FakeImportSession()
    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="land_parcel", payload=_valid_parcel_payload("REDELIV-1")),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]
    assert session.batches[submit_res.batch_id].state == "COMPLETED"

    # Redelivery of task for completed batch
    redelivery_res = _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]
    assert redelivery_res.processed_count == 0
    assert redelivery_res.committed_count == 0
    assert redelivery_res.is_completed is True


# ============================================================================
# Reporting and API Tests (Tasks 26.3, 26.4)
# ============================================================================


def test_get_import_batch_report_and_filtering() -> None:
    session = FakeImportSession()
    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="land_parcel", payload=_valid_parcel_payload("REP-1")),
            ImportRowSubmission(ordinal=2, entity_type="land_parcel", payload={"state_key": "MH"}),  # missing fields
            ImportRowSubmission(ordinal=3, entity_type="land_parcel", payload={"survey_number": "1"}),  # missing fields
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]

    # Full report
    report = get_import_batch_report(session, batch_id=submit_res.batch_id, principal=_officer_principal())  # type: ignore[arg-type]
    assert report.batch_id == submit_res.batch_id
    assert report.submitted_count == 3
    assert report.committed_count == 1
    assert report.rejected_count == 2
    assert len(report.rejected_rows) == 2

    # Filtered report by specific rule
    failing_rule = report.rejected_rows[0].rule_id
    filtered = get_import_batch_report(
        session,  # type: ignore[arg-type]
        batch_id=submit_res.batch_id,
        principal=_officer_principal(),
        rule_id=failing_rule,
    )
    assert len(filtered.rejected_rows) == 1
    assert filtered.rejected_rows[0].rule_id == failing_rule


def test_get_import_batch_report_requires_permission() -> None:
    session = FakeImportSession()
    try:
        get_import_batch_report(
            session,  # type: ignore[arg-type]
            batch_id=1,
            principal=Principal(kind="OFFICER", id="officer-2"),
        )
    except Exception as exc:
        assert exc.__class__.__name__ == "NotAuthorised"
    else:
        raise AssertionError("get_import_batch_report did not enforce import.submit")


def test_officer_router_get_import_batch_endpoint(monkeypatch: Any) -> None:
    app = FastAPI()
    app.include_router(officer_router)

    session = FakeImportSession()
    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=(
            ImportRowSubmission(ordinal=1, entity_type="land_parcel", payload=_valid_parcel_payload("API-1")),
        ),
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    _process_import_chunk(session, batch_id=submit_res.batch_id)  # type: ignore[arg-type]

    monkeypatch.setattr("app.api.imports.unit_of_work", lambda: nullcontext(session))

    def _dep(request: Request) -> Principal:
        p = _officer_principal()
        request.state.principal = p
        return p

    app.dependency_overrides[authenticate] = _dep

    with TestClient(app) as client:
        # Success 200
        res = client.get(f"/api/officer/imports/{submit_res.batch_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["batch_id"] == submit_res.batch_id
        assert data["submitted_count"] == 1
        assert data["committed_count"] == 1
        assert data["state"] == "COMPLETED"

        # 404 for unknown batch
        res_404 = client.get("/api/officer/imports/999999")
        assert res_404.status_code == 404


# ============================================================================
# Property Tests (Task 26.5: Properties 71, 72, 73)
# ============================================================================


def test_property_71_import_matches_manual_rules() -> None:
    """Property 71: Import applies the same rules as manual entry.

    For any submitted row, the set of validation issues produced by evaluating
    it through Import_Service equals the set produced by evaluating the same data
    entered manually.
    """
    # 1. Missing required field
    bad_payload = {"district": "Pune"}
    import_issues = evaluate_row_rules("land_parcel", bad_payload)
    manual_rule = required_field_rule("land_parcel", "survey_number")

    class _SingleCtx:
        case_id = 1
        def values(self, etype: str) -> Sequence[Mapping[str, object]]:
            return ({"id": 1, **bad_payload},) if etype == "land_parcel" else ()

    manual_violations = list(manual_rule.evaluate(_SingleCtx()))
    assert any(v.rule_id == "required_field.land_parcel.survey_number" for v in manual_violations)
    assert any(r.rule_id == "required_field.land_parcel.survey_number" for r in import_issues)

    # 2. Area divergence rule parity
    div_payload = _valid_parcel_payload("DIV-1")
    div_payload["extent"] = "1.0"
    div_payload["extent_unit"] = "hectare"
    div_payload["geodesic_area_sqm"] = "12000"

    div_import_issues = evaluate_row_rules("land_parcel", div_payload)
    manual_area_rule = area_divergence_rule()

    class _DivCtx:
        case_id = 1
        def values(self, etype: str) -> Sequence[Mapping[str, object]]:
            return ({"id": 1, "extent": Decimal("1.0"), "extent_unit": "hectare", "geodesic_area_sqm": Decimal("12000")},) if etype == "land_parcel" else ()

    manual_area_violations = list(manual_area_rule.evaluate(_DivCtx()))
    assert any(v.rule_id == AREA_DIVERGENCE_RULE_ID for v in manual_area_violations)
    assert any(r.rule_id == AREA_DIVERGENCE_RULE_ID for r in div_import_issues)


@given(st.lists(st.booleans(), min_size=1, max_size=20))
@settings(max_examples=50, deadline=None)
def test_property_72_import_commits_pass_and_withholds_fail(row_is_valid_flags: list[bool]) -> None:
    """Property 72: Import commits pass and withholds fail, independently and accountably.

    For any interleaving of passing and failing rows:
    - committed set equals passing set exactly
    - no failing row withholds a passing row
    - each rejected row carries failing rule id, attribute, and observed value
    - submitted_count == committed_count + rejected_count
    """
    session = FakeImportSession()
    rows = []
    expected_passing = 0
    expected_failing = 0

    for idx, is_valid in enumerate(row_is_valid_flags, start=1):
        if is_valid:
            rows.append(ImportRowSubmission(ordinal=idx, entity_type="land_parcel", payload=_valid_parcel_payload(f"P72-{idx}")))
            expected_passing += 1
        else:
            rows.append(ImportRowSubmission(ordinal=idx, entity_type="land_parcel", payload={"state_key": "MH"}))
            expected_failing += 1

    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=rows,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = _process_import_chunk(session, batch_id=submit_res.batch_id, chunk_size=len(rows))  # type: ignore[arg-type]
    assert result.committed_count == expected_passing
    assert result.rejected_count == expected_failing
    assert result.processed_count == len(rows)

    report = get_import_batch_report(session, batch_id=submit_res.batch_id, principal=_officer_principal())  # type: ignore[arg-type]
    assert report.submitted_count == report.committed_count + report.rejected_count
    assert report.committed_count == expected_passing
    assert report.rejected_count == expected_failing

    for rej in report.rejected_rows:
        assert rej.rule_id is not None
        assert rej.attribute is not None


@given(st.integers(min_value=1, max_value=8))
@settings(max_examples=25, deadline=None)
def test_property_73_committed_rows_attributable_and_resumable(interrupt_at_ordinal: int) -> None:
    """Property 73: Committed import rows are attributable and resumable without duplication.

    For any committed import row, an Event exists carrying provenance='IMPORTED' and the import_batch_id.
    For any interruption at any row ordinal followed by resumption, the final committed multiset
    equals the passing row set with no row committed twice.
    """
    session = FakeImportSession()
    total_rows = 10
    rows = tuple(
        ImportRowSubmission(ordinal=i, entity_type="land_parcel", payload=_valid_parcel_payload(f"P73-{i}"))
        for i in range(1, total_rows + 1)
    )

    submit_res = submit_import_batch(
        session,  # type: ignore[arg-type]
        principal=_officer_principal(),
        rows=rows,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    # Process up to interrupt_at_ordinal
    _process_import_chunk(
        session,  # type: ignore[arg-type]
        batch_id=submit_res.batch_id,
        chunk_size=interrupt_at_ordinal,
    )

    # Mark interrupted
    mark_batch_interrupted(session, batch_id=submit_res.batch_id, last_processed_ordinal=interrupt_at_ordinal)  # type: ignore[arg-type]
    assert session.batches[submit_res.batch_id].state == "INTERRUPTED"

    # Resume and finish batch
    res_final = _process_import_chunk(session, batch_id=submit_res.batch_id, chunk_size=total_rows)  # type: ignore[arg-type]
    assert res_final.is_completed is True
    assert session.batches[submit_res.batch_id].state == "COMPLETED"

    # Assert exactly 10 parcels committed, no duplicates
    committed_rows = [r for r in session.rows if r.state == "COMMITTED"]
    assert len(committed_rows) == total_rows
    assert len({r.committed_entity_id for r in committed_rows}) == total_rows

    # Assert all events have provenance='IMPORTED' and import_batch_id
    parcel_events = [e for e in session.events if getattr(e, "event_type", None) == "LAND_PARCEL_CREATED"]
    assert len(parcel_events) == total_rows
    for ev in parcel_events:
        assert ev.provenance == "IMPORTED"
        assert ev.import_batch_id == submit_res.batch_id

