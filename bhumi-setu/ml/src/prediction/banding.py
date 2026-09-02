"""Risk-band classification and rebanding."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.acquisition_case import AcquisitionCase
from app.models.event import ActorType, Event, Provenance
from app.models.ml import MLFeatureRow, MLPrediction, MLTrainingRow

__all__ = [
    "BandingResult",
    "classify",
    "band_for",
    "labelled_case_count",
    "reband_predictions",
]

DISTRICT_CUTOFFS_PREFIX = "risk.band_cutoffs.district."
PLATFORM_CUTOFFS_KEY = "risk.band_cutoffs"
MIN_DISTRICT_COUNT_KEY = "risk.min_district_calibration_count"


@dataclass(frozen=True)
class BandingResult:
    band: str
    cutoff_source: str
    cutoff_set_version: str


def classify(probability: float, cutoffs: Mapping[str, float]) -> str:
    """Assign exactly one band from a validated cutoff partition."""
    for band, upper in sorted(cutoffs.items(), key=lambda item: item[1]):
        if probability <= upper:
            return band
    raise ValueError("cutoff set does not cover probability")


def band_for(
    probability: float,
    case: AcquisitionCase,
    *,
    session: Session,
    resolver: Any,
    observed_count: Callable[[Session, str], int] | None = None,
    now: date | None = None,
) -> BandingResult:
    """Return the band and whether district or platform cutoffs produced it."""
    as_of = now or date.today()
    district_key = f"{DISTRICT_CUTOFFS_PREFIX}{case.area_code}"
    district = resolver.try_get(
        district_key,
        state=case.state_key,
        act=case.act_key,
        as_of=as_of,
    )
    if district is not None:
        observed_count = observed_count or labelled_case_count
        observed = observed_count(session, case.area_code)
        minimum = int(
            resolver.get(
                MIN_DISTRICT_COUNT_KEY,
                state=case.state_key,
                act=case.act_key,
                as_of=as_of,
            )
        )
        if observed >= minimum:
            return BandingResult(
                classify(probability, _cutoff_values(district)),
                "DISTRICT",
                _cutoff_version(district, district_key),
            )
        _record_district_withheld(session, case, observed, minimum, as_of)

    platform = resolver.get(
        PLATFORM_CUTOFFS_KEY,
        state=case.state_key,
        act=case.act_key,
        as_of=as_of,
    )
    return BandingResult(
        classify(probability, _cutoff_values(platform)),
        "PLATFORM",
        _cutoff_version(platform, PLATFORM_CUTOFFS_KEY),
    )


def labelled_case_count(session: Session, district: str) -> int:
    return int(
        session.execute(
            select(func.count(func.distinct(MLFeatureRow.case_id)))
            .join(MLFeatureRow, MLFeatureRow.id == MLTrainingRow.feature_row_id)
            .join(AcquisitionCase, AcquisitionCase.id == MLFeatureRow.case_id)
            .where(
                AcquisitionCase.area_code == district,
                MLTrainingRow.label.in_(("DELAYED", "NOT_DELAYED")),
            )
        ).scalar_one()
    )


def reband_predictions(
    session: Session,
    *,
    predictions: list[MLPrediction],
    cases: Mapping[int, AcquisitionCase],
    resolver: Any,
    now: date,
) -> int:
    """Recompute bands while preserving probability, model version and timestamps."""
    changed = 0
    for prediction in predictions:
        case = cases[prediction.case_id]
        prior = (prediction.risk_band, prediction.cutoff_source, prediction.cutoff_set_version)
        banding = band_for(
            prediction.risk_probability,
            case,
            session=session,
            resolver=resolver,
            now=now,
        )
        prediction.risk_band = banding.band
        prediction.cutoff_source = banding.cutoff_source
        prediction.cutoff_set_version = banding.cutoff_set_version
        if (
            case.risk_probability == prediction.risk_probability
            and case.risk_generated_at == prediction.generated_at
        ):
            case.risk_band = banding.band
            case.risk_cutoff_source = banding.cutoff_source
        if prior != (prediction.risk_band, prediction.cutoff_source, prediction.cutoff_set_version):
            changed += 1
    if changed:
        session.flush()
    return changed


def _cutoff_values(value: Mapping[str, Any]) -> Mapping[str, float]:
    if "cutoffs" in value and isinstance(value["cutoffs"], Mapping):
        return value["cutoffs"]
    return value


def _cutoff_version(value: Mapping[str, Any], fallback: str) -> str:
    return str(value.get("version", fallback))


def _record_district_withheld(
    session: Session,
    case: AcquisitionCase,
    observed: int,
    minimum: int,
    as_of: date,
) -> None:
    session.add(
        Event(
            event_type="DISTRICT_CUTOFFS_WITHHELD",
            entity_type="acquisition_case",
            entity_id=case.id,
            case_id=case.id,
            actor_type=ActorType.SYSTEM,
            actor_id="ml.band_for",
            occurrence_time=datetime.combine(as_of, datetime.min.time()),
            payload={
                "district": case.area_code,
                "observed": observed,
                "minimum": minimum,
            },
            has_pd_refs=False,
            provenance=Provenance.SYSTEM,
        )
    )
