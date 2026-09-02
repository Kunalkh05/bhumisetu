from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from app.models.ml import MLExplanationFactor
from prediction.explanations import (  # noqa: E402
    explanation_payload,
    persist_explanation_factors,
    rank_explanation_factors,
    ShapFactor,
)


class _Session:
    def __init__(self) -> None:
        self.added = []
        self.executed = []
        self.flushed = False

    def execute(self, statement):  # type: ignore[no-untyped-def]
        self.executed.append(statement)
        return _Result(())

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed = True

    def get(self, model, key):  # type: ignore[no-untyped-def]
        return _Model()


class _Result:
    def __init__(self, rows) -> None:
        self._rows = rows

    def scalars(self):  # type: ignore[no-untyped-def]
        return iter(self._rows)


@dataclass
class _Model:
    version: str = "model-v3"


@dataclass
class _Prediction:
    id: int = 12
    model_version_id: int = 7
    generated_at: datetime = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)


def test_rank_explanation_factors_keeps_top_five_with_label_keys() -> None:
    ranked = rank_explanation_factors(
        [
            ShapFactor("notice_count", 0.10),
            ShapFactor("days_since_latest_notice", -0.40),
            ShapFactor("parcel_count", 0.30),
            ShapFactor("objection_count", 0.50),
            ShapFactor("open_issue_count", 0.20),
            ShapFactor("award_recorded", -0.05),
        ],
        label_key_for=lambda name: f"translated.{name}",
    )

    assert [factor.feature_name for factor in ranked] == [
        "objection_count",
        "days_since_latest_notice",
        "parcel_count",
        "open_issue_count",
        "notice_count",
    ]
    assert [factor.rank for factor in ranked] == [1, 2, 3, 4, 5]
    assert ranked[0].direction == "INCREASES_RISK"
    assert ranked[1].direction == "DECREASES_RISK"
    assert ranked[0].label_key == "translated.objection_count"
    assert all(" " not in factor.label_key for factor in ranked)


def test_persist_explanation_factors_writes_ranked_rows() -> None:
    session = _Session()
    ranked = rank_explanation_factors([ShapFactor("notice_count", 0.2)])

    rows = persist_explanation_factors(session, prediction_id=9, factors=ranked)

    assert rows == tuple(session.added)
    assert isinstance(rows[0], MLExplanationFactor)
    assert rows[0].prediction_id == 9
    assert rows[0].label_key == "ml.feature.notice_count"
    assert session.flushed


def test_explanation_payload_carries_model_version_generation_time_and_top_factors() -> None:
    row = MLExplanationFactor(
        prediction_id=12,
        rank=1,
        feature_name="notice_count",
        label_key="ml.feature.notice_count",
        direction="INCREASES_RISK",
        magnitude=0.4,
    )
    session = _Session()
    session.execute = lambda statement: _Result((row,))  # type: ignore[method-assign]
    prediction = _Prediction()

    payload = explanation_payload(session, prediction=prediction)

    assert payload["model_version"] == "model-v3"
    assert payload["generated_at"] == prediction.generated_at
    assert payload["factors"] == [
        {
            "rank": 1,
            "feature_name": "notice_count",
            "label_key": "ml.feature.notice_count",
            "direction": "INCREASES_RISK",
            "magnitude": pytest.approx(0.4),
        }
    ]
