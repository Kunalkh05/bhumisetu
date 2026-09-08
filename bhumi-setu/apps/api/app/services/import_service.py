"""Bulk import service: submission, chunked processing, and reporting (tasks 26.1 - 26.4)."""

from __future__ import annotations

import base64
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.event_log import EventLog
from app.db.session import unit_of_work
from app.models.document import Document
from app.models.event import Event
from app.models.import_batch import ImportBatch, ImportRow
from app.models.land_parcel import LandParcel
from app.models.ownership_record import OwnershipRecord
from app.security.access import Principal
from app.security.permissions import require_permission
from app.services.document import (
    ACCEPTED_CONTENT_TYPES,
    MAX_UPLOAD_BYTES,
    DocumentService,
    DocumentStore,
    build_minio_store,
)
from app.services.validation.rules import (
    AREA_DIVERGENCE_FRACTION,
    AREA_DIVERGENCE_RULE_ID,
    DUPLICATE_OWNERSHIP_RULE_ID,
    DUPLICATE_PARCEL_RULE_ID,
    _extent_to_sqm,
    _to_decimal,
)
from app.settings import get_object_storage_settings
from app.workers.celery_app import celery_app

__all__ = [
    "CHUNK_SIZE",
    "ImportBatchReport",
    "ImportChunkResult",
    "ImportRowReport",
    "ImportRowSubmission",
    "ImportSubmissionResult",
    "RowRejection",
    "evaluate_row_rules",
    "get_import_batch_report",
    "mark_batch_interrupted",
    "process_import_chunk",
    "submit_import_batch",
]

CHUNK_SIZE = 1000

PARCEL_REQUIRED_FIELDS = (
    "state_key",
    "district",
    "tehsil",
    "village",
    "survey_number",
    "classification",
    "extent",
    "extent_unit",
    "area_code",
)

OWNERSHIP_REQUIRED_FIELDS = (
    "parcel_id",
    "interest_type",
    "share",
    "valid_from",
)


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


@dataclass(frozen=True)
class RowRejection:
    rule_id: str
    attribute: str | None
    observed: Any
    matching_id: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "attribute": self.attribute,
            "observed": self.observed,
            "matching_id": self.matching_id,
        }


@dataclass(frozen=True)
class ImportChunkResult:
    batch_id: int
    processed_count: int
    committed_count: int
    rejected_count: int
    last_processed_ordinal: int
    is_completed: bool


@dataclass(frozen=True)
class ImportRowReport:
    ordinal: int
    entity_type: str
    rule_id: str
    attribute: str | None
    observed: Any
    matching_id: int | None = None


@dataclass(frozen=True)
class ImportBatchReport:
    batch_id: int
    submitted_by: str
    submitted_at: datetime
    submitted_count: int
    committed_count: int
    rejected_count: int
    state: str
    last_processed_ordinal: int
    rejected_rows: tuple[ImportRowReport, ...]


class InMemoryDocumentStore:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        self._objects[key] = body

    def get_object(self, *, key: str) -> bytes:
        if key not in self._objects:
            raise KeyError(key)
        return self._objects[key]

    def presigned_get(self, *, key: str, expires_in: int) -> str:
        return f"https://storage.local/{key}?expires={expires_in}"


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
    try:
        from app.db.outbox import enqueue

        enqueue(
            session,
            queue="import",
            task_name="app.services.import_service.process_import_chunk",
            kwargs={"batch_id": batch.id},
            idempotency_key=f"import:{batch.id}:1",
        )
    except Exception:
        pass
    return ImportSubmissionResult(
        batch_id=batch.id,
        submitted_count=len(submitted),
        state=batch.state,
        content_checksum=checksum.hex(),
    )


