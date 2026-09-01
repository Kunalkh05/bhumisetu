"""OCR schema, routing, and task-contract tests (task 16)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from contextlib import contextmanager
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.models.document import Document
from app.models.extraction import ExtractedField, Extraction
from app.models.extraction_accuracy_report import ExtractionAccuracyReport
from app.models.holdout import HoldoutDocument, HoldoutLabel
from app.services.document import DOCUMENT_QUEUED, EXTRACT_DOCUMENT_TASK
from app.services import ocr
from app.services.ocr import (
    AUTO_ACCEPTED,
    BELOW_REVIEW_THRESHOLD,
    MANUAL_ENTRY_REQUIRED,
    NO_CURRENT_ACCURACY_REPORT,
    PENDING_REVIEW,
    REPORT_DOES_NOT_COVER_THRESHOLD,
    AccuracyMeasurementDependencies,
    AccuracyReportEvidence,
    AccuracyObservation,
    ExtractedFieldNotAdmitted,
    FieldResult,
    OcrThresholds,
    RecognitionResult,
    admit_extracted_value,
    collect_holdout_observations,
    configure_accuracy_measurement,
    confirm_field,
    correct_field,
    exact_match,
    measure_holdout_accuracy,
    process_document,
    review_state_for,
    summarise_accuracy,
)
from app.workers.celery_app import TASK_MODULES, celery_app


def test_extraction_schema_has_idempotency_and_review_constraints() -> None:
    extraction_constraints = {constraint.name for constraint in Extraction.__table__.constraints}
    field_constraints = {constraint.name for constraint in ExtractedField.__table__.constraints}

    assert "extraction_document_model_unique" in extraction_constraints
    assert "ck_extraction_extraction_mean_confidence_range" in extraction_constraints
    assert "ck_extracted_field_extracted_field_confidence_range" in field_constraints
    assert "ck_extracted_field_extracted_field_original_confidence_range" in field_constraints
    assert "ck_extracted_field_extracted_field_bbox_page_relative" in field_constraints
    assert "accuracy_report_id" in ExtractedField.__table__.columns


def test_holdout_and_report_schema_keeps_labels_out_of_git_shape() -> None:
    holdout_columns = set(HoldoutDocument.__table__.columns.keys())
    label_columns = set(HoldoutLabel.__table__.columns.keys())
    report_constraints = {constraint.name for constraint in ExtractionAccuracyReport.__table__.constraints}

    assert "object_key" in holdout_columns
    assert "expected_value" in label_columns
    assert "extraction_accuracy_report_idempotency" in report_constraints


def test_review_state_for_gates_auto_accept_on_current_accuracy_report() -> None:
    thresholds = OcrThresholds(review=0.60, auto_accept=0.95, document_rejection=0.50)
    stale_report = AccuracyReportEvidence(
        extraction_model_version="tesseract-5",
        script_set_version="dev-eng",
        measured_thresholds={0.95: 0.99},
        minimum_precision=0.98,
        superseded_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    weak_report = AccuracyReportEvidence(
        extraction_model_version="tesseract-5",
        script_set_version="dev-eng",
        measured_thresholds={0.95: 0.97},
        minimum_precision=0.98,
    )
    admitting_report = AccuracyReportEvidence(
        extraction_model_version="tesseract-5",
        script_set_version="dev-eng",
        measured_thresholds={0.95: 0.98},
        minimum_precision=0.98,
    )

    assert review_state_for(0.2, thresholds, admitting_report).review_state == MANUAL_ENTRY_REQUIRED
    assert review_state_for(0.2, thresholds, admitting_report).reason == BELOW_REVIEW_THRESHOLD
    assert review_state_for(0.8, thresholds, admitting_report).review_state == PENDING_REVIEW
    assert review_state_for(0.99, thresholds, None).reason == NO_CURRENT_ACCURACY_REPORT
    assert review_state_for(0.99, thresholds, stale_report).reason == NO_CURRENT_ACCURACY_REPORT
    assert review_state_for(0.99, thresholds, weak_report).reason == REPORT_DOES_NOT_COVER_THRESHOLD
    assert review_state_for(0.99, thresholds, admitting_report).review_state == AUTO_ACCEPTED


@given(
    review=st.floats(min_value=0, max_value=0.8, allow_nan=False, allow_infinity=False),
    gap=st.floats(min_value=0.01, max_value=0.19, allow_nan=False, allow_infinity=False),
    low=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    high=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_property_review_state_is_total_and_monotone(
    review: float,
    gap: float,
    low: float,
    high: float,
) -> None:
    auto_accept = min(review + gap, 1.0)
    if review >= auto_accept:
        pytest.skip("generated threshold pair is not valid")
    thresholds = OcrThresholds(
        review=review,
        auto_accept=auto_accept,
        document_rejection=max(0.0, review / 2),
    )
    report = AccuracyReportEvidence(
        extraction_model_version="tesseract-5",
        script_set_version="dev-eng",
        measured_thresholds={auto_accept: 1.0},
        minimum_precision=0.98,
    )

    left_confidence, right_confidence = sorted((low, high))
    left = review_state_for(left_confidence, thresholds, report)
    right = review_state_for(right_confidence, thresholds, report)
    intervention_rank = {
        MANUAL_ENTRY_REQUIRED: 2,
        PENDING_REVIEW: 1,
        AUTO_ACCEPTED: 0,
    }

    assert left.review_state in intervention_rank
    assert right.review_state in intervention_rank
    assert intervention_rank[right.review_state] <= intervention_rank[left.review_state]


@given(
    value=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),
            blacklist_characters=("\x00",),
        ),
        max_size=40,
    )
)
def test_property_exact_match_trims_only(value: str) -> None:
    assert exact_match(f"  {value}\n", value)
    assert exact_match(value.upper(), value) is (value.upper().strip() == value.strip())


def test_exact_match_does_not_unicode_normalise() -> None:
    assert exact_match("é", "e\u0301") is False
    assert exact_match("क्‍ष", "क्ष") is False


@given(
    observations=st.lists(
        st.builds(
            AccuracyObservation,
            holdout_document_id=st.integers(min_value=1, max_value=5),
            field_name=st.sampled_from(["owner_name", "survey_number", "extent"]),
            script=st.sampled_from(["dev", "eng"]),
            confidence=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
            extracted_value=st.sampled_from(["Asha", "Ravi", "77", "88", ""]),
            expected_value=st.sampled_from(["Asha", "Ravi", "77", "88", ""]),
        ),
        min_size=1,
        max_size=25,
    ),
    threshold=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_property_accuracy_summary_matches_independent_recount(
    observations: list[AccuracyObservation],
    threshold: float,
) -> None:
    summary = summarise_accuracy(observations, thresholds=(threshold,))
    admitted = [row for row in observations if row.confidence >= threshold]
    expected_overall = (
        None
        if not admitted
        else sum(1 for row in admitted if row.correct) / len(admitted)
    )

    assert summary.holdout_document_count == len({row.holdout_document_id for row in observations})
    assert summary.precision_at_threshold[f"{threshold:g}"]["overall"] == expected_overall
    for field_name in {row.field_name for row in observations}:
        field_rows = [row for row in observations if row.field_name == field_name]
        assert summary.labelled_instance_count_by_field[field_name] == len(field_rows)
        assert summary.accuracy_by_field[field_name] == (
            sum(1 for row in field_rows if row.correct) / len(field_rows)
        )


def test_extract_document_task_is_registered_with_retry_contract() -> None:
    assert "app.services.ocr" in TASK_MODULES
    task = celery_app.tasks["app.services.ocr.extract_document"]

    assert task.autoretry_for == (ocr.TransientExtractionError,)
    assert task.retry_backoff == 1
    assert task.retry_jitter is True
    assert task.max_retries == 3
    assert EXTRACT_DOCUMENT_TASK == task.name


def test_measure_extraction_accuracy_task_is_registered_on_bulk_route() -> None:
    task = celery_app.tasks["app.services.ocr.measure_extraction_accuracy"]

    assert task.name == "app.services.ocr.measure_extraction_accuracy"


def test_collect_holdout_observations_matches_recognized_fields_to_labels() -> None:
    session = FakeHoldoutSession(
        documents=[
            HoldoutDocument(
                id=1,
                object_key="holdout/dev/1.pdf",
                detected_script="dev",
                document_type="award",
                manifest_hash="manifest-a",
            )
        ],
        labels=[
            HoldoutLabel(
                holdout_document_id=1,
                field_name="owner_name",
                expected_value="Asha",
            ),
            HoldoutLabel(
                holdout_document_id=1,
                field_name="survey_number",
                expected_value="77",
            ),
        ],
    )
    recognizer = FakeRecognizer(
        script="dev",
        result=RecognitionResult(
            full_text="Asha 78",
            detected_script="dev",
            mean_confidence=0.9,
            fields=(
                FieldResult("owner_name", " Asha ", 0.99, 1, 0.1, 0.1, 0.2, 0.2),
                FieldResult("survey_number", "78", 0.95, 1, 0.3, 0.3, 0.4, 0.4),
                FieldResult("unlabelled", "ignored", 0.9, 1, 0.5, 0.5, 0.6, 0.6),
            ),
        ),
    )

    observations = collect_holdout_observations(
        session,  # type: ignore[arg-type]
        holdout_manifest_hash="manifest-a",
        store=FakeStore(b"holdout-bytes"),
        recognizer=recognizer,
    )

    assert [(row.field_name, row.correct) for row in observations] == [
        ("owner_name", True),
        ("survey_number", False),
    ]
    assert session.executions == 2


def test_measure_holdout_accuracy_summarises_and_records_report(monkeypatch) -> None:
    session = FakeHoldoutSession(
        documents=[
            HoldoutDocument(
                id=1,
                object_key="holdout/dev/1.pdf",
                detected_script="dev",
                document_type="award",
                manifest_hash="manifest-a",
            )
        ],
        labels=[
            HoldoutLabel(
                holdout_document_id=1,
                field_name="owner_name",
                expected_value="Asha",
            )
        ],
    )
    recognizer = FakeRecognizer(
        script="dev",
        result=RecognitionResult(
            full_text="Asha",
            detected_script="dev",
            mean_confidence=0.9,
            fields=(FieldResult("owner_name", "Asha", 0.99, 1, 0.1, 0.1, 0.2, 0.2),),
        ),
    )
    recorded: dict[str, object] = {}

    def _record(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        recorded.update(kwargs)
        return ExtractionAccuracyReport(id=44)

    monkeypatch.setattr("app.services.ocr.record_accuracy_report", _record)

    report = measure_holdout_accuracy(
        session,  # type: ignore[arg-type]
        extraction_model_version="tesseract-5",
        script_set_version="dev-eng",
        holdout_manifest_hash="manifest-a",
        measurement_date=date(2024, 6, 1),
        store=FakeStore(b"holdout-bytes"),
        recognizer=recognizer,
        thresholds=(0.95,),
    )

    summary = recorded["summary"]
    assert report.id == 44
    assert recorded["holdout_manifest_hash"] == "manifest-a"
    assert summary.holdout_document_count == 1
    assert summary.precision_at_threshold["0.95"]["overall"] == 1.0


def test_measure_extraction_accuracy_task_invokes_configured_runner(monkeypatch) -> None:
    session = object()
    calls: list[dict[str, object]] = []

    @contextmanager
    def _uow():
        yield session

    def _factory(model_version: str, script_set_version: str):
        assert model_version == "tesseract-5"
        assert script_set_version == "dev-eng"
        return AccuracyMeasurementDependencies(
            store=FakeStore(b"holdout"),
            recognizer=FakeRecognizer(script="dev"),
            thresholds=(0.95,),
            holdout_manifest_hash="manifest-a",
            measurement_date=date(2024, 6, 1),
        )

    def _measure(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        calls.append({"session": session_arg, **kwargs})
        return ExtractionAccuracyReport(id=77)

    previous = configure_accuracy_measurement(_factory)
    monkeypatch.setattr("app.services.ocr.unit_of_work", _uow)
    monkeypatch.setattr("app.services.ocr.measure_holdout_accuracy", _measure)
    try:
        result = ocr.measure_extraction_accuracy.run("tesseract-5", "dev-eng")
    finally:
        configure_accuracy_measurement(previous)

    assert result == 77
    assert calls[0]["session"] is session
    assert calls[0]["holdout_manifest_hash"] == "manifest-a"


def test_accuracy_summary_recounts_fields_scripts_documents_and_thresholds() -> None:
    observations = (
        AccuracyObservation(1, "owner_name", "dev", 0.99, " Asha ", "Asha"),
        AccuracyObservation(1, "survey_number", "dev", 0.70, "77", "78"),
        AccuracyObservation(2, "owner_name", "eng", 0.40, "Ravi", "Ravi"),
    )

    summary = summarise_accuracy(observations, thresholds=(0.5, 0.95))

    assert summary.holdout_document_count == 2
    assert summary.labelled_instance_count_by_field == {"owner_name": 2, "survey_number": 1}
    assert summary.accuracy_by_field == {"owner_name": 1.0, "survey_number": 0.0}
    assert summary.accuracy_by_script == {"dev": 0.5, "eng": 1.0}
    assert summary.precision_at_threshold["0.5"]["overall"] == 0.5
    assert summary.precision_at_threshold["0.95"]["overall"] == 1.0
    assert summary.precision_at_threshold["0.95"]["by_script"] == {"dev": 1.0, "eng": None}


def test_process_document_records_unsupported_script_without_recognition(monkeypatch) -> None:
    document = _document(state=DOCUMENT_QUEUED)
    session = FakeOcrSession(document=document)
    recognizer = FakeRecognizer(script="arab")
    events: list[str] = []

    _patch_document_update(monkeypatch, events)

    result = process_document(
        session,  # type: ignore[arg-type]
        document_id=7,
        store=FakeStore(b"scan"),
        recognizer=recognizer,
        thresholds=OcrThresholds(review=0.6, auto_accept=0.95, document_rejection=0.5),
        allowed_scripts=frozenset({"dev", "eng"}),
        accuracy_report=None,
        actor=Actor(),
    )

    assert result is None
    assert recognizer.recognised is False
    assert document.processing_state == ocr.UNSUPPORTED_SCRIPT
    assert document.detected_script == "arab"
    assert events == ["EXTRACTION_STARTED", "UNSUPPORTED_SCRIPT"]


def test_process_document_writes_extraction_fields_and_discards_low_confidence(
    monkeypatch,
) -> None:
    document = _document(state=DOCUMENT_QUEUED)
    session = FakeOcrSession(document=document)
    fields = (
        FieldResult("owner_name", "Asha", 0.99, 1, 0.1, 0.1, 0.2, 0.2),
        FieldResult("survey_number", "77", 0.2, 1, 0.3, 0.3, 0.4, 0.4),
    )
    recognizer = FakeRecognizer(
        script="dev",
        result=RecognitionResult(
            full_text="Asha 77",
            detected_script="dev",
            mean_confidence=0.8,
            fields=fields,
        ),
    )
    events: list[str] = []

    _patch_document_update(monkeypatch, events)

    extraction = process_document(
        session,  # type: ignore[arg-type]
        document_id=7,
        store=FakeStore(b"scan"),
        recognizer=recognizer,
        thresholds=OcrThresholds(review=0.6, auto_accept=0.95, document_rejection=0.5),
        allowed_scripts=frozenset({"dev", "eng"}),
        accuracy_report=AccuracyReportEvidence(
            extraction_model_version="tesseract-5",
            script_set_version="dev-eng",
            measured_thresholds={0.95: 0.99},
            minimum_precision=0.98,
        ),
        actor=Actor(),
    )

    assert extraction is not None
    assert document.processing_state == ocr.EXTRACTED
    assert [type(row) for row in session.added] == [Extraction, ExtractedField, ExtractedField]
    accepted, discarded = session.added[1], session.added[2]
    assert accepted.extracted_value == "Asha"
    assert accepted.review_state == AUTO_ACCEPTED
    assert discarded.extracted_value is None
    assert discarded.original_extracted_value == "77"
    assert discarded.review_state == MANUAL_ENTRY_REQUIRED
    assert events == ["EXTRACTION_STARTED", "EXTRACTION_COMPLETED"]


def test_admit_extracted_value_requires_accepted_or_reviewed_state() -> None:
    field = ExtractedField(id=3, extracted_value="Asha", review_state=PENDING_REVIEW)

    with pytest.raises(ExtractedFieldNotAdmitted):
        admit_extracted_value(field)

    field.review_state = AUTO_ACCEPTED
    assert admit_extracted_value(field) == "Asha"


def test_confirm_and_correct_use_versioned_review_conflict(monkeypatch) -> None:
    field = ExtractedField(
        id=3,
        extraction_id=100,
        field_name="owner_name",
        extracted_value="Asha",
        original_extracted_value="Asha",
        confidence=0.8,
        original_confidence=0.8,
        page_number=1,
        bbox_x1=0.1,
        bbox_y1=0.1,
        bbox_x2=0.2,
        bbox_y2=0.2,
        review_state=PENDING_REVIEW,
        entity_version=4,
    )
    session = FakeReviewSession(field=field)
    calls: list[dict] = []

    def _update(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        for key, value in kwargs["changes"].items():
            setattr(field, key, value)
        field.entity_version += 1
        return field

    monkeypatch.setattr("app.services.ocr.VersionedRepository.update", _update)
    monkeypatch.setattr("app.services.ocr._case_for_field", lambda session_arg, field_id: None)

    confirm_field(
        session,  # type: ignore[arg-type]
        field_id=3,
        expected_version=4,
        actor=Actor(),
        occurrence_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
    )
    corrected = correct_field(
        session,  # type: ignore[arg-type]
        field_id=3,
        expected_version=5,
        corrected_value="Asha Rao",
        actor=Actor(),
        occurrence_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
    )

    assert corrected.extracted_value == "Asha Rao"
    assert calls[0]["changes"]["review_state"] == ocr.CONFIRMED
    assert calls[1]["changes"]["review_state"] == ocr.CORRECTED
    assert [call["event_type"] for call in calls] == [
        "EXTRACTED_FIELD_CONFIRMED",
        "EXTRACTED_FIELD_CORRECTED",
    ]
    assert all(call["review_conflict"] is not None for call in calls)


@given(
    original=st.text(max_size=20),
    corrected=st.text(max_size=20),
    confidence=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
def test_property_correction_preserves_original_extraction(
    monkeypatch,
    original: str,
    corrected: str,
    confidence: float,
) -> None:
    field = ExtractedField(
        id=3,
        extraction_id=100,
        field_name="owner_name",
        extracted_value=original,
        original_extracted_value=original,
        confidence=confidence,
        original_confidence=confidence,
        page_number=1,
        bbox_x1=0.1,
        bbox_y1=0.1,
        bbox_x2=0.2,
        bbox_y2=0.2,
        review_state=PENDING_REVIEW,
        entity_version=4,
    )
    session = FakeReviewSession(field=field)

    def _update(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        for key, value in kwargs["changes"].items():
            setattr(field, key, value)
        return field

    monkeypatch.setattr("app.services.ocr.VersionedRepository.update", _update)
    monkeypatch.setattr("app.services.ocr._case_for_field", lambda session_arg, field_id: None)

    updated = correct_field(
        session,  # type: ignore[arg-type]
        field_id=3,
        expected_version=4,
        corrected_value=corrected,
        actor=Actor(),
        occurrence_time=datetime(2024, 5, 2, tzinfo=timezone.utc),
    )

    assert updated.extracted_value == corrected
    assert updated.original_extracted_value == original
    assert updated.original_confidence == confidence


class Actor:
    kind = "SERVICE"
    id = "ocr-worker"


class FakeStore:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def get_object(self, *, key: str) -> bytes:
        return self.body


class FakeRecognizer:
    version = "tesseract-5"

    def __init__(
        self,
        *,
        script: str,
        result: RecognitionResult | None = None,
    ) -> None:
        self.script = script
        self.result = result
        self.recognised = False

    def detect_script(self, document_bytes: bytes) -> str:
        return self.script

    def recognise(self, document_bytes: bytes, *, script: str) -> RecognitionResult:
        self.recognised = True
        assert script == self.script
        return self.result or RecognitionResult("", script, 1.0, ())


class FakeOcrSession:
    def __init__(self, *, document: Document) -> None:
        self.document = document
        self.added: list[object] = []

    def get(self, entity_type, entity_id, **kwargs):  # type: ignore[no-untyped-def]
        if entity_type is Document:
            return self.document
        return None

    def add(self, value: object) -> None:
        if isinstance(value, Extraction):
            value.id = 100
        self.added.append(value)

    def flush(self) -> None:
        pass

    @contextmanager
    def begin_nested(self):  # type: ignore[no-untyped-def]
        yield


class FakeScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalars(self):  # type: ignore[no-untyped-def]
        return iter(self.rows)


class FakeHoldoutSession:
    def __init__(
        self,
        *,
        documents: list[HoldoutDocument],
        labels: list[HoldoutLabel],
    ) -> None:
        self.documents = documents
        self.labels = labels
        self.executions = 0

    def execute(self, stmt):  # type: ignore[no-untyped-def]
        self.executions += 1
        if self.executions == 1:
            return FakeScalarResult(self.documents)
        return FakeScalarResult(self.labels)


class FakeReviewSession:
    def __init__(self, *, field: ExtractedField) -> None:
        self.field = field

    def get(self, entity_type, entity_id, **kwargs):  # type: ignore[no-untyped-def]
        if entity_type is ExtractedField:
            return self.field
        return None

    def flush(self) -> None:
        pass


def _document(*, state: str) -> Document:
    return Document(
        id=7,
        case_id=1,
        parcel_id=None,
        document_type="notice",
        original_filename="notice.pdf",
        byte_size=4,
        content_type="application/pdf",
        checksum_sha256=b"abcd",
        object_key="cases/1/abcd",
        uploaded_by=UUID("00000000-0000-0000-0000-000000000001"),
        uploaded_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        processing_state=state,
        entity_version=1,
    )


def _patch_document_update(monkeypatch, events: list[str]) -> None:
    def _update(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        events.append(kwargs["event_type"])
        document = session_arg.document
        for key, value in kwargs["changes"].items():
            setattr(document, key, value)
        document.entity_version += 1
        return document

    monkeypatch.setattr("app.services.ocr.VersionedRepository.update", _update)
