"""Build deterministic ML feature rows from point-in-time event replay."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from sqlalchemy.orm import Session

from app.db.event_log import AsOfMode
from features.asof import build_as_of_view
from features.extractors import CURRENT_FEATURE_SET_VERSION
from features.leakage import no_database_access
from features.registry import FEATURE_REGISTRY, FeatureExtractor, FeatureRegistry
from features.value import FeatureValue, ModelColumns

__all__ = [
    "FeatureRow",
    "build_feature_row",
    "canonical_feature_payload",
    "canonical_hash",
]


@dataclass(frozen=True)
class FeatureRow:
    case_id: int
    reference_t: datetime
    as_of_mode: str
    feature_set_version: str
    purpose: str
    values: Mapping[str, dict[str, object]]
    model_input: Mapping[str, float]
    consumed_event_ids: tuple[int, ...]
    content_hash: str


def build_feature_row(
    session: Session,
    case_id: int,
    t: datetime,
    mode: AsOfMode | str,
    feature_set_version: str = CURRENT_FEATURE_SET_VERSION,
    *,
    purpose: str = "TRAINING",
    registry: FeatureRegistry = FEATURE_REGISTRY,
) -> FeatureRow:
    """Build one feature row; all database I/O is confined to as-of replay."""
    view = build_as_of_view(session, case_id, t, mode)
    mode = AsOfMode(mode)
    extractors = _extractors_for_version(registry, feature_set_version)

    with no_database_access(session):
        values = {extractor.name: extractor.compute(view, t) for extractor in extractors}

    serialized = _serialize(values)
    consumed = tuple(sorted(view.consumed_event_ids))
    return FeatureRow(
        case_id=case_id,
        reference_t=t,
        as_of_mode=str(mode),
        feature_set_version=feature_set_version,
        purpose=purpose,
        values=serialized,
        model_input=_model_input(values),
        consumed_event_ids=consumed,
        content_hash=canonical_hash(
            feature_set_version=feature_set_version,
            as_of_mode=str(mode),
            consumed_event_ids=consumed,
            values=serialized,
        ),
    )


def _extractors_for_version(
    registry: FeatureRegistry,
    feature_set_version: str,
) -> tuple[FeatureExtractor, ...]:
    if feature_set_version != CURRENT_FEATURE_SET_VERSION:
        raise ValueError(f"unknown feature_set_version: {feature_set_version}")
    return registry.all()


def _serialize(values: Mapping[str, FeatureValue]) -> dict[str, dict[str, object]]:
    return {name: value.to_json() for name, value in sorted(values.items())}


def _model_input(values: Mapping[str, FeatureValue]) -> ModelColumns:
    columns: ModelColumns = {}
    for name, value in sorted(values.items()):
        columns.update(value.to_model_columns(name))
    return columns


def canonical_hash(
    *,
    feature_set_version: str,
    as_of_mode: str,
    consumed_event_ids: tuple[int, ...],
    values: Mapping[str, dict[str, object]],
) -> str:
    payload = canonical_feature_payload(
        feature_set_version=feature_set_version,
        as_of_mode=as_of_mode,
        consumed_event_ids=consumed_event_ids,
        values=values,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_feature_payload(
    *,
    feature_set_version: str,
    as_of_mode: str,
    consumed_event_ids: tuple[int, ...],
    values: Mapping[str, dict[str, object]],
) -> str:
    payload = {
        "feature_set_version": feature_set_version,
        "as_of_mode": as_of_mode,
        "consumed_event_ids": sorted(consumed_event_ids),
        "values": values,
    }
    return json.dumps(payload, allow_nan=False, separators=(",", ":"), sort_keys=True)
