"""Retention projection response models."""

from __future__ import annotations

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["OwnershipRetentionOut", "RetentionAttributeOut"]


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
