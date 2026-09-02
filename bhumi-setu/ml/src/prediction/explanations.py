"""Prediction explanation factor ranking and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.ml import MLExplanationFactor, MLModelVersion, MLPrediction

__all__ = [
    "ExplanationFactor",
    "ShapFactor",
    "explanation_payload",
    "persist_explanation_factors",
    "rank_explanation_factors",
]

DEFAULT_EXPLANATION_LIMIT = 5


class LabelKeyResolver(Protocol):
    def __call__(self, feature_name: str) -> str:
        ...


@dataclass(frozen=True)
class ShapFactor:
    feature_name: str
    value: float


@dataclass(frozen=True)
class ExplanationFactor:
    rank: int
    feature_name: str
    label_key: str
    direction: str
    magnitude: float

    def to_response(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "feature_name": self.feature_name,
            "label_key": self.label_key,
            "direction": self.direction,
            "magnitude": self.magnitude,
        }


def rank_explanation_factors(
    factors: Iterable[ShapFactor],
    *,
    label_key_for: LabelKeyResolver | None = None,
    limit: int = DEFAULT_EXPLANATION_LIMIT,
) -> tuple[ExplanationFactor, ...]:
    """Rank TreeSHAP-style values by absolute impact and expose translation keys."""
    if limit < 1:
        raise ValueError("explanation limit must be positive")
    resolver = label_key_for or _default_label_key
    ranked = sorted(
        factors,
        key=lambda factor: (-abs(float(factor.value)), factor.feature_name),
    )[:limit]
    return tuple(
        ExplanationFactor(
            rank=index,
            feature_name=factor.feature_name,
            label_key=resolver(factor.feature_name),
            direction="INCREASES_RISK" if factor.value >= 0 else "DECREASES_RISK",
            magnitude=abs(float(factor.value)),
        )
        for index, factor in enumerate(ranked, start=1)
    )


def persist_explanation_factors(
    session: Session,
    *,
    prediction_id: int,
    factors: Iterable[ExplanationFactor],
) -> tuple[MLExplanationFactor, ...]:
    """Replace and persist the ranked top factors for one prediction."""
    session.execute(
        delete(MLExplanationFactor).where(
            MLExplanationFactor.prediction_id == prediction_id
        )
    )
    rows = tuple(
        MLExplanationFactor(
            prediction_id=prediction_id,
            rank=factor.rank,
            feature_name=factor.feature_name,
            label_key=factor.label_key,
            direction=factor.direction,
            magnitude=factor.magnitude,
        )
        for factor in factors
    )
    for row in rows:
        session.add(row)
    session.flush()
    return rows


def explanation_payload(
    session: Session,
    *,
    prediction: MLPrediction,
) -> dict[str, object]:
    """Return the officer-facing explanation block for a stored prediction."""
    model = session.get(MLModelVersion, prediction.model_version_id)
    factors = session.execute(
        select(MLExplanationFactor)
        .where(MLExplanationFactor.prediction_id == prediction.id)
        .order_by(MLExplanationFactor.rank)
        .limit(DEFAULT_EXPLANATION_LIMIT)
    ).scalars()
    return {
        "model_version": model.version if model is not None else None,
        "generated_at": prediction.generated_at,
        "factors": [
            ExplanationFactor(
                rank=row.rank,
                feature_name=row.feature_name,
                label_key=row.label_key,
                direction=row.direction,
                magnitude=row.magnitude,
            ).to_response()
            for row in factors
        ],
    }


def _default_label_key(feature_name: str) -> str:
    return f"ml.feature.{feature_name}"