@celery_app.task(name="app.services.import_service.process_import_chunk")
def process_import_chunk(
    session_or_batch_id: Any = None,
    batch_id: int | None = None,
    *,
    ordinals: range | Sequence[int] | None = None,
    chunk_size: int = CHUNK_SIZE,
    actor: Principal | None = None,
    now: datetime | None = None,
    document_store: DocumentStore | None = None,
) -> ImportChunkResult:
    if isinstance(session_or_batch_id, int):
        target_batch_id = session_or_batch_id
        with unit_of_work() as session:
            return _process_import_chunk(
                session,
                batch_id=target_batch_id,
                ordinals=ordinals,
                chunk_size=chunk_size,
                actor=actor,
                now=now,
                document_store=document_store,
            )
    if session_or_batch_id is None:
        assert batch_id is not None
        with unit_of_work() as session:
            return _process_import_chunk(
                session,
                batch_id=batch_id,
                ordinals=ordinals,
                chunk_size=chunk_size,
                actor=actor,
                now=now,
                document_store=document_store,
            )
    assert batch_id is not None or hasattr(session_or_batch_id, "id")
    target_id = batch_id if batch_id is not None else session_or_batch_id.id
    return _process_import_chunk(
        session_or_batch_id,
        batch_id=target_id,
        ordinals=ordinals,
        chunk_size=chunk_size,
        actor=actor,
        now=now,
        document_store=document_store,
    )


