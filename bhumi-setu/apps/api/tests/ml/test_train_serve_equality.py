from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from app.workers.celery_app import TASK_ROUTES, celery_app

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.equality import (  # noqa: E402
    RECENT_INFERENCE_WINDOW_SECONDS,
    RederivationReport,
    recent_inference_window_start,
)
from features.registry import FEATURE_REGISTRY  # noqa: E402
from labelling.sources import LABEL_SOURCE_ATTRIBUTES  # noqa: E402


def test_label_and_feature_sources_are_disjoint() -> None:
    feature_sources = frozenset(
        source
        for extractor in FEATURE_REGISTRY.all()
        for source in extractor.source_attributes
    )

    assert feature_sources
    assert LABEL_SOURCE_ATTRIBUTES
    assert not (feature_sources & LABEL_SOURCE_ATTRIBUTES)


def test_recent_inference_window_is_the_declared_rolling_day() -> None:
    now = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)

    assert RECENT_INFERENCE_WINDOW_SECONDS == 24 * 60 * 60
    assert (
        now - recent_inference_window_start(now)
    ).total_seconds() == RECENT_INFERENCE_WINDOW_SECONDS


def test_rederivation_report_serializes_divergences() -> None:
    report = RederivationReport(checked_count=0, divergences=())

    assert report.ok
    assert report.to_json() == {"checked_count": 0, "ok": True, "divergences": []}


def test_train_serve_rederivation_job_is_routed_to_ml_queue() -> None:
    assert TASK_ROUTES["ml.tasks.verify_train_serve_equality"]["queue"] == "ml"
    scheduled = {entry["task"] for entry in celery_app.conf.beat_schedule.values()}
    assert "ml.tasks.verify_train_serve_equality" in scheduled
