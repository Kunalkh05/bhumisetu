"""OCR extraction primitives and confidence routing (task 16)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Mapping, Protocol, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.db.session import unit_of_work
from app.db.versioned_repository import ReviewConflictSpec, VersionedRepository
from app.errors import DomainError, ErrorCode
from app.models.acquisition_case import AcquisitionCase
from app.models.document import Document
from app.models.extraction import ExtractedField, Extraction
from app.models.extraction_accuracy_report import ExtractionAccuracyReport
from app.models.holdout import HoldoutDocument, HoldoutLabel
from app.services.document import DocumentStore
from app.workers.celery_app import celery_app

__all__ = [
    "AUTO_ACCEPTED",
    "BELOW_REVIEW_THRESHOLD",
    "MANUAL_ENTRY_REQUIRED",
    "NO_CURRENT_ACCURACY_REPORT",
    "PENDING_REVIEW",
    "REPORT_DOES_NOT_COVER_THRESHOLD",
    "AccuracyReportEvidence",
    "AccuracyObservation",
    "AccuracyMeasurementDependencies",
    "AccuracySummary",
    "ExtractedFieldNotAdmitted",
    "FieldResult",
    "OcrThresholds",
    "RecognitionResult",
    "Recognizer",
    "ReviewDecision",
    "TerminalExtractionError",
    "TransientExtractionError",
    "extract_document",
    "exact_match",
    "measure_extraction_accuracy",
    "measure_holdout_accuracy",
    "admit_extracted_value",
    "confirm_field",
    "configure_accuracy_measurement",
    "correct_field",
    "process_document",
    "record_accuracy_report",
    "review_state_for",
    "summarise_accuracy",
    "supersede_accuracy_reports",
]

MANUAL_ENTRY_REQUIRED = "MANUAL_ENTRY_REQUIRED"
PENDING_REVIEW = "PENDING_REVIEW"
AUTO_ACCEPTED = "AUTO_ACCEPTED"
CONFIRMED = "CONFIRMED"
CORRECTED = "CORRECTED"
BELOW_REVIEW_THRESHOLD = "BELOW_REVIEW_THRESHOLD"
NO_CURRENT_ACCURACY_REPORT = "NO_CURRENT_ACCURACY_REPORT"
REPORT_DOES_NOT_COVER_THRESHOLD = "REPORT_DOES_NOT_COVER_THRESHOLD"
PROCESSING = "PROCESSING"
EXTRACTED = "EXTRACTED"
UNSUPPORTED_SCRIPT = "UNSUPPORTED_SCRIPT"
EXTRACTION_FAILED = "EXTRACTION_FAILED"
REJECTED_LOW_QUALITY = "REJECTED_LOW_QUALITY"
PROCESSABLE_STATES = frozenset({"QUEUED", PROCESSING})
ADMITTED_REVIEW_STATES = frozenset({AUTO_ACCEPTED, CONFIRMED, CORRECTED})


class TransientExtractionError(RuntimeError):
    """A temporary OCR failure that should be retried by Celery."""


class TerminalExtractionError(RuntimeError):
    """A deterministic OCR failure that should not be retried."""


class ExtractedFieldNotAdmitted(DomainError):
    code = ErrorCode.VALIDATION_FAILED
    status_code = 422

    def __init__(self, *, field_id: int, review_state: str) -> None:
        super().__init__(
            "Extracted field is not admitted for case data",
            details={"field_id": field_id, "review_state": review_state},
        )


class Recognizer(Protocol):
    """Deployment-swappable OCR engine."""

    version: str

    def detect_script(self, document_bytes: bytes) -> str:
        ...

    def recognise(self, document_bytes: bytes, *, script: str) -> "RecognitionResult":
        ...


class ThresholdProvider(Protocol):
    def __call__(self, session: Session) -> Sequence[float]:
        ...


@dataclass(frozen=True)
class FieldResult:
    field_name: str
    extracted_value: str | None
    confidence: float
    page_number: int
    bbox_x1: float
    bbox_y1: float
    bbox_x2: float
    bbox_y2: float


@dataclass(frozen=True)
class RecognitionResult:
    full_text: str
    detected_script: str
    mean_confidence: float
    fields: tuple[FieldResult, ...]


@dataclass(frozen=True)
class OcrThresholds:
    review: float
    auto_accept: float
    document_rejection: float

    def __post_init__(self) -> None:
        for name, value in (
            ("review", self.review),
            ("auto_accept", self.auto_accept),
            ("document_rejection", self.document_rejection),
        ):
            if value < 0 or value > 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.review >= self.auto_accept:
            raise ValueError("review threshold must be below auto_accept threshold")


@dataclass(frozen=True)
class AccuracyReportEvidence:
    extraction_model_version: str
    script_set_version: str
    measured_thresholds: Mapping[float, float]
    minimum_precision: float
    superseded_at: datetime | None = None

    def admits(self, threshold: float) -> bool:
        precision = self.measured_thresholds.get(threshold)
        return precision is not None and precision >= self.minimum_precision


@dataclass(frozen=True)
class AccuracyObservation:
    holdout_document_id: int
    field_name: str
    script: str
    confidence: float
    extracted_value: str
    expected_value: str

    @property
    def correct(self) -> bool:
        return exact_match(self.extracted_value, self.expected_value)


@dataclass(frozen=True)
class AccuracySummary:
    accuracy_by_field: dict[str, float]
    accuracy_by_script: dict[str, float]
    holdout_document_count: int
    labelled_instance_count_by_field: dict[str, int]
    precision_at_threshold: dict[str, dict[str, object]]


@dataclass(frozen=True)
class ReviewDecision:
    review_state: str
    reason: str | None


@dataclass(frozen=True)
class AccuracyMeasurementDependencies:
    store: DocumentStore
    recognizer: Recognizer
    thresholds: Sequence[float]
    holdout_manifest_hash: str
    measurement_date: date


AccuracyDependencyFactory = Callable[
    [str, str],
    AccuracyMeasurementDependencies,
]

_accuracy_dependency_factory: AccuracyDependencyFactory | None = None


def configure_accuracy_measurement(
    factory: AccuracyDependencyFactory | None,
) -> AccuracyDependencyFactory | None:
    """Install the deployment-specific holdout measurement wiring.

    The measurement process owns holdout-storage credentials. Keeping that wiring
    outside import time preserves the per-process credential split while still
    making the Celery task execute the real orchestration when configured.
    """
    global _accuracy_dependency_factory
    previous = _accuracy_dependency_factory
    _accuracy_dependency_factory = factory
    return previous


def review_state_for(
    confidence: float,
    thresholds: OcrThresholds,
    report: AccuracyReportEvidence | None,
) -> ReviewDecision:
    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be in [0, 1]")
    if confidence < thresholds.review:
        return ReviewDecision(MANUAL_ENTRY_REQUIRED, BELOW_REVIEW_THRESHOLD)
    if confidence < thresholds.auto_accept:
        return ReviewDecision(PENDING_REVIEW, None)
    if report is None or report.superseded_at is not None:
        return ReviewDecision(PENDING_REVIEW, NO_CURRENT_ACCURACY_REPORT)
    if not report.admits(thresholds.auto_accept):
        return ReviewDecision(PENDING_REVIEW, REPORT_DOES_NOT_COVER_THRESHOLD)
    return ReviewDecision(AUTO_ACCEPTED, None)


def exact_match(extracted: str, expected: str) -> bool:
    return extracted.strip() == expected.strip()


def summarise_accuracy(
    observations: Sequence[AccuracyObservation],
    *,
    thresholds: Sequence[float],
) -> AccuracySummary:
    rows = tuple(observations)
    return AccuracySummary(
        accuracy_by_field=_mean_by(rows, key=lambda row: row.field_name),
        accuracy_by_script=_mean_by(rows, key=lambda row: row.script),
        holdout_document_count=len({row.holdout_document_id for row in rows}),
        labelled_instance_count_by_field=_count_by(rows, key=lambda row: row.field_name),
        precision_at_threshold={
            _threshold_key(threshold): {
                "overall": _precision(
                    tuple(row for row in rows if row.confidence >= threshold)
                ),
                "by_field": _precision_by(
                    rows,
                    threshold=threshold,
                    key=lambda row: row.field_name,
                ),
                "by_script": _precision_by(
                    rows,
                    threshold=threshold,
                    key=lambda row: row.script,
                ),
            }
            for threshold in thresholds
        },
    )


def record_accuracy_report(
    session: Session,
    *,
    extraction_model_version: str,
    script_set_version: str,
    holdout_manifest_hash: str,
    measurement_date,
    summary: AccuracySummary,
) -> ExtractionAccuracyReport:
    values = {
        "extraction_model_version": extraction_model_version,
        "script_set_version": script_set_version,
        "holdout_manifest_hash": holdout_manifest_hash,
        "accuracy_by_field": summary.accuracy_by_field,
        "accuracy_by_script": summary.accuracy_by_script,
        "holdout_document_count": summary.holdout_document_count,
        "labelled_instance_count_by_field": summary.labelled_instance_count_by_field,
        "precision_at_threshold": summary.precision_at_threshold,
        "measurement_date": measurement_date,
    }
    inserted_id = session.execute(
        pg_insert(ExtractionAccuracyReport)
        .values(**values)
        .on_conflict_do_nothing(constraint="extraction_accuracy_report_idempotency")
        .returning(ExtractionAccuracyReport.id)
    ).scalar_one_or_none()
    if inserted_id is not None:
        return session.get(ExtractionAccuracyReport, inserted_id)
    return session.execute(
        select(ExtractionAccuracyReport).where(
            ExtractionAccuracyReport.extraction_model_version == extraction_model_version,
            ExtractionAccuracyReport.script_set_version == script_set_version,
            ExtractionAccuracyReport.holdout_manifest_hash == holdout_manifest_hash,
        )
    ).scalar_one()


def measure_holdout_accuracy(
    session: Session,
    *,
    extraction_model_version: str,
    script_set_version: str,
    holdout_manifest_hash: str,
    measurement_date: date,
    store: DocumentStore,
    recognizer: Recognizer,
    thresholds: Sequence[float],
) -> ExtractionAccuracyReport:
    observations = collect_holdout_observations(
        session,
        holdout_manifest_hash=holdout_manifest_hash,
        store=store,
        recognizer=recognizer,
    )
    summary = summarise_accuracy(observations, thresholds=thresholds)
    return record_accuracy_report(
        session,
        extraction_model_version=extraction_model_version,
        script_set_version=script_set_version,
        holdout_manifest_hash=holdout_manifest_hash,
        measurement_date=measurement_date,
        summary=summary,
    )


def collect_holdout_observations(
    session: Session,
    *,
    holdout_manifest_hash: str,
    store: DocumentStore,
    recognizer: Recognizer,
) -> tuple[AccuracyObservation, ...]:
    holdout_documents = tuple(
        session.execute(
            select(HoldoutDocument).where(
                HoldoutDocument.manifest_hash == holdout_manifest_hash
            )
        ).scalars()
    )
    if not holdout_documents:
        return ()

    labels = tuple(
        session.execute(
            select(HoldoutLabel).where(
                HoldoutLabel.holdout_document_id.in_(
                    document.id for document in holdout_documents
                )
            )
        ).scalars()
    )
    labels_by_document: dict[int, dict[str, str]] = {}
    for label in labels:
        labels_by_document.setdefault(label.holdout_document_id, {})[
            label.field_name
        ] = label.expected_value

    observations: list[AccuracyObservation] = []
    for document in holdout_documents:
        document_bytes = store.get_object(key=document.object_key)
        result = recognizer.recognise(
            document_bytes,
            script=document.detected_script,
        )
        expected_by_field = labels_by_document.get(document.id, {})
        for field in result.fields:
            expected_value = expected_by_field.get(field.field_name)
            if expected_value is None:
                continue
            observations.append(
                AccuracyObservation(
                    holdout_document_id=document.id,
                    field_name=field.field_name,
                    script=document.detected_script,
                    confidence=field.confidence,
                    extracted_value=field.extracted_value or "",
                    expected_value=expected_value,
                )
            )
    return tuple(observations)


def supersede_accuracy_reports(
    session: Session,
    *,
    occurrence_time: datetime,
    extraction_model_version: str | None = None,
    script_set_version: str | None = None,
) -> int:
    stmt = select(ExtractionAccuracyReport).where(
        ExtractionAccuracyReport.superseded_at.is_(None)
    )
    if extraction_model_version is not None:
        stmt = stmt.where(
            ExtractionAccuracyReport.extraction_model_version == extraction_model_version
        )
    if script_set_version is not None:
        stmt = stmt.where(ExtractionAccuracyReport.script_set_version == script_set_version)
    reports = list(session.execute(stmt).scalars())
    for report in reports:
        report.superseded_at = occurrence_time
    session.flush()
    return len(reports)


def admit_extracted_value(field: ExtractedField) -> str | None:
    if field.review_state not in ADMITTED_REVIEW_STATES:
        raise ExtractedFieldNotAdmitted(field_id=field.id, review_state=field.review_state)
    return field.extracted_value


def confirm_field(
    session: Session,
    *,
    field_id: int,
    expected_version: int,
    actor: Actor,
    occurrence_time: datetime,
) -> ExtractedField:
    field = _load_field(session, field_id)
    prior_review_state = field.review_state
    updated = _update_field_review(
        session,
        field,
        expected_version=expected_version,
        changes={"review_state": CONFIRMED, "review_reason": None},
        actor=actor,
        occurrence_time=occurrence_time,
        event_type="EXTRACTED_FIELD_CONFIRMED",
    )
    _adjust_pending_review_count(session, field_id, prior_review_state, updated.review_state)
    return updated


def correct_field(
    session: Session,
    *,
    field_id: int,
    expected_version: int,
    corrected_value: str,
    actor: Actor,
    occurrence_time: datetime,
) -> ExtractedField:
    field = _load_field(session, field_id)
    prior_review_state = field.review_state
    updated = _update_field_review(
        session,
        field,
        expected_version=expected_version,
        changes={
            "extracted_value": corrected_value,
            "review_state": CORRECTED,
            "review_reason": None,
        },
        actor=actor,
        occurrence_time=occurrence_time,
        event_type="EXTRACTED_FIELD_CORRECTED",
    )
    _adjust_pending_review_count(session, field_id, prior_review_state, updated.review_state)
    return updated


def process_document(
    session: Session,
    *,
    document_id: int,
    store: DocumentStore,
    recognizer: Recognizer,
    thresholds: OcrThresholds,
    allowed_scripts: frozenset[str],
    accuracy_report: AccuracyReportEvidence | None,
    actor: Actor,
) -> Extraction | None:
    document = session.get(Document, document_id, populate_existing=True)
    if document is None:
        raise LookupError(f"document {document_id} does not exist")
    if document.processing_state not in PROCESSABLE_STATES:
        return None

    document = _update_document(
        session,
        document,
        changes={"processing_state": PROCESSING},
        actor=actor,
        event_type="EXTRACTION_STARTED",
    )
    document_bytes = store.get_object(key=document.object_key)
    try:
        script = recognizer.detect_script(document_bytes)
        if script not in allowed_scripts:
            _update_document(
                session,
                document,
                changes={"processing_state": UNSUPPORTED_SCRIPT, "detected_script": script},
                actor=actor,
                event_type="UNSUPPORTED_SCRIPT",
            )
            return None
        result = recognizer.recognise(document_bytes, script=script)
    except TerminalExtractionError as exc:
        _update_document(
            session,
            document,
            changes={"processing_state": EXTRACTION_FAILED, "failure_reason": str(exc)},
            actor=actor,
            event_type="EXTRACTION_FAILED",
        )
        return None

    if result.mean_confidence < thresholds.document_rejection:
        _update_document(
            session,
            document,
            changes={
                "processing_state": REJECTED_LOW_QUALITY,
                "detected_script": result.detected_script,
            },
            actor=actor,
            event_type="DOCUMENT_REUPLOAD_REQUESTED",
        )
        return None

    extraction = Extraction(
        document_id=document.id,
        extraction_model_version=recognizer.version,
        full_text=result.full_text,
        detected_script=result.detected_script,
        mean_confidence=result.mean_confidence,
    )
    try:
        with session.begin_nested():
            session.add(extraction)
            session.flush()
    except IntegrityError:
        return None
    for field in result.fields:
        decision = review_state_for(field.confidence, thresholds, accuracy_report)
        session.add(
            ExtractedField(
                extraction_id=extraction.id,
                field_name=field.field_name,
                extracted_value=(
                    None
                    if decision.review_state == MANUAL_ENTRY_REQUIRED
                    else field.extracted_value
                ),
                original_extracted_value=field.extracted_value,
                confidence=field.confidence,
                original_confidence=field.confidence,
                page_number=field.page_number,
                bbox_x1=field.bbox_x1,
                bbox_y1=field.bbox_y1,
                bbox_x2=field.bbox_x2,
                bbox_y2=field.bbox_y2,
                review_state=decision.review_state,
                review_reason=decision.reason,
                accuracy_report_id=None,
            )
        )
    session.flush()
    _update_document(
        session,
        document,
        changes={"processing_state": EXTRACTED, "detected_script": result.detected_script},
        actor=actor,
        event_type="EXTRACTION_COMPLETED",
    )
    return extraction


def _update_document(
    session: Session,
    document: Document,
    *,
    changes: Mapping[str, object],
    actor: Actor,
    event_type: str,
) -> Document:
    return VersionedRepository.update(
        session,
        entity_type=Document,
        entity_id=document.id,
        expected_version=document.entity_version,
        submitted_prior={key: getattr(document, key) for key in changes},
        changes=changes,
        actor=actor,
        occurrence_time=datetime.now(timezone.utc),
        event_type=event_type,
    )


def _load_field(session: Session, field_id: int) -> ExtractedField:
    field = session.get(ExtractedField, field_id, populate_existing=True)
    if field is None:
        raise LookupError(f"extracted field {field_id} does not exist")
    return field


def _update_field_review(
    session: Session,
    field: ExtractedField,
    *,
    expected_version: int,
    changes: Mapping[str, object],
    actor: Actor,
    occurrence_time: datetime,
    event_type: str,
) -> ExtractedField:
    return VersionedRepository.update(
        session,
        entity_type=ExtractedField,
        entity_id=field.id,
        expected_version=expected_version,
        submitted_prior={
            "extracted_value": field.extracted_value,
            "review_state": field.review_state,
        },
        changes=changes,
        actor=actor,
        occurrence_time=occurrence_time,
        event_type=event_type,
        review_conflict=ReviewConflictSpec(
            value_attribute="extracted_value",
            review_state_attribute="review_state",
        ),
    )


def _adjust_pending_review_count(
    session: Session,
    field_id: int,
    prior_review_state: str,
    updated_review_state: str,
) -> None:
    if prior_review_state not in {PENDING_REVIEW, MANUAL_ENTRY_REQUIRED}:
        return
    if updated_review_state in {PENDING_REVIEW, MANUAL_ENTRY_REQUIRED}:
        return
    case = _case_for_field(session, field_id)
    if case is not None:
        case.pending_review_count = max(0, (case.pending_review_count or 0) - 1)
        session.flush()


def _case_for_field(session: Session, field_id: int) -> AcquisitionCase | None:
    from sqlalchemy import select

    return session.execute(
        select(AcquisitionCase)
        .join(Document, Document.case_id == AcquisitionCase.id)
        .join(Extraction, Extraction.document_id == Document.id)
        .join(ExtractedField, ExtractedField.extraction_id == Extraction.id)
        .where(ExtractedField.id == field_id)
    ).scalar_one_or_none()


def _mean_by(
    rows: Sequence[AccuracyObservation],
    *,
    key,
) -> dict[str, float]:
    grouped: dict[str, list[AccuracyObservation]] = {}
    for row in rows:
        grouped.setdefault(str(key(row)), []).append(row)
    return {
        group_key: sum(1 for row in group if row.correct) / len(group)
        for group_key, group in grouped.items()
    }


def _count_by(
    rows: Sequence[AccuracyObservation],
    *,
    key,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        group_key = str(key(row))
        counts[group_key] = counts.get(group_key, 0) + 1
    return counts


def _precision(rows: Sequence[AccuracyObservation]) -> float | None:
    if not rows:
        return None
    return sum(1 for row in rows if row.correct) / len(rows)


def _precision_by(
    rows: Sequence[AccuracyObservation],
    *,
    threshold: float,
    key,
) -> dict[str, float | None]:
    grouped: dict[str, list[AccuracyObservation]] = {}
    for row in rows:
        grouped.setdefault(str(key(row)), []).append(row)
    return {
        group_key: _precision(tuple(row for row in group if row.confidence >= threshold))
        for group_key, group in grouped.items()
    }


def _threshold_key(threshold: float) -> str:
    return f"{threshold:g}"


@celery_app.task(
    bind=True,
    name="app.services.ocr.extract_document",
    autoretry_for=(TransientExtractionError,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=3,
)
def extract_document(self, document_id: int) -> int:
    """Registered OCR task shell.

    The recognizer and extraction persistence are wired by the later task-16
    subtasks; this shell pins the delivery contract now so outbox jobs route to a
    real registered task instead of a missing name.
    """
    with unit_of_work() as session:
        session.connection()
        return document_id


@celery_app.task(
    bind=True,
    name="app.services.ocr.measure_extraction_accuracy",
)
def measure_extraction_accuracy(
    self,
    extraction_model_version: str,
    script_set_version: str,
) -> int:
    if _accuracy_dependency_factory is None:
        raise RuntimeError("OCR accuracy measurement dependencies are not configured")
    dependencies = _accuracy_dependency_factory(
        extraction_model_version,
        script_set_version,
    )
    with unit_of_work() as session:
        report = measure_holdout_accuracy(
            session,
            extraction_model_version=extraction_model_version,
            script_set_version=script_set_version,
            holdout_manifest_hash=dependencies.holdout_manifest_hash,
            measurement_date=dependencies.measurement_date,
            store=dependencies.store,
            recognizer=dependencies.recognizer,
            thresholds=dependencies.thresholds,
        )
        return report.id