def _process_import_chunk(
    session: Session,
    *,
    batch_id: int,
    ordinals: range | Sequence[int] | None = None,
    chunk_size: int = CHUNK_SIZE,
    actor: Principal | None = None,
    now: datetime | None = None,
    document_store: DocumentStore | None = None,
) -> ImportChunkResult:
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise LookupError(f"Import batch {batch_id} does not exist")
    if batch.state == "COMPLETED":
        return ImportChunkResult(
            batch_id=batch_id,
            processed_count=0,
            committed_count=0,
            rejected_count=0,
            last_processed_ordinal=batch.last_processed_ordinal,
            is_completed=True,
        )

    stmt = (
        select(ImportRow)
        .where(ImportRow.batch_id == batch_id, ImportRow.state == "PENDING")
        .order_by(ImportRow.ordinal)
    )
    if ordinals is not None:
        if isinstance(ordinals, range):
            stmt = stmt.where(
                ImportRow.ordinal >= ordinals.start,
                ImportRow.ordinal < ordinals.stop,
            )
        else:
            stmt = stmt.where(ImportRow.ordinal.in_(tuple(ordinals)))
    stmt = stmt.limit(chunk_size)
    pending_rows = list(session.execute(stmt).scalars())

    effective_actor = actor or Principal(
        kind="OFFICER",
        id=batch.submitted_by,
        permissions=frozenset({"import.submit"}),
    )
    occurred = now or datetime.now(timezone.utc)

    if not pending_rows:
        pending_remaining = session.execute(
            select(func.count())
            .select_from(ImportRow)
            .where(ImportRow.batch_id == batch_id, ImportRow.state == "PENDING")
        ).scalar_one()
        is_completed = False
        if pending_remaining == 0:
            _finalize_batch(session, batch, actor=effective_actor, now=occurred)
            is_completed = True
        return ImportChunkResult(
            batch_id=batch_id,
            processed_count=0,
            committed_count=0,
            rejected_count=0,
            last_processed_ordinal=batch.last_processed_ordinal,
            is_completed=is_completed,
        )

    if batch.state == "PENDING":
        batch.state = "PROCESSING"

    try:
        session.execute(text("SET LOCAL bhumisetu.skip_event_backstop = 'on'"))
    except Exception:
        pass

    parcel_identities = []
    ownership_keys = []
    doc_checksum_lookups = []
    for r in pending_rows:
        etype = _canonical_entity_type(r.entity_type)
        payload = r.payload or {}
        if etype == "land_parcel":
            parcel_identities.append(_parcel_identity_tuple(payload))
        elif etype == "ownership_record":
            pid = payload.get("parcel_id")
            if pid is not None:
                try:
                    ownership_keys.append(int(pid))
                except (ValueError, TypeError):
                    pass
        elif etype == "document":
            cid = payload.get("case_id")
            if cid is not None:
                body_bytes = _extract_body_bytes(payload)
                if body_bytes:
                    doc_checksum_lookups.append((int(cid), hashlib.sha256(body_bytes).digest()))

    existing_parcels = _fetch_existing_parcels(session, parcel_identities)
    existing_ownerships = _fetch_existing_ownerships(session, ownership_keys)
    existing_doc_checksums = _fetch_existing_doc_checksums(session, doc_checksum_lookups)

    observed_parcels: dict[tuple[Any, ...], int] = {}
    observed_ownerships: list[dict[str, Any]] = []
    observed_doc_checksums: set[tuple[int, bytes]] = set()

    committed_parcels_by_ordinal: dict[int, int] = {}
    committed_parcels_by_identity: dict[tuple[Any, ...], int] = {}

    passed: list[tuple[ImportRow, str]] = []
    rejected: list[tuple[ImportRow, RowRejection]] = []

    for r in pending_rows:
        etype = _canonical_entity_type(r.entity_type)
        payload = r.payload or {}

        if etype == "land_parcel":
            rejections = _evaluate_parcel_row(
                payload,
                existing_parcels=existing_parcels,
                observed_parcels=observed_parcels,
            )
            if rejections:
                rejected.append((r, rejections[0]))
            else:
                ident = _parcel_identity_tuple(payload)
                observed_parcels[ident] = r.ordinal
                passed.append((r, "land_parcel"))

        elif etype == "ownership_record":
            target_pid = payload.get("parcel_id")
            if target_pid is None and "parcel_ordinal" in payload:
                target_pid = committed_parcels_by_ordinal.get(payload["parcel_ordinal"])
            if target_pid is None and "parcel_identity" in payload:
                target_pid = committed_parcels_by_identity.get(
                    _parcel_identity_tuple(payload["parcel_identity"])
                )

            rejections = _evaluate_ownership_row(
                payload,
                resolved_parcel_id=target_pid,
                existing_ownerships=existing_ownerships,
                observed_ownerships=observed_ownerships,
            )
            if rejections:
                rejected.append((r, rejections[0]))
            else:
                observed_ownerships.append(payload)
                passed.append((r, "ownership_record"))

        elif etype == "document":
            rejections = _evaluate_document_row(
                payload,
                existing_checksums=existing_doc_checksums,
                observed_checksums=observed_doc_checksums,
            )
            if rejections:
                rejected.append((r, rejections[0]))
            else:
                cid = payload.get("case_id")
                if cid is not None:
                    b_bytes = _extract_body_bytes(payload)
                    observed_doc_checksums.add((int(cid), hashlib.sha256(b_bytes).digest()))
                passed.append((r, "document"))
        else:
            rejected.append(
                (
                    r,
                    RowRejection(
                        rule_id="unknown_entity_type",
                        attribute="entity_type",
                        observed=r.entity_type,
                    ),
                )
            )

    for r, rej in rejected:
        r.state = "REJECTED"
        r.rejection = rej.as_dict()

    inserted_parcel_ids: list[int] = []
    inserted_ownership_ids: list[int] = []
    key_secret = _get_key_secret()
    doc_store = document_store or _resolve_doc_store()

    for r, etype in passed:
        p = r.payload or {}
        if etype == "land_parcel":
            parcel = LandParcel(
                state_key=p["state_key"],
                district=p["district"],
                tehsil=p["tehsil"],
                village=p["village"],
                survey_number=str(p["survey_number"]),
                sub_division=p.get("sub_division") or None,
                classification=p["classification"],
                extent=Decimal(str(p["extent"])),
                extent_unit=p["extent_unit"],
                area_code=p["area_code"],
                geom=p.get("geom"),
                geodesic_area_sqm=Decimal(str(p["geodesic_area_sqm"]))
                if p.get("geodesic_area_sqm") is not None
                else None,
            )
            session.add(parcel)
            session.flush()
            inserted_parcel_ids.append(parcel.id)
            r.state = "COMMITTED"
            r.committed_entity_id = parcel.id
            committed_parcels_by_ordinal[r.ordinal] = parcel.id
            committed_parcels_by_identity[_parcel_identity_tuple(p)] = parcel.id

            EventLog.append(
                session,
                event_type="LAND_PARCEL_CREATED",
                entity=parcel,
                actor=effective_actor,
                changes={
                    "state_key": (None, parcel.state_key),
                    "district": (None, parcel.district),
                    "tehsil": (None, parcel.tehsil),
                    "village": (None, parcel.village),
                    "survey_number": (None, parcel.survey_number),
                    "sub_division": (None, parcel.sub_division),
                    "classification": (None, parcel.classification),
                    "extent": (None, str(parcel.extent)),
                    "extent_unit": (None, parcel.extent_unit),
                    "area_code": (None, parcel.area_code),
                },
                occurrence_time=occurred,
                entity_version_after=parcel.entity_version,
                provenance="IMPORTED",
                import_batch_id=batch_id,
            )

        elif etype == "ownership_record":
            target_pid = p.get("parcel_id")
            if target_pid is None and "parcel_ordinal" in p:
                target_pid = committed_parcels_by_ordinal.get(p["parcel_ordinal"])
            if target_pid is None and "parcel_identity" in p:
                target_pid = committed_parcels_by_identity.get(
                    _parcel_identity_tuple(p["parcel_identity"])
                )

            rec = OwnershipRecord(
                parcel_id=int(target_pid),
                owner_name=p.get("owner_name"),
                owner_identity_key=p.get("owner_identity_key"),
                government_identifier=p.get("government_identifier"),
                contact_mobile=p.get("contact_mobile"),
                contact_mobile_hash=_mobile_hash(key_secret, p.get("contact_mobile")),
                interest_type=p["interest_type"],
                share=Decimal(str(p["share"])),
                valid_from=_parse_date(p["valid_from"]),
                valid_to=_parse_date(p.get("valid_to")),
            )
            session.add(rec)
            session.flush()
            inserted_ownership_ids.append(rec.id)
            r.state = "COMMITTED"
            r.committed_entity_id = rec.id

            EventLog.append(
                session,
                event_type="OWNERSHIP_RECORDED",
                entity=rec,
                actor=effective_actor,
                changes={
                    "parcel_id": (None, rec.parcel_id),
                    "owner_name": (None, rec.owner_name),
                    "owner_identity_key": (None, rec.owner_identity_key),
                    "government_identifier": (None, rec.government_identifier),
                    "contact_mobile": (None, rec.contact_mobile),
                    "interest_type": (None, rec.interest_type),
                    "share": (None, str(rec.share)),
                    "valid_from": (
                        None,
                        rec.valid_from.isoformat() if rec.valid_from else None,
                    ),
                    "valid_to": (
                        None,
                        rec.valid_to.isoformat() if rec.valid_to else None,
                    ),
                },
                occurrence_time=occurred,
                entity_version_after=rec.entity_version,
                provenance="IMPORTED",
                import_batch_id=batch_id,
            )

        elif etype == "document":
            body_bytes = _extract_body_bytes(p)
            doc_service = DocumentService(store=doc_store)
            doc_actor = effective_actor
            try:
                import uuid as _uuid
                _uuid.UUID(str(effective_actor.id))
            except (ValueError, TypeError):
                doc_actor = Principal(
                    kind=effective_actor.kind,
                    id=str(_uuid.uuid5(_uuid.NAMESPACE_DNS, str(effective_actor.id))),
                    permissions=effective_actor.permissions,
                )
            stored = doc_service.store(
                session,
                case_id=p.get("case_id"),
                parcel_id=p.get("parcel_id"),
                document_type=p["document_type"],
                original_filename=p["original_filename"],
                content_type=p["content_type"],
                body=body_bytes,
                actor=doc_actor,
                occurrence_time=occurred,
            )
            r.state = "COMMITTED"
            r.committed_entity_id = stored.document.id

            doc_ev = session.execute(
                select(Event)
                .where(
                    Event.entity_type == "document",
                    Event.entity_id == stored.document.id,
                )
                .order_by(Event.id.desc())
                .limit(1)
            ).scalar_one_or_none()
            if doc_ev is not None:
                doc_ev.provenance = "IMPORTED"
                doc_ev.import_batch_id = batch_id

    _assert_set_wise_event_backstop(
        session,
        inserted_parcel_ids=inserted_parcel_ids,
        inserted_ownership_ids=inserted_ownership_ids,
    )

    batch.last_processed_ordinal = max(r.ordinal for r in pending_rows)

    pending_count = session.execute(
        select(func.count())
        .select_from(ImportRow)
        .where(ImportRow.batch_id == batch_id, ImportRow.state == "PENDING")
    ).scalar_one()

    is_completed = False
    if pending_count == 0:
        _finalize_batch(session, batch, actor=effective_actor, now=occurred)
        is_completed = True

    return ImportChunkResult(
        batch_id=batch_id,
        processed_count=len(pending_rows),
        committed_count=len(passed),
        rejected_count=len(rejected),
        last_processed_ordinal=batch.last_processed_ordinal,
        is_completed=is_completed,
    )


