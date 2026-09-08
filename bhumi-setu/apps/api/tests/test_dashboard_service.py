"""Dashboard snapshot aggregation and drill-through contracts (task 24.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.dashboard import DashboardSnapshot
from app.security.access import Principal
from app.services.dashboard import (
    DashboardMetric,
    dashboard_response,
    drill_through_cases,
    refresh_area_snapshot,
)
from app.services.dashboard import service as dashboard_service


NOW = datetime(2026, 9, 3, 9, 30, tzinfo=UTC)


@dataclass
class _Case:
    id: int
    stage_key: str
    risk_band: str | None
    deadline_breached: bool = False
    undisposed_objection_count: int = 0
    aggregate_awarded: Decimal = Decimal("0")
    aggregate_disbursed: Decimal = Decimal("0")


class _SnapshotSession:
    def __init__(self) -> None:
        self.flushed = False

    def flush(self) -> None:
        self.flushed = True

    def get(self, model, key):
        return None


def test_metric_json_carries_per_metric_time_or_failure_time() -> None:
    assert DashboardMetric(value=3, computed_at=NOW).to_json() == {
        "value": 3,
        "computed_at": NOW.isoformat(),
    }
    assert DashboardMetric(unavailable_at=NOW, reason="TimeoutError").to_json() == {
        "unavailable_at": NOW.isoformat(),
        "reason": "TimeoutError",
    }


def test_refresh_area_snapshot_marks_only_failed_metric_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, object] = {}

    def working_metric(session, area_code: str, now: datetime) -> int:
        return 2

    def failing_metric(session, area_code: str, now: datetime) -> int:
        raise RuntimeError("boom")

    def record_snapshot(session, area_code, metrics, computed_at) -> None:
        recorded["area_code"] = area_code
        recorded["metrics"] = metrics
        recorded["computed_at"] = computed_at

    monkeypatch.setattr(dashboard_service, "_upsert_snapshot", record_snapshot)
    monkeypatch.setattr(dashboard_service, "_append_band_history", lambda *args: None)

    snapshot = refresh_area_snapshot(
        _SnapshotSession(),
        area_code="MH.PUNE",
        now=NOW,
        computers={"open_cases": working_metric, "slow_metric": failing_metric},
    )

    metrics = recorded["metrics"]
    assert snapshot.metrics == metrics
    assert metrics["open_cases"] == {"value": 2, "computed_at": NOW.isoformat()}
    assert metrics["slow_metric"] == {
        "unavailable_at": NOW.isoformat(),
        "reason": "RuntimeError",
    }


def test_dashboard_response_rolls_up_additive_leaf_snapshots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    older = datetime(2026, 9, 3, 9, tzinfo=UTC).isoformat()
    newer = datetime(2026, 9, 3, 9, 5, tzinfo=UTC).isoformat()
    snapshots = (
        DashboardSnapshot(
            area_code="MH.PUNE",
            metrics={
                "cases_by_stage": {"value": {"NOTICE": 2}, "computed_at": newer},
                "breached_deadline_count": {"value": 1, "computed_at": newer},
                "aggregate_awarded": {"value": "10.50", "computed_at": newer},
            },
            computed_at=NOW,
        ),
        DashboardSnapshot(
            area_code="MH.SATARA",
            metrics={
                "cases_by_stage": {"value": {"NOTICE": 3, "AWARD": 1}, "computed_at": older},
                "breached_deadline_count": {"value": 2, "computed_at": older},
                "aggregate_awarded": {"value": "4.50", "computed_at": older},
            },
            computed_at=NOW,
        ),
    )
    monkeypatch.setattr(
        dashboard_service,
        "_snapshots_for_principal",
        lambda session, principal: snapshots,
    )
    monkeypatch.setattr(
        dashboard_service,
        "_stage_keys_for_principal",
        lambda session, principal: ("NOTICE", "AWARD"),
    )
    monkeypatch.setattr(
        dashboard_service,
        "_band_history_for_principal",
        lambda session, principal: (
            {"month": "2026-09-01", "band": "HIGH", "case_count": 5},
        ),
    )

    response = dashboard_response(
        object(),
        principal=Principal(
            kind="OFFICER",
            id="officer-1",
            permissions=frozenset(),
            scope_paths=("MH",),
        ),
    )

    assert response.metrics["cases_by_stage"].value == {"NOTICE": 5, "AWARD": 1}
    assert response.metrics["breached_deadline_count"].value == 3
    assert response.metrics["aggregate_awarded"].value == "15.00"
    assert response.metrics["aggregate_awarded"].computed_at == datetime.fromisoformat(older)
    assert response.stage_keys == ("NOTICE", "AWARD")
    assert response.band_history == (
        {"month": "2026-09-01", "band": "HIGH", "case_count": 5},
    )


def test_unavailable_metric_does_not_hide_other_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dashboard_service,
        "_snapshots_for_principal",
        lambda session, principal: (
            DashboardSnapshot(
                area_code="MH.PUNE",
                metrics={
                    "cases_by_band": {
                        "unavailable_at": NOW.isoformat(),
                        "reason": "StatementTimeout",
                    },
                    "breached_deadline_count": {
                        "value": 4,
                        "computed_at": NOW.isoformat(),
                    },
                },
                computed_at=NOW,
            ),
        ),
    )
    monkeypatch.setattr(
        dashboard_service,
        "_stage_keys_for_principal",
        lambda session, principal: (),
    )
    monkeypatch.setattr(
        dashboard_service,
        "_band_history_for_principal",
        lambda session, principal: (),
    )

    response = dashboard_response(
        object(),
        principal=Principal(
            kind="OFFICER",
            id="officer-1",
            permissions=frozenset(),
            scope_paths=("MH",),
        ),
    )

    assert response.metrics["cases_by_band"].reason == "StatementTimeout"
    assert response.metrics["breached_deadline_count"].value == 4


def test_drill_through_uses_the_same_predicate_as_the_metric() -> None:
    cases = (
        _Case(id=1, stage_key="NOTICE", risk_band="HIGH", deadline_breached=True),
        _Case(id=2, stage_key="NOTICE", risk_band="LOW"),
        _Case(id=3, stage_key="AWARD", risk_band="HIGH"),
    )

    drill = drill_through_cases(cases, metric_key="cases_by_stage", bucket="NOTICE")

    assert [case.id for case in drill] == [1, 2]
    assert len(drill) == sum(1 for case in cases if case.stage_key == "NOTICE")


def test_each_dashboard_count_uses_the_same_predicate_as_drill_through() -> None:
    cases = (
        _Case(id=1, stage_key="NOTICE", risk_band="HIGH", deadline_breached=True),
        _Case(id=2, stage_key="NOTICE", risk_band="LOW"),
        _Case(id=3, stage_key="AWARD", risk_band="HIGH", deadline_breached=True),
    )
    metrics = {
        ("cases_by_stage", "NOTICE"): 2,
        ("cases_by_band", "HIGH"): 2,
        ("breached_deadline_count", None): 2,
    }

    for (metric_key, bucket), expected in metrics.items():
        assert (
            len(drill_through_cases(cases, metric_key=metric_key, bucket=bucket))
            == expected
        )
