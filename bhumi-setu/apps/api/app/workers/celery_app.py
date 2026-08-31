"""The Celery application: §13.7's queue topology, declared once.

Queues (§13.7)
--------------

======================  ==============  =============  ==================================
Queue                   Worker          Concurrency    Tasks
======================  ==============  =============  ==================================
``ocr``                 worker-ocr      2              ``extract_document``
``ocr_bulk``            worker-ocr      1, prefetch 1  ``measure_extraction_accuracy``
``ml``                  worker-ml       1              scoring, features, training, monitoring
``import``              worker-general  4              ``process_import_chunk``
``maintenance``         worker-general  2              outbox, dashboard, deadlines, retention, OTP
======================  ==============  =============  ==================================

``ocr_bulk`` is a separate queue rather than a priority on ``ocr`` because an
accuracy measurement over 200+ documents (§13.6) would otherwise sit in front of
interactive extraction. Separation is what makes starvation impossible; a
priority would only make it unlikely.

``worker_prefetch_multiplier = 1`` is set here rather than per worker, because
prefetch is a worker-level setting in Celery and cannot vary by queue on a shared
process. With the multiplier at 1, §13.7's "prefetch 1" for ``ocr_bulk`` follows
from running that queue on its own process at concurrency 1
(``-Q ocr_bulk -c 1``), which is what the compose entry in task 1.3 declares.
One long measurement then reserves one job, not several.

Delivery guarantees
-------------------

``task_acks_late`` with ``task_reject_on_worker_lost`` means a task killed
mid-flight is redelivered rather than lost. Combined with the transactional
outbox (§5.2) — which publishes at-least-once because Redis has no transactional
enqueue — every task is delivered one *or more* times, which is why §13.4
requires each one to be idempotent. That is a constraint on every task task 3.8
onward adds, and it is a consequence of settings on this object.

``task_create_missing_queues = False``: a task routed to a queue name that is not
declared below raises at publish time. Left at Celery's default, a typo would
create a queue nobody consumes and the task would vanish without an error.

No ``result_backend`` is configured. Nothing in the design waits on a task
result; outcomes are persisted by the task itself and read from PostgreSQL.

Task registration
-----------------

``TASK_MODULES`` is the single registry of importable task modules, and it is
empty at task 1.1. Unlike ``app/models/`` (registered by a disk walk, see
``app/models/__init__.py``), task modules are scattered across services by §3.2 —
``app.services.notice`` holds ``deadline_sweep``, ``workers/ocr`` holds the
engine — so there is no single package to walk. Adding a task means adding its
module here; a task in an unlisted module is not registered and its beat entry
will fail loudly at dispatch rather than silently no-op.

Beat schedule
-------------

Declared here as the skeleton §13.7 names. The tasks themselves belong to their
own later tasks, so every entry is commented and inert until its module appears
in ``TASK_MODULES``. Intervals are ``crontab`` expressions or plain seconds, not
``timedelta(...)`` — task 2.6's AST lint fails on a constant keyword argument to
``timedelta``, and a scheduling interval is not worth an exception to a rule whose
purpose is to keep statutory periods out of the code.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.settings import get_broker_settings

#: §13.7's five queues. Nothing else may be published to (see
#: ``task_create_missing_queues`` above).
QUEUE_NAMES: tuple[str, ...] = ("ocr", "ocr_bulk", "ml", "import", "maintenance")

#: The single registry of modules Celery imports to find tasks. Empty at task
#: 1.1; each later task adds its own module. Task 3.8 adds the first —
#: ``app.db.outbox`` — whose ``dispatch_outbox`` the beat schedule below drives.
#: A task whose module is absent here is never registered, and its beat entry
#: fails loudly at dispatch rather than silently no-opping.
TASK_MODULES: tuple[str, ...] = ("app.db.outbox",)

#: Task name -> queue. Routing is explicit for every task in §13.7 so that a
#: task's queue is a property of the topology rather than of its call site.
TASK_ROUTES: dict[str, dict[str, str]] = {
    # ocr — interactive extraction (§13.2)
    "app.services.ocr.extract_document": {"queue": "ocr"},
    # ocr_bulk — accuracy measurement over the holdout set (§13.6)
    "app.services.ocr.measure_extraction_accuracy": {"queue": "ocr_bulk"},
    # ml — features, scoring, training, monitoring (§14)
    "ml.tasks.build_feature_rows": {"queue": "ml"},
    "ml.tasks.score_case": {"queue": "ml"},
    "ml.tasks.score_stale_cases": {"queue": "ml"},
    "ml.tasks.train_model": {"queue": "ml"},
    "ml.tasks.monitor_calibration": {"queue": "ml"},
    "ml.tasks.monitor_drift": {"queue": "ml"},
    # import — chunked bulk import (§16)
    "app.services.import_service.process_import_chunk": {"queue": "import"},
    # maintenance — everything scheduled or fired from the outbox (§5.2, §13.7)
    "app.db.outbox.dispatch_outbox": {"queue": "maintenance"},
    "app.services.dashboard.refresh_dashboard_snapshot": {"queue": "maintenance"},
    "app.services.notice.deadline_sweep": {"queue": "maintenance"},
    "app.retention.tasks.run_retention_sweep": {"queue": "maintenance"},
    "app.security.otp.send_otp": {"queue": "maintenance"},
}


def _beat_schedule() -> dict[str, dict[str, object]]:
    """The §13.7 beat schedule.

    Two entries are not simply "run on this cadence":

    * ``monitor_calibration`` and ``monitor_drift`` run on a cadence that is a
      ``Policy_Config`` value with a 7-day ceiling (R31.1, R31.5). Beat cannot
      read configuration at import time, so they are dispatched daily and the
      task returns immediately unless the configured interval has elapsed. The
      ceiling is enforced by the task, which is also what makes R31.13's
      "monitoring unavailable" state reachable when a cadence is overrun.
    * ``run_retention_sweep`` is scheduled but ships inert: the task checks
      ``retention.sweep_enabled``, which is unseeded and therefore false until
      Q10 is confirmed (§1.3). Erasure is irreversible, so the sweep is disabled
      by configuration rather than by omitting the entry, which would hide the
      fact that it exists.
    """
    return {
        # R7.6, R7.7 — approaching and breached Stage_Deadlines.
        "deadline-sweep-hourly": {
            "task": "app.services.notice.deadline_sweep",
            "schedule": crontab(minute="0"),
        },
        # R19.2 — rescore cases whose score is older than the configured age.
        # The age filter is resolved by the task from Policy_Config, not passed
        # here: a number in this file is a statutory-adjacent constant in code.
        "score-stale-cases-hourly": {
            "task": "ml.tasks.score_stale_cases",
            "schedule": crontab(minute="30"),
        },
        # R31.1 — realized-versus-predicted calibration.
        "monitor-calibration-daily": {
            "task": "ml.tasks.monitor_calibration",
            "schedule": crontab(hour="1", minute="0"),
        },
        # R31.5 — population stability over the training-window bins.
        "monitor-drift-daily": {
            "task": "ml.tasks.monitor_drift",
            "schedule": crontab(hour="1", minute="30"),
        },
        # R22.5 — the dashboard is materialized, refreshed every 5 minutes.
        "refresh-dashboard-snapshot": {
            "task": "app.services.dashboard.refresh_dashboard_snapshot",
            "schedule": crontab(minute="*/5"),
        },
        # R32.10 — daily, and inert until `retention.sweep_enabled` is true.
        "run-retention-sweep-daily": {
            "task": "app.retention.tasks.run_retention_sweep",
            "schedule": crontab(hour="2", minute="0"),
        },
        # §5.2 — the transactional outbox is only as timely as this entry.
        # Seconds as a float; see the note on timedelta in the module docstring.
        "dispatch-outbox": {
            "task": "app.db.outbox.dispatch_outbox",
            "schedule": 2.0,
        },
    }


def create_celery_app() -> Celery:
    """Build the Celery application from the process environment.

    Reads ``BrokerSettings`` and nothing else. Every Celery process in the stack
    imports this module — including ``worker-beat``, which holds no
    object-storage credential and no ``DATABASE_URL`` consumer — so requiring
    anything more here would stop those processes from starting or would force
    the compose file to hand every process every credential. See the note on
    capability groups in ``app/settings.py``.
    """
    broker = get_broker_settings()
    app = Celery("bhumisetu", broker=broker.redis_url, include=TASK_MODULES)
    app.conf.update(
        # Topology (§13.7).
        task_queues=tuple(Queue(name) for name in QUEUE_NAMES),
        task_default_queue="maintenance",
        task_routes=TASK_ROUTES,
        task_create_missing_queues=False,
        worker_prefetch_multiplier=1,
        # Delivery (§13.4, §5.2).
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        result_backend=None,
        # Time. Every occurrence and recording time in the event log is UTC
        # (§5.1), and a worker on a different clock convention would write
        # inconsistent timestamps.
        timezone="UTC",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        beat_schedule=_beat_schedule(),
    )
    return app


celery_app = create_celery_app()