def _assert_set_wise_event_backstop(
    session: Session,
    *,
    inserted_parcel_ids: Sequence[int],
    inserted_ownership_ids: Sequence[int],
) -> None:
    try:
        bind = session.get_bind()
    except Exception:
        bind = None

    if bind is not None and getattr(bind.dialect, "name", "") == "postgresql":
        if inserted_parcel_ids:
            missing = session.execute(
                text(
                    """
                    SELECT count(*) FROM land_parcel p
                     WHERE p.id = ANY(:ids)
                       AND NOT EXISTS (
                           SELECT 1 FROM event e
                            WHERE e.entity_type = 'land_parcel' AND e.entity_id = p.id
                              AND e.txid = txid_current()
                       )
                    """
                ),
                {"ids": list(inserted_parcel_ids)},
            ).scalar_one()
            if missing != 0:
                raise RuntimeError(
                    f"Set-wise event backstop invariant violated: {missing} parcels without event"
                )

        if inserted_ownership_ids:
            missing = session.execute(
                text(
                    """
                    SELECT count(*) FROM ownership_record o
                     WHERE o.id = ANY(:ids)
                       AND NOT EXISTS (
                           SELECT 1 FROM event e
                            WHERE e.entity_type = 'ownership_record' AND e.entity_id = o.id
                              AND e.txid = txid_current()
                       )
                    """
                ),
                {"ids": list(inserted_ownership_ids)},
            ).scalar_one()
            if missing != 0:
                raise RuntimeError(
                    f"Set-wise event backstop invariant violated: {missing} ownership records without event"
                )


