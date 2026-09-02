"""Citizen-specific response shapes."""

from __future__ import annotations

from decimal import Decimal

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["CitizenParcelOut"]


class CitizenParcelOut(GatedModel):
    """Citizen parcel shape with aggregate co-owner facts, not co-owner rows."""

    model_config = ConfigDict(from_attributes=True)

    parcel_id: int = Sensitive(Visibility.PUBLIC)
    survey_number: str = Sensitive(Visibility.PUBLIC)
    village: str = Sensitive(Visibility.PUBLIC)
    extent: Decimal = Sensitive(Visibility.PUBLIC)
    extent_unit: str = Sensitive(Visibility.PUBLIC)
    share: Decimal = Sensitive(Visibility.PUBLIC)
    co_owner_count: int = Sensitive(Visibility.PUBLIC)
    other_share_total: Decimal = Sensitive(Visibility.PUBLIC)
