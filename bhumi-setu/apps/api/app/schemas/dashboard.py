"""Officer dashboard response models."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["DashboardMetricOut", "DashboardOut"]


class DashboardMetricOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    value: Any | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    computed_at: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    unavailable_at: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)
    reason: str | None = Sensitive(Visibility.OFFICER_ONLY, default=None)


class DashboardOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    metrics: dict[str, DashboardMetricOut] = Sensitive(Visibility.OFFICER_ONLY)
