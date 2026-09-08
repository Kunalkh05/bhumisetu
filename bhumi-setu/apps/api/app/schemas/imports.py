"""Bulk import request and response models."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["ImportBatchOut", "ImportRowIn", "ImportSubmitIn"]


class ImportRowIn(GatedModel):
    ordinal: int = Sensitive(Visibility.PUBLIC)
    entity_type: str = Sensitive(Visibility.PUBLIC)
    payload: dict[str, Any] = Sensitive(Visibility.OFFICER_ONLY)


class ImportSubmitIn(GatedModel):
    rows: tuple[ImportRowIn, ...] = Sensitive(Visibility.OFFICER_ONLY)


class ImportBatchOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: int = Sensitive(Visibility.PUBLIC)
    submitted_count: int = Sensitive(Visibility.OFFICER_ONLY)
    state: str = Sensitive(Visibility.OFFICER_ONLY)
    content_checksum: str = Sensitive(Visibility.OFFICER_ONLY)

