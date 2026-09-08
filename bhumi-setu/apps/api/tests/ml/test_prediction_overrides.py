from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.security.access import Principal

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from prediction.overrides import record_prediction_override  # noqa: E402


NOW = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)


class _Session:
    def __init__(self) -> None:
        self.added = []
        self.flushed = False

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed = True


@dataclass
class _Case:
    id: int = 42
    risk_probability: float | None = 0.72
    risk_band: str | None = "HIGH"
    risk_model_version: str | None = "model-v3"
    risk_generated_at: datetime | None = NOW


def _officer() -> Principal:
    return Principal(kind="OFFICER", id="officer-1", permissions=frozenset())


def test_record_prediction_override_appends_event_with_model_output_retained() -> None:
    session = _Session()
    override = record_prediction_override(
        session,
        case=_Case(),
        principal=_officer(),
        overridden_value="LOW",
        reason="site inspection resolved the delay risk",
        occurrence_time=NOW,
    )

    assert override.overridden_value == "LOW"
    assert override.model_probability == pytest.approx(0.72)
    event = session.added[0]
    assert event.event_type == "PREDICTION_OVERRIDE_RECORDED"
    assert event.actor_type == "OFFICER"
    assert event.actor_id == "officer-1"
    assert event.payload == {
        "overridden_value": "LOW",
        "reason": "site inspection resolved the delay risk",
        "model_probability": 0.72,
        "model_band": "HIGH",
        "model_version": "model-v3",
        "model_generated_at": NOW.isoformat(),
    }
    assert session.flushed


def test_prediction_override_refuses_non_officer_principals() -> None:
    with pytest.raises(PermissionError):
        record_prediction_override(
            _Session(),
            case=_Case(),
            principal=Principal(kind="CITIZEN", id="citizen-1", case_id=42),
            overridden_value="LOW",
            reason="not allowed",
            occurrence_time=NOW,
        )
