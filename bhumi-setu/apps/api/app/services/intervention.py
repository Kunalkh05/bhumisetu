"""Live intervention queue and recommended-action dispositions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import unit_of_work
from app.models.extraction import ExtractedField, Extraction
from app.models.acquisition_case import AcquisitionCase
from app.models.award import Award
from app.models.case_parcel import CaseParcel
from app.models.document import Document
from app.models.event import Event, Provenance
from app.models.objection import Objection
from app.models.ownership_record import OwnershipRecord
from app.models.payout import Payout
from app.models.validation_issue import ValidationIssue
from app.security.access import Principal, scoped
from app.services.policy import PolicyResolver
from app.workers.celery_app import celery_app

__all__ = [
    "CounterSnapshot",
    "InterventionQueuePage",
    "QueueItem",
    "RecommendedAction",
    "attach_recommended_actions",
    "counter_discrepancies",
    "intervention_queue_statement",
    "load_intervention_queue",
    "reconcile_case_counters",
    "reconcile_denormalized_counters",
    "record_action_disposition",
    "remaining_days",
]

ACTION_RULES_KEY = "intervention.action_rules"
ALLOWED_DISPOSITIONS = frozenset({"ACCEPTED", "REJECTED", "DEFERRED"})


@dataclass(frozen=True)
class RecommendedAction:
    action_id: str
    label_key: str
    reason_key: str
    severity: str


@dataclass(frozen=True)
class QueueItem:
    case_id: int
    case_reference: str
    stage_key: str
    risk_band: str | None
    remaining_days: int | None
    priority_score: Decimal | None
    priority_computed_at: datetime | None
    recommended_actions: tuple[RecommendedAction, ...]


@dataclass(frozen=True)
class InterventionQueuePage:
    items: tuple[QueueItem, ...]
    oldest_priority_computed_at: datetime | None
    limit: int
    offset: int


@dataclass(frozen=True)
class CounterSnapshot:
    open_blocking_count: int
    undisposed_objection_count: int
    pending_review_count: int
    aggregate_awarded: Decimal
    aggregate_disbursed: Decimal


def intervention_queue_statement(
    principal: Principal,
    *,
    limit: int,
    offset: int,
):
    """Live queue ordered by the `case_queue` partial-index key."""
    bounded_limit = max(1, min(limit, 100))
    bounded_offset = max(0, offset)
    return scoped(
        select(AcquisitionCase)
        .where(AcquisitionCase.is_terminal.is_(False))
        .order_by(
            AcquisitionCase.priority_score.desc().nullslast(),
            AcquisitionCase.id.asc(),
        )
        .limit(bounded_limit)
        .offset(bounded_offset),
        principal,
        area_col=AcquisitionCase.area_code,
        case_col=AcquisitionCase.id,
    )


def load_intervention_queue(
    session: Session,
    *,
    principal: Principal,
    resolver: PolicyResolver,
    limit: int = 50,
    offset: int = 0,
    today: date | None = None,
) -> InterventionQueuePage:
    as_of = today or date.today()
    cases = tuple(
        session.execute(
            intervention_queue_statement(principal, limit=limit, offset=offset)
        ).scalars()
    )
    rules = _action_rules(resolver, cases, as_of)
    items = tuple(
        QueueItem(
            case_id=case.id,
            case_reference=case.case_reference,
            stage_key=case.stage_key,
            risk_band=case.risk_band,
            remaining_days=remaining_days(case, as_of),
            priority_score=case.priority_score,
            priority_computed_at=case.priority_computed_at,
            recommended_actions=match_recommended_actions(case, rules, as_of),
        )
        for case in cases
    )
    computed_times = tuple(
        item.priority_computed_at for item in items if item.priority_computed_at is not None
    )
    return InterventionQueuePage(
        items=items,
        oldest_priority_computed_at=min(computed_times) if computed_times else None,
        limit=max(1, min(limit, 100)),
        offset=max(0, offset),
    )


def attach_recommended_actions(
    cases: Iterable[AcquisitionCase],
    *,
    rules: Iterable[Mapping[str, Any]],
    today: date,
) -> dict[int, tuple[RecommendedAction, ...]]:
    return {
        case.id: match_recommended_actions(case, rules, today)
        for case in cases
    }


def match_recommended_actions(
    case: AcquisitionCase,
    rules: Iterable[Mapping[str, Any]],
    today: date,
) -> tuple[RecommendedAction, ...]:
    return tuple(
        RecommendedAction(
            action_id=str(rule["id"]),
            label_key=str(rule["label_key"]),
            reason_key=str(rule["reason_key"]),
            severity=str(rule.get("severity", "INFO")),
        )
        for rule in rules
        if _rule_matches(case, rule, today)
    )


def record_action_disposition(
    session: Session,
    *,
    case: AcquisitionCase,
    principal: Principal,
    action_id: str,
    disposition: str,
    reason: str | None,
    occurrence_time: datetime | None = None,
    expected_version: int | None = None,
) -> Event:
    if principal.kind != "OFFICER":
        raise PermissionError("recommended action disposition requires an officer")
    if disposition not in ALLOWED_DISPOSITIONS:
        raise ValueError(f"unknown disposition {disposition!r}")
    if expected_version is not None and case.entity_version != expected_version:
        raise ValueError("case version changed before action disposition was recorded")
    occurred = occurrence_time or datetime.now(UTC)
    event = Event(
        event_type="RECOMMENDED_ACTION_DISPOSITION_RECORDED",
        entity_type="acquisition_case",
        entity_id=case.id,
        case_id=case.id,
        actor_type=principal.kind,
        actor_id=principal.id,
        occurrence_time=occurred,
        payload={
            "action_id": action_id,
            "disposition": disposition,
            "reason": reason,
        },
        has_pd_refs=False,
        provenance=Provenance.MANUAL,
    )
    session.add(event)
    session.flush()
    return event


def reconcile_denormalized_counters(
    session: Session,
    *,
    case_ids: Iterable[int],
    now: datetime | None = None,
) -> int:
    occurred = now or datetime.now(UTC)
    discrepancy_count = 0
    for case_id in case_ids:
        case = session.get(AcquisitionCase, case_id, populate_existing=True)
        if case is None:
            continue
        actual = actual_counters(session, case_id=case_id)
        discrepancies = counter_discrepancies(case, actual)
        if discrepancies:
            discrepancy_count += 1
            session.add(
                Event(
                    event_type="DENORMALIZED_COUNTER_DISCREPANCY",
                    entity_type="acquisition_case",
                    entity_id=case.id,
                    case_id=case.id,
                    actor_type="SYSTEM",
                    actor_id="intervention.reconcile_denormalized_counters",
                    occurrence_time=occurred,
                    payload={"discrepancies": discrepancies},
                    has_pd_refs=False,
                    provenance=Provenance.SYSTEM,
                )
            )
    session.flush()
    return discrepancy_count


def counter_discrepancies(
    case: AcquisitionCase,
    actual: CounterSnapshot,
) -> dict[str, dict[str, object]]:
    discrepancies: dict[str, dict[str, object]] = {}
    for name in (
        "open_blocking_count",
        "undisposed_objection_count",
        "pending_review_count",
        "aggregate_awarded",
        "aggregate_disbursed",
    ):
        stored = getattr(case, name)
        observed = getattr(actual, name)
        if stored != observed:
            discrepancies[name] = {"stored": stored, "actual": observed}
    return discrepancies


def actual_counters(session: Session, *, case_id: int) -> CounterSnapshot:
    open_blocking = session.scalar(
        select(func.count(ValidationIssue.id)).where(
            ValidationIssue.case_id == case_id,
            ValidationIssue.resolution_state == "OPEN",
            ValidationIssue.severity == "BLOCKING",
        )
    )
    undisposed = session.scalar(
        select(func.count(Objection.id)).where(
            Objection.case_id == case_id,
            Objection.disposal_outcome.is_(None),
        )
    )
    pending_review = session.scalar(
        select(func.count(ExtractedField.id))
        .join(Extraction, Extraction.id == ExtractedField.extraction_id)
        .join(Document, Document.id == Extraction.document_id)
        .where(
            ExtractedField.review_state == "PENDING_REVIEW",
            (
                (Document.case_id == case_id)
                | (
                    Document.parcel_id.in_(
                        select(CaseParcel.parcel_id).where(CaseParcel.case_id == case_id)
                    )
                )
            ),
        )
    )
    awarded = session.scalar(
        select(func.coalesce(func.sum(Award.total_amount), 0))
        .join(OwnershipRecord, OwnershipRecord.id == Award.ownership_record_id)
        .join(CaseParcel, CaseParcel.parcel_id == OwnershipRecord.parcel_id)
        .where(CaseParcel.case_id == case_id)
    )
    disbursed = session.scalar(
        select(func.coalesce(func.sum(Payout.amount), 0))
        .join(Award, Award.id == Payout.award_id)
        .join(OwnershipRecord, OwnershipRecord.id == Award.ownership_record_id)
        .join(CaseParcel, CaseParcel.parcel_id == OwnershipRecord.parcel_id)
        .where(CaseParcel.case_id == case_id)
    )
    return CounterSnapshot(
        open_blocking_count=int(open_blocking or 0),
        undisposed_objection_count=int(undisposed or 0),
        pending_review_count=pending_review,
        aggregate_awarded=Decimal(str(awarded or 0)),
        aggregate_disbursed=Decimal(str(disbursed or 0)),
    )


def remaining_days(case: AcquisitionCase, today: date) -> int | None:
    if case.stage_deadline is None:
        return None
    return (case.stage_deadline - today).days


def _action_rules(
    resolver: PolicyResolver,
    cases: tuple[AcquisitionCase, ...],
    as_of: date,
) -> tuple[Mapping[str, Any], ...]:
    if not cases:
        return ()
    value = resolver.get(
        ACTION_RULES_KEY,
        state=cases[0].state_key,
        act=cases[0].act_key,
        as_of=as_of,
    )
    if isinstance(value, Mapping) and "rules" in value:
        return tuple(value["rules"])
    return tuple(value)


def _rule_matches(case: AcquisitionCase, rule: Mapping[str, Any], today: date) -> bool:
    when = rule.get("when", {})
    if not isinstance(when, Mapping):
        return False
    return all(_condition_matches(case, key, value, today) for key, value in when.items())


def _condition_matches(
    case: AcquisitionCase,
    key: str,
    value: object,
    today: date,
) -> bool:
    if key == "open_blocking_count_gt":
        return case.open_blocking_count > int(value)
    if key == "undisposed_objection_count_gt":
        return case.undisposed_objection_count > int(value)
    if key == "pending_review_count_gt":
        return case.pending_review_count > int(value)
    if key == "deadline_within_days":
        days = remaining_days(case, today)
        return days is not None and days <= int(value)
    if key == "deadline_breached":
        return bool(case.deadline_breached) is bool(value)
    if key == "risk_band_in":
        return case.risk_band in set(value)  # type: ignore[arg-type]
    return False


@celery_app.task(name="app.services.intervention.reconcile_case_counters")
def reconcile_case_counters() -> dict[str, int]:
    with unit_of_work() as session:
        case_ids = tuple(
            session.execute(
                select(AcquisitionCase.id)
                .where(AcquisitionCase.is_terminal.is_(False))
                .order_by(AcquisitionCase.id)
            ).scalars()
        )
        discrepancies = reconcile_denormalized_counters(session, case_ids=case_ids)
        return {"checked_count": len(case_ids), "discrepancy_count": discrepancies}
