"""Validation engine foundation tests (task 13)."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone

import pytest

from app.models.acquisition_case import AcquisitionCase
from app.models.validation_issue import ValidationIssue
from app.services import validation
from app.services.validation import (
    RESOLUTION_OPEN,
    RESOLUTION_WAIVED,
    ChunkRuleContext,
    Rule,
    ValidationEngine,
    Violation,
    WaiverReasonRequired,
    fingerprint,
)


@dataclass(frozen=True)
class Actor:
    kind: str = "OFFICER"
    id: str = "officer-1"

    def has_permission(self, permission: str) -> bool:
        return True


class FakeResolver:
    def get(self, key, *, state, act, as_of):  # type: ignore[no-untyped-def]
        assert key == "validation.severity.share_sum"
        return "BLOCKING"


class FakeSession:
    def __init__(self, *, case: AcquisitionCase | None = None, issue: ValidationIssue | None = None) -> None:
        self.case = case
        self.issue = issue
        self.added: list[object] = []
        self.events: list[str] = []
        self.flushed = False

    def get(self, entity_type, entity_id, **kwargs):  # type: ignore[no-untyped-def]
        if entity_type is AcquisitionCase:
            return self.case
        if entity_type is ValidationIssue:
            return self.issue
        return None

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flushed = True

    @contextmanager
    def begin_nested(self):  # type: ignore[no-untyped-def]
        yield


def _case() -> AcquisitionCase:
    return AcquisitionCase(
        id=1,
        case_reference="MH-1",
        project_id=1,
        state_key="MH",
        act_key="RFCTLARR_2013",
        area_code="MH.PN",
        stage_key="AWARD",
        stage_set_effective_from=date(2024, 1, 1),
        stage_entered_on=date(2024, 1, 2),
        stage_deadline=None,
        deadline_breached=False,
        is_terminal=False,
        open_blocking_count=0,
        entity_version=1,
    )


def test_fingerprint_is_deterministic_over_sorted_entity_refs() -> None:
    left = fingerprint("share_sum", [("ownership_record", 2), ("land_parcel", 1)])
    right = fingerprint("share_sum", [("land_parcel", 1), ("ownership_record", 2)])

    assert left == right
    assert left != fingerprint("different", [("land_parcel", 1), ("ownership_record", 2)])


def test_chunk_context_reads_preloaded_rows_and_fails_closed_for_unknown_entity() -> None:
    ctx = ChunkRuleContext(
        case_id=10,
        rows={"ownership_record": ({"id": 1, "share": "1.0"},)},
    )

    assert ctx.values("ownership_record") == ({"id": 1, "share": "1.0"},)
    assert ctx.values("award") == ()


def test_evaluate_case_resolves_severity_from_policy_and_updates_blocking_count(monkeypatch) -> None:
    session = FakeSession(case=_case())
    violation = Violation(
        rule_id="share_sum",
        offending_entities=(("land_parcel", 7),),
        observed_values={"sum": "1.2"},
    )
    rule = Rule(
        rule_id="share_sum",
        kind="tolerance",
        severity_key="validation.severity.share_sum",
        evaluate=lambda ctx: [violation],
    )
    created: list[tuple[str, str]] = []

    def _create_issue(session_arg, *, case_id, violation, severity, actor, occurred):  # type: ignore[no-untyped-def]
        created.append((violation.rule_id, severity))
        return ValidationIssue(
            id=5,
            case_id=case_id,
            rule_id=violation.rule_id,
            fingerprint=violation.fingerprint,
            severity=severity,
            offending_entities={},
            observed_values={},
            detected_at=occurred,
            resolution_state=RESOLUTION_OPEN,
            entity_version=1,
        )

    monkeypatch.setattr(validation, "_create_issue", _create_issue)
    monkeypatch.setattr(validation, "_resolve_absent_open_issues", lambda session, **kwargs: [])
    monkeypatch.setattr(validation, "_open_blocking_count", lambda session, case_id: 1)

    issues = ValidationEngine(resolver=FakeResolver(), rules=(rule,)).evaluate_case(
        session,  # type: ignore[arg-type]
        context=ChunkRuleContext(case_id=1, rows={}),
        actor=Actor(),
        occurrence_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
    )

    assert created == [("share_sum", "BLOCKING")]
    assert len(issues) == 1
    assert session.case.open_blocking_count == 1


def test_waive_requires_non_empty_reason() -> None:
    with pytest.raises(WaiverReasonRequired):
        ValidationEngine(resolver=FakeResolver(), rules=()).waive(
            FakeSession(issue=ValidationIssue()),  # type: ignore[arg-type]
            issue_id=5,
            actor=Actor(),
            reason=" ",
            occurrence_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
        )


def test_waive_records_history_and_uses_permission_for_blocking(monkeypatch) -> None:
    issue = ValidationIssue(
        id=5,
        case_id=1,
        rule_id="share_sum",
        fingerprint="fp",
        severity="BLOCKING",
        offending_entities={},
        observed_values={},
        detected_at=datetime(2024, 5, 1, tzinfo=timezone.utc),
        resolution_state=RESOLUTION_OPEN,
        entity_version=3,
    )
    session = FakeSession(issue=issue)
    permissions: list[str] = []

    def _require_permission(session_arg, principal, permission, **kwargs):  # type: ignore[no-untyped-def]
        permissions.append(permission)

    def _update(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["changes"]["resolution_state"] == RESOLUTION_WAIVED
        issue.resolution_state = RESOLUTION_WAIVED
        return issue

    monkeypatch.setattr(validation, "require_permission", _require_permission)
    monkeypatch.setattr("app.services.validation.VersionedRepository.update", _update)

    updated = ValidationEngine(resolver=FakeResolver(), rules=()).waive(
        session,  # type: ignore[arg-type]
        issue_id=5,
        actor=Actor(),
        reason="Officer reviewed supporting record",
        occurrence_time=datetime(2024, 5, 1, tzinfo=timezone.utc),
    )

    assert updated.resolution_state == RESOLUTION_WAIVED
    assert permissions == ["validation.waive.BLOCKING"]
    assert len(session.added) == 1
