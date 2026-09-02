"""Officer intervention queue response models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.api.versioning import VersionedWrite
from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = [
    "ActionDispositionIn",
    "ActionDispositionOut",
    "InterventionQueueOut",
    "QueueItemOut",
    "RecommendedActionOut",
]


class RecommendedActionOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    action_id: str = Sensitive(Visibility.OFFICER_ONLY)
    label_key: str = Sensitive(Visibility.OFFICER_ONLY)
    reason_key: str = Sensitive(Visibility.OFFICER_ONLY)
    severity: str = Sensitive(Visibility.OFFICER_ONLY)


class QueueItemOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: int = Sensitive(Visibility.PUBLIC)
    case_reference: str = Sensitive(Visibility.OFFICER_ONLY)
    stage_key: str = Sensitive(Visibility.OFFICER_ONLY)
    risk_band: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    remaining_days: int | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    priority_score: Decimal | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    priority_computed_at: datetime | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    recommended_actions: tuple[RecommendedActionOut, ...] = Sensitive(
        Visibility.OFFICER_ONLY,
        default_factory=tuple,
    )


class InterventionQueueOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    items: tuple[QueueItemOut, ...] = Sensitive(Visibility.OFFICER_ONLY)
    oldest_priority_computed_at: datetime | None = Sensitive(
        Visibility.OFFICER_ONLY,
        default=None,
    )
    limit: int = Sensitive(Visibility.OFFICER_ONLY)
    offset: int = Sensitive(Visibility.OFFICER_ONLY)


class ActionDispositionIn(VersionedWrite):
    disposition: str = Field(..., pattern="^(ACCEPTED|REJECTED|DEFERRED)$")
    reason: str | None = Field(default=None, max_length=500)
    occurrence_time: datetime | None = None


class ActionDispositionOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: int = Sensitive(Visibility.PUBLIC)
    action_id: str = Sensitive(Visibility.OFFICER_ONLY)
    disposition: str = Sensitive(Visibility.OFFICER_ONLY)
    reason: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    occurrence_time: datetime = Sensitive(Visibility.OFFICER_ONLY)