def _finalize_batch(
    session: Session,
    batch: ImportBatch,
    *,
    actor: Principal,
    now: datetime,
) -> None:
    committed_count = session.execute(
        select(func.count())
        .select_from(ImportRow)
        .where(ImportRow.batch_id == batch.id, ImportRow.state == "COMMITTED")
    ).scalar_one()
    rejected_count = session.execute(
        select(func.count())
        .select_from(ImportRow)
        .where(ImportRow.batch_id == batch.id, ImportRow.state == "REJECTED")
    ).scalar_one()

    assert batch.submitted_count == committed_count + rejected_count, (
        f"submitted count ({batch.submitted_count}) != "
        f"committed ({committed_count}) + rejected ({rejected_count})"
    )

    prior_state = batch.state
    batch.state = "COMPLETED"
    EventLog.append(
        session,
        event_type="IMPORT_BATCH_COMPLETED",
        entity=batch,
        actor=actor,
        changes={
            "state": (prior_state, "COMPLETED"),
            "committed_count": (None, committed_count),
            "rejected_count": (None, rejected_count),
        },
        occurrence_time=now,
        import_batch_id=batch.id,
    )


def mark_batch_interrupted(
    session: Session,
    *,
    batch_id: int,
    last_processed_ordinal: int,
) -> None:
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise LookupError(f"Import batch {batch_id} does not exist")
    batch.state = "INTERRUPTED"
    batch.last_processed_ordinal = last_processed_ordinal
    session.flush()


def get_import_batch_report(
    session: Session,
    *,
    batch_id: int,
    principal: Principal | None = None,
    rule_id: str | None = None,
) -> ImportBatchReport:
    if principal is not None:
        require_permission(session, principal, "import.submit")
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise LookupError(f"Import batch {batch_id} does not exist")

    committed_count = session.execute(
        select(func.count())
        .select_from(ImportRow)
        .where(
            ImportRow.batch_id == batch_id,
            ImportRow.state == "COMMITTED",
        )
    ).scalar_one()

    rejected_stmt = (
        select(ImportRow)
        .where(
            ImportRow.batch_id == batch_id,
            ImportRow.state == "REJECTED",
        )
        .order_by(ImportRow.ordinal)
    )
    rejected_rows_raw = list(session.execute(rejected_stmt).scalars())
    rejected_count = len(rejected_rows_raw)

    rejected_reports: list[ImportRowReport] = []
    for r in rejected_rows_raw:
        rej = r.rejection or {}
        r_rule_id = str(rej.get("rule_id", "unknown"))
        if rule_id is not None and r_rule_id != rule_id:
            continue
        rejected_reports.append(
            ImportRowReport(
                ordinal=r.ordinal,
                entity_type=r.entity_type,
                rule_id=r_rule_id,
                attribute=rej.get("attribute"),
                observed=rej.get("observed"),
                matching_id=rej.get("matching_id"),
            )
        )

    return ImportBatchReport(
        batch_id=batch.id,
        submitted_by=batch.submitted_by,
        submitted_at=batch.submitted_at,
        submitted_count=batch.submitted_count,
        committed_count=committed_count,
        rejected_count=rejected_count,
        state=batch.state,
        last_processed_ordinal=batch.last_processed_ordinal,
        rejected_rows=tuple(rejected_reports),
    )


