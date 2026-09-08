"""Feature value representation with explicit missingness."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

__all__ = ["FeatureValue", "ModelColumns"]

ModelColumns = dict[str, float]


@dataclass(frozen=True)
class FeatureValue:
    """One derived feature value or one explicit reason it is missing."""

    value: int | float | bool | None = None
    missing_reason: str | None = None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.missing_reason is None):
            raise ValueError("exactly one of value and missing_reason must be set")

    @property
    def is_missing(self) -> bool:
        return self.missing_reason is not None

    def to_json(self) -> dict[str, Any]:
        return {"value": self.value, "missing_reason": self.missing_reason}

    def to_model_columns(self, name: str) -> ModelColumns:
        """Return the tree-model representation without imputation."""
        if self.is_missing:
            return {name: math.nan, f"{name}_is_missing": 1.0}
        return {name: float(self.value), f"{name}_is_missing": 0.0}
