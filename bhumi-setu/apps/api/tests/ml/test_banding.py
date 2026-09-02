from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from prediction.banding import band_for, classify, reband_predictions  # noqa: E402


class _Session:
    def __init__(self) -> None:
        self.added = []
        self.flushed = False

    def add(self, obj) -> None:
        obj.id = len(self.added) + 1
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed = True


class _Resolver:
    def __init__(self, values) -> None:
        self.values = values

    def get(self, key: str, *, state: str, act: str | None, as_of: date):
        return self.values[(key, state, act)]

    def try_get(self, key: str, *, state: str, act: str | None, as_of: date):
        return self.values.get((key, state, act))


@dataclass
class _Case:
    id: int = 42
    area_code: str = "D1"
    state_key: str = "IN-MH"
    act_key: str = "RFCTLARR-2013"
    risk_probability: float | None = None
    risk_band: str | None = None
    risk_generated_at: datetime | None = None
    risk_cutoff_source: str | None = None


@dataclass
class _Prediction:
    id: int
    case_id: int
    risk_probability: float
    risk_band: str
    cutoff_source: str
    cutoff_set_version: str
    generated_at: datetime
    model_version_id: int = 5


def _cutoffs(version: str, low: float = 0.25, medium: float = 0.5, high: float = 0.75):
    return {
        "version": version,
        "cutoffs": {"LOW": low, "MEDIUM": medium, "HIGH": high, "CRITICAL": 1.0},
    }


def test_classify_assigns_exactly_one_band_at_boundaries() -> None:
    cutoffs = _cutoffs("v1")["cutoffs"]

    assert classify(0.0, cutoffs) == "LOW"
    assert classify(0.25, cutoffs) == "LOW"
    assert classify(0.2501, cutoffs) == "MEDIUM"
    assert classify(1.0, cutoffs) == "CRITICAL"


@given(
    left=st.floats(min_value=0, max_value=1, allow_nan=False),
    right=st.floats(min_value=0, max_value=1, allow_nan=False),
)
@settings(max_examples=60)
def test_classify_is_monotone_for_valid_cutoffs(left: float, right: float) -> None:
    cutoffs = _cutoffs("v1")["cutoffs"]
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    low, high = sorted((left, right))

    assert order[classify(low, cutoffs)] <= order[classify(high, cutoffs)]


def test_district_cutoffs_apply_above_the_calibration_floor() -> None:
    session = _Session()
    case = _Case()
    resolver = _Resolver(
        {
            ("risk.band_cutoffs.district.D1", "IN-MH", "RFCTLARR-2013"): _cutoffs(
                "district-v1",
                low=0.1,
                medium=0.2,
                high=0.3,
            ),
            ("risk.min_district_calibration_count", "IN-MH", "RFCTLARR-2013"): 10,
            ("risk.band_cutoffs", "IN-MH", "RFCTLARR-2013"): _cutoffs("platform-v1"),
        }
    )

    result = band_for(
        0.35,
        case,
        session=session,
        resolver=resolver,
        observed_count=lambda session, district: 10,
        now=date(2026, 1, 1),
    )

    assert result.band == "CRITICAL"
    assert result.cutoff_source == "DISTRICT"
    assert result.cutoff_set_version == "district-v1"
    assert session.added == []


def test_district_cutoffs_withhold_below_the_floor_and_fall_back_to_platform() -> None:
    session = _Session()
    case = _Case()
    resolver = _Resolver(
        {
            ("risk.band_cutoffs.district.D1", "IN-MH", "RFCTLARR-2013"): _cutoffs(
                "district-v1",
                low=0.1,
                medium=0.2,
                high=0.3,
            ),
            ("risk.min_district_calibration_count", "IN-MH", "RFCTLARR-2013"): 10,
            ("risk.band_cutoffs", "IN-MH", "RFCTLARR-2013"): _cutoffs("platform-v1"),
        }
    )

    result = band_for(
        0.35,
        case,
        session=session,
        resolver=resolver,
        observed_count=lambda session, district: 9,
        now=date(2026, 1, 1),
    )

    assert result.band == "MEDIUM"
    assert result.cutoff_source == "PLATFORM"
    assert result.cutoff_set_version == "platform-v1"
    assert session.added[0].event_type == "DISTRICT_CUTOFFS_WITHHELD"
    assert session.added[0].payload == {"district": "D1", "observed": 9, "minimum": 10}


def test_reband_preserves_probability_model_version_and_generation_time() -> None:
    session = _Session()
    generated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    prediction = _Prediction(
        id=1,
        case_id=42,
        risk_probability=0.6,
        risk_band="LOW",
        cutoff_source="PLATFORM",
        cutoff_set_version="old",
        generated_at=generated_at,
    )
    case = _Case(
        risk_probability=0.6,
        risk_band="LOW",
        risk_generated_at=generated_at,
    )
    resolver = _Resolver(
        {
            ("risk.band_cutoffs", "IN-MH", "RFCTLARR-2013"): _cutoffs("platform-v2"),
        }
    )

    changed = reband_predictions(
        session,
        predictions=[prediction],
        cases={42: case},
        resolver=resolver,
        now=date(2026, 1, 2),
    )

    assert changed == 1
    assert prediction.risk_probability == pytest.approx(0.6)
    assert prediction.model_version_id == 5
    assert prediction.generated_at == generated_at
    assert prediction.risk_band == "HIGH"
    assert prediction.cutoff_set_version == "platform-v2"
    assert case.risk_band == "HIGH"
    assert case.risk_generated_at == generated_at