def evaluate_row_rules(
    entity_type: str,
    payload: Mapping[str, Any],
    *,
    existing_parcels: Mapping[tuple[Any, ...], int] | None = None,
    observed_parcels: Mapping[tuple[Any, ...], int] | None = None,
    existing_ownerships: Mapping[tuple[int, str], Sequence[Any]] | None = None,
    observed_ownerships: Sequence[Mapping[str, Any]] | None = None,
    existing_doc_checksums: set[tuple[int, bytes]] | None = None,
    observed_doc_checksums: set[tuple[int, bytes]] | None = None,
) -> list[RowRejection]:
    etype = _canonical_entity_type(entity_type)
    if etype == "land_parcel":
        return _evaluate_parcel_row(
            payload,
            existing_parcels=existing_parcels or {},
            observed_parcels=observed_parcels or {},
        )
    if etype == "ownership_record":
        return _evaluate_ownership_row(
            payload,
            resolved_parcel_id=payload.get("parcel_id"),
            existing_ownerships=existing_ownerships or {},
            observed_ownerships=observed_ownerships or (),
        )
    if etype == "document":
        return _evaluate_document_row(
            payload,
            existing_checksums=existing_doc_checksums or set(),
            observed_checksums=observed_doc_checksums or set(),
        )
    return [
        RowRejection(
            rule_id="unknown_entity_type",
            attribute="entity_type",
            observed=entity_type,
        )
    ]


def _evaluate_parcel_row(
    payload: Mapping[str, Any],
    *,
    existing_parcels: Mapping[tuple[Any, ...], int],
    observed_parcels: Mapping[tuple[Any, ...], int],
) -> list[RowRejection]:
    rejections: list[RowRejection] = []
    for f in PARCEL_REQUIRED_FIELDS:
        val = payload.get(f)
        if val is None or (isinstance(val, str) and not val.strip()):
            rejections.append(
                RowRejection(
                    rule_id=f"required_field.land_parcel.{f}",
                    attribute=f,
                    observed=val,
                )
            )

    ident = _parcel_identity_tuple(payload)
    if ident in existing_parcels:
        rejections.append(
            RowRejection(
                rule_id=DUPLICATE_PARCEL_RULE_ID,
                attribute="survey_number",
                observed=payload.get("survey_number"),
                matching_id=existing_parcels[ident],
            )
        )
    elif ident in observed_parcels:
        rejections.append(
            RowRejection(
                rule_id=DUPLICATE_PARCEL_RULE_ID,
                attribute="survey_number",
                observed=payload.get("survey_number"),
                matching_id=None,
            )
        )

    area_rej = _check_area_divergence(payload)
    if area_rej is not None:
        rejections.append(area_rej)

    return rejections


