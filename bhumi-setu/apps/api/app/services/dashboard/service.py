"""Materialized dashboard snapshots with per-metric timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Callable, Iterable, Mapping

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.session import unit_of_work
from app.models.acquisition_case import AcquisitionCase
from app.models.dashboard import DashboardBandHistory, DashboardSnapshot
from app.models.jurisdiction import AdministrativeArea
from app.models.validation_issue import ValidationIssue
from app.security.access import Principal
from app.services.dashboard.metrics import metric_predicate
from app.workers.celery_app import celery_app

__all__ = [
    "DashboardMetric",
    "DashboardResponse",
    "dashboard_response",
    "refresh_area_snapshot",
    "refresh_dashboard_snapshot",
]

MetricComputer = Callable[[Session, str, datetime], object]


@dataclass(frozen=True)
class DashboardMetric:
    value: object | None = None
    computed_at: datetime | None = None
    unavailable_at: datetime | None = None
    reason: str | None = None

    def to_json(self) -> dict[str, object]:
        if self.reason is not None:
            return {
                "unavailable_at": self.unavailable_at.isoformat()
                if self.unavailable_at is not None
                else None,
                "reason": self.reason,
            }
        return {
            "value": self.value,
            "computed_at": self.computed_at.isoformat()
            if self.computed_at is not None
            else None,
        }


@dataclass(frozen=True)
class DashboardResponse:
    metrics: Mapping[str, DashboardMetric]

    def to_json(self) -> dict[str, object]:
        return {"metrics": {key: metric.to_json() for key, metric in self.metrics.items()}}


def refresh_area_snapshot(
    session: Session,
    *,
    area_code: str,
    now: datetime | None = None,
    computers: Mapping[str, MetricComputer] | None = None,
) -> DashboardSnapshot:
    computed_at = now or datetime.now(UTC)
    metric_computers = computers or DEFAULT_METRICS
    metrics: dict[str, dict[str, object]] = {}
    for name, computer in metric_computers.items():
        try:
            value = computer(session, area_code, computed_at)
            metrics[name] = DashboardMetric(value=value, computed_at=computed_at).to_json()
        except Exception as exc:
            metrics[name] = DashboardMetric(
                unavailable_at=computed_at,
                reason=type(exc).__name__,
            ).to_json()
    _upsert_snapshot(session, area_code, metrics, computed_at)
    _append_band_history(session, area_code, metrics, computed_at)
    session.flush()
    snapshot = session.get(DashboardSnapshot, area_code)
    if snapshot is not None:
        return snapshot
    return DashboardSnapshot(area_code=area_code, metrics=metrics, computed_at=computed_at)


def dashboard_response(
    session: Session,
    *,
    principal: Principal,
) -> DashboardResponse:
    snapshots = tuple(_snapshots_for_principal(session, principal))
    merged = _merge_snapshot_metrics(snapshot.metrics for snapshot in snapshots)
    return DashboardResponse(metrics=merged)


def drill_through_cases(
    cases: Iterable[AcquisitionCase],
    *,
    metric_key: str,
    bucket: str | None = None,
) -> tuple[AcquisitionCase, ...]:
    predicate = metric_predicate(metric_key, bucket)
    return tuple(case for case in cases if predicate(case))


def _cases_by_stage(session: Session, area_code: str, now: datetime) -> dict[str, int]:
    rows = session.execute(
        select(AcquisitionCase.stage_key, func.count(AcquisitionCase.id))
        .where(AcquisitionCase.area_code == area_code, AcquisitionCase.is_terminal.is_(False))
        .group_by(AcquisitionCase.stage_key)
    )
    return {stage: int(count) for stage, count in rows}


def _cases_by_band(session: Session, area_code: str, now: datetime) -> dict[str, int]:
    rows = session.execute(
        select(AcquisitionCase.risk_band, func.count(AcquisitionCase.id))
        .where(AcquisitionCase.area_code == area_code, AcquisitionCase.is_terminal.is_(False))
        .group_by(AcquisitionCase.risk_band)
    )
    return {str(band) if band is not None else "NOT_SCORED": int(count) for band, count in rows}


def _breached_deadline_count(session: Session, area_code: str, now: datetime) -> int:
    return int(
        session.scalar(
            select(func.count(AcquisitionCase.id)).where(
                AcquisitionCase.area_code == area_code,
                AcquisitionCase.is_terminal.is_(False),
                AcquisitionCase.deadline_breached.is_(True),
            )
        )
        or 0
    )


def _validation_issues_by_severity(session: Session, area_code: str, now: datetime) -> dict[str, int]:
    rows = session.execute(
        select(ValidationIssue.severity, func.count(ValidationIssue.id))
        .join(AcquisitionCase, AcquisitionCase.id == ValidationIssue.case_id)
        .where(
            AcquisitionCase.area_code == area_code,
            AcquisitionCase.is_terminal.is_(False),
            ValidationIssue.resolution_state == "OPEN",
        )
        .group_by(ValidationIssue.severity)
    )
    return {severity: int(count) for severity, count in rows}


def _undisposed_objection_count(session: Session, area_code: str, now: datetime) -> int:
    return int(
        session.scalar(
            select(func.coalesce(func.sum(AcquisitionCase.undisposed_objection_count), 0))
            .where(AcquisitionCase.area_code == area_code, AcquisitionCase.is_terminal.is_(False))
        )
        or 0
    )


def _aggregate_awarded(session: Session, area_code: str, now: datetime) -> str:
    return str(
        session.scalar(
            select(func.coalesce(func.sum(AcquisitionCase.aggregate_awarded), 0))
            .where(AcquisitionCase.area_code == area_code, AcquisitionCase.is_terminal.is_(False))
        )
        or Decimal("0")
    )


def _aggregate_disbursed(session: Session, area_code: str, now: datetime) -> str:
    return str(
        session.scalar(
            select(func.coalesce(func.sum(AcquisitionCase.aggregate_disbursed), 0))
            .where(AcquisitionCase.area_code == area_code, AcquisitionCase.is_terminal.is_(False))
        )
        or Decimal("0")
    )


DEFAULT_METRICS: dict[str, MetricComputer] = {
    "cases_by_stage": _cases_by_stage,
    "cases_by_band": _cases_by_band,
    "breached_deadline_count": _breached_deadline_count,
    "validation_issues_by_severity": _validation_issues_by_severity,
    "undisposed_objection_count": _undisposed_objection_count,
    "aggregate_awarded": _aggregate_awarded,
    "aggregate_disbursed": _aggregate_disbursed,
}


def _upsert_snapshot(
    session: Session,
    area_code: str,
    metrics: Mapping[str, object],
    computed_at: datetime,
) -> None:
    stmt = (
        pg_insert(DashboardSnapshot)
        .values(area_code=area_code, metrics=dict(metrics), computed_at=computed_at)
        .on_conflict_do_update(
            index_elements=["area_code"],
            set_={"metrics": dict(metrics), "computed_at": computed_at},
        )
    )
    session.execute(stmt)


def _append_band_history(
    session: Session,
    area_code: str,
    metrics: Mapping[str, object],
    computed_at: datetime,
) -> None:
    band_metric = metrics.get("cases_by_band")
    if not isinstance(band_metric, Mapping) or "value" not in band_metric:
        return
    month = date(computed_at.year, computed_at.month, 1)
    for band, count in dict(band_metric["value"]).items():
        session.add(
            DashboardBandHistory(
                area_code=area_code,
                month=month,
                band=str(band),
                case_count=int(count),
                computed_at=computed_at,
            )
        )


def _snapshots_for_principal(
    session: Session,
    principal: Principal,
) -> tuple[DashboardSnapshot, ...]:
    if principal.kind != "OFFICER" or not principal.scope_paths:
        return ()
    rows = session.execute(
        select(DashboardSnapshot)
        .join(AdministrativeArea, AdministrativeArea.code == DashboardSnapshot.area_code)
        .where(
            or_(
                *(
                    AdministrativeArea.path.op("<@")(scope_path)
                    for scope_path in principal.scope_paths
                )
            )
        )
        .order_by(DashboardSnapshot.area_code)
    )
    return tuple(rows.scalars())


def _merge_snapshot_metrics(
    metric_sets: Iterable[Mapping[str, object]],
) -> dict[str, DashboardMetric]:
    merged: dict[str, DashboardMetric] = {}
    for metrics in metric_sets:
        for key, raw in metrics.items():
            if not isinstance(raw, Mapping):
                continue
            if "reason" in raw:
                merged[key] = DashboardMetric(
                    unavailable_at=_parse_time(raw.get("unavailable_at")),
                    reason=str(raw["reason"]),
                )
                continue
            current = merged.get(key)
            value = _merge_values(current.value if current else None, raw.get("value"))
            computed_at = _oldest_time(current.computed_at if current else None, raw.get("computed_at"))
            merged[key] = DashboardMetric(value=value, computed_at=computed_at)
    return merged


def _merge_values(left: object | None, right: object | None) -> object | None:
    if isinstance(right, Mapping):
        base = dict(left) if isinstance(left, Mapping) else {}
        for key, value in right.items():
            base[key] = int(base.get(key, 0)) + int(value)
        return base
    if right is None:
        return left
    if isinstance(left, int | type(None)) and isinstance(right, int):
        return int(left or 0) + right
    return _decimal_sum(left, right)


def _decimal_sum(left: object | None, right: object) -> str:
    return str(Decimal(str(left or 0)) + Decimal(str(right)))


def _oldest_time(left: datetime | None, right: object | None) -> datetime | None:
    parsed = _parse_time(right)
    if left is None:
        return parsed
    if parsed is None:
        return left
    return min(left, parsed)


def _parse_time(value: object | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


@celery_app.task(name="app.services.dashboard.refresh_dashboard_snapshot")
def refresh_dashboard_snapshot() -> dict[str, int]:
    with unit_of_work() as session:
        area_codes = tuple(
            session.execute(
                select(AcquisitionCase.area_code)
                .where(AcquisitionCase.is_terminal.is_(False))
                .distinct()
                .order_by(AcquisitionCase.area_code)
            ).scalars()
        )
        for area_code in area_codes:
            refresh_area_snapshot(session, area_code=area_code)
        return {"refreshed_count": len(area_codes)}
