"""Celery entrypoint for the retention sweep."""

from __future__ import annotations

from datetime import UTC, datetime

from app.db.session import unit_of_work
from app.retention.dsar import flag_overdue_requests
from app.retention.sweep import run_retention_sweep as run_sweep
from app.services.policy import PolicyResolver
from app.workers.celery_app import celery_app

__all__ = ["flag_dsar_overdue", "run_retention_sweep"]


@celery_app.task(name="app.retention.tasks.run_retention_sweep")
def run_retention_sweep() -> dict[str, int | bool]:
    today = datetime.now(UTC).date()
    with unit_of_work() as session:
        result = run_sweep(
            session,
            today=today,
            resolver=PolicyResolver(session),
        )
        return {
            "enabled": result.enabled,
            "scanned": result.scanned,
            "erased": result.erased,
            "withheld": result.withheld,
        }


@celery_app.task(name="app.retention.tasks.flag_dsar_overdue")
def flag_dsar_overdue() -> dict[str, int]:
    with unit_of_work() as session:
        return {"flagged": flag_overdue_requests(session)}
