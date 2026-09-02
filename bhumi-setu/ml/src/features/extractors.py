"""The first point-in-time feature extractor set."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from features.asof import AsOfView
from features.registry import FEATURE_REGISTRY
from features.value import FeatureValue

__all__ = [
    "CURRENT_FEATURE_SET_VERSION",
    "DEFAULT_EXTRACTORS",
    "AwardRecordedExtractor",
    "DaysInCurrentStageExtractor",
    "DaysSinceLatestNoticeExtractor",
    "NoticeCountExtractor",
    "ObjectionCountExtractor",
    "OpenIssueCountExtractor",
    "ParcelCountExtractor",
    "register_default_extractors",
]

CURRENT_FEATURE_SET_VERSION = "fs-v1"


@dataclass(frozen=True)
class DaysInCurrentStageExtractor:
    name: str = "days_in_current_stage"
    source_attributes: frozenset[str] = frozenset({"stage_key", "occurrence_time"})

    def compute(self, view: AsOfView, t: datetime) -> FeatureValue:
        if not view.stage_history:
            return FeatureValue(missing_reason="NO_STAGE_ENTRY_EVENT")
        entered_at = view.stage_history[-1].occurrence_time
        return FeatureValue(value=max((t - entered_at).days, 0))


@dataclass(frozen=True)
class DaysSinceLatestNoticeExtractor:
    name: str = "days_since_latest_notice"
    source_attributes: frozenset[str] = frozenset({"notice_id", "occurrence_time"})

    def compute(self, view: AsOfView, t: datetime) -> FeatureValue:
        if not view.notices:
            return FeatureValue(missing_reason="NO_NOTICE_EVENT")
        latest = view.notices[-1].occurrence_time
        return FeatureValue(value=max((t - latest).days, 0))


@dataclass(frozen=True)
class NoticeCountExtractor:
    name: str = "notice_count"
    source_attributes: frozenset[str] = frozenset({"notice_id"})

    def compute(self, view: AsOfView, t: datetime) -> FeatureValue:
        return FeatureValue(value=len(view.notices))


@dataclass(frozen=True)
class ObjectionCountExtractor:
    name: str = "objection_count"
    source_attributes: frozenset[str] = frozenset({"objection_id"})

    def compute(self, view: AsOfView, t: datetime) -> FeatureValue:
        return FeatureValue(value=len(view.objections))


@dataclass(frozen=True)
class ParcelCountExtractor:
    name: str = "parcel_count"
    source_attributes: frozenset[str] = frozenset({"parcel_id"})

    def compute(self, view: AsOfView, t: datetime) -> FeatureValue:
        return FeatureValue(value=len(view.parcels))


@dataclass(frozen=True)
class AwardRecordedExtractor:
    name: str = "award_recorded"
    source_attributes: frozenset[str] = frozenset({"award_id"})

    def compute(self, view: AsOfView, t: datetime) -> FeatureValue:
        return FeatureValue(value=bool(view.awards))


@dataclass(frozen=True)
class OpenIssueCountExtractor:
    name: str = "open_issue_count"
    source_attributes: frozenset[str] = frozenset({"issue_id", "event_type"})

    def compute(self, view: AsOfView, t: datetime) -> FeatureValue:
        return FeatureValue(
            value=len([issue for issue in view.issues if not _closed(issue.event_type)])
        )


def _closed(event_type: str) -> bool:
    return event_type.lower() in {"validation_issue_resolved", "issue_resolved", "closed"}


DEFAULT_EXTRACTORS = (
    DaysInCurrentStageExtractor(),
    DaysSinceLatestNoticeExtractor(),
    NoticeCountExtractor(),
    ObjectionCountExtractor(),
    ParcelCountExtractor(),
    AwardRecordedExtractor(),
    OpenIssueCountExtractor(),
)


def register_default_extractors() -> None:
    existing = {extractor.name for extractor in FEATURE_REGISTRY.all()}
    for extractor in DEFAULT_EXTRACTORS:
        if extractor.name not in existing:
            FEATURE_REGISTRY.register(extractor)


register_default_extractors()
