"""Bulk import submission (task 26.1); chunk processing lands in 26.2."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.db.event_log import EventLog
from app.models.import_batch import ImportBatch, ImportRow
from app.security.access import Principal
from app.security.permissions import require_permission

__all__ = ["ImportRowSubmission", "ImportSubmissionResult", "submit_import_batch"]


@dataclass(frozen=True)
class ImportRowSubmission:
    ordinal: int
    entity_type: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ImportSubmissionResult:
    batch_id: int
    submitted_count: int
    state: str
    content_checksum: str


def submit_import_batch(
    session: Session,
    *,
    principal: Principal,
    rows: Iterable[ImportRowSubmission],
    now: datetime | None = None,
) -> ImportSubmissionResult:
    require_permission(session, principal, "import.submit")
    submitted = tuple(sorted(rows, key=lambda row: row.ordinal))
    checksum = _content_checksum(submitted)
    batch = ImportBatch(
        submitted_by=principal.id,
        submitted_at=now or datetime.now(timezone.utc),
        submitted_count=len(submitted),
        content_checksum=checksum,
        state="PENDING",
        last_processed_ordinal=0,
    )
    session.add(batch)
    session.flush()
    for row in submitted:
        session.add(
            ImportRow(
                batch_id=batch.id,
                ordinal=row.ordinal,
                entity_type=row.entity_type,
                payload=row.payload,
                state="PENDING",
            )
        )
    event = EventLog.append(
        session,
        event_type="IMPORT_BATCH_CREATED",
        entity=batch,
        actor=principal,
        changes={
            "submitted_count": (None, len(submitted)),
            "content_checksum": (None, checksum.hex()),
        },
        occurrence_time=batch.submitted_at,
    )
    event.import_batch_id = batch.id
    return ImportSubmissionResult(
        batch_id=batch.id,
        submitted_count=len(submitted),
        state=batch.state,
        content_checksum=checksum.hex(),
    )


def _content_checksum(rows: tuple[ImportRowSubmission, ...]) -> bytes:
    payload = [
        {
            "ordinal": row.ordinal,
            "entity_type": row.entity_type,
            "payload": row.payload,
        }
        for row in rows
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).digest()


def process_import_chunk() -> None:
    raise NotImplementedError("task 26.2 wires chunked import processing")

