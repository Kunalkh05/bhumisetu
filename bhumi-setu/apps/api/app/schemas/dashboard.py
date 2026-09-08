"""Officer dashboard response models."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["DashboardBandPointOut", "DashboardMetricOut", "DashboardOut"]


class DashboardMetricOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    value: Any | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    computed_at: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    unavailable_at: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    reason: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)


class DashboardBandPointOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    month: str = Sensitive(Visibility.OFFICER_ONLY)
    band: str = Sensitive(Visibility.OFFICER_ONLY)
    case_count: int = Sensitive(Visibility.OFFICER_ONLY)


class DashboardOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    metrics: dict[str, DashboardMetricOut] = Sensitive(Visibility.OFFICER_ONLY)
    stage_keys: tuple[str, ...] = Sensitive(Visibility.OFFICER_ONLY, default_factory=tuple)
    band_history: tuple[DashboardBandPointOut, ...] = Sensitive(
        Visibility.OFFICER_ONLY,
        default_factory=tuple,
    )
