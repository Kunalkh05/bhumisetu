"""Public train/serve feature-row entry points."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.event_log import AsOfMode
from features.builder import FeatureRow, build_feature_row
from features.extractors import CURRENT_FEATURE_SET_VERSION

__all__ = ["build_inference_row", "build_training_row"]


def build_training_row(
    session: Session,
    case_id: int,
    t: datetime,
    feature_set_version: str = CURRENT_FEATURE_SET_VERSION,
) -> FeatureRow:
    return build_feature_row(
        session,
        case_id,
        t,
        AsOfMode.KNOWABLE_AT,
        feature_set_version,
        purpose="TRAINING",
    )


def build_inference_row(
    session: Session,
    case_id: int,
    t: datetime,
    feature_set_version: str = CURRENT_FEATURE_SET_VERSION,
) -> FeatureRow:
    return build_feature_row(
        session,
        case_id,
        t,
        AsOfMode.KNOWABLE_AT,
        feature_set_version,
        purpose="INFERENCE",
    )
