"""The conflict description and the §9.4 error envelope.

Task 4.3, requirements R29.3, R29.4 and R29.8, and Correctness Property 68.

Where task 4.2 stopped and 4.3 begins
-------------------------------------

``tests/db/test_versioned_repository.py`` proves the *mechanism* — the conditional
UPDATE first, the event append second, a rejection writing nothing — and asserts a
rejection is only that it is an ``EntityVersionConflict`` in the §9.4 envelope, the
simple signal 4.2 raised. Task 4.3 fills that signal in: R29.4 says a rejection must
tell the losing officer *what* diverged and *who* moved it, in enough detail to
resubmit. So these tests exercise the description :meth:`VersionedRepository.update`
now builds on the rejection path:

* every attribute whose stored value differs from the value the request presented as
  its prior, with the current stored value of each (R29.4), and *only* those — an
  attribute still matching its presented prior is not a conflict;
* the actor and occurrence time of the modification that produced the current
  version, read from ``event.entity_version_after`` (R29.4, §7.2);
* for a double field review, the winning review's recorded state and value (R29.8),
  through the model-free :class:`ReviewConflictSpec` — ``extracted_field`` does not
  exist until task 16.1, so the mechanism is exercised here against
  ``acquisition_case`` columns standing in for the reviewed value and review state.

Isolation
---------

Follows ``test_versioned_repository.py``: the area and project are seeded once on the
function-scoped ``db_connection`` (inside its always-rolled-back outer transaction),
and each modification runs on a session bound to that connection with
``join_transaction_mode="create_savepoint"``. The winning and losing modifications
of one example share a session so the loser sees the winner's committed state,
exactly as two officers racing through one write path would. The property test closes
its session at the end of each example, rolling that example's writes back so the
next starts from the seeded case alone.
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

from app.db.versioned_repository import (
    EntityVersionConflict,
    ReviewConflictSpec,
    VersionedRepository,
)
from app.models.acquisition_case import AcquisitionCase
from app.models.event import ActorType


# ---------------------------------------------------------------------------
# Collaborators task 4.3 does not own
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Actor:
    """Satisfies the ``Actor`` protocol the event append types against."""

    kind: str
    id: str


#: The winner: its id and the time of its modification are what a rejection must name.
WINNER = _Actor(kind=ActorType.OFFICER, id="officer:412")
#: The loser, whose modification is rejected.
LOSER = _Actor(kind=ActorType.OFFICER, id="officer:927")

#: Distinct occurrence times so the description's "occurrence time of that
#: modification" is unambiguously the winner's, not the loser's.
WINNER_TIME = datetime(2024, 3, 4, 9, 12, 44, tzinfo=timezone.utc)
LOSER_TIME = datetime(2024, 3, 5, 10, 0, 0, tzinfo=timezone.utc)


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
    """Insert one acquisition_case at version 1 with the known initial column values.

    Raw SQL rather than the ORM on purpose: it leaves the session's identity map
    empty and appends no event, so the only event a description can attribute the
    current version to is the winning modification the test itself makes.
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


@pytest.fixture
def project_id(db_connection: Connection, area_factory) -> int:
    """Seed the area and project the cases hang off, once per test."""
    area_factory("MH", "state", "Maharashtra")
    return _insert_project(db_connection, "MH")


@pytest.fixture
def session(db_connection: Connection) -> Session:
    return Session(bind=db_connection, join_transaction_mode="create_savepoint")


def _commit_winning_modification(
    session: Session,
    *,
    case_id: int,
    version: int,
    changes: dict[str, Any],
    submitted_prior: dict[str, Any],
    event_type: str = "CASE_UPDATED",
) -> None:
    """Have WINNER commit a modification, taking the case to ``version + 1``."""
    VersionedRepository.update(
        session,
        entity_type=AcquisitionCase,
        entity_id=case_id,
        expected_version=version,
        changes=changes,
        submitted_prior=submitted_prior,
        actor=WINNER,
        occurrence_time=WINNER_TIME,
        event_type=event_type,
    )


# ===========================================================================
# The conflict description (R29.4)
# ===========================================================================


