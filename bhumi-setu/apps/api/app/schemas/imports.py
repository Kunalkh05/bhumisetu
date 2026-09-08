"""Bulk import request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = [
    "ImportBatchDetailOut",
    "ImportBatchOut",
    "ImportRowIn",
    "ImportSubmitIn",
    "RejectedRowOut",
]


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


class RejectedRowOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    ordinal: int = Sensitive(Visibility.OFFICER_ONLY)
    entity_type: str = Sensitive(Visibility.OFFICER_ONLY)
    rule_id: str = Sensitive(Visibility.OFFICER_ONLY)
    attribute: str | None = Sensitive(Visibility.OFFICER_ONLY)
    observed: Any = Sensitive(Visibility.OFFICER_ONLY)
    matching_id: int | None = Sensitive(Visibility.OFFICER_ONLY)


class ImportBatchDetailOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: int = Sensitive(Visibility.PUBLIC)
    submitted_by: str = Sensitive(Visibility.OFFICER_ONLY)
    submitted_at: datetime = Sensitive(Visibility.OFFICER_ONLY)
    submitted_count: int = Sensitive(Visibility.OFFICER_ONLY)
    committed_count: int = Sensitive(Visibility.OFFICER_ONLY)
    rejected_count: int = Sensitive(Visibility.OFFICER_ONLY)
    state: str = Sensitive(Visibility.OFFICER_ONLY)
    last_processed_ordinal: int = Sensitive(Visibility.OFFICER_ONLY)
    rejected_rows: list[RejectedRowOut] = Sensitive(Visibility.OFFICER_ONLY)

