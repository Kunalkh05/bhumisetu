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


@celery_app.task(name="ml.tasks.verify_train_serve_equality")
def verify_train_serve_equality() -> dict[str, object]:
    with unit_of_work() as session:
        return verify_recent_inference_rows(session, now=datetime.now(UTC)).to_json()
