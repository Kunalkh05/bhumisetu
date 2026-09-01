"""Gated notice response models."""

from __future__ import annotations

from datetime import date

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["NoticeOut"]


class NoticeOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Sensitive(Visibility.PUBLIC)
    case_id: int = Sensitive(Visibility.PUBLIC)
    notice_type: str = Sensitive(Visibility.PUBLIC)
    issuing_authority: str = Sensitive(Visibility.PUBLIC)
    issue_date: date = Sensitive(Visibility.PUBLIC)
    service_date: date | None = Sensitive(Visibility.PUBLIC, default=None)
    publication_mode: str = Sensitive(Visibility.PUBLIC)
    response_deadline: date = Sensitive(Visibility.PUBLIC)
    breach_state: str = Sensitive(Visibility.PUBLIC)
    entity_version: int = Sensitive(Visibility.PUBLIC)
