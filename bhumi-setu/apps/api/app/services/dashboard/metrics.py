"""Dashboard metric predicates shared by aggregates and drill-through."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

from app.models.acquisition_case import AcquisitionCase

__all__ = [
    "MetricPredicate",
    "breached_deadline_predicate",
    "metric_predicate",
    "risk_band_predicate",
    "stage_predicate",
]

MetricPredicate = Callable[[AcquisitionCase], bool]


@dataclass(frozen=True)
class PredicateMetric:
    key: str
    predicate: MetricPredicate


def stage_predicate(stage_key: str) -> MetricPredicate:
    return lambda case: case.stage_key == stage_key


def risk_band_predicate(risk_band: str | None) -> MetricPredicate:
    return lambda case: case.risk_band == risk_band


def breached_deadline_predicate() -> MetricPredicate:
    return lambda case: bool(case.deadline_breached)


def metric_predicate(metric_key: str, bucket: str | None = None) -> MetricPredicate:
    if metric_key == "cases_by_stage" and bucket is not None:
        return stage_predicate(bucket)
    if metric_key == "cases_by_band":
        return risk_band_predicate(bucket)
    if metric_key == "breached_deadline_count":
        return breached_deadline_predicate()
    if metric_key == "undisposed_objection_count":
        return lambda case: case.undisposed_objection_count > 0
    if metric_key == "aggregate_awarded":
        return lambda case: Decimal(case.aggregate_awarded or 0) > 0
    if metric_key == "aggregate_disbursed":
        return lambda case: Decimal(case.aggregate_disbursed or 0) > 0
    raise KeyError(f"unknown dashboard metric {metric_key!r}")
