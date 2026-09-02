"""Internal i18n telemetry response models."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from app.api.versioning import VersionedWrite
from app.security.gate import GatedModel, Sensitive, Visibility

__all__ = ["MissingI18nKeyIn", "MissingI18nKeyOut"]


class MissingI18nKeyIn(VersionedWrite):
    language: str = Field(..., min_length=2, max_length=12)
    namespace: str = Field(..., min_length=1, max_length=80)
    key: str = Field(..., min_length=1, max_length=200)
    fallback_value: str | None = Field(default=None, max_length=500)


class MissingI18nKeyOut(GatedModel):
    model_config = ConfigDict(from_attributes=True)

    accepted: bool = Sensitive(Visibility.PUBLIC)
