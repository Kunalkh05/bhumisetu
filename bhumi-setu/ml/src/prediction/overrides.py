"""Officer override recording for model predictions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.acquisition_case import AcquisitionCase
from app.models.event import Event, Provenance
from app.security.access import Principal

__all__ = ["PredictionOverride", "record_prediction_override"]


@dataclass(frozen=True)
class PredictionOverride:
    case_id: int
    officer_id: str
    overridden_value: str
    reason: str
    occurrence_time: datetime
    model_probability: float | None
    model_band: str | None
    model_version: str | None
    model_generated_at: datetime | None


def record_prediction_override(
    session: Session,
    *,
    case: AcquisitionCase,
    principal: Principal,
    overridden_value: str,
    reason: str,
    occurrence_time: datetime | None = None,
) -> PredictionOverride:
    """Append an immutable override event while retaining the model output."""
    if principal.kind != "OFFICER":
        raise PermissionError("prediction overrides require an officer principal")
    now = occurrence_time or datetime.now(UTC)
    override = PredictionOverride(
        case_id=case.id,
        officer_id=principal.id,
        overridden_value=overridden_value,
        reason=reason,
        occurrence_time=now,
        model_probability=case.risk_probability,
        model_band=case.risk_band,
        model_version=case.risk_model_version,
        model_generated_at=case.risk_generated_at,
    )
    session.add(
        Event(
            event_type="PREDICTION_OVERRIDE_RECORDED",
            entity_type="acquisition_case",
            entity_id=case.id,
            case_id=case.id,
            actor_type=principal.kind,
            actor_id=principal.id,
            occurrence_time=now,
            payload={
                "overridden_value": overridden_value,
                "reason": reason,
                "model_probability": case.risk_probability,
                "model_band": case.risk_band,
                "model_version": case.risk_model_version,
                "model_generated_at": case.risk_generated_at.isoformat()
                if case.risk_generated_at is not None
                else None,
            },
            has_pd_refs=False,
            provenance=Provenance.MANUAL,
        )
    )
    session.flush()
    return override
