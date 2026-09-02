"""ML Celery tasks owned by the worker-ml queue."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

from app.db.session import unit_of_work
from app.workers.celery_app import celery_app

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.equality import verify_recent_inference_rows  # noqa: E402
from prediction.service import score_case as score_one_case  # noqa: E402
from prediction.service import stale_case_ids  # noqa: E402


class ArtifactScorer:
    def predict_probability(self, model_version, model_input):  # type: ignore[no-untyped-def]
        raise RuntimeError(
            "model artifact loading is not configured in this worker process"
        )


@celery_app.task(name="ml.tasks.verify_train_serve_equality")
def verify_train_serve_equality() -> dict[str, object]:
    with unit_of_work() as session:
        return verify_recent_inference_rows(session, now=datetime.now(UTC)).to_json()


@celery_app.task(name="ml.tasks.score_case")
def score_case(case_id: int) -> dict[str, object]:
    with unit_of_work() as session:
        return score_one_case(
            session,
            case_id,
            ArtifactScorer(),
            now=datetime.now(UTC),
        ).to_response()


@celery_app.task(name="ml.tasks.score_stale_cases")
def score_stale_cases() -> dict[str, object]:
    now = datetime.now(UTC)
    with unit_of_work() as session:
        case_ids = stale_case_ids(session, now=now)
        for case_id in case_ids:
            score_one_case(session, case_id, ArtifactScorer(), now=now)
        return {"scored_count": len(case_ids), "case_ids": list(case_ids)}