class TestConflictDescription:
    def test_it_names_every_diverged_attribute_with_its_current_value(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        """R29.4: the rejection names each attribute whose stored value differs from
        the presented prior, and the current stored value of each."""
        case = _insert_case(db_connection, project_id=project_id, case_reference="C-D1")

        _commit_winning_modification(
            session,
            case_id=case.id,
            version=case.entity_version,
            changes={"pending_review_count": 7, "risk_band": "HIGH"},
            submitted_prior={"pending_review_count": 0, "risk_band": None},
        )

        with pytest.raises(EntityVersionConflict) as caught:
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=case.entity_version,  # stale: the winner moved it on
                changes={"pending_review_count": 99, "risk_band": "LOW"},
                submitted_prior={"pending_review_count": 0, "risk_band": None},
                actor=LOSER,
                occurrence_time=LOSER_TIME,
                event_type="CASE_UPDATED",
            )

        by_name = {attr.name: attr for attr in caught.value.detail.attributes}
        assert set(by_name) == {"pending_review_count", "risk_band"}
        assert by_name["pending_review_count"].submitted_prior == 0
        assert by_name["pending_review_count"].current == 7
        assert by_name["risk_band"].submitted_prior is None
        assert by_name["risk_band"].current == "HIGH"

    def test_it_attributes_the_current_version_to_the_winning_actor_and_time(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        """R29.4: the actor whose modification produced the current version, and the
        occurrence time of that modification — read from event.entity_version_after,
        not guessed from timestamps."""
        case = _insert_case(db_connection, project_id=project_id, case_reference="C-D2")

        _commit_winning_modification(
            session,
            case_id=case.id,
            version=case.entity_version,
            changes={"pending_review_count": 3},
            submitted_prior={"pending_review_count": 0},
        )

        with pytest.raises(EntityVersionConflict) as caught:
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=case.entity_version,  # stale
                changes={"pending_review_count": 5},
                submitted_prior={"pending_review_count": 0},
                actor=LOSER,
                occurrence_time=LOSER_TIME,
                event_type="CASE_UPDATED",
            )

        detail = caught.value.detail
        assert detail.current_entity_version == case.entity_version + 1
        assert detail.conflicting_actor_id == WINNER.id
        assert detail.conflicting_occurrence_time == WINNER_TIME

    def test_an_attribute_still_matching_its_prior_is_not_reported(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        """R29.4 asks only for attributes that *differ*. The loser names risk_band
        with the prior the winner never changed it from, so it is not a conflict; only
        pending_review_count, which the winner moved, is reported."""
        case = _insert_case(db_connection, project_id=project_id, case_reference="C-D3")

        _commit_winning_modification(
            session,
            case_id=case.id,
            version=case.entity_version,
            changes={"pending_review_count": 4},
            submitted_prior={"pending_review_count": 0},
        )

        with pytest.raises(EntityVersionConflict) as caught:
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=case.entity_version,  # stale
                changes={"pending_review_count": 8, "risk_band": "LOW"},
                # risk_band's presented prior (None) still matches the stored value.
                submitted_prior={"pending_review_count": 0, "risk_band": None},
                actor=LOSER,
                occurrence_time=LOSER_TIME,
                event_type="CASE_UPDATED",
            )

        assert {attr.name for attr in caught.value.detail.attributes} == {
            "pending_review_count"
        }

    def test_a_conflict_with_no_prior_modifier_reports_no_actor(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        """A stale version presented against a freshly created case — one no
        modification has touched through the repository — has no event attributing its
        current version, so the actor and time are truthfully absent rather than
        fabricated."""
        case = _insert_case(db_connection, project_id=project_id, case_reference="C-D4")

        with pytest.raises(EntityVersionConflict) as caught:
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=case.entity_version + 1,  # stale, but nothing moved it
                changes={"pending_review_count": 5},
                submitted_prior={"pending_review_count": 0},
                actor=LOSER,
                occurrence_time=LOSER_TIME,
                event_type="CASE_UPDATED",
            )

        detail = caught.value.detail
        assert detail.current_entity_version == case.entity_version
        assert detail.conflicting_actor_id is None
        assert detail.conflicting_occurrence_time is None
        # pending_review_count's prior (0) still matches the stored value, so nothing
        # diverged.
        assert detail.attributes == ()


# ===========================================================================
# The §9.4 envelope shape
# ===========================================================================