def _evaluate_ownership_row(
    payload: Mapping[str, Any],
    *,
    resolved_parcel_id: Any | None,
    existing_ownerships: Mapping[tuple[int, str], Sequence[Any]],
    observed_ownerships: Sequence[Mapping[str, Any]],
) -> list[RowRejection]:
    rejections: list[RowRejection] = []
    for f in OWNERSHIP_REQUIRED_FIELDS:
        val = payload.get(f) if f != "parcel_id" else resolved_parcel_id
        if val is None or (isinstance(val, str) and not val.strip()):
            rejections.append(
                RowRejection(
                    rule_id=f"required_field.ownership_record.{f}",
                    attribute=f,
                    observed=val,
                )
            )

    valid_from = _parse_date(payload.get("valid_from"))
    valid_to = _parse_date(payload.get("valid_to"))
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        rejections.append(
            RowRejection(
                rule_id="date_chronology.ownership_record.valid_from.valid_to",
                attribute="valid_to",
                observed=str(valid_to),
            )
        )

    owner_key = payload.get("owner_identity_key")
    if resolved_parcel_id is not None and owner_key is not None:
        try:
            pid = int(resolved_parcel_id)
            for ex in existing_ownerships.get((pid, str(owner_key)), ()):
                ex_from = getattr(ex, "valid_from", None)
                ex_to = getattr(ex, "valid_to", None)
                if _date_ranges_overlap(valid_from, valid_to, ex_from, ex_to):
                    rejections.append(
                        RowRejection(
                            rule_id=DUPLICATE_OWNERSHIP_RULE_ID,
                            attribute="valid_from",
                            observed={
                                "valid_from": str(valid_from) if valid_from else None,
                                "valid_to": str(valid_to) if valid_to else None,
                            },
                            matching_id=getattr(ex, "id", None),
                        )
                    )
                    break

            if not rejections:
                for obs in observed_ownerships:
                    obs_pid = obs.get("parcel_id")
                    obs_okey = obs.get("owner_identity_key")
                    if obs_pid == pid and obs_okey == owner_key:
                        obs_from = _parse_date(obs.get("valid_from"))
                        obs_to = _parse_date(obs.get("valid_to"))
                        if _date_ranges_overlap(valid_from, valid_to, obs_from, obs_to):
                            rejections.append(
                                RowRejection(
                                    rule_id=DUPLICATE_OWNERSHIP_RULE_ID,
                                    attribute="valid_from",
                                    observed={
                                        "valid_from": str(valid_from)
                                        if valid_from
                                        else None,
                                        "valid_to": str(valid_to)
                                        if valid_to
                                        else None,
                                    },
                                    matching_id=None,
                                )
                            )
                            break
        except (ValueError, TypeError):
            pass

    return rejections


def _evaluate_document_row(
    payload: Mapping[str, Any],
    *,
    existing_checksums: set[tuple[int, bytes]],
    observed_checksums: set[tuple[int, bytes]],
) -> list[RowRejection]:
    rejections: list[RowRejection] = []
    content_type = payload.get("content_type", "")
    if content_type not in ACCEPTED_CONTENT_TYPES:
        rejections.append(
            RowRejection(
                rule_id="upload_admitted",
                attribute="content_type",
                observed=content_type,
            )
        )

    body_bytes = _extract_body_bytes(payload)
    effective_byte_size = len(body_bytes) if body_bytes else int(payload.get("byte_size") or 0)
    if effective_byte_size > MAX_UPLOAD_BYTES:
        rejections.append(
            RowRejection(
                rule_id="upload_admitted",
                attribute="byte_size",
                observed=effective_byte_size,
            )
        )

    if payload.get("case_id") is None and payload.get("parcel_id") is None:
        rejections.append(
            RowRejection(
                rule_id="required_field.document.attachment",
                attribute="case_id",
                observed=None,
            )
        )

    cid = payload.get("case_id")
    if cid is not None and body_bytes:
        try:
            cid_int = int(cid)
            csum = hashlib.sha256(body_bytes).digest()
            if (cid_int, csum) in existing_checksums or (cid_int, csum) in observed_checksums:
                rejections.append(
                    RowRejection(
                        rule_id="duplicate_document",
                        attribute="checksum_sha256",
                        observed=csum.hex(),
                        matching_id=None,
                    )
                )
        except (ValueError, TypeError):
            pass

    return rejections


def _check_area_divergence(payload: Mapping[str, Any]) -> RowRejection | None:
    extent = payload.get("extent")
    extent_unit = payload.get("extent_unit")
    geodesic = payload.get("geodesic_area_sqm")
    if extent is None or extent_unit is None or geodesic is None:
        return None

    recorded_sqm = _extent_to_sqm(extent, extent_unit)
    geodesic_sqm = _to_decimal(geodesic)
    if recorded_sqm is None or geodesic_sqm is None or recorded_sqm == 0:
        return None
    delta = abs(geodesic_sqm - recorded_sqm)
    fraction = delta / recorded_sqm
    if fraction > AREA_DIVERGENCE_FRACTION:
        return RowRejection(
            rule_id=AREA_DIVERGENCE_RULE_ID,
            attribute="geodesic_area_sqm",
            observed=str(geodesic),
        )
    return None


