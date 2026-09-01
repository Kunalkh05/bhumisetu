"""Gated response models for acquisition-case endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["CaseOut", "TimelineEventOut"]


class CaseOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Sensitive(Visibility.PUBLIC)
    case_reference: str = Sensitive(Visibility.PUBLIC)
    project_id: int = Sensitive(Visibility.PUBLIC)
    state_key: str = Sensitive(Visibility.PUBLIC)
    act_key: str = Sensitive(Visibility.PUBLIC)
    area_code: str = Sensitive(Visibility.PUBLIC)
    stage_key: str = Sensitive(Visibility.PUBLIC)
    stage_entered_on: date = Sensitive(Visibility.PUBLIC)
    stage_deadline: date | None = Sensitive(Visibility.PUBLIC)
    deadline_breached: bool = Sensitive(Visibility.PUBLIC)
    is_terminal: bool = Sensitive(Visibility.PUBLIC)
    entity_version: int = Sensitive(Visibility.PUBLIC)


class TimelineEventOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Sensitive(Visibility.PUBLIC)
    event_type: str = Sensitive(Visibility.PUBLIC)
    entity_type: str = Sensitive(Visibility.PUBLIC)
    entity_id: int = Sensitive(Visibility.PUBLIC)
    occurrence_time: datetime = Sensitive(Visibility.PUBLIC)
    recording_time: datetime = Sensitive(Visibility.PUBLIC)
    payload: dict = Sensitive(Visibility.PUBLIC)