class TestEnvelope:
    def test_the_envelope_carries_the_section_9_4_details(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        """The details dict is the §9.4 shape: identity keys, the attribute diff with
        JSON-native values, the winning actor and ISO occurrence time, and the current
        version. A plain conflict carries no review-state key."""
        case = _insert_case(db_connection, project_id=project_id, case_reference="C-E1")

        _commit_winning_modification(
            session,
            case_id=case.id,
            version=case.entity_version,
            changes={"risk_band": "HIGH"},
            submitted_prior={"risk_band": None},
        )

        with pytest.raises(EntityVersionConflict) as caught:
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=case.entity_version,  # stale
                changes={"risk_band": "LOW"},
                submitted_prior={"risk_band": None},
                actor=LOSER,
                occurrence_time=LOSER_TIME,
                event_type="CASE_UPDATED",
            )

        error = caught.value
        assert error.status_code == 409
        details = error.envelope().details

        assert details["entity_type"] == "acquisition_case"
        assert details["entity_id"] == case.id
        assert details["expected_version"] == case.entity_version
        assert details["current_entity_version"] == case.entity_version + 1
        assert details["conflicting_actor_id"] == WINNER.id
        # datetime is rendered as an ISO string so the envelope serialises to JSON.
        assert details["conflicting_occurrence_time"] == WINNER_TIME.isoformat()
        assert details["attributes"] == [
            {"name": "risk_band", "submitted_prior": None, "current": "HIGH"}
        ]
        assert "current_review_state" not in details


# ===========================================================================
# The double-field-review conflict (R29.8), exercised model-free
# ===========================================================================


class TestFieldReviewConflict:
    """R29.8 through the generic ReviewConflictSpec. Extracted_Field arrives in task
    16.1; here acquisition_case columns stand in — ``risk_band`` for the reviewed
    value, ``stage_key`` for the review state — so the mechanism is proven without a
    model that does not exist yet."""

    def test_it_returns_the_winning_state_and_recorded_value(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        case = _insert_case(
            db_connection, project_id=project_id, case_reference="C-FR1", stage_key="SIA"
        )

        _commit_winning_modification(
            session,
            case_id=case.id,
            version=case.entity_version,
            changes={"risk_band": "HIGH", "stage_key": "PRELIMINARY_NOTIFICATION"},
            submitted_prior={"risk_band": None, "stage_key": "SIA"},
            event_type="FIELD_REVIEWED",
        )

        spec = ReviewConflictSpec(
            value_attribute="risk_band", review_state_attribute="stage_key"
        )
        with pytest.raises(EntityVersionConflict) as caught:
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=case.entity_version,  # stale
                changes={"risk_band": "LOW"},
                submitted_prior={"risk_band": None},
                actor=LOSER,
                occurrence_time=LOSER_TIME,
                event_type="FIELD_REVIEWED",
                review_conflict=spec,
            )

        detail = caught.value.detail
        assert detail.is_field_review
        # R29.8: the review state the winner recorded.
        assert detail.current_review_state == "PRELIMINARY_NOTIFICATION"
        # R29.8: the value the winner recorded, surfaced as the value attribute's
        # current.
        by_name = {attr.name: attr for attr in detail.attributes}
        assert by_name["risk_band"].current == "HIGH"
        # And it reaches the envelope.
        assert (
            caught.value.envelope().details["current_review_state"]
            == "PRELIMINARY_NOTIFICATION"
        )

    def test_the_reviewed_value_is_reported_even_without_a_presented_prior(
        self, session: Session, db_connection: Connection, project_id: int
    ) -> None:
        """R29.8 requires the value the winner recorded regardless of what the loser
        presented — the loser here changes a different attribute and presents no prior
        for the reviewed value, yet the value attribute is still surfaced."""
        case = _insert_case(
            db_connection, project_id=project_id, case_reference="C-FR2", stage_key="SIA"
        )

        _commit_winning_modification(
            session,
            case_id=case.id,
            version=case.entity_version,
            changes={"risk_band": "CRITICAL", "stage_key": "AWARD"},
            submitted_prior={"risk_band": None, "stage_key": "SIA"},
            event_type="FIELD_REVIEWED",
        )

        spec = ReviewConflictSpec(
            value_attribute="risk_band", review_state_attribute="stage_key"
        )
        with pytest.raises(EntityVersionConflict) as caught:
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=case.entity_version,  # stale
                changes={"pending_review_count": 2},
                submitted_prior={"pending_review_count": 0},  # no risk_band prior
                actor=LOSER,
                occurrence_time=LOSER_TIME,
                event_type="FIELD_REVIEWED",
                review_conflict=spec,
            )

        by_name = {attr.name: attr for attr in caught.value.detail.attributes}
        assert "risk_band" in by_name, "the reviewed value is forced into the diff"
        assert by_name["risk_band"].submitted_prior is None
        assert by_name["risk_band"].current == "CRITICAL"


