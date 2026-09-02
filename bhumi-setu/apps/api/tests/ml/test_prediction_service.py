from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.db.event_log import AsOfMode
from app.models.acquisition_case import AcquisitionCase
from app.models.ml import MLModelVersion

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.builder import FeatureRow  # noqa: E402
from prediction.service import (  # noqa: E402
    BandingDecision,
    PredictionView,
    score_case,
    should_trigger_scoring,
    stale_cutoff,
)

NOW = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)


class _Session:
    def __init__(self, case) -> None:
        self.case = case
        self.added = []
        self.flushed = False

    def get(self, model, key, **kwargs):  # type: ignore[no-untyped-def]
        if model is AcquisitionCase and key == self.case.id:
            return self.case
        return None

    def add(self, obj) -> None:
        obj.id = len(self.added) + 100
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed = True


class _Scorer:
    def __init__(self, probability: float | Exception) -> None:
        self.probability = probability

    def predict_probability(self, model_version, model_input):  # type: ignore[no-untyped-def]
        if isinstance(self.probability, Exception):
            raise self.probability
        return self.probability


@dataclass
class _Case:
    id: int = 42
    risk_probability: float | None = None
    risk_band: str | None = None
    risk_model_version: str | None = None
    risk_generated_at: datetime | None = None
    risk_is_stale: bool = False
    risk_cutoff_source: str | None = None


@dataclass
class _Model:
    id: int = 7
    version: str = "model-v1"
    feature_set_version: str = "fs-v1"


def _feature_row() -> FeatureRow:
    return FeatureRow(
        case_id=42,
        reference_t=NOW,
        as_of_mode=str(AsOfMode.KNOWABLE_AT),
        feature_set_version="fs-v1",
        purpose="INFERENCE",
        values={"days": {"value": 1, "missing_reason": None}},
        model_input={"days": 1.0, "days_is_missing": 0.0},
        consumed_event_ids=(1,),
        content_hash="hash",
    )


def test_not_scored_response_omits_probability() -> None:
    response = PredictionView(
        case_id=42,
        risk_probability=None,
        risk_band=None,
        risk_model_version=None,
        risk_generated_at=None,
        risk_is_stale=False,
        risk_cutoff_source=None,
    ).to_response()

    assert "risk_probability" not in response
    assert response == {"case_id": 42, "risk_is_stale": False, "not_scored": True}


def test_scored_response_carries_monitoring_state_when_attached() -> None:
    response = PredictionView(
        case_id=42,
        risk_probability=0.72,
        risk_band="HIGH",
        risk_model_version="model-v3",
        risk_generated_at=NOW,
        risk_is_stale=False,
        risk_cutoff_source="PLATFORM",
    ).with_monitoring_state(
        state="UNAVAILABLE",
        last_successful_at=NOW - timedelta(days=2),
    ).to_response()

    assert response["risk_probability"] == pytest.approx(0.72)
    assert response["monitoring_state"] == "UNAVAILABLE"
    assert response["monitoring_last_successful_at"] == NOW - timedelta(days=2)


def test_score_case_returns_not_scored_when_no_model_is_promoted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import prediction.service as service

    monkeypatch.setattr(service, "current_promoted_model", lambda session: None)
    result = score_case(_Session(_Case()), 42, _Scorer(0.7), now=NOW)

    assert result.risk_probability is None
    assert "risk_probability" not in result.to_response()


def test_score_case_records_prediction_and_denormalizes_to_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import prediction.service as service

    case = _Case()
    session = _Session(case)
    monkeypatch.setattr(service, "current_promoted_model", lambda session: _Model())
    monkeypatch.setattr(service, "build_inference_row", lambda *args, **kwargs: _feature_row())

    result = score_case(
        session,
        42,
        _Scorer(0.72),
        now=NOW,
        band_for=lambda probability, case: BandingDecision("HIGH", "PLATFORM", "risk-v1"),
    )

    assert result.risk_probability == pytest.approx(0.72)
    assert case.risk_probability == pytest.approx(0.72)
    assert case.risk_band == "HIGH"
    assert case.risk_model_version == "model-v1"
    assert case.risk_generated_at == NOW
    assert case.risk_is_stale is False
    assert [type(obj).__name__ for obj in session.added] == ["MLFeatureRow", "MLPrediction"]
    assert session.flushed


def test_score_case_marks_stale_and_records_event_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import prediction.service as service

    case = _Case(
        risk_probability=0.4,
        risk_band="MEDIUM",
        risk_model_version="model-v0",
        risk_generated_at=NOW - timedelta(seconds=20),
    )
    session = _Session(case)
    monkeypatch.setattr(service, "current_promoted_model", lambda session: _Model())
    monkeypatch.setattr(service, "build_inference_row", lambda *args, **kwargs: _feature_row())

    result = score_case(session, 42, _Scorer(RuntimeError("artifact missing")), now=NOW)

    assert result.risk_probability == pytest.approx(0.4)
    assert result.risk_band == "MEDIUM"
    assert result.risk_is_stale is True
    assert case.risk_is_stale is True
    assert session.added[-1].event_type == "SCORING_FAILED"
    assert session.added[-1].payload["reason"] == "RuntimeError"


def test_feature_source_events_trigger_scoring() -> None:
    assert should_trigger_scoring("stage_key")
    assert should_trigger_scoring(
        "CASE_UPDATED",
        changed_attributes={"stage_key"},
    )
    assert not should_trigger_scoring("UNRELATED_EVENT", changed_attributes={"owner_name"})


def test_stale_cutoff_uses_the_twenty_four_hour_age_filter() -> None:
    assert stale_cutoff(NOW) == NOW - timedelta(seconds=24 * 60 * 60)
