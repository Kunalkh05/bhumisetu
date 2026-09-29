"""Survival-specific feature definitions, schemas, and leakage guards for BHUMISETU (LOOP 4 & LOOP 5).

Guarantees:
1. Strict separation of predictor features, training targets, and metadata.
2. Verified safe predictor allowlist excluding leaky and 0% coverage attributes.
3. Explicit tracking of statutory missingness semantics (no NULL -> 0 coercion).
4. Leakage risk classification and training admissibility for all candidate features.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping, Sequence

# 1. Identification Keys (used strictly for joining/indexing, NEVER as model predictors)
IDENTIFIER_COLUMNS: tuple[str, ...] = (
    "case_id",
    "snapshot_id",
    "transition",
)

# 2. Target Columns (future outcomes relative to snapshot_date, NEVER in predictor matrix)
TARGET_COLUMNS: tuple[str, ...] = (
    "duration_at_risk_days",
    "event_observed",
    "entry_date",
    "snapshot_date",
    "event_date",
    "censoring_date",
)

# Training Target Columns (strictly the duration and event indicator for survival training)
TRAINING_TARGET_COLUMNS: tuple[str, ...] = (
    "duration_at_risk_days",
    "event_observed",
)

# Complete target/identification metadata set excluded from training predictors
TARGET_METADATA_COLUMNS: tuple[str, ...] = (
    "case_id",
    "snapshot_id",
    "snapshot_date",
    "transition",
    "entry_date",
    "event_date",
    "censoring_date",
    "duration_at_risk_days",
    "event_observed",
)

# 3. Categorical Predictor Columns
CATEGORICAL_FEATURE_COLUMNS: tuple[str, ...] = (
    "current_stage",
    "district",
    "taluka",
    "village",
    "acquiring_authority",
    "act_key",
    "derived_project_type",
)

# 4. Boolean Predictor Columns
BOOLEAN_FEATURE_COLUMNS: tuple[str, ...] = (
    "has_statutory_extension",
    "award_recorded",
    "derived_is_direct_purchase",
)

# 5. Numerical Predictor Columns (available and missing)
NUMERICAL_FEATURE_COLUMNS: tuple[str, ...] = (
    "derived_days_since_case_initiation",
    "derived_days_in_current_stage",
    "derived_days_since_latest_notice",
    "derived_notice_count",
    "derived_statutory_sec19_proximity_ratio",
    "extension_count",
    "objection_count",
    "parcel_count",
    "open_issue_count",
    "notified_area_hectares",
    "affected_landowner_count",
    "compensation_amount_inr",
)

# 6. Statutory Missing Attribute Columns (must remain NULL/NaN where unpublished)
MISSING_ATTRIBUTE_COLUMNS: tuple[str, ...] = (
    "objection_count",
    "parcel_count",
    "open_issue_count",
    "notified_area_hectares",
    "affected_landowner_count",
    "compensation_amount_inr",
)

# 7. Complete Candidate Predictor Feature Set (22 features)
FEATURE_COLUMNS: tuple[str, ...] = (
    # Core Temporal
    "derived_days_since_case_initiation",
    "derived_days_in_current_stage",
    "derived_days_since_latest_notice",
    "derived_notice_count",
    # Statutory
    "derived_statutory_sec19_proximity_ratio",
    "extension_count",
    "has_statutory_extension",
    # Current Stage
    "current_stage",
    # Administrative Context
    "district",
    "taluka",
    "village",
    "acquiring_authority",
    "act_key",
    "derived_project_type",
    "derived_is_direct_purchase",
    # Award
    "award_recorded",
    # Missing Attributes (Preserved as NULL / NaN)
    "objection_count",
    "parcel_count",
    "open_issue_count",
    "notified_area_hectares",
    "affected_landowner_count",
    "compensation_amount_inr",
)

# 8. Verified Safe Predictor Features for Survival Training (15 features, LOOP 5 Purged Set)
SAFE_PREDICTOR_COLUMNS: tuple[str, ...] = (
    # Core Temporal
    "derived_days_since_case_initiation",
    "derived_days_in_current_stage",
    "derived_days_since_latest_notice",
    "derived_notice_count",
    # Statutory
    "derived_statutory_sec19_proximity_ratio",
    "extension_count",
    "has_statutory_extension",
    # Active Stage
    "current_stage",
    # Administrative Context
    "district",
    "taluka",
    "village",
    "acquiring_authority",
    "act_key",
    "derived_project_type",
    "derived_is_direct_purchase",
)

# 9. Purged / Rejected Features (LOOP 5 Purged Set: 7 features)
PURGED_FEATURE_COLUMNS: tuple[str, ...] = (
    "award_recorded",
    "objection_count",
    "parcel_count",
    "open_issue_count",
    "notified_area_hectares",
    "affected_landowner_count",
    "compensation_amount_inr",
)

# 10. Missingness Reason Audit Columns
MISSING_REASON_COLUMNS: tuple[str, ...] = (
    "missing_reason_latest_notice",
    "missing_reason_sec19_proximity",
    "missing_reason_objection_count",
    "missing_reason_parcel_count",
    "missing_reason_open_issue_count",
    "missing_reason_notified_area",
    "missing_reason_affected_landowners",
    "missing_reason_compensation",
)

# Standard Missingness Reason Constants
MISSING_REASON_NOT_PUBLISHED_IN_GAZETTE = "NOT_PUBLISHED_IN_GAZETTE"
MISSING_REASON_NOT_PUBLISHED_IN_STRUCTURED_DATA = "NOT_PUBLISHED_IN_STRUCTURED_DATA"
MISSING_REASON_UNPARSED_SCHEDULE_TABLE = "UNPARSED_SCHEDULE_TABLE"
MISSING_REASON_NOT_APPLICABLE_IN_REAL_DATA = "NOT_APPLICABLE_IN_REAL_DATA"
MISSING_REASON_NOT_APPLICABLE_PRE_AWARD = "NOT_APPLICABLE_PRE_AWARD"
MISSING_REASON_NOT_APPLICABLE_PRE_SEC11 = "NOT_APPLICABLE_PRE_SEC11"
MISSING_REASON_NO_NOTICE_EVENT = "NO_NOTICE_EVENT"
MISSING_REASON_NONE = "NONE"


def assert_target_feature_disjointness() -> None:
    """Assert that feature columns and target columns have an empty intersection."""
    overlap_target = set(FEATURE_COLUMNS).intersection(set(TARGET_COLUMNS))
    if overlap_target:
        raise AssertionError(f"Target leakage detected! Overlapping columns: {overlap_target}")

    overlap_ident = set(FEATURE_COLUMNS).intersection(set(IDENTIFIER_COLUMNS))
    if overlap_ident:
        raise AssertionError(f"Identifier leakage into features! Overlapping columns: {overlap_ident}")

    overlap_meta = set(FEATURE_COLUMNS).intersection(set(TARGET_METADATA_COLUMNS))
    if overlap_meta:
        raise AssertionError(f"Metadata leakage into features! Overlapping columns: {overlap_meta}")

    # Safe predictor invariants
    overlap_safe_purged = set(SAFE_PREDICTOR_COLUMNS).intersection(set(PURGED_FEATURE_COLUMNS))
    if overlap_safe_purged:
        raise AssertionError(f"Purged feature found in safe predictor set: {overlap_safe_purged}")

    if set(SAFE_PREDICTOR_COLUMNS).union(set(PURGED_FEATURE_COLUMNS)) != set(FEATURE_COLUMNS):
        raise AssertionError("Safe and purged sets do not partition FEATURE_COLUMNS exactly!")


# Run disjointness assertion at import time
assert_target_feature_disjointness()


def export_survival_training_features_to_csv(
    snapshots: Sequence[Any],
    target_path: str | Path,
) -> None:
    """Export ONLY verified safe predictor features with index keys for model training (LOOP 5)."""
    if not snapshots:
        return
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(IDENTIFIER_COLUMNS) + list(SAFE_PREDICTOR_COLUMNS)
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in snapshots:
            d = s.to_dict() if hasattr(s, "to_dict") else dict(s)
            row = {col: d[col] if d.get(col) is not None else "" for col in fieldnames}
            writer.writerow(row)


def export_survival_training_targets_to_csv(
    snapshots: Sequence[Any],
    target_path: str | Path,
) -> None:
    """Export ONLY duration_at_risk_days and event_observed with index keys for model training (LOOP 5)."""
    if not snapshots:
        return
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(IDENTIFIER_COLUMNS) + list(TRAINING_TARGET_COLUMNS)
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in snapshots:
            d = s.to_dict() if hasattr(s, "to_dict") else dict(s)
            row = {col: d[col] if d.get(col) is not None else "" for col in fieldnames}
            writer.writerow(row)
