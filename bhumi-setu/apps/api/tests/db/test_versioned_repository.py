"""``VersionedRepository.update`` — conditional UPDATE first, event append second.

Task 4.2, requirements R29.1, R29.3, R29.5, R29.6, R29.7, and Correctness
Properties 67 and 69.

Where task 4.1 stopped and 4.2 begins
-------------------------------------

``tests/db/test_versioned_mixin.py`` already proves Property 67 at the level of the
bare compare-and-set the mixin's column exists for — an ``UPDATE ... WHERE
entity_version = :expected`` matches one row on the live version and none on a stale
one. Task 4.2 lifts that into the real write path: :meth:`VersionedRepository.update`
issues that compare-and-set *and then*, only if a row came back, appends one event on
the same session with ``entity_version_after`` set. So these tests exercise the two
things 4.1's could not:

* **the event append is ordered second and is conditional** — a committed
  modification appends exactly one event carrying the incremented version, and a
  rejected one appends none (Property 69, R29.5), which holds because the append is
  never reached on the rejection path rather than because a rollback undoes it;
* **the strengthened stage predicate** (§7.2, R29.7) — a transition passes
  ``expected_stage`` and commits only while the case is still in that stage.

Everything runs against the real ``acquisition_case`` table (migration 0006) through
the ``db_connection`` fixture, which skips cleanly without PostgreSQL. The conflict
*description* — the per-attribute diff, the winning actor and occurrence time (R29.4)
— is task 4.3's; here a rejection is asserted only to be an ``EntityVersionConflict``
in the §9.4 envelope, the simple signal 4.3 will enrich.

Isolation
---------

Follows ``test_event_log_append.py`` and ``test_versioned_mixin.py``: the area and
project are seeded once on the function-scoped ``db_connection`` (inside its
always-rolled-back outer transaction), and each modification runs on a session bound
to that connection with ``join_transaction_mode="create_savepoint"``. The example
tests read back through ``db_connection`` while the session is open; the property
tests close the session at the end of each example, rolling that example's writes
back to the savepoint so the next starts from the seeded case alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.db.versioned_repository import EntityVersionConflict, VersionedRepository
from app.errors import ErrorCode
from app.models.acquisition_case import AcquisitionCase
from app.models.event import ActorType


# ---------------------------------------------------------------------------
# Collaborators task 4.2 does not own
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Actor:
    """Satisfies the ``Actor`` protocol the event append types against; ``Principal``
    (task 5.1) will satisfy it the same way."""

    kind: str
    id: str


OFFICER = _Actor(kind=ActorType.OFFICER, id="officer:412")
OTHER_OFFICER = _Actor(kind=ActorType.OFFICER, id="officer:927")
OCCURRED = datetime(2024, 3, 4, 9, 12, 44, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Seeding: an area, a project, and a case to modify
# ---------------------------------------------------------------------------


def _insert_project(handle: Any, area_code: str = "MH") -> int:
    return handle.execute(
        text(
            """
            INSERT INTO project
                (name, implementing_authority, area_code, purpose_category,
                 sanctioned_extent, extent_unit)
            VALUES ('Ring Road', 'PWD', :area_code, 'INFRASTRUCTURE', 100, 'hectare')
            RETURNING id
            """
        ),
        {"area_code": area_code},
    ).scalar_one()


def _insert_case(
    handle: Any,
    *,
    project_id: int,
    case_reference: str,
    area_code: str = "MH",
    stage_key: str = "SIA",
) -> Any:
    """Insert one acquisition_case at version 1, returning its id and version.

    Raw SQL rather than the ORM on purpose: it leaves the session's identity map
    empty, so ``update``'s ``RETURNING`` builds a fresh instance and its behaviour
    does not depend on a pre-loaded copy — which is also how a service that has not
    loaded the entity first would call it.
    """
    return handle.execute(
        text(
            """
            INSERT INTO acquisition_case
                (case_reference, project_id, state_key, act_key, area_code, stage_key,
                 stage_set_effective_from, stage_entered_on)
            VALUES
                (:case_reference, :project_id, 'MH', 'RFCTLARR_2013', :area_code,
                 :stage_key, DATE '2024-01-01', DATE '2024-01-01')
            RETURNING id, entity_version
            """
        ),
        {
            "case_reference": case_reference,
            "project_id": project_id,
            "area_code": area_code,
            "stage_key": stage_key,
        },
    ).one()


def _event_count(handle: Any, case_id: int) -> int:
    return handle.execute(
        text(
            "SELECT count(*) FROM event "
            "WHERE entity_type = 'acquisition_case' AND entity_id = :id"
        ),
        {"id": case_id},
    ).scalar_one()


def _case_row(handle: Any, case_id: int) -> dict[str, Any]:
    return dict(
        handle.execute(
            text("SELECT * FROM acquisition_case WHERE id = :id"), {"id": case_id}
        )
        .mappings()
        .one()
    )


@pytest.fixture
def project_id(db_connection: Connection, area_factory) -> int:
    """Seed the area and project the cases hang off, once per test.

    Seeded on the outer ``db_connection`` so that under a Hypothesis property test —
    where this fixture is created once and reused across examples — the reference
    data persists while each example's own case (inserted on its per-example
    session) rolls back.
    """
    area_factory("MH", "state", "Maharashtra")
    return _insert_project(db_connection, "MH")


@pytest.fixture
def session(db_connection: Connection) -> Session:
    return Session(bind=db_connection, join_transaction_mode="create_savepoint")


# ===========================================================================
# The commit path (R29.1) — increment, apply, one event
# ===========================================================================


class TestCommit:
    def test_a_matching_version_commits_increments_and_returns_the_row(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        case = _insert_case(db_connection, project_id=project_id, case_reference="C-1")

        row = VersionedRepository.update(
            session,
            entity_type=AcquisitionCase,
            entity_id=case.id,
            expected_version=case.entity_version,
            changes={"pending_review_count": 4},
            submitted_prior={"pending_review_count": 0},
            actor=OFFICER,
            occurrence_time=OCCURRED,
            event_type="CASE_UPDATED",
        )

        assert row.id == case.id
        assert row.entity_version == case.entity_version + 1, "the version increments by one"
        assert row.pending_review_count == 4, "the change is applied"

        stored = _case_row(db_connection, case.id)
        assert stored["entity_version"] == case.entity_version + 1
        assert stored["pending_review_count"] == 4

    def test_a_commit_appends_exactly_one_event_carrying_the_new_version(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        """R29.4's hook: the event records ``entity_version_after`` as the version the
        modification produced, so a version is attributable to the actor that made it,
        and the changed attribute is recorded prior-and-new (R4.1)."""
        case = _insert_case(db_connection, project_id=project_id, case_reference="C-2")

        VersionedRepository.update(
            session,
            entity_type=AcquisitionCase,
            entity_id=case.id,
            expected_version=case.entity_version,
            changes={"risk_band": "HIGH"},
            submitted_prior={"risk_band": None},
            actor=OFFICER,
            occurrence_time=OCCURRED,
            event_type="CASE_UPDATED",
        )

        assert _event_count(db_connection, case.id) == 1
        event = db_connection.execute(
            text(
                "SELECT event_type, actor_type, actor_id, entity_version_after, "
                "occurrence_time, payload FROM event "
                "WHERE entity_type = 'acquisition_case' AND entity_id = :id"
            ),
            {"id": case.id},
        ).one()
        assert event.event_type == "CASE_UPDATED"
        assert event.actor_type == ActorType.OFFICER
        assert event.actor_id == "officer:412"
        assert event.entity_version_after == case.entity_version + 1
        assert event.occurrence_time == OCCURRED
        assert event.payload == {"risk_band": {"from": None, "to": "HIGH"}}


# ===========================================================================
# The rejection path (R29.3, R29.5) — nothing written, no event
# ===========================================================================


class TestRejection:
    def test_a_stale_version_raises_a_conflict_in_the_envelope(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        """The simple signal task 4.2 raises: a 409 ``ENTITY_VERSION_CONFLICT`` naming
        the entity and the presented version. Task 4.3 fills in the per-attribute
        diff and the winning actor."""
        case = _insert_case(db_connection, project_id=project_id, case_reference="C-3")

        with pytest.raises(EntityVersionConflict) as caught:
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=case.entity_version + 1,  # stale
                changes={"pending_review_count": 9},
                submitted_prior={"pending_review_count": 0},
                actor=OFFICER,
                occurrence_time=OCCURRED,
                event_type="CASE_UPDATED",
            )

        error = caught.value
        assert error.code == ErrorCode.ENTITY_VERSION_CONFLICT
        assert error.status_code == 409
        envelope = error.envelope()
        assert envelope.details["entity_type"] == "acquisition_case"
        assert envelope.details["entity_id"] == case.id
        assert envelope.details["expected_version"] == case.entity_version + 1

    def test_a_rejected_modification_writes_no_event_and_leaves_the_row(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        """R29.5 as an example: nothing written, no event. The property test below
        generalises this over arbitrary changes and stale versions."""
        case = _insert_case(db_connection, project_id=project_id, case_reference="C-4")
        before = _case_row(db_connection, case.id)

        with pytest.raises(EntityVersionConflict):
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=case.entity_version + 5,
                changes={"pending_review_count": 9, "risk_band": "CRITICAL"},
                submitted_prior={"pending_review_count": 0, "risk_band": None},
                actor=OFFICER,
                occurrence_time=OCCURRED,
                event_type="CASE_UPDATED",
            )

        assert _event_count(db_connection, case.id) == 0
        assert _case_row(db_connection, case.id) == before


# ===========================================================================
# The strengthened stage predicate (§7.2, R29.7)
# ===========================================================================


class TestStageTransition:
    def test_a_transition_from_the_expected_stage_commits(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        case = _insert_case(
            db_connection, project_id=project_id, case_reference="C-5", stage_key="SIA"
        )

        row = VersionedRepository.update(
            session,
            entity_type=AcquisitionCase,
            entity_id=case.id,
            expected_version=case.entity_version,
            changes={"stage_key": "PRELIMINARY_NOTIFICATION"},
            submitted_prior={"stage_key": "SIA"},
            actor=OFFICER,
            occurrence_time=OCCURRED,
            event_type="STAGE_TRANSITIONED",
            expected_stage="SIA",
        )

        assert row.stage_key == "PRELIMINARY_NOTIFICATION"
        assert row.entity_version == case.entity_version + 1
        assert _event_count(db_connection, case.id) == 1

    def test_a_transition_from_the_wrong_stage_is_rejected_even_at_the_right_version(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        """R29.7: the strengthened predicate catches the second officer even if both
        somehow present the same version. The case is at SIA; a transition that
        expects it still at PRELIMINARY_NOTIFICATION matches no row, so nothing is
        written and no event is appended — exactly the losing officer's outcome after
        the first transition has moved the case on."""
        case = _insert_case(
            db_connection, project_id=project_id, case_reference="C-6", stage_key="SIA"
        )
        before = _case_row(db_connection, case.id)

        with pytest.raises(EntityVersionConflict):
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=case.entity_version,  # correct version
                changes={"stage_key": "AWARD"},
                submitted_prior={"stage_key": "PRELIMINARY_NOTIFICATION"},
                actor=OTHER_OFFICER,
                occurrence_time=OCCURRED,
                event_type="STAGE_TRANSITIONED",
                expected_stage="PRELIMINARY_NOTIFICATION",  # but the case is at SIA
            )

        assert _event_count(db_connection, case.id) == 0
        assert _case_row(db_connection, case.id) == before


# ===========================================================================
# The repository-managed-key guard
# ===========================================================================


class TestManagedKeyGuard:
    @pytest.mark.parametrize("managed_key", ["entity_version", "id"])
    def test_changes_may_not_set_a_repository_managed_key(
        self, session: Session, managed_key: str
    ) -> None:
        """``entity_version`` is the repository's to increment and ``id`` selects the
        row; letting either through ``.values(**changes)`` would break the
        compare-and-set. The guard raises before any SQL is issued."""
        with pytest.raises(ValueError, match=managed_key):
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=1,
                expected_version=1,
                changes={managed_key: 99},
                submitted_prior={},
                actor=OFFICER,
                occurrence_time=OCCURRED,
                event_type="CASE_UPDATED",
            )


# ===========================================================================
# Property 67 (database-backed; skips without PostgreSQL)
# ===========================================================================
#
# Property 67: for any versioned entity and any modification, the Entity_Version
# increases by one when and only when the modification commits, and is unchanged when
# the modification is rejected.
#
# test_versioned_mixin.py proves this for the raw compare-and-set; here it is proven
# through VersionedRepository.update, so the biconditional holds of the actual write
# path — including that exactly one event is appended per commit and none per
# rejection.


@dataclass(frozen=True)
class _Attempt:
    """One modification presenting ``current + delta`` as its prior version, so
    ``delta == 0`` is a well-formed request that commits and any other delta is a
    stale one that is rejected."""

    delta: int


@st.composite
def _attempt_sequences(draw: st.DrawFn) -> tuple[_Attempt, ...]:
    """A run of attempts against one case, dense around ``delta == 0`` so both arms
    of the biconditional — commit and reject — are exercised heavily."""
    return tuple(
        _Attempt(delta=d)
        for d in draw(
            st.lists(st.integers(min_value=-4, max_value=4), min_size=1, max_size=15)
        )
    )


@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(attempts=_attempt_sequences())
def test_property_67_versions_increase_exactly_on_commit(
    db_connection: Connection, project_id: int, attempts: tuple[_Attempt, ...]
) -> None:
    """Feature: bhumisetu, Property 67: for any versioned entity and any modification,
    the entity version increases by one when and only when the modification commits,
    and is unchanged when it is rejected.

    **Validates: Requirements 29.1**

    Each attempt presents ``current + delta`` as its expected version through
    :meth:`VersionedRepository.update`: ``delta == 0`` is the commit case (the row is
    at the presented version), any other delta is the reject case (it is not). The
    assertions are the biconditional itself — a commit increments by one and appends
    one event, a rejection changes nothing and appends none — plus the running
    invariant that the version equals its start plus the number of commits and that
    the event count equals the number of commits.
    """
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        case = _insert_case(session, project_id=project_id, case_reference="C-P67")
        case_id = case.id

        current = case.entity_version
        stored_value = 0
        commits = 0
        for index, attempt in enumerate(attempts):
            presented = current + attempt.delta
            new_value = index + 1
            try:
                row = VersionedRepository.update(
                    session,
                    entity_type=AcquisitionCase,
                    entity_id=case_id,
                    expected_version=presented,
                    changes={"pending_review_count": new_value},
                    submitted_prior={"pending_review_count": stored_value},
                    actor=OFFICER,
                    occurrence_time=OCCURRED,
                    event_type="CASE_UPDATED",
                )
                committed = True
            except EntityVersionConflict:
                committed = False

            # Commit iff the presented version was the live one. Nothing in between.
            assert committed == (attempt.delta == 0)

            db_version, db_value = session.execute(
                text(
                    "SELECT entity_version, pending_review_count "
                    "FROM acquisition_case WHERE id = :id"
                ),
                {"id": case_id},
            ).one()

            if committed:
                commits += 1
                current += 1
                stored_value = new_value
                assert row.entity_version == current
                assert db_version == current, "a commit increases the version by one"
                assert db_value == new_value, "a commit applies the change"
            else:
                assert db_version == current, "a rejected write leaves the version"
                assert db_value == stored_value, "a rejected write changes nothing"

            # entity_version - INITIAL == committed modifications, and one event per
            # commit — the append is ordered after, and conditional on, the UPDATE.
            assert db_version == case.entity_version + commits
            assert _event_count(session, case_id) == commits
    finally:
        session.close()


# ===========================================================================
# Property 69 (database-backed; skips without PostgreSQL)
# ===========================================================================
#
# Property 69: for any rejected modification, no Event is appended for it and the
# target entity's stored state equals its state immediately before the request,
# attribute for attribute.

_MUTABLE_COLUMNS = st.fixed_dictionaries(
    {},
    optional={
        "pending_review_count": st.integers(min_value=0, max_value=10_000),
        "open_blocking_count": st.integers(min_value=0, max_value=10_000),
        "risk_band": st.sampled_from(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
        "deadline_breached": st.booleans(),
    },
).filter(lambda changes: len(changes) >= 1)


@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    changes=_MUTABLE_COLUMNS,
    stale_offset=st.integers(min_value=1, max_value=6),
)
def test_property_69_a_rejected_modification_leaves_no_trace(
    db_connection: Connection,
    project_id: int,
    changes: dict[str, Any],
    stale_offset: int,
) -> None:
    """Feature: bhumisetu, Property 69: for any rejected modification, no event is
    appended for it and the target entity's stored state equals its state immediately
    before the request, attribute for attribute.

    **Validates: Requirements 29.5**

    A modification presenting a stale version (the live version plus a non-zero
    offset) is rejected. The row is snapshotted column-by-column before the attempt
    and compared after: the compare-and-set matched nothing, so no column moved and —
    because the append is ordered strictly after the UPDATE and never reached — no
    event exists for the entity.
    """
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        case = _insert_case(session, project_id=project_id, case_reference="C-P69")
        case_id = case.id
        before = _case_row(session, case_id)
        events_before = _event_count(session, case_id)

        with pytest.raises(EntityVersionConflict):
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case_id,
                expected_version=case.entity_version + stale_offset,
                changes=changes,
                submitted_prior={column: None for column in changes},
                actor=OFFICER,
                occurrence_time=OCCURRED,
                event_type="CASE_UPDATED",
            )

        assert _case_row(session, case_id) == before, "the row is bit-identical, attribute for attribute"
        assert _event_count(session, case_id) == events_before, "no event was appended"
        assert events_before == 0
    finally:
        session.close()
