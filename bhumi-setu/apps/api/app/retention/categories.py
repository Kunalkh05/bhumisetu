"""Declarative attribute classification — the one registry (§17.1).

Every stored attribute belongs to exactly one ``Data_Category`` (R32.2). That
assignment is data, not logic scattered through services: one dict keyed by
``(table, column)``, in one file, so the retention sweep, the redaction gate, the
DSAR response, and the feature-disjointness guard all read the same source rather
than four drifting copies.

Why a raised ``KeyError`` rather than a default
----------------------------------------------

:func:`category_of` looks the attribute up with ``CATEGORY_MAP[(table, column)]``
and lets a missing key raise. There is deliberately no ``.get(..., default)``. A
default would classify an unmapped column as *something* — and if that something
were "not personal", a newly added ``contact_mobile`` column would be treated as
non-personal and never erased, silently. Failing loud is the point: task 25.2
turns this into a build failure by walking ``Base.metadata`` and asserting every
column has an entry. Until then the loud failure is a runtime ``KeyError``, which
is still far better than a wrong answer.

Two entry kinds beyond a plain category
---------------------------------------

Most attributes map to a fixed category string. Two do not, and both resolve from
the stored row rather than from ``(table, column)`` alone:

* :class:`Discriminated` — the category depends on the value of another column.
  ``extracted_field.extracted_value`` is ``OWNER_IDENTITY`` when the extracted
  ``field_name`` is ``owner_name`` but ``LAND_RECORD`` when it is
  ``survey_number``. Its explicit ``default`` is *not* the forbidden silent
  default above: it is a deliberate classification for extracted fields the map
  does not name specifically, chosen as the safe non-erasable ``LAND_RECORD``.
* :class:`Reference` — the category is carried by the row itself, in another
  column. ``personal_datum.value_ciphertext`` holds a value of whatever
  ``data_category`` its row records, so the category *follows* that column.

Scope at task 3.3
-----------------

This file carries the **personal-data entries** the event log must externalise —
owner identity and contact attributes, the objector's name, the value-dependent
extracted field, the ``personal_datum`` referent, and the ML feature row — plus
the mechanism above. It is **not** yet complete over the whole schema; most of the
entities these entries name (``ownership_record``, ``objection``,
``extracted_field``, ``ml_feature_row``) are declared in later tasks, and the map
is keyed by string tuples precisely so a classification can be recorded before its
table exists. Task 25.2 completes the map to full schema coverage and adds the
metadata-walk test that fails the build on any unclassified column.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "NOT_PERSONAL",
    "OWNER_CONTACT",
    "OWNER_IDENTITY",
    "MODEL_FEATURE",
    "LAND_RECORD",
    "DOCUMENT_CONTENT",
    "AUDIT_EVENT",
    "PERSONAL_DATA_CATEGORIES",
    "Discriminated",
    "Reference",
    "CATEGORY_MAP",
    "category_of",
    "personal_data_attributes",
]

# ---------------------------------------------------------------------------
# Data_Category names (Q10, resolved as the maintainer default)
# ---------------------------------------------------------------------------

#: The classification for an attribute that holds no personal data. Spelled out
#: rather than left implicit so 25.2's completeness walk can require a *positive*
#: classification for every column — silence is never "not personal".
NOT_PERSONAL = "NOT_PERSONAL_DATA"

# Personal data about a data subject. These are the erasable categories.
OWNER_CONTACT = "OWNER_CONTACT"
OWNER_IDENTITY = "OWNER_IDENTITY"
MODEL_FEATURE = "MODEL_FEATURE"

# Statutory record, retained without expiry (R32.11).
LAND_RECORD = "LAND_RECORD"
DOCUMENT_CONTENT = "DOCUMENT_CONTENT"
AUDIT_EVENT = "AUDIT_EVENT"

#: The categories that denote personal data. These are exactly Q10's erasable set
#: (``retention.erasable_categories`` defaults to this), and that is not a
#: coincidence: an attribute is "personal" for the purpose of the guards below
#: precisely because its value can be erased, and a feature or an unannotated
#: response field built on an erasable value is the failure those guards prevent.
#: Whether a category is *actually* erased at runtime is a ``Policy_Config``
#: decision (§17.2); this static set is what "personal" means to the code.
PERSONAL_DATA_CATEGORIES: frozenset[str] = frozenset(
    {OWNER_CONTACT, OWNER_IDENTITY, MODEL_FEATURE}
)


# ---------------------------------------------------------------------------
# The two value-dependent entry kinds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Discriminated:
    """A category decided by the value of another column on the same row.

    ``on`` names the discriminator column; ``by_value`` maps its value to a
    category; ``default`` classifies any value not listed. The default is an
    intentional classification (see the module docstring), not the silent default
    that :func:`category_of` refuses.
    """

    on: str
    by_value: Mapping[str, str]
    default: str

    def resolve(self, row: Mapping[str, Any] | None) -> str:
        if row is None:
            raise ValueError(
                f"cannot classify a Discriminated attribute without the row: "
                f"the category depends on column {self.on!r}"
            )
        # row[self.on] raises KeyError if the discriminator is absent — the right
        # failure, since the attribute genuinely cannot be classified without it.
        return self.by_value.get(row[self.on], self.default)

    def possible_categories(self) -> frozenset[str]:
        """Every category this entry could resolve to, used by the guards to decide
        whether the attribute is *potentially* personal."""
        return frozenset(self.by_value.values()) | {self.default}


@dataclass(frozen=True)
class Reference:
    """A category carried by the row itself, in the column named by ``follows``.

    Used for ``personal_datum.value_ciphertext``, whose row records its own
    ``data_category``. A ``personal_datum`` row only ever holds a personal
    category by construction, so an attribute classified this way is treated as
    personal by the guards below.
    """

    follows: str

    def resolve(self, row: Mapping[str, Any] | None) -> str:
        if row is None:
            raise ValueError(
                f"cannot classify a Reference attribute without the row: "
                f"the category is carried by column {self.follows!r}"
            )
        return row[self.follows]


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

#: The personal-data entries the event log must externalise, plus the two
#: value-dependent entries. Not yet complete over the schema — see the module
#: docstring and task 25.2. Keyed by ``(table, column)`` string tuples, so an
#: entry can be recorded before its table's model exists.
CATEGORY_MAP: dict[tuple[str, str], str | Discriminated | Reference] = {
    # administrative geography.
    ("administrative_area", "code"): LAND_RECORD,
    ("administrative_area", "area_type"): LAND_RECORD,
    ("administrative_area", "name"): LAND_RECORD,
    ("administrative_area", "parent_code"): LAND_RECORD,
    ("administrative_area", "state_key"): LAND_RECORD,
    ("administrative_area", "path"): LAND_RECORD,
    # immutable event log metadata. Payload personal values are externalised into
    # personal_datum and resolved there; the event row itself is retained.
    ("event", "id"): AUDIT_EVENT,
    ("event", "event_type"): AUDIT_EVENT,
    ("event", "entity_type"): AUDIT_EVENT,
    ("event", "entity_id"): AUDIT_EVENT,
    ("event", "case_id"): AUDIT_EVENT,
    ("event", "actor_type"): AUDIT_EVENT,
    ("event", "actor_id"): AUDIT_EVENT,
    ("event", "occurrence_time"): AUDIT_EVENT,
    ("event", "recording_time"): AUDIT_EVENT,
    ("event", "payload"): AUDIT_EVENT,
    ("event", "has_pd_refs"): AUDIT_EVENT,
    ("event", "entity_version_after"): AUDIT_EVENT,
    ("event", "provenance"): AUDIT_EVENT,
    ("event", "import_batch_id"): AUDIT_EVENT,
    ("event", "corrects_event_id"): AUDIT_EVENT,
    ("event", "txid"): AUDIT_EVENT,
    # operational audit/config tables.
    ("officer", "id"): AUDIT_EVENT,
    ("officer", "officer_code"): AUDIT_EVENT,
    ("officer", "display_name"): AUDIT_EVENT,
    ("officer", "designation"): AUDIT_EVENT,
    ("officer", "credential_hash"): AUDIT_EVENT,
    ("officer", "is_active"): AUDIT_EVENT,
    ("officer", "created_at"): AUDIT_EVENT,
    ("role", "id"): AUDIT_EVENT,
    ("role", "key"): AUDIT_EVENT,
    ("role", "name"): AUDIT_EVENT,
    ("role", "permissions"): AUDIT_EVENT,
    ("role", "created_at"): AUDIT_EVENT,
    ("officer_role", "officer_id"): AUDIT_EVENT,
    ("officer_role", "role_id"): AUDIT_EVENT,
    ("officer_role", "granted_at"): AUDIT_EVENT,
    ("jurisdiction_scope", "role_id"): AUDIT_EVENT,
    ("jurisdiction_scope", "area_code"): AUDIT_EVENT,
    ("jurisdiction_scope", "granted_at"): AUDIT_EVENT,
    ("policy_config", "id"): AUDIT_EVENT,
    ("policy_config", "policy_key"): AUDIT_EVENT,
    ("policy_config", "state_key"): AUDIT_EVENT,
    ("policy_config", "act_key"): AUDIT_EVENT,
    ("policy_config", "effective_from"): AUDIT_EVENT,
    ("policy_config", "value"): AUDIT_EVENT,
    ("policy_config", "justification_report_id"): AUDIT_EVENT,
    ("policy_config", "created_by"): AUDIT_EVENT,
    ("policy_config", "created_at"): AUDIT_EVENT,
    ("task_outbox", "id"): AUDIT_EVENT,
    ("task_outbox", "queue"): AUDIT_EVENT,
    ("task_outbox", "task_name"): AUDIT_EVENT,
    ("task_outbox", "kwargs"): AUDIT_EVENT,
    ("task_outbox", "idempotency_key"): AUDIT_EVENT,
    ("task_outbox", "enqueued_at"): AUDIT_EVENT,
    ("task_outbox", "created_at"): AUDIT_EVENT,
    # dashboard aggregates contain counters and model outputs, not raw personal
    # values; source personal data remains classified on its source table.
    ("dashboard_snapshot", "area_code"): NOT_PERSONAL,
    ("dashboard_snapshot", "metrics"): NOT_PERSONAL,
    ("dashboard_snapshot", "computed_at"): NOT_PERSONAL,
    ("dashboard_band_history", "id"): NOT_PERSONAL,
    ("dashboard_band_history", "area_code"): NOT_PERSONAL,
    ("dashboard_band_history", "month"): NOT_PERSONAL,
    ("dashboard_band_history", "band"): NOT_PERSONAL,
    ("dashboard_band_history", "case_count"): NOT_PERSONAL,
    ("dashboard_band_history", "computed_at"): NOT_PERSONAL,
    # land and case domain records.
    ("project", "id"): LAND_RECORD,
    ("project", "name"): LAND_RECORD,
    ("project", "implementing_authority"): LAND_RECORD,
    ("project", "area_code"): LAND_RECORD,
    ("project", "purpose_category"): LAND_RECORD,
    ("project", "sanctioned_extent"): LAND_RECORD,
    ("project", "extent_unit"): LAND_RECORD,
    ("project", "geom"): LAND_RECORD,
    ("land_parcel", "id"): LAND_RECORD,
    ("land_parcel", "state_key"): LAND_RECORD,
    ("land_parcel", "district"): LAND_RECORD,
    ("land_parcel", "tehsil"): LAND_RECORD,
    ("land_parcel", "village"): LAND_RECORD,
    ("land_parcel", "survey_number"): LAND_RECORD,
    ("land_parcel", "sub_division"): LAND_RECORD,
    ("land_parcel", "village_norm"): LAND_RECORD,
    ("land_parcel", "classification"): LAND_RECORD,
    ("land_parcel", "extent"): LAND_RECORD,
    ("land_parcel", "extent_unit"): LAND_RECORD,
    ("land_parcel", "area_code"): LAND_RECORD,
    ("land_parcel", "geom"): LAND_RECORD,
    ("land_parcel", "geodesic_area_sqm"): LAND_RECORD,
    ("land_parcel", "entity_version"): LAND_RECORD,
    ("acquisition_case", "id"): LAND_RECORD,
    ("acquisition_case", "case_reference"): LAND_RECORD,
    ("acquisition_case", "project_id"): LAND_RECORD,
    ("acquisition_case", "state_key"): LAND_RECORD,
    ("acquisition_case", "act_key"): LAND_RECORD,
    ("acquisition_case", "area_code"): LAND_RECORD,
    ("acquisition_case", "stage_key"): LAND_RECORD,
    ("acquisition_case", "stage_set_effective_from"): LAND_RECORD,
    ("acquisition_case", "stage_entered_on"): LAND_RECORD,
    ("acquisition_case", "stage_deadline"): LAND_RECORD,
    ("acquisition_case", "deadline_breached"): LAND_RECORD,
    ("acquisition_case", "is_terminal"): LAND_RECORD,
    ("acquisition_case", "terminal_event_id"): LAND_RECORD,
    ("acquisition_case", "open_blocking_count"): LAND_RECORD,
    ("acquisition_case", "undisposed_objection_count"): LAND_RECORD,
    ("acquisition_case", "pending_review_count"): LAND_RECORD,
    ("acquisition_case", "aggregate_awarded"): LAND_RECORD,
    ("acquisition_case", "aggregate_disbursed"): LAND_RECORD,
    ("acquisition_case", "risk_probability"): NOT_PERSONAL,
    ("acquisition_case", "risk_band"): NOT_PERSONAL,
    ("acquisition_case", "risk_model_version"): NOT_PERSONAL,
    ("acquisition_case", "risk_generated_at"): NOT_PERSONAL,
    ("acquisition_case", "risk_is_stale"): NOT_PERSONAL,
    ("acquisition_case", "risk_cutoff_source"): NOT_PERSONAL,
    ("acquisition_case", "priority_score"): NOT_PERSONAL,
    ("acquisition_case", "priority_weight_version"): NOT_PERSONAL,
    ("acquisition_case", "priority_computed_at"): NOT_PERSONAL,
    ("acquisition_case", "entity_version"): LAND_RECORD,
    ("case_parcel", "case_id"): LAND_RECORD,
    ("case_parcel", "parcel_id"): LAND_RECORD,
    # ownership_record — the landowner's identity and contact details (§17.1).
    ("ownership_record", "id"): LAND_RECORD,
    ("ownership_record", "parcel_id"): LAND_RECORD,
    ("ownership_record", "owner_name"): OWNER_IDENTITY,
    ("ownership_record", "government_identifier"): OWNER_IDENTITY,
    ("ownership_record", "owner_identity_key"): OWNER_IDENTITY,
    ("ownership_record", "contact_mobile"): OWNER_CONTACT,
    ("ownership_record", "contact_mobile_hash"): OWNER_CONTACT,
    ("ownership_record", "interest_type"): LAND_RECORD,
    ("ownership_record", "share"): LAND_RECORD,
    ("ownership_record", "valid_from"): LAND_RECORD,
    ("ownership_record", "valid_to"): LAND_RECORD,
    ("ownership_record", "validity"): LAND_RECORD,
    ("ownership_record", "entity_version"): LAND_RECORD,
    ("award", "id"): LAND_RECORD,
    ("award", "ownership_record_id"): LAND_RECORD,
    ("award", "total_amount"): LAND_RECORD,
    ("award", "currency"): LAND_RECORD,
    ("award", "determination_date"): LAND_RECORD,
    ("award", "determining_authority"): LAND_RECORD,
    ("award", "disbursement_state"): LAND_RECORD,
    ("award", "entity_version"): LAND_RECORD,
    ("award_component", "id"): LAND_RECORD,
    ("award_component", "award_id"): LAND_RECORD,
    ("award_component", "component_label"): LAND_RECORD,
    ("award_component", "amount"): LAND_RECORD,
    ("payout", "id"): LAND_RECORD,
    ("payout", "award_id"): LAND_RECORD,
    ("payout", "amount"): LAND_RECORD,
    ("payout", "payout_date"): LAND_RECORD,
    ("payout", "instrument_reference"): LAND_RECORD,
    ("payout", "beneficiary"): OWNER_IDENTITY,
    ("payout", "entity_version"): LAND_RECORD,
    # objection — the objector is a person.
    ("objection", "id"): LAND_RECORD,
    ("objection", "case_id"): LAND_RECORD,
    ("objection", "objector_name"): OWNER_IDENTITY,
    ("objection", "ownership_record_id"): LAND_RECORD,
    ("objection", "receipt_date"): LAND_RECORD,
    ("objection", "grounds_category"): LAND_RECORD,
    ("objection", "substance"): LAND_RECORD,
    ("objection", "governing_notice_id"): LAND_RECORD,
    ("objection", "window_state"): LAND_RECORD,
    ("objection", "disposal_deadline"): LAND_RECORD,
    ("objection", "is_disposal_overdue"): LAND_RECORD,
    ("objection", "disposal_outcome"): LAND_RECORD,
    ("objection", "disposal_date"): LAND_RECORD,
    ("objection", "disposal_reasons"): LAND_RECORD,
    ("objection", "deciding_officer_id"): LAND_RECORD,
    ("objection", "entity_version"): LAND_RECORD,
    ("statutory_notice", "id"): LAND_RECORD,
    ("statutory_notice", "case_id"): LAND_RECORD,
    ("statutory_notice", "notice_type"): LAND_RECORD,
    ("statutory_notice", "issuing_authority"): LAND_RECORD,
    ("statutory_notice", "issue_date"): LAND_RECORD,
    ("statutory_notice", "publication_mode"): LAND_RECORD,
    ("statutory_notice", "response_deadline"): LAND_RECORD,
    ("statutory_notice", "policy_snapshot_hash"): LAND_RECORD,
    ("statutory_notice", "breach_state"): LAND_RECORD,
    ("statutory_notice", "entity_version"): LAND_RECORD,
    ("notice_parcel", "notice_id"): LAND_RECORD,
    ("notice_parcel", "parcel_id"): LAND_RECORD,
    ("notice_service_record", "id"): LAND_RECORD,
    ("notice_service_record", "notice_id"): LAND_RECORD,
    ("notice_service_record", "ownership_record_id"): LAND_RECORD,
    ("notice_service_record", "service_date"): LAND_RECORD,
    ("notice_service_record", "service_mode"): LAND_RECORD,
    ("notice_service_record", "service_location"): LAND_RECORD,
    ("notice_service_record", "entity_version"): LAND_RECORD,
    # document — the object itself contains record scans and OCR source content.
    ("document", "id"): DOCUMENT_CONTENT,
    ("document", "case_id"): LAND_RECORD,
    ("document", "parcel_id"): LAND_RECORD,
    ("document", "document_type"): DOCUMENT_CONTENT,
    ("document", "object_key"): DOCUMENT_CONTENT,
    ("document", "original_filename"): LAND_RECORD,
    ("document", "byte_size"): DOCUMENT_CONTENT,
    ("document", "content_type"): DOCUMENT_CONTENT,
    ("document", "checksum_sha256"): DOCUMENT_CONTENT,
    ("document", "uploaded_by"): AUDIT_EVENT,
    ("document", "uploaded_at"): DOCUMENT_CONTENT,
    ("document", "processing_state"): DOCUMENT_CONTENT,
    ("document", "failure_reason"): DOCUMENT_CONTENT,
    ("document", "detected_script"): DOCUMENT_CONTENT,
    ("document", "entity_version"): DOCUMENT_CONTENT,
    # extracted_field — value-dependent: the category is decided by which field
    # was extracted, so it is resolved from the row.
    ("extracted_field", "id"): DOCUMENT_CONTENT,
    ("extracted_field", "extraction_id"): DOCUMENT_CONTENT,
    ("extracted_field", "field_name"): DOCUMENT_CONTENT,
    ("extracted_field", "extracted_value"): Discriminated(
        on="field_name",
        by_value={
            "owner_name": OWNER_IDENTITY,
            "father_name": OWNER_IDENTITY,
            "mobile": OWNER_CONTACT,
            "aadhaar": OWNER_IDENTITY,
            "survey_number": LAND_RECORD,
            "extent": LAND_RECORD,
        },
        default=LAND_RECORD,
    ),
    ("extracted_field", "original_extracted_value"): Discriminated(
        on="field_name",
        by_value={
            "owner_name": OWNER_IDENTITY,
            "father_name": OWNER_IDENTITY,
            "mobile": OWNER_CONTACT,
            "aadhaar": OWNER_IDENTITY,
            "survey_number": LAND_RECORD,
            "extent": LAND_RECORD,
        },
        default=LAND_RECORD,
    ),
    ("extracted_field", "confidence"): DOCUMENT_CONTENT,
    ("extracted_field", "original_confidence"): DOCUMENT_CONTENT,
    ("extracted_field", "page_number"): DOCUMENT_CONTENT,
    ("extracted_field", "bbox_x1"): DOCUMENT_CONTENT,
    ("extracted_field", "bbox_y1"): DOCUMENT_CONTENT,
    ("extracted_field", "bbox_x2"): DOCUMENT_CONTENT,
    ("extracted_field", "bbox_y2"): DOCUMENT_CONTENT,
    ("extracted_field", "review_state"): DOCUMENT_CONTENT,
    ("extracted_field", "review_reason"): DOCUMENT_CONTENT,
    ("extracted_field", "accuracy_report_id"): DOCUMENT_CONTENT,
    ("extracted_field", "entity_version"): DOCUMENT_CONTENT,
    ("extraction", "id"): DOCUMENT_CONTENT,
    ("extraction", "document_id"): DOCUMENT_CONTENT,
    ("extraction", "extraction_model_version"): DOCUMENT_CONTENT,
    ("extraction", "full_text"): DOCUMENT_CONTENT,
    ("extraction", "detected_script"): DOCUMENT_CONTENT,
    ("extraction", "mean_confidence"): DOCUMENT_CONTENT,
    ("extraction", "created_at"): DOCUMENT_CONTENT,
    ("extraction_accuracy_report", "id"): NOT_PERSONAL,
    ("extraction_accuracy_report", "extraction_model_version"): NOT_PERSONAL,
    ("extraction_accuracy_report", "script_set_version"): NOT_PERSONAL,
    ("extraction_accuracy_report", "holdout_manifest_hash"): NOT_PERSONAL,
    ("extraction_accuracy_report", "accuracy_by_field"): NOT_PERSONAL,
    ("extraction_accuracy_report", "accuracy_by_script"): NOT_PERSONAL,
    ("extraction_accuracy_report", "holdout_document_count"): NOT_PERSONAL,
    ("extraction_accuracy_report", "labelled_instance_count_by_field"): NOT_PERSONAL,
    ("extraction_accuracy_report", "precision_at_threshold"): NOT_PERSONAL,
    ("extraction_accuracy_report", "measurement_date"): NOT_PERSONAL,
    ("extraction_accuracy_report", "superseded_at"): NOT_PERSONAL,
    ("holdout_document", "id"): DOCUMENT_CONTENT,
    ("holdout_document", "object_key"): DOCUMENT_CONTENT,
    ("holdout_document", "detected_script"): DOCUMENT_CONTENT,
    ("holdout_document", "document_type"): DOCUMENT_CONTENT,
    ("holdout_document", "manifest_hash"): DOCUMENT_CONTENT,
    ("holdout_document", "created_at"): DOCUMENT_CONTENT,
    ("holdout_label", "holdout_document_id"): DOCUMENT_CONTENT,
    ("holdout_label", "field_name"): DOCUMENT_CONTENT,
    ("holdout_label", "expected_value"): Discriminated(
        on="field_name",
        by_value={
            "owner_name": OWNER_IDENTITY,
            "father_name": OWNER_IDENTITY,
            "mobile": OWNER_CONTACT,
            "aadhaar": OWNER_IDENTITY,
            "survey_number": LAND_RECORD,
            "extent": LAND_RECORD,
        },
        default=LAND_RECORD,
    ),
    # ml feature rows are erasable personal data under Q10 (MODEL_FEATURE); a
    # feature must never derive from another feature's stored value either.
    ("ml_feature_row", "id"): NOT_PERSONAL,
    ("ml_feature_row", "case_id"): NOT_PERSONAL,
    ("ml_feature_row", "reference_t"): NOT_PERSONAL,
    ("ml_feature_row", "as_of_mode"): NOT_PERSONAL,
    ("ml_feature_row", "feature_set_version"): NOT_PERSONAL,
    ("ml_feature_row", "label_definition_version"): NOT_PERSONAL,
    ("ml_feature_row", "features"): MODEL_FEATURE,
    ("ml_feature_row", "consumed_event_ids"): NOT_PERSONAL,
    ("ml_feature_row", "content_hash"): NOT_PERSONAL,
    ("ml_feature_row", "purpose"): NOT_PERSONAL,
    ("ml_feature_row", "created_at"): NOT_PERSONAL,
    ("ml_training_row", "feature_row_id"): NOT_PERSONAL,
    ("ml_training_row", "label"): NOT_PERSONAL,
    ("ml_training_row", "time_to_event_days"): NOT_PERSONAL,
    ("ml_training_row", "event_observed"): NOT_PERSONAL,
    ("ml_training_row", "label_definition_version"): NOT_PERSONAL,
    ("ml_training_row", "split"): NOT_PERSONAL,
    ("ml_model_version", "id"): NOT_PERSONAL,
    ("ml_model_version", "version"): NOT_PERSONAL,
    ("ml_model_version", "feature_set_version"): NOT_PERSONAL,
    ("ml_model_version", "label_definition_version"): NOT_PERSONAL,
    ("ml_model_version", "training_window_start"): NOT_PERSONAL,
    ("ml_model_version", "training_window_end"): NOT_PERSONAL,
    ("ml_model_version", "hyperparameters"): NOT_PERSONAL,
    ("ml_model_version", "metrics"): NOT_PERSONAL,
    ("ml_model_version", "baseline_metrics"): NOT_PERSONAL,
    ("ml_model_version", "train_base_rate"): NOT_PERSONAL,
    ("ml_model_version", "eval_base_rate"): NOT_PERSONAL,
    ("ml_model_version", "censored_count"): NOT_PERSONAL,
    ("ml_model_version", "censoring_rate"): NOT_PERSONAL,
    ("ml_model_version", "feature_reference_bins"): NOT_PERSONAL,
    ("ml_model_version", "promotion_state"): NOT_PERSONAL,
    ("ml_model_version", "promoted_by"): AUDIT_EVENT,
    ("ml_model_version", "promoted_at"): NOT_PERSONAL,
    ("ml_model_version", "artifact_object_key"): NOT_PERSONAL,
    ("ml_model_version", "superseded_by"): NOT_PERSONAL,
    ("ml_prediction", "id"): NOT_PERSONAL,
    ("ml_prediction", "case_id"): NOT_PERSONAL,
    ("ml_prediction", "model_version_id"): NOT_PERSONAL,
    ("ml_prediction", "feature_row_id"): NOT_PERSONAL,
    ("ml_prediction", "risk_probability"): NOT_PERSONAL,
    ("ml_prediction", "risk_band"): NOT_PERSONAL,
    ("ml_prediction", "cutoff_source"): NOT_PERSONAL,
    ("ml_prediction", "cutoff_set_version"): NOT_PERSONAL,
    ("ml_prediction", "reference_t"): NOT_PERSONAL,
    ("ml_prediction", "generated_at"): NOT_PERSONAL,
    ("ml_explanation_factor", "prediction_id"): NOT_PERSONAL,
    ("ml_explanation_factor", "rank"): NOT_PERSONAL,
    ("ml_explanation_factor", "feature_name"): NOT_PERSONAL,
    ("ml_explanation_factor", "label_key"): NOT_PERSONAL,
    ("ml_explanation_factor", "direction"): NOT_PERSONAL,
    ("ml_explanation_factor", "magnitude"): NOT_PERSONAL,
    ("ml_monitor_run", "id"): NOT_PERSONAL,
    ("ml_monitor_run", "model_version_id"): NOT_PERSONAL,
    ("ml_monitor_run", "kind"): NOT_PERSONAL,
    ("ml_monitor_run", "started_at"): NOT_PERSONAL,
    ("ml_monitor_run", "finished_at"): NOT_PERSONAL,
    ("ml_monitor_run", "state"): NOT_PERSONAL,
    ("ml_monitor_run", "withholding_reason"): NOT_PERSONAL,
    ("ml_monitor_run", "evaluable_case_count"): NOT_PERSONAL,
    ("ml_monitor_run", "results"): NOT_PERSONAL,
    ("validation_issue", "id"): AUDIT_EVENT,
    ("validation_issue", "case_id"): AUDIT_EVENT,
    ("validation_issue", "rule_id"): AUDIT_EVENT,
    ("validation_issue", "fingerprint"): AUDIT_EVENT,
    ("validation_issue", "severity"): AUDIT_EVENT,
    ("validation_issue", "offending_entities"): AUDIT_EVENT,
    ("validation_issue", "observed_values"): AUDIT_EVENT,
    ("validation_issue", "detected_at"): AUDIT_EVENT,
    ("validation_issue", "resolution_state"): AUDIT_EVENT,
    ("validation_issue", "resolved_at"): AUDIT_EVENT,
    ("validation_issue", "entity_version"): AUDIT_EVENT,
    ("validation_issue_history", "id"): AUDIT_EVENT,
    ("validation_issue_history", "issue_id"): AUDIT_EVENT,
    ("validation_issue_history", "prior_state"): AUDIT_EVENT,
    ("validation_issue_history", "new_state"): AUDIT_EVENT,
    ("validation_issue_history", "actor_id"): AUDIT_EVENT,
    ("validation_issue_history", "reason"): AUDIT_EVENT,
    ("validation_issue_history", "occurrence_time"): AUDIT_EVENT,
    ("data_subject_request", "id"): AUDIT_EVENT,
    ("data_subject_request", "request_type"): AUDIT_EVENT,
    ("data_subject_request", "subject_key"): AUDIT_EVENT,
    ("data_subject_request", "case_id"): AUDIT_EVENT,
    ("data_subject_request", "ownership_record_id"): AUDIT_EVENT,
    ("data_subject_request", "target_attribute"): AUDIT_EVENT,
    ("data_subject_request", "current_value"): AUDIT_EVENT,
    ("data_subject_request", "asserted_value"): AUDIT_EVENT,
    ("data_subject_request", "received_at"): AUDIT_EVENT,
    ("data_subject_request", "due_at"): AUDIT_EVENT,
    ("data_subject_request", "completed_at"): AUDIT_EVENT,
    ("data_subject_request", "status"): AUDIT_EVENT,
    ("data_subject_request", "routed_area_code"): AUDIT_EVENT,
    ("data_subject_request", "created_event_id"): AUDIT_EVENT,
    ("data_subject_request", "disposed_event_id"): AUDIT_EVENT,
    ("retention_withholding", "id"): AUDIT_EVENT,
    ("retention_withholding", "entity_type"): AUDIT_EVENT,
    ("retention_withholding", "entity_id"): AUDIT_EVENT,
    ("retention_withholding", "attribute_name"): AUDIT_EVENT,
    ("retention_withholding", "data_category"): AUDIT_EVENT,
    ("retention_withholding", "reason"): AUDIT_EVENT,
    ("retention_withholding", "retention_start"): AUDIT_EVENT,
    ("retention_withholding", "policy_key"): AUDIT_EVENT,
    ("retention_withholding", "recorded_at"): AUDIT_EVENT,
    # personal_datum — the referent's category is the one recorded on its row.
    ("personal_datum", "id"): AUDIT_EVENT,
    ("personal_datum", "data_category"): AUDIT_EVENT,
    ("personal_datum", "entity_type"): AUDIT_EVENT,
    ("personal_datum", "entity_id"): AUDIT_EVENT,
    ("personal_datum", "attribute_name"): AUDIT_EVENT,
    ("personal_datum", "value_ciphertext"): Reference(follows="data_category"),
    ("personal_datum", "key_version"): AUDIT_EVENT,
    ("personal_datum", "erased_at"): AUDIT_EVENT,
    ("personal_datum", "erasure_event_id"): AUDIT_EVENT,
    ("personal_datum", "created_at"): AUDIT_EVENT,
}


def category_of(
    table: str, column: str, row: Mapping[str, Any] | None = None
) -> str:
    """Return the ``Data_Category`` assigned to ``table.column`` (R32.2).

    Raises ``KeyError`` if the attribute is unclassified — there is no silent
    default. For a value-dependent entry (:class:`Discriminated` or
    :class:`Reference`), ``row`` supplies the values the category is resolved
    from; omitting it for such an entry raises ``ValueError``.
    """
    entry = CATEGORY_MAP[(table, column)]
    if isinstance(entry, (Discriminated, Reference)):
        return entry.resolve(row)
    return entry


def _entry_is_personal(entry: str | Discriminated | Reference) -> bool:
    """Whether an entry classifies its attribute as (potentially) personal data.

    A :class:`Discriminated` entry is personal if *any* value it can resolve to is
    personal — a feature reading such an attribute might read a personal value. A
    :class:`Reference` follows a category column that, for the only current use,
    always holds a personal category, so it is treated as personal.
    """
    if isinstance(entry, Discriminated):
        return bool(entry.possible_categories() & PERSONAL_DATA_CATEGORIES)
    if isinstance(entry, Reference):
        return True
    return entry in PERSONAL_DATA_CATEGORIES


def personal_data_attributes(
    category_map: Mapping[tuple[str, str], str | Discriminated | Reference]
) -> frozenset[str]:
    """The set of attribute (column) names classified as personal data.

    Returned as bare column names, because that is what a feature extractor's
    ``source_attributes`` and a ``GatedModel``'s field names are stated in, and
    both the disjointness guard (§5.4) and the field-coverage test (§8.3)
    intersect against this set. Using column names is deliberately conservative:
    a name that is personal in any table is treated as personal everywhere it
    appears as a source, which fails safe for a guard whose whole job is to block.
    """
    return frozenset(
        column
        for (_table, column), entry in category_map.items()
        if _entry_is_personal(entry)
    )
