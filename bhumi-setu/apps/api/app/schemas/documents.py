"""Gated document response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["DocumentGrantOut", "DocumentOut"]


class DocumentOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Sensitive(Visibility.PUBLIC)
    case_id: int | None = Sensitive(Visibility.PUBLIC)
    parcel_id: int | None = Sensitive(Visibility.PUBLIC)
    document_type: str = Sensitive(Visibility.PUBLIC)
    original_filename: str = Sensitive(Visibility.PUBLIC)
    byte_size: int = Sensitive(Visibility.PUBLIC)
    content_type: str = Sensitive(Visibility.PUBLIC)
    uploaded_at: datetime = Sensitive(Visibility.PUBLIC)
    processing_state: str = Sensitive(Visibility.PUBLIC)
    failure_reason: str | None = Sensitive(Visibility.PUBLIC)
    detected_script: str | None = Sensitive(Visibility.PUBLIC)
    entity_version: int = Sensitive(Visibility.PUBLIC)


class DocumentGrantOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int = Sensitive(Visibility.PUBLIC)
    url: str = Sensitive(Visibility.PUBLIC)
    expires_in: int = Sensitive(Visibility.PUBLIC)
