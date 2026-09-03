"""Priority, queue, dashboard, and validation performance guards (task 24.5)."""

from __future__ import annotations

import os
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.dashboard import DashboardSnapshot
from app.services.dashboard import service as dashboard_service
from app.services.intervention import attach_recommended_actions
from app.services.validation import ChunkRuleContext
from app.services.validation.rules import DEFAULT_RULES

pytestmark = pytest.mark.perf

QUEUE_BUDGET_SECONDS = 3.0
DASHBOARD_BUDGET_SECONDS = 3.0
VALIDATION_BUDGET_SECONDS = 5.0


@dataclass(frozen=True)
class _Case:
    id: int
    case_reference: str
    stage_key: str
    risk_band: str | None
    priority_score: Decimal
    priority_computed_at: datetime
    stage_deadline: date
    open_blocking_count: int
    undisposed_objection_count: int
    pending_review_count: int


def test_queue_page_attachment_p95_under_three_seconds() -> None:
    cases = tuple(
        _Case(
            id=index,
            case_reference=f"BENCH-{index}",
            stage_key="AWARD",
            risk_band="HIGH" if index % 3 == 0 else "LOW",
            priority_score=Decimal(10_000 - index) / Decimal("100"),
            priority_computed_at=datetime(2026, 9, 3, tzinfo=UTC),
            stage_deadline=date(2026, 9, 6),
            open_blocking_count=index % 2,
            undisposed_objection_count=index % 4,
            pending_review_count=0,
        )
        for index in range(_case_count())
    )
    rules = (
        {
            "id": "blocking",
            "label_key": "action.blocking",
            "reason_key": "action.reason.blocking",
            "when": {"open_blocking_count_gt": 0},
        },
        {
            "id": "deadline",
            "label_key": "action.deadline",
            "reason_key": "action.reason.deadline",
            "when": {"deadline_within_days": 3, "risk_band_in": ["HIGH"]},
        },
    )
    timings = []
    for _ in range(_sample_count()):
        started = time.perf_counter()
        page = sorted(cases, key=lambda case: (-case.priority_score, case.id))[:50]
        actions = attach_recommended_actions(page, rules=rules, today=date(2026, 9, 3))
        assert len(actions) == 50
        timings.append(time.perf_counter() - started)

    assert _p95(timings) <= QUEUE_BUDGET_SECONDS


def test_dashboard_rollup_p95_under_three_seconds() -> None:
    snapshots = tuple(
        DashboardSnapshot(
            area_code=f"A{index}",
            metrics={
                "cases_by_stage": {
                    "value": {"NOTICE": 1, "AWARD": index % 2},
                    "computed_at": "2026-09-03T00:00:00+00:00",
                },
                "cases_by_band": {
                    "value": {"HIGH": index % 3, "LOW": 1},
                    "computed_at": "2026-09-03T00:00:00+00:00",
                },
                "breached_deadline_count": {
                    "value": index % 5,
                    "computed_at": "2026-09-03T00:00:00+00:00",
                },
            },
            computed_at=datetime(2026, 9, 3, tzinfo=UTC),
        )
        for index in range(_case_count())
    )
    timings = []
    for _ in range(_sample_count()):
        started = time.perf_counter()
        merged = dashboard_service._merge_snapshot_metrics(  # noqa: SLF001
            snapshot.metrics for snapshot in snapshots
        )
        assert merged["cases_by_stage"].value["NOTICE"] == _case_count()
        timings.append(time.perf_counter() - started)

    assert _p95(timings) <= DASHBOARD_BUDGET_SECONDS


def test_validation_rule_evaluation_p95_under_five_seconds() -> None:
    context = ChunkRuleContext(
        case_id=1,
        rows={
            "land_parcel": tuple(
                {
                    "id": index,
                    "state_key": "MH",
                    "district": "Pune",
                    "tehsil": "Haveli",
                    "village": f"Village {index}",
                    "survey_number": str(index),
                    "extent": "1",
                    "extent_unit": "hectare",
                    "geodesic_area_sqm": Decimal("10000"),
                }
                for index in range(100)
            ),
            "ownership_record": tuple(
                {
                    "id": index,
                    "parcel_id": index % 100,
                    "owner_identity_key": f"owner-{index}",
                    "share": Decimal("1"),
                    "valid_from": date(2026, 1, 1),
                    "valid_to": None,
                }
                for index in range(100)
            ),
            "award": tuple(
                {"id": index, "ownership_record_id": index, "total_amount": Decimal("10")}
                for index in range(100)
            ),
            "award_component": tuple(
                {"id": index, "award_id": index, "amount": Decimal("10")}
                for index in range(100)
            ),
            "extracted_field": tuple(
                {
                    "id": index,
                    "document_id": index % 200,
                    "field_key": f"field-{index % 20}",
                    "admitted_value": f"value-{index % 20}",
                }
                for index in range(200)
            ),
        },
    )
    timings = []
    for _ in range(_sample_count()):
        started = time.perf_counter()
        violations = [
            violation
            for rule in DEFAULT_RULES
            if rule.rule_id != "parcel_overlap"
            for violation in rule.evaluate(context)
        ]
        assert violations == []
        timings.append(time.perf_counter() - started)

    assert _p95(timings) <= VALIDATION_BUDGET_SECONDS


def _case_count() -> int:
    return 10_000 if os.environ.get("BHUMISETU_NIGHTLY_PERF") == "1" else 1_000


def _sample_count() -> int:
    return 25 if os.environ.get("BHUMISETU_NIGHTLY_PERF") == "1" else 5


def _p95(values: list[float]) -> float:
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=20, method="inclusive")[18]