def _fetch_existing_parcels(
    session: Session, identities: Sequence[tuple[Any, ...]]
) -> dict[tuple[Any, ...], int]:
    if not identities:
        return {}
    states = {p[0] for p in identities if p[0]}
    surveys = {p[4] for p in identities if p[4]}
    if not states or not surveys:
        return {}
    try:
        stmt = select(
            LandParcel.id,
            LandParcel.state_key,
            LandParcel.district,
            LandParcel.tehsil,
            LandParcel.village,
            LandParcel.village_norm,
            LandParcel.survey_number,
            LandParcel.sub_division,
        ).where(
            LandParcel.state_key.in_(states),
            LandParcel.survey_number.in_(surveys),
        )
        results = session.execute(stmt).all()
        existing = {}
        for r in results:
            v_norm = r.village_norm or _normalise_village(r.village)
            sub = r.sub_division or ""
            key = (
                r.state_key,
                r.district,
                r.tehsil,
                v_norm,
                str(r.survey_number),
                sub,
            )
            existing[key] = r.id
        return existing
    except Exception:
        return {}


def _fetch_existing_ownerships(
    session: Session, parcel_ids: Sequence[int]
) -> dict[tuple[int, str], list[Any]]:
    if not parcel_ids:
        return {}
    try:
        stmt = select(OwnershipRecord).where(OwnershipRecord.parcel_id.in_(parcel_ids))
        records = list(session.execute(stmt).scalars())
        existing: dict[tuple[int, str], list[Any]] = defaultdict(list)
        for rec in records:
            if rec.owner_identity_key:
                existing[(rec.parcel_id, rec.owner_identity_key)].append(rec)
        return existing
    except Exception:
        return {}


def _fetch_existing_doc_checksums(
    session: Session, lookups: Sequence[tuple[int, bytes]]
) -> set[tuple[int, bytes]]:
    if not lookups:
        return set()
    cases = {c for c, _ in lookups}
    try:
        stmt = select(Document.case_id, Document.checksum_sha256).where(
            Document.case_id.in_(cases)
        )
        results = session.execute(stmt).all()
        return {(r.case_id, bytes(r.checksum_sha256)) for r in results}
    except Exception:
        return set()


def _parcel_identity_tuple(p: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        p.get("state_key"),
        p.get("district"),
        p.get("tehsil"),
        _normalise_village(p.get("village_norm") or p.get("village")),
        str(p.get("survey_number") or ""),
        str(p.get("sub_division") or ""),
    )


def _normalise_village(value: Any) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value).strip())


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _date_ranges_overlap(
    left_from: date | None,
    left_to: date | None,
    right_from: date | None,
    right_to: date | None,
) -> bool:
    if left_from is None or right_from is None:
        return False
    left_end = left_to if left_to is not None else date.max
    right_end = right_to if right_to is not None else date.max
    return left_from <= right_end and right_from <= left_end


def _canonical_entity_type(name: str) -> str:
    cleaned = name.strip().lower()
    if cleaned in {"parcel", "land_parcel"}:
        return "land_parcel"
    if cleaned in {"ownership", "ownership_record"}:
        return "ownership_record"
    if cleaned in {"doc", "document"}:
        return "document"
    return cleaned


def _extract_body_bytes(payload: Mapping[str, Any]) -> bytes:
    body = payload.get("body") or payload.get("content") or b""
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        try:
            return base64.b64decode(body, validate=True)
        except Exception:
            return body.encode("utf-8")
    return b""


def _get_key_secret() -> bytes:
    try:
        from app.settings import get_core_settings

        return get_core_settings().jwt_secret.get_secret_value().encode("utf-8")
    except Exception:
        return b"bhumisetu-default-key-secret"


def _mobile_hash(secret: bytes, mobile: str | None) -> bytes | None:
    if mobile is None:
        return None
    from app.security.rate_limit import hmac_key

    return bytes.fromhex(hmac_key(secret, mobile))


def _resolve_doc_store() -> DocumentStore:
    try:
        return build_minio_store(get_object_storage_settings())
    except Exception:
        return InMemoryDocumentStore()


def _content_checksum(rows: tuple[ImportRowSubmission, ...]) -> bytes:
    payload = [
        {
            "ordinal": row.ordinal,
            "entity_type": row.entity_type,
            "payload": row.payload,
        }
        for row in rows
    ]

    def _default(obj: Any) -> Any:
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("ascii")
        return str(obj)

    encoded = json.dumps(payload, default=_default, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).digest()

