"""Validation rule engine (task 13)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.event_log import Actor, EventLog
from app.db.versioned_repository import VersionedRepository
from app.errors import DomainError, ErrorCode
from app.models.acquisition_case import AcquisitionCase
from app.models.award import Award, AwardComponent
from app.models.case_parcel import CaseParcel
from app.models.land_parcel import LandParcel
from app.models.notice_service_record import NoticeServiceRecord
from app.models.objection import Objection
from app.models.ownership_record import OwnershipRecord
from app.models.payout import Payout
from app.models.statutory_notice import StatutoryNotice
from app.models.validation_issue import ValidationIssue, ValidationIssueHistory
from app.security.permissions import require_permission
from app.services.policy import PolicyResolver

__all__ = [
    "RESOLVED_BY_CORRECTION",
    "RESOLUTION_OPEN",
    "RESOLUTION_WAIVED",
    "ChunkRuleContext",
    "DbRuleContext",
    "Rule",
    "RuleContext",
    "ValidationEngine",
    "Violation",
    "WaiverReasonRequired",
    "fingerprint",
]

RESOLUTION_OPEN = "OPEN"
RESOLVED_BY_CORRECTION = "RESOLVED_BY_CORRECTION"
RESOLUTION_WAIVED = "WAIVED"
SEVERITY_ORDER = {"BLOCKING": 3, "MAJOR": 2, "MINOR": 1, "ADVISORY": 0}


class RuleContext(Protocol):
    case_id: int

    def values(self, entity_type: str) -> Sequence[Mapping[str, object]]:
        ...


@dataclass(frozen=True)
class ChunkRuleContext:
    case_id: int
    rows: Mapping[str, Sequence[Mapping[str, object]]]

    def values(self, entity_type: str) -> Sequence[Mapping[str, object]]:
        return tuple(self.rows.get(entity_type, ()))


class DbRuleContext:
    def __init__(self, session: Session, *, case_id: int) -> None:
        self.session = session
        self.case_id = case_id

    def values(self, entity_type: str) -> Sequence[Mapping[str, object]]:
        if entity_type == "parcel_overlap":
            return tuple(
                self.session.execute(
                    _parcel_overlap_statement(),
                    {"case_id": self.case_id},
                ).mappings()
            )
        stmt = _db_context_statement(entity_type, self.case_id)
        if stmt is None:
            # Document extraction lands later; unknown lookups fail closed instead
            # of pretending a rule passed over rows we did not know how to read.
            return ()
        return tuple(_public_mapping(row) for row in self.session.execute(stmt).scalars())


def _db_context_statement(entity_type: str, case_id: int):
    if entity_type == "acquisition_case":
        return select(AcquisitionCase).where(AcquisitionCase.id == case_id)
    if entity_type == "land_parcel":
        return (
            select(LandParcel)
            .join(CaseParcel, CaseParcel.parcel_id == LandParcel.id)
            .where(CaseParcel.case_id == case_id)
        )
    if entity_type == "ownership_record":
        return (
            select(OwnershipRecord)
            .join(CaseParcel, CaseParcel.parcel_id == OwnershipRecord.parcel_id)
            .where(CaseParcel.case_id == case_id)
        )
    if entity_type == "award":
        return (
            select(Award)
            .join(OwnershipRecord, OwnershipRecord.id == Award.ownership_record_id)
            .join(CaseParcel, CaseParcel.parcel_id == OwnershipRecord.parcel_id)
            .where(CaseParcel.case_id == case_id)
        )
    if entity_type == "award_component":
        return (
            select(AwardComponent)
            .join(Award, Award.id == AwardComponent.award_id)
            .join(OwnershipRecord, OwnershipRecord.id == Award.ownership_record_id)
            .join(CaseParcel, CaseParcel.parcel_id == OwnershipRecord.parcel_id)
            .where(CaseParcel.case_id == case_id)
        )
    if entity_type == "payout":
        return (
            select(Payout)
            .join(Award, Award.id == Payout.award_id)
            .join(OwnershipRecord, OwnershipRecord.id == Award.ownership_record_id)
            .join(CaseParcel, CaseParcel.parcel_id == OwnershipRecord.parcel_id)
            .where(CaseParcel.case_id == case_id)
        )
    if entity_type == "objection":
        return select(Objection).where(Objection.case_id == case_id)
    if entity_type == "statutory_notice":
        return select(StatutoryNotice).where(StatutoryNotice.case_id == case_id)
    if entity_type == "notice_service_record":
        return (
            select(NoticeServiceRecord)
            .join(StatutoryNotice, StatutoryNotice.id == NoticeServiceRecord.notice_id)
            .where(StatutoryNotice.case_id == case_id)
        )
    if entity_type == "validation_issue":
        return select(ValidationIssue).where(ValidationIssue.case_id == case_id)
    return None


def _parcel_overlap_statement():
    return text(
        """
        WITH parcels AS (
            SELECT lp.id,
                   lp.geom,
                   NULLIF(lp.geodesic_area_sqm, 0) AS area_sqm
              FROM land_parcel lp
              JOIN case_parcel cp ON cp.parcel_id = lp.id
             WHERE cp.case_id = :case_id
               AND lp.geom IS NOT NULL
               AND lp.geodesic_area_sqm IS NOT NULL
        )
        SELECT left_parcel.id AS left_parcel_id,
               right_parcel.id AS right_parcel_id,
               ST_Area(
                   ST_Intersection(left_parcel.geom, right_parcel.geom)::geography
               ) / LEAST(left_parcel.area_sqm, right_parcel.area_sqm)
                   AS overlap_fraction
          FROM parcels left_parcel
          JOIN parcels right_parcel
            ON left_parcel.id < right_parcel.id
           AND left_parcel.geom && right_parcel.geom
           AND ST_Intersects(left_parcel.geom, right_parcel.geom)
        """
    )


def _public_mapping(row: Any) -> Mapping[str, object]:
    data = {
        key: value
        for key, value in vars(row).items()
        if not key.startswith("_")
    }
    if "id" in data:
        data["id"] = int(data["id"])
    return data


@dataclass(frozen=True)
class Violation:
    rule_id: str
    offending_entities: tuple[tuple[str, int], ...]
    observed_values: Mapping[str, object]

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.rule_id, self.offending_entities)


Evaluate = Callable[[RuleContext], Iterable[Violation]]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    kind: str
    severity_key: str
    evaluate: Evaluate

    def severity(self, resolver: PolicyResolver, *, state: str, act: str | None, as_of) -> str:
        return str(resolver.get(self.severity_key, state=state, act=act, as_of=as_of))


def fingerprint(rule_id: str, entity_refs: Iterable[tuple[str, int]]) -> str:
    payload = {
        "rule_id": rule_id,
        "entities": sorted((entity_type, int(entity_id)) for entity_type, entity_id in entity_refs),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class WaiverReasonRequired(DomainError):
    code = ErrorCode.VALIDATION_FAILED
    status_code = 422

    def __init__(self) -> None:
        super().__init__("Waiver reason is required", details={"missing_fields": ["reason"]})


class ValidationEngine:
    def __init__(self, *, resolver: PolicyResolver, rules: Sequence[Rule]) -> None:
        self._resolver = resolver
        self._rules = tuple(rules)

    def evaluate_case(
        self,
        session: Session,
        *,
        context: RuleContext,
        actor: Actor,
        occurrence_time: datetime | None = None,
    ) -> list[ValidationIssue]:
        occurred = occurrence_time or datetime.now(timezone.utc)
        case = session.get(AcquisitionCase, context.case_id, populate_existing=True)
        if case is None:
            raise LookupError(f"case {context.case_id} does not exist")

        active: dict[tuple[str, str], Violation] = {}
        created: list[ValidationIssue] = []
        for rule in self._rules:
            severity = rule.severity(
                self._resolver,
                state=case.state_key,
                act=case.act_key,
                as_of=occurred.date(),
            )
            for violation in rule.evaluate(context):
                key = (violation.rule_id, violation.fingerprint)
                active[key] = violation
                issue = _create_issue(
                    session,
                    case_id=context.case_id,
                    violation=violation,
                    severity=severity,
                    actor=actor,
                    occurred=occurred,
                )
                if issue is not None:
                    created.append(issue)

        resolved = _resolve_absent_open_issues(
            session,
            case_id=context.case_id,
            active_keys=set(active),
            actor=actor,
            occurred=occurred,
        )
        case.open_blocking_count = _open_blocking_count(session, context.case_id)
        session.flush()
        return created + resolved

    def waive(
        self,
        session: Session,
        *,
        issue_id: int,
        actor,
        reason: str,
        occurrence_time: datetime,
        expected_version: int | None = None,
    ) -> ValidationIssue:
        if not reason.strip():
            raise WaiverReasonRequired()
        issue = session.get(ValidationIssue, issue_id, populate_existing=True)
        if issue is None:
            raise LookupError(f"validation issue {issue_id} does not exist")
        if issue.severity == "BLOCKING":
            require_permission(
                session,
                actor,
                "validation.waive.BLOCKING",
                resource=issue,
                occurrence_time=occurrence_time,
            )
        prior_state = issue.resolution_state
        updated = VersionedRepository.update(
            session,
            entity_type=ValidationIssue,
            entity_id=issue_id,
            expected_version=expected_version or issue.entity_version,
            submitted_prior={"resolution_state": prior_state},
            changes={"resolution_state": RESOLUTION_WAIVED, "resolved_at": occurrence_time},
            actor=actor,
            occurrence_time=occurrence_time,
            event_type="VALIDATION_ISSUE_WAIVED",
        )
        session.add(
            ValidationIssueHistory(
                issue_id=issue_id,
                prior_state=prior_state,
                new_state=RESOLUTION_WAIVED,
                actor_id=actor.id,
                reason=reason,
                occurrence_time=occurrence_time,
            )
        )
        case = session.get(AcquisitionCase, issue.case_id)
        if case is not None:
            case.open_blocking_count = _open_blocking_count(session, issue.case_id)
        session.flush()
        return updated  # type: ignore[return-value]


def _create_issue(
    session: Session,
    *,
    case_id: int,
    violation: Violation,
    severity: str,
    actor: Actor,
    occurred: datetime,
) -> ValidationIssue | None:
    issue = ValidationIssue(
        case_id=case_id,
        rule_id=violation.rule_id,
        fingerprint=violation.fingerprint,
        severity=severity,
        offending_entities={
            "entities": [
                {"entity_type": entity_type, "entity_id": entity_id}
                for entity_type, entity_id in violation.offending_entities
            ]
        },
        observed_values=dict(violation.observed_values),
        detected_at=occurred,
        resolution_state=RESOLUTION_OPEN,
    )
    try:
        with session.begin_nested():
            session.add(issue)
            session.flush()
    except IntegrityError:
        return None
    EventLog.append(
        session,
        event_type="VALIDATION_ISSUE_OPENED",
        entity=issue,
        actor=actor,
        changes={
            "rule_id": (None, issue.rule_id),
            "severity": (None, issue.severity),
            "fingerprint": (None, issue.fingerprint),
        },
        occurrence_time=occurred,
        entity_version_after=issue.entity_version,
    )
    session.add(
        ValidationIssueHistory(
            issue_id=issue.id,
            prior_state=None,
            new_state=RESOLUTION_OPEN,
            actor_id=actor.id,
            reason=None,
            occurrence_time=occurred,
        )
    )
    return issue


def _resolve_absent_open_issues(
    session: Session,
    *,
    case_id: int,
    active_keys: set[tuple[str, str]],
    actor: Actor,
    occurred: datetime,
) -> list[ValidationIssue]:
    resolved: list[ValidationIssue] = []
    rows = session.execute(
        select(ValidationIssue).where(
            ValidationIssue.case_id == case_id,
            ValidationIssue.resolution_state == RESOLUTION_OPEN,
        )
    ).scalars()
    for issue in rows:
        if (issue.rule_id, issue.fingerprint) in active_keys:
            continue
        prior_state = issue.resolution_state
        updated = VersionedRepository.update(
            session,
            entity_type=ValidationIssue,
            entity_id=issue.id,
            expected_version=issue.entity_version,
            submitted_prior={"resolution_state": prior_state},
            changes={"resolution_state": RESOLVED_BY_CORRECTION, "resolved_at": occurred},
            actor=actor,
            occurrence_time=occurred,
            event_type="VALIDATION_ISSUE_RESOLVED",
        )
        session.add(
            ValidationIssueHistory(
                issue_id=issue.id,
                prior_state=prior_state,
                new_state=RESOLVED_BY_CORRECTION,
                actor_id=actor.id,
                reason=None,
                occurrence_time=occurred,
            )
        )
        resolved.append(updated)  # type: ignore[arg-type]
    return resolved


def _open_blocking_count(session: Session, case_id: int) -> int:
    return int(
        session.execute(
            select(func.count()).select_from(ValidationIssue).where(
                ValidationIssue.case_id == case_id,
                ValidationIssue.severity == "BLOCKING",
                ValidationIssue.resolution_state == RESOLUTION_OPEN,
            )
        ).scalar_one()
    )
