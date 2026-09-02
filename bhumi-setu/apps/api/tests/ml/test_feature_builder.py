from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.event_log import AsOfMode

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.asof import AsOfView, AwardState, NoticeState, StageEntry  # noqa: E402
from features.builder import build_feature_row, canonical_hash  # noqa: E402
from features.leakage import LeakageGuardViolation  # noqa: E402
from features.registry import FeatureRegistry  # noqa: E402
from features.value import FeatureValue  # noqa: E402

T = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)


def _view(*, event_ids: tuple[int, ...] = (3, 1, 2)) -> AsOfView:
    return AsOfView(
        case_id=42,
        t=T,
        mode=AsOfMode.KNOWABLE_AT,
        stage_history=(
            StageEntry(1, "PN", datetime(2026, 1, 1, 9, tzinfo=timezone.utc)),
        ),
        notices=(
            NoticeState(
                2,
                20,
                "notice_issued",
                datetime(2026, 1, 10, 9, tzinfo=timezone.utc),
                {},
            ),
        ),
        objections=(),
        parcels=(),
        awards=(
            AwardState(
                3,
                30,
                "award_recorded",
                datetime(2026, 1, 12, 9, tzinfo=timezone.utc),
                {},
            ),
        ),
        issues=(),
        documents=(),
        consumed_event_ids=event_ids,
    )


def test_feature_value_distinguishes_zero_from_missing() -> None:
    zero = FeatureValue(value=0)
    missing = FeatureValue(missing_reason="NO_STAGE_ENTRY_EVENT")

    assert zero.to_json() == {"value": 0, "missing_reason": None}
    assert missing.to_json() == {
        "value": None,
        "missing_reason": "NO_STAGE_ENTRY_EVENT",
    }
    assert zero.to_model_columns("days") == {"days": 0.0, "days_is_missing": 0.0}
    missing_columns = missing.to_model_columns("days")
    assert math.isnan(missing_columns["days"])
    assert missing_columns["days_is_missing"] == 1.0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({}, "exactly one"),
        ({"value": 1, "missing_reason": "NOPE"}, "exactly one"),
    ],
)
def test_feature_value_refuses_ambiguous_values(kwargs, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        FeatureValue(**kwargs)


def test_build_feature_row_hashes_canonical_values_and_consumed_event_ids(
    monkeypatch: pytest.MonkeyPatch,
    transactional_sqlite_engine,
) -> None:
    import features.builder as builder

    monkeypatch.setattr(builder, "build_as_of_view", lambda *args, **kwargs: _view())
    session = Session(bind=transactional_sqlite_engine)

    row = build_feature_row(session, 42, T, AsOfMode.KNOWABLE_AT)

    assert row.consumed_event_ids == (1, 2, 3)
    assert row.values["days_in_current_stage"] == {
        "value": 14,
        "missing_reason": None,
    }
    assert row.values["days_since_latest_notice"] == {
        "value": 5,
        "missing_reason": None,
    }
    assert row.values["award_recorded"] == {"value": True, "missing_reason": None}
    assert row.model_input["days_in_current_stage"] == 14.0
    assert row.model_input["days_in_current_stage_is_missing"] == 0.0
    assert row.content_hash == canonical_hash(
        feature_set_version=row.feature_set_version,
        as_of_mode=row.as_of_mode,
        consumed_event_ids=(3, 2, 1),
        values=row.values,
    )


def test_build_feature_row_runs_extractors_inside_database_guard(
    monkeypatch: pytest.MonkeyPatch,
    transactional_sqlite_engine,
) -> None:
    import features.builder as builder

    session = Session(bind=transactional_sqlite_engine)
    session.execute(text("SELECT 0")).scalar_one()
    monkeypatch.setattr(builder, "build_as_of_view", lambda *args, **kwargs: _view())

    class QueryingExtractor:
        name = "querying_extractor"
        source_attributes = frozenset({"stage_key"})

        def compute(self, view, t):
            session.execute(text("SELECT 1")).scalar_one()
            return FeatureValue(value=1)

    registry = FeatureRegistry()
    registry.register(QueryingExtractor())

    with pytest.raises(LeakageGuardViolation, match="SELECT 1"):
        build_feature_row(session, 42, T, AsOfMode.KNOWABLE_AT, registry=registry)
