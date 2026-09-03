"""Retention projection response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = [
    "CorrectionRequestIn",
    "DSARAccessOut",
    "DSARAttributeOut",
    "DSARDisposalIn",
    "DSARDisposalOut",
    "DSARRequestOut",
    "OwnershipRetentionOut",
    "RetentionAttributeOut",
]


class RetentionAttributeOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    attribute_name: str = Sensitive(Visibility.OFFICER_ONLY)
    data_category: str = Sensitive(Visibility.OFFICER_ONLY)
    retention_start: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    erasure_date: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    withholding_reason: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    policy_key: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)


class OwnershipRetentionOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    ownership_record_id: int = Sensitive(Visibility.PUBLIC)
    case_id: int = Sensitive(Visibility.PUBLIC)
    attributes: tuple[RetentionAttributeOut, ...] = Sensitive(Visibility.OFFICER_ONLY)


class DSARAttributeOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)
    __owner_record_id_field__ = "ownership_record_id"

    ownership_record_id: int = Sensitive(Visibility.PUBLIC)
    attribute_name: str = Sensitive(Visibility.OWNER_ONLY)
    data_category: str = Sensitive(Visibility.OWNER_ONLY)
    value: Any = Sensitive(Visibility.OWNER_ONLY)


class DSARAccessOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)
    __owner_case_id_field__ = "case_id"
    __owner_record_id_field__ = None

    request_id: int = Sensitive(Visibility.PUBLIC)
    case_id: int = Sensitive(Visibility.PUBLIC)
    served_at: datetime = Sensitive(Visibility.OWNER_ONLY)
    attributes: tuple[DSARAttributeOut, ...] = Sensitive(Visibility.OWNER_ONLY)


class CorrectionRequestIn(GatedModel):
    ownership_record_id: int = Sensitive(Visibility.PUBLIC)
    target_attribute: str = Sensitive(Visibility.PUBLIC)
    asserted_value: Any = Sensitive(Visibility.OWNER_ONLY)


class DSARRequestOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)
    __owner_case_id_field__ = "case_id"
    __owner_record_id_field__ = "ownership_record_id"

    id: int = Sensitive(Visibility.PUBLIC)
    request_type: str = Sensitive(Visibility.OFFICER_ONLY)
    subject_key: str = Sensitive(Visibility.OFFICER_ONLY)
    case_id: int | None = Sensitive(Visibility.PUBLIC, default=None)
    ownership_record_id: int | None = Sensitive(Visibility.PUBLIC, default=None)
    target_attribute: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    current_value: Any | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    asserted_value: Any | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    received_at: datetime = Sensitive(Visibility.OFFICER_ONLY)
    due_at: datetime = Sensitive(Visibility.OFFICER_ONLY)
    completed_at: datetime | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    status: str = Sensitive(Visibility.OFFICER_ONLY)
    routed_area_code: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    disposal_outcome: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    disposal_reasons: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    deciding_officer_id: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)


class DSARDisposalIn(GatedModel):
    outcome: str = Sensitive(Visibility.PUBLIC)
    reasons: str = Sensitive(Visibility.PUBLIC)


class DSARDisposalOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: int = Sensitive(Visibility.PUBLIC)
    outcome: str = Sensitive(Visibility.PERMISSION, permission="dsar.dispose")
    reasons: str = Sensitive(Visibility.PERMISSION, permission="dsar.dispose")
    decided_at: datetime = Sensitive(Visibility.PERMISSION, permission="dsar.dispose")
