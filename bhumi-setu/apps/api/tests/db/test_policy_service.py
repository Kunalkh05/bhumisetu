"""The policy write path (R2.5, R28.3, R28.9), Property 65.

Four things must happen together on every write — validate, insert a new version,
append an event, check the permission — and any one being skipped is a defect that
surfaces much later. So most of these tests assert on what *did not* happen when the
write was refused: no row, no event, nothing partially applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.services.policy import PolicyResolver
from app.services.policy_service import (
    CONFIG_WRITE_PERMISSION,
    NotAuthorisedToWritePolicy,
    PolicyService,
    ReportAssertionUnavailable,
)
from app.services.policy_validators import PolicyValueInvalid

STATE = "IN-MH"
ACT = "RFCTLARR-2013"
KEY = "period.pn.to_declaration"
APR = date(2024, 4, 1)


@dataclass
class FakePrincipal:
    id: str
    permissions: set[str] = field(default_factory=lambda: {CONFIG_WRITE_PERMISSION})


@pytest.fixture
def officer_id(db_connection: Connection) -> str:
    return db_connection.execute(
        text(
            """
            INSERT INTO officer (officer_code, display_name, credential_hash)
            VALUES ('policy-writer', 'Policy Writer', 'argon2-placeholder')
            RETURNING id
            """
        )
    ).scalar_one()


@pytest.fixture
def session(db_connection: Connection) -> Session:
    return Session(bind=db_connection, join_transaction_mode="create_savepoint")


@pytest.fixture
def service(session: Session) -> PolicyService:
    return PolicyService(session)


@pytest.fixture
def actor(officer_id: str) -> FakePrincipal:
    return FakePrincipal(id=str(officer_id))


def row_count(connection: Connection, key: str) -> int:
    return connection.execute(
        text("SELECT count(*) FROM policy_config WHERE policy_key = :k"), {"k": key}
    ).scalar_one()


def events_for(connection: Connection, config_id: int):
    return connection.execute(
        text(
            "SELECT event_type, actor_id, payload, has_pd_refs FROM event "
            "WHERE entity_type = 'policy_config' AND entity_id = :id"
        ),
        {"id": config_id},
    ).all()


# ---------------------------------------------------------------------------
# The happy path, and what it records
# ---------------------------------------------------------------------------


def test_a_write_inserts_a_version_and_appends_an_event(
    db_connection: Connection, service: PolicyService, actor
) -> None:
    result = service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=actor)

    assert result.policy_config_id > 0
    events = events_for(db_connection, result.policy_config_id)
    assert len(events) == 1
    assert events[0].event_type == "POLICY_CHANGED"
    assert events[0].actor_id == str(actor.id)
    assert events[0].has_pd_refs is False


def test_the_event_carries_the_prior_and_new_value(
    db_connection: Connection, service: PolicyService, actor
) -> None:
    """R28.3 requires the prior value, the new value, the effective date and the
    officer. Without the prior value the log records that something changed but not
    from what, which is not a change history."""
    service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=actor)
    second = service.set(
        KEY, 180, state=STATE, act=ACT, effective_from=date(2025, 1, 1), actor=actor
    )

    payload = events_for(db_connection, second.policy_config_id)[0].payload
    assert payload["value"] == {"from": 365, "to": 180}
    assert payload["effective_from"] == "2025-01-01"
    assert payload["policy_key"] == KEY
    assert payload["state_key"] == STATE


def test_a_change_is_a_new_row_not_an_update(
    db_connection: Connection, service: PolicyService, actor
) -> None:
    """What gives R28.3 its history and R7.8 its frozen deadlines."""
    service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=actor)
    service.set(KEY, 180, state=STATE, act=ACT, effective_from=date(2025, 1, 1), actor=actor)
    assert row_count(db_connection, KEY) == 2


def test_the_prior_value_is_read_as_of_the_new_effective_date(
    db_connection: Connection, service: PolicyService, actor
) -> None:
    """Not as of today.

    Inserting a version effective *between* two existing ones must record what it
    actually supersedes. Reading "current" instead would record the latest value as
    the prior, which is wrong whenever a change is backdated — and backdating a
    correction is exactly when an accurate history matters most.
    """
    service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=actor)
    service.set(KEY, 90, state=STATE, act=ACT, effective_from=date(2026, 1, 1), actor=actor)

    wedged = service.set(
        KEY, 180, state=STATE, act=ACT, effective_from=date(2025, 1, 1), actor=actor
    )
    assert wedged.prior_value == 365, "recorded the latest value rather than what it supersedes"


def test_a_written_value_is_immediately_resolvable(
    session: Session, service: PolicyService, actor
) -> None:
    service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=actor)
    resolver = PolicyResolver(session)
    assert resolver.get(KEY, state=STATE, act=ACT, as_of=date(2024, 6, 1)) == 365


def test_history_returns_every_version_newest_first(
    service: PolicyService, actor
) -> None:
    service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=actor)
    service.set(KEY, 180, state=STATE, act=ACT, effective_from=date(2025, 1, 1), actor=actor)
    history = service.history(KEY, state=STATE, act=ACT)
    assert [h.value for h in history] == [180, 365]


# ---------------------------------------------------------------------------
# R2.5 — the permission gate
# ---------------------------------------------------------------------------


def test_a_writer_without_config_write_is_refused(
    db_connection: Connection, service: PolicyService, officer_id
) -> None:
    unprivileged = FakePrincipal(id=str(officer_id), permissions=set())
    with pytest.raises(NotAuthorisedToWritePolicy):
        service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=unprivileged)


def test_a_refused_write_leaves_no_row_and_no_event(
    db_connection: Connection, service: PolicyService, officer_id
) -> None:
    """The permission check runs before anything is written, so there is nothing to
    roll back — a stronger guarantee than relying on the transaction."""
    unprivileged = FakePrincipal(id=str(officer_id), permissions=set())
    with pytest.raises(NotAuthorisedToWritePolicy):
        service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=unprivileged)
    assert row_count(db_connection, KEY) == 0


def test_the_refusal_discloses_nothing(service: PolicyService, officer_id) -> None:
    """R2.3: a 403 carries no body detail."""
    unprivileged = FakePrincipal(id=str(officer_id), permissions=set())
    with pytest.raises(NotAuthorisedToWritePolicy) as exc:
        service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=unprivileged)
    assert exc.value.details == {}
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Validation runs before the insert
# ---------------------------------------------------------------------------


def test_an_invalid_value_is_refused_before_anything_is_written(
    db_connection: Connection, service: PolicyService, actor
) -> None:
    """A validator running after the insert would leave the bad row visible to a
    concurrent reader inside this transaction."""
    with pytest.raises(PolicyValueInvalid):
        service.set(
            "risk.band_cutoffs",
            {"LOW": 0.25, "MEDIUM": 0.5, "HIGH": 0.75, "CRITICAL": 0.9},
            state=STATE,
            act=ACT,
            effective_from=APR,
            actor=actor,
        )
    assert row_count(db_connection, "risk.band_cutoffs") == 0


def test_a_valid_cutoff_set_is_written(service: PolicyService, actor) -> None:
    result = service.set(
        "risk.band_cutoffs",
        {"LOW": 0.25, "MEDIUM": 0.5, "HIGH": 0.75, "CRITICAL": 1.0},
        state=STATE,
        act=ACT,
        effective_from=APR,
        actor=actor,
    )
    assert result.new_value["CRITICAL"] == 1.0


def test_a_stage_graph_that_strands_cases_is_refused(
    service: PolicyService, actor
) -> None:
    with pytest.raises(PolicyValueInvalid, match="can never advance"):
        service.set(
            "policy.stage_set",
            {"stages": [
                {"key": "A", "successors": [], "terminal": False},
                {"key": "B", "successors": [], "terminal": True},
            ]},
            state=STATE,
            act=ACT,
            effective_from=APR,
            actor=actor,
        )


# ---------------------------------------------------------------------------
# R19.9 — a cutoff change owes a reband
# ---------------------------------------------------------------------------


def test_a_band_cutoff_change_reports_that_a_reband_is_required(
    service: PolicyService, actor
) -> None:
    """Carried in the result rather than fired here: the enqueue needs the outbox
    from task 3.8. Returning it means the caller cannot silently drop the obligation.
    """
    result = service.set(
        "risk.band_cutoffs",
        {"LOW": 0.25, "MEDIUM": 0.5, "HIGH": 0.75, "CRITICAL": 1.0},
        state=STATE,
        act=ACT,
        effective_from=APR,
        actor=actor,
    )
    assert result.reband_required is True


def test_an_unrelated_change_owes_no_reband(service: PolicyService, actor) -> None:
    result = service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=actor)
    assert result.reband_required is False


# ---------------------------------------------------------------------------
# R28.9 — OCR thresholds
# ---------------------------------------------------------------------------


def test_an_ocr_threshold_without_a_report_is_refused_with_the_requirement(
    db_connection: Connection, service: PolicyService, actor
) -> None:
    """The CHECK constraint would also catch this, but an IntegrityError naming a
    constraint is less use to an administrator than a message naming R28.9."""
    with pytest.raises(DomainError, match="accuracy report reference"):
        service.set(
            "ocr.threshold.auto_accept",
            0.95,
            state=STATE,
            act=ACT,
            effective_from=APR,
            actor=actor,
        )
    assert row_count(db_connection, "ocr.threshold.auto_accept") == 0


def test_an_ocr_threshold_with_a_report_defers_to_task_16_7(
    service: PolicyService, actor
) -> None:
    """The seam, asserted rather than glossed.

    §13.6's checks — report not superseded, matching model version and script set,
    precision stated at the new threshold — need extraction_accuracy_report, which
    task 16.7 creates. Raising here means the first threshold change after 16.7 lands
    cannot go unvalidated unnoticed; passing silently would guarantee it does.
    """
    with pytest.raises(ReportAssertionUnavailable, match="task 16.7"):
        service.set(
            "ocr.threshold.auto_accept",
            0.95,
            state=STATE,
            act=ACT,
            effective_from=APR,
            actor=actor,
            justification_report_id=1,
        )


# ---------------------------------------------------------------------------
# Uniqueness
# ---------------------------------------------------------------------------


def test_two_versions_on_the_same_date_are_refused(
    service: PolicyService, actor
) -> None:
    service.set(KEY, 365, state=STATE, act=ACT, effective_from=APR, actor=actor)
    with pytest.raises(Exception, match="policy_config_unique_version"):
        service.set(KEY, 180, state=STATE, act=ACT, effective_from=APR, actor=actor)


def test_the_same_key_may_differ_by_state(
    db_connection: Connection, service: PolicyService, actor
) -> None:
    service.set(KEY, 365, state="*", act=ACT, effective_from=APR, actor=actor)
    service.set(KEY, 180, state=STATE, act=ACT, effective_from=APR, actor=actor)
    assert row_count(db_connection, KEY) == 2
