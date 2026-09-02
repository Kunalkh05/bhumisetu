"""Officer prediction endpoints."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import Depends
from sqlalchemy import select

from app.api.cases import _read_session
from app.api.routers import officer_router
from app.db.session import unit_of_work
from app.models.acquisition_case import AcquisitionCase
from app.models.ml import MLPrediction
from app.schemas.predictions import (
    ExplanationFactorOut,
    PredictionExplanationOut,
    PredictionOverrideIn,
    PredictionOverrideOut,
)
from app.security.access import Principal, authenticate, scoped

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from prediction.explanations import explanation_payload  # noqa: E402
from prediction.overrides import record_prediction_override  # noqa: E402

__all__ = []


@officer_router.get(
    "/predictions/{case_id}",
    response_model=PredictionExplanationOut,
)
def get_prediction(
    case_id: int,
    principal: Principal = Depends(authenticate),
) -> PredictionExplanationOut:
    with _read_session() as session:
        case = session.execute(_scoped_case(case_id, principal)).scalar_one()
        prediction = session.execute(
            select(MLPrediction)
            .where(MLPrediction.case_id == case_id)
            .order_by(MLPrediction.generated_at.desc(), MLPrediction.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        payload = (
            explanation_payload(session, prediction=prediction)
            if prediction is not None
            else {
                "model_version": case.risk_model_version,
                "generated_at": case.risk_generated_at,
                "factors": [],
            }
        )
        return PredictionExplanationOut(
            case_id=case.id,
            risk_probability=case.risk_probability,
            risk_band=case.risk_band,
            priority_score=float(case.priority_score) if case.priority_score is not None else None,
            model_version=payload["model_version"],
            generated_at=payload["generated_at"],
            explanation_factors=[
                ExplanationFactorOut.model_validate(factor)
                for factor in payload["factors"]
            ],
        )


@officer_router.post(
    "/predictions/{case_id}/override",
    response_model=PredictionOverrideOut,
)
def override_prediction(
    case_id: int,
    body: PredictionOverrideIn,
    principal: Principal = Depends(authenticate),
) -> PredictionOverrideOut:
    with unit_of_work() as session:
        case = session.execute(_scoped_case(case_id, principal)).scalar_one()
        override = record_prediction_override(
            session,
            case=case,
            principal=principal,
            overridden_value=body.overridden_value,
            reason=body.reason,
            occurrence_time=body.occurrence_time,
        )
        return PredictionOverrideOut.model_validate(override)


def _scoped_case(case_id: int, principal: Principal):
    return scoped(
        select(AcquisitionCase).where(AcquisitionCase.id == case_id),
        principal,
        area_col=AcquisitionCase.area_code,
        case_col=AcquisitionCase.id,
    )
