"""The §13.7 queue topology, asserted rather than assumed.

The topology carries two guarantees that are easy to lose in a config edit:
bulk accuracy measurement cannot starve interactive extraction, and a task
routed to a name nobody declared fails loudly instead of vanishing.
"""

from __future__ import annotations

import pytest

from app.workers.celery_app import (
    QUEUE_NAMES,
    TASK_MODULES,
    TASK_ROUTES,
    celery_app,
)

EXPECTED_QUEUES = {"ocr", "ocr_bulk", "ml", "import", "maintenance"}

EXPECTED_BEAT_TASKS = {
    "app.services.notice.deadline_sweep",
    "ml.tasks.score_stale_cases",
    "ml.tasks.monitor_calibration",
    "ml.tasks.monitor_drift",
    "app.services.dashboard.refresh_dashboard_snapshot",
    "app.retention.tasks.run_retention_sweep",
    "app.db.outbox.dispatch_outbox",
}


def declared_queue_names() -> set[str]:
    return {queue.name for queue in celery_app.conf.task_queues}


def test_the_five_queues_of_section_13_7_are_declared() -> None:
    assert set(QUEUE_NAMES) == EXPECTED_QUEUES
    assert declared_queue_names() == EXPECTED_QUEUES


def test_bulk_measurement_cannot_starve_interactive_extraction() -> None:
    """``ocr_bulk`` is a separate queue, not a priority on ``ocr``.

    An accuracy measurement runs over 200+ documents (§13.6). Sharing a queue
    would put it in front of interactive extraction; a priority would only make
    that unlikely, while a separate queue makes it impossible.
    """
    assert TASK_ROUTES["app.services.ocr.extract_document"]["queue"] == "ocr"
    assert (
        TASK_ROUTES["app.services.ocr.measure_extraction_accuracy"]["queue"]
        == "ocr_bulk"
    )


def test_every_route_targets_a_declared_queue() -> None:
    targets = {route["queue"] for route in TASK_ROUTES.values()}
    assert targets <= EXPECTED_QUEUES


def test_a_task_routed_to_an_undeclared_queue_fails_rather_than_vanishing() -> None:
    """Celery's default would create the queue; nobody would consume it."""
    assert celery_app.conf.task_create_missing_queues is False
    assert celery_app.conf.task_default_queue == "maintenance"
    assert celery_app.conf.task_default_queue in EXPECTED_QUEUES


def test_prefetch_is_one_so_a_long_job_reserves_one_job() -> None:
    """§13.7's ``ocr_bulk`` prefetch 1.

    Prefetch is a worker-level setting in Celery, so it is set here and the
    per-queue effect follows from running ``ocr_bulk`` at concurrency 1.
    """
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_delivery_is_at_least_once_which_is_why_tasks_must_be_idempotent() -> None:
    """§13.4's idempotency requirement is a consequence of these two settings.

    Combined with the transactional outbox publishing at-least-once (§5.2,
    because Redis has no transactional enqueue), a task can be delivered more
    than once and must tolerate it.
    """
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_times_are_utc() -> None:
    """Every occurrence and recording time in the event log is UTC (§5.1)."""
    assert celery_app.conf.enable_utc is True
    assert celery_app.conf.timezone == "UTC"


def test_beat_declares_the_section_13_7_schedule() -> None:
    scheduled = {entry["task"] for entry in celery_app.conf.beat_schedule.values()}
    assert scheduled == EXPECTED_BEAT_TASKS


def test_every_beat_entry_routes_to_a_declared_queue() -> None:
    for name, entry in celery_app.conf.beat_schedule.items():
        assert entry["task"] in TASK_ROUTES, f"beat entry {name} has no route"


def test_the_outbox_is_dispatched_every_two_seconds() -> None:
    """§5.2: nothing enqueued in a transaction is visible to a worker until this runs."""
    entry = celery_app.conf.beat_schedule["dispatch-outbox"]
    assert entry["task"] == "app.db.outbox.dispatch_outbox"
    assert entry["schedule"] == pytest.approx(2.0)


def test_no_task_modules_are_registered_yet() -> None:
    """Task 1.1 ships the topology, not the tasks. Each lands with its own task."""
    assert TASK_MODULES == ()
    assert celery_app.conf.include == ()


def test_broker_is_the_committed_redis_url() -> None:
    from app.settings import get_broker_settings

    assert celery_app.conf.broker_url == get_broker_settings().redis_url


def test_the_celery_app_reads_only_the_broker_group() -> None:
    """Every Celery process imports this module, including ``worker-beat``.

    ``worker-beat`` holds no object-storage credential and ``worker-ocr`` holds no
    ``APP_ENV``. Reading anything beyond ``REDIS_URL`` here would stop those
    processes from starting, or force compose to hand every process every
    credential — which is the option that destroys R11.10's credential
    separation.
    """
    import inspect

    from app.workers import celery_app as module

    source = inspect.getsource(module)
    for accessor in (
        "get_core_settings",
        "get_database_settings",
        "get_object_storage_settings",
        "get_internal_token_settings",
    ):
        assert accessor not in source


def test_no_result_backend_is_configured() -> None:
    """Nothing waits on a task result; outcomes are read from PostgreSQL."""
    assert not celery_app.conf.result_backend
