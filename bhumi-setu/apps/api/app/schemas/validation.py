"""Gated validation issue response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from app.api.versioning import VersionedWrite
from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["ValidationHistoryOut", "ValidationIssueOut", "WaiveIssueIn"]


class ValidationIssueOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Sensitive(Visibility.PUBLIC)
    case_id: int = Sensitive(Visibility.PUBLIC)
    rule_id: str = Sensitive(Visibility.PUBLIC)
    fingerprint: str = Sensitive(Visibility.PUBLIC)
    severity: str = Sensitive(Visibility.PUBLIC)
    offending_entities: dict = Sensitive(Visibility.PUBLIC)
    observed_values: dict = Sensitive(Visibility.PUBLIC)
    detected_at: datetime = Sensitive(Visibility.PUBLIC)
    resolution_state: str = Sensitive(Visibility.PUBLIC)
    resolved_at: datetime | None = Sensitive(Visibility.PUBLIC)
    entity_version: int = Sensitive(Visibility.PUBLIC)


class ValidationHistoryOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Sensitive(Visibility.PUBLIC)
    issue_id: int = Sensitive(Visibility.PUBLIC)
    prior_state: str | None = Sensitive(Visibility.PUBLIC)
    new_state: str = Sensitive(Visibility.PUBLIC)
    actor_id: str = Sensitive(Visibility.PUBLIC)
    reason: str | None = Sensitive(Visibility.PUBLIC)
    occurrence_time: datetime = Sensitive(Visibility.PUBLIC)


class WaiveIssueIn(VersionedWrite):
    reason: str = Field(..., min_length=1)
