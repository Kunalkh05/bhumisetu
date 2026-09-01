"""Gated ownership response models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import ConfigDict

from app.retention.categories import OWNER_CONTACT, OWNER_IDENTITY
from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["OwnershipOut"]


class OwnershipOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Sensitive(Visibility.PUBLIC)
    parcel_id: int = Sensitive(Visibility.PUBLIC)
    owner_name: str | None = Sensitive(Visibility.OWNER_ONLY, data_category=OWNER_IDENTITY)
    government_identifier: str | None = Sensitive(
        Visibility.OWNER_ONLY,
        mask="TRAILING_4",
        data_category=OWNER_IDENTITY,
    )
    contact_mobile: str | None = Sensitive(Visibility.OWNER_ONLY, data_category=OWNER_CONTACT)
    interest_type: str = Sensitive(Visibility.PUBLIC)
    share: Decimal = Sensitive(Visibility.PUBLIC)
    valid_from: date = Sensitive(Visibility.PUBLIC)
    valid_to: date | None = Sensitive(Visibility.PUBLIC)
    entity_version: int = Sensitive(Visibility.PUBLIC)