# ===========================================================================
# Property 68 (database-backed; skips without PostgreSQL)
# ===========================================================================
#
# Property 68: for any modification request presenting a stale version, the
# modification is rejected and the response names every attribute whose stored value
# differs from the value the request presented as prior, the current stored value of
# each, the identifier of the actor whose modification produced the current version,
# and the occurrence time of that modification.

#: The columns the property drives, with their known initial values from _insert_case
#: (the schema server defaults). A winner that changes a column always moves it to a
#: value differing from its initial, so "current differs from the initial prior" holds
#: exactly for the columns the winner touched.
_INITIALS: dict[str, Any] = {
    "pending_review_count": 0,
    "open_blocking_count": 0,
    "risk_band": None,
    "deadline_breached": False,
}


def _differing_value(column: str) -> st.SearchStrategy[Any]:
    """A value for ``column`` guaranteed to differ from its initial value."""
    if column in ("pending_review_count", "open_blocking_count"):
        return st.integers(min_value=1, max_value=10_000)
    if column == "risk_band":
        return st.sampled_from(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    return st.just(True)  # deadline_breached, initial False


@st.composite
def _winner_and_loser(draw: st.DrawFn) -> tuple[dict[str, Any], tuple[str, ...]]:
    """A winning change set and the columns the loser presents priors for.

    The winner changes a non-empty subset of columns to values differing from their
    initials; the loser presents a non-empty subset of columns with their initial
    values as prior. The expected divergence is then exactly the intersection — a
    column the loser names is a conflict iff the winner moved it.
    """
    columns = list(_INITIALS)
    winner_columns = draw(
        st.lists(st.sampled_from(columns), min_size=1, max_size=len(columns), unique=True)
    )
    winner_changes = {column: draw(_differing_value(column)) for column in winner_columns}
    loser_columns = draw(
        st.lists(st.sampled_from(columns), min_size=1, max_size=len(columns), unique=True)
    )
    return winner_changes, tuple(loser_columns)


@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(plan=_winner_and_loser())
def test_property_68_a_stale_version_is_rejected_with_a_complete_description(
    db_connection: Connection,
    project_id: int,
    plan: tuple[dict[str, Any], tuple[str, ...]],
) -> None:
    """Feature: bhumisetu, Property 68: for any modification request presenting an
    Entity_Version other than the target entity's current version, the modification is
    rejected and the response names every attribute whose stored value differs from
    the value the request presented as prior, the current stored value of each, the
    identifier of the actor whose modification produced the current version, and the
    occurrence time of that modification.

    **Validates: Requirements 29.3, 29.4**

    The winner commits a change set at version 1, taking the case to version 2. The
    loser then presents the now-stale version 1, naming its columns with their initial
    values as the priors it believes it is replacing. The rejection's description must
    name exactly the columns the winner moved (their stored value now differs from the
    initial prior), give each column's current value, and attribute the current version
    to the winner and the winner's occurrence time.
    """
    winner_changes, loser_columns = plan
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        case = _insert_case(session, project_id=project_id, case_reference="C-P68")
        start_version = case.entity_version

        _commit_winning_modification(
            session,
            case_id=case.id,
            version=start_version,
            changes=winner_changes,
            submitted_prior={column: _INITIALS[column] for column in winner_changes},
        )

        with pytest.raises(EntityVersionConflict) as caught:
            VersionedRepository.update(
                session,
                entity_type=AcquisitionCase,
                entity_id=case.id,
                expected_version=start_version,  # stale: the winner moved it to +1
                changes={column: winner_changes.get(column, 1) for column in loser_columns},
                submitted_prior={column: _INITIALS[column] for column in loser_columns},
                actor=LOSER,
                occurrence_time=LOSER_TIME,
                event_type="CASE_UPDATED",
            )

        detail = caught.value.detail
        expected_diverged = set(loser_columns) & set(winner_changes)

        assert {attr.name for attr in detail.attributes} == expected_diverged
        for attr in detail.attributes:
            assert attr.submitted_prior == _INITIALS[attr.name], (
                "the prior reported is the one the loser presented"
            )
            assert attr.current == winner_changes[attr.name], (
                "the current reported is the value the winner committed"
            )

        assert detail.current_entity_version == start_version + 1
        assert detail.conflicting_actor_id == WINNER.id
        assert detail.conflicting_occurrence_time == WINNER_TIME
    finally:
        session.close()
