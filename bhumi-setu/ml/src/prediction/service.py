"""Prediction scoring and failure handling."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Mapping, Protocol

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.acquisition_case import AcquisitionCase
from app.models.event import ActorType, Event, Provenance
from app.models.ml import MLFeatureRow, MLModelVersion, MLPrediction
from features.api import build_inference_row
from features.registry import FEATURE_REGISTRY, FeatureRegistry
from prediction.banding import band_for as configured_band_for

__all__ = [
    "BandingDecision",
    "PredictionView",
    "Scorer",
    "current_promoted_model",
    "feature_trigger_keys",
    "score_case",
    "should_trigger_scoring",
    "stale_cutoff",
    "stale_case_ids",
]

STALE_SCORE_AGE_SECONDS = 24 * 60 * 60


class Scorer(Protocol):
    def predict_probability(
        self,
        model_version: MLModelVersion,
        model_input: Mapping[str, float],
    ) -> float:
        ...


@dataclass(frozen=True)
class BandingDecision:
    band: str
    cutoff_source: str
    cutoff_set_version: str


@dataclass(frozen=True)
class PredictionView:
    case_id: int
    risk_probability: float | None
    risk_band: str | None
    risk_model_version: str | None
    risk_generated_at: datetime | None
    risk_is_stale: bool
    risk_cutoff_source: str | None
    monitoring_state: str | None = None
    monitoring_last_successful_at: datetime | None = None

    def with_monitoring_state(
        self,
        *,
        state: str,
        last_successful_at: datetime | None,
    ) -> "PredictionView":
        return PredictionView(
            case_id=self.case_id,
            risk_probability=self.risk_probability,
            risk_band=self.risk_band,
            risk_model_version=self.risk_model_version,
            risk_generated_at=self.risk_generated_at,
            risk_is_stale=self.risk_is_stale,
            risk_cutoff_source=self.risk_cutoff_source,
            monitoring_state=state,
            monitoring_last_successful_at=last_successful_at,
        )

    def to_response(self) -> dict[str, object]:
        response: dict[str, object] = {
            "case_id": self.case_id,
            "risk_is_stale": self.risk_is_stale,
        }
        if self.risk_probability is None:
            response["not_scored"] = True
            return response
        response.update(
            {
                "risk_probability": self.risk_probability,
                "risk_band": self.risk_band,
                "risk_model_version": self.risk_model_version,
                "risk_generated_at": self.risk_generated_at,
                "risk_cutoff_source": self.risk_cutoff_source,
            }
        )
        if self.monitoring_state is not None:
            response["monitoring_state"] = self.monitoring_state
            response["monitoring_last_successful_at"] = self.monitoring_last_successful_at
        return response


BandResolver = Callable[[float, AcquisitionCase], BandingDecision]


def current_promoted_model(session: Session) -> MLModelVersion | None:
    return session.execute(
        select(MLModelVersion)
        .where(MLModelVersion.promotion_state == "PROMOTED")
        .order_by(MLModelVersion.promoted_at.desc().nullslast(), MLModelVersion.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def feature_trigger_keys(registry: FeatureRegistry = FEATURE_REGISTRY) -> frozenset[str]:
    return frozenset(
        source
        for extractor in registry.all()
        for source in extractor.source_attributes
    )


def should_trigger_scoring(
    event_type: str,
    *,
    changed_attributes: set[str] | frozenset[str] | None = None,
    registry: FeatureRegistry = FEATURE_REGISTRY,
) -> bool:
    triggers = feature_trigger_keys(registry)
    return event_type in triggers or bool((changed_attributes or set()) & triggers)


def stale_cutoff(now: datetime) -> datetime:
    return now - timedelta(seconds=STALE_SCORE_AGE_SECONDS)


def stale_case_ids(session: Session, *, now: datetime) -> tuple[int, ...]:
    rows = session.execute(
        select(AcquisitionCase.id)
        .where(
            AcquisitionCase.is_terminal.is_(False),
            or_(
                AcquisitionCase.risk_generated_at.is_(None),
                AcquisitionCase.risk_generated_at < stale_cutoff(now),
            ),
        )
        .order_by(AcquisitionCase.id)
    )
    return tuple(rows.scalars())


def score_case(
    session: Session,
    case_id: int,
    scorer: Scorer,
    *,
    now: datetime | None = None,
    band_for: BandResolver | None = None,
) -> PredictionView:
    now = now or datetime.now(UTC)
    model = current_promoted_model(session)
    case = session.get(AcquisitionCase, case_id, populate_existing=True)
    if case is None:
        raise LookupError(f"case {case_id} does not exist")
    if model is None:
        return _view(case)

    try:
        feature_row = build_inference_row(
            session,
            case_id,
            now,
            model.feature_set_version,
        )
        probability = _checked_probability(
            scorer.predict_probability(model, feature_row.model_input)
        )
        banding = band_for(probability, case) if band_for else _configured_banding(session, probability, case)
        stored_feature = _store_feature_row(session, feature_row)
        session.flush()
        prediction = MLPrediction(
            case_id=case_id,
            model_version_id=model.id,
            feature_row_id=stored_feature.id,
            risk_probability=probability,
            risk_band=banding.band,
            cutoff_source=banding.cutoff_source,
            cutoff_set_version=banding.cutoff_set_version,
            reference_t=now,
            generated_at=now,
        )
        session.add(prediction)
        _copy_prediction_to_case(case, model, probability, banding, now)
        session.flush()
        return _view(case)
    except Exception as exc:
        _mark_stale_and_record_failure(session, case, exc, now)
        session.flush()
        return _view(case)


def _checked_probability(value: float) -> float:
    probability = float(value)
    if not 0 <= probability <= 1:
        raise ValueError(f"risk probability out of range: {probability!r}")
    return probability


def _unbanded() -> BandingDecision:
    return BandingDecision(
        band="UNBANDED",
        cutoff_source="PENDING_CUTOFFS",
        cutoff_set_version="PENDING",
    )


def _configured_banding(
    session: Session,
    probability: float,
    case: AcquisitionCase,
) -> BandingDecision:
    from app.services.policy import PolicyResolver

    result = configured_band_for(
        probability,
        case,
        session=session,
        resolver=PolicyResolver(session),
        now=datetime.now(UTC).date(),
    )
    return BandingDecision(result.band, result.cutoff_source, result.cutoff_set_version)


def _store_feature_row(session: Session, feature_row) -> MLFeatureRow:
    stored = MLFeatureRow(
        case_id=feature_row.case_id,
        reference_t=feature_row.reference_t,
        as_of_mode=feature_row.as_of_mode,
        feature_set_version=feature_row.feature_set_version,
        label_definition_version=None,
        features=feature_row.values,
        consumed_event_ids=list(feature_row.consumed_event_ids),
        content_hash=feature_row.content_hash,
        purpose=feature_row.purpose,
    )
    session.add(stored)
    return stored


def _copy_prediction_to_case(
    case: AcquisitionCase,
    model: MLModelVersion,
    probability: float,
    banding: BandingDecision,
    now: datetime,
) -> None:
    case.risk_probability = probability
    case.risk_band = banding.band
    case.risk_model_version = model.version
    case.risk_generated_at = now
    case.risk_is_stale = False
    case.risk_cutoff_source = banding.cutoff_source


def _mark_stale_and_record_failure(
    session: Session,
    case: AcquisitionCase,
    exc: Exception,
    now: datetime,
) -> None:
    case.risk_is_stale = True
    session.add(
        Event(
            event_type="SCORING_FAILED",
            entity_type="acquisition_case",
            entity_id=case.id,
            case_id=case.id,
            actor_type=ActorType.SYSTEM,
            actor_id="ml.score_case",
            occurrence_time=now,
            payload={"reason": type(exc).__name__, "message": str(exc)},
            has_pd_refs=False,
            provenance=Provenance.SYSTEM,
        )
    )


def _view(case: AcquisitionCase) -> PredictionView:
    return PredictionView(
        case_id=case.id,
        risk_probability=case.risk_probability,
        risk_band=case.risk_band,
        risk_model_version=case.risk_model_version,
        risk_generated_at=case.risk_generated_at,
        risk_is_stale=bool(case.risk_is_stale),
        risk_cutoff_source=case.risk_cutoff_source,
    )
