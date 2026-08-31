"""The stage set as data (§4.3), and R28.6's two-date deadline resolution.

The tests that carry weight here are the ones about *which date* configuration is
read at. Deadline resolution reads policy twice, at two different dates, and either
one being wrong produces a wrong statutory deadline — with no error, and looking
entirely plausible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from app.services.policy import PolicyResolver, PolicyValueMissing
from app.services.stage_graph import (
    STAGE_SET_KEY,
    StageGraph,
    StageNotInGraph,
    StageTransitionInvalid,
    resolve_stage_graph,
    stage_deadline,
)

STATE = "IN-MH"
ACT = "RFCTLARR-2013"

FIVE_STAGE = {
    "stages": [
        {"key": "SIA", "label_key": "stage.sia", "successors": ["PN"],
         "period_key": "period.sia", "terminal": False},
        {"key": "PN", "label_key": "stage.pn", "successors": ["DECL", "LAPSED"],
         "period_key": "period.pn", "terminal": False},
        {"key": "DECL", "label_key": "stage.decl", "successors": ["POSSESSION"],
         "period_key": "period.decl", "terminal": False},
        {"key": "POSSESSION", "label_key": "stage.possession", "successors": [],
         "period_key": None, "terminal": True},
        {"key": "LAPSED", "label_key": "stage.lapsed", "successors": [],
         "period_key": None, "terminal": True},
    ]
}

# A different act with different stages entirely (§4.4). Nothing in the code knows
# these strings exist.
FOUR_STAGE_TG = {
    "stages": [
        {"key": "NOTIF", "successors": ["ENQUIRY"], "period_key": "period.tg.notif",
         "terminal": False},
        {"key": "ENQUIRY", "successors": ["AWARD"], "period_key": "period.tg.enquiry",
         "terminal": False},
        {"key": "AWARD", "successors": ["HANDOVER"], "period_key": "period.tg.award",
         "terminal": False},
        {"key": "HANDOVER", "successors": [], "period_key": None, "terminal": True},
    ]
}


@dataclass
class FakeCase:
    """Stands in for acquisition_case, which lands in task 8.1."""

    state_key: str = STATE
    act_key: str | None = ACT
    stage_key: str = "PN"
    stage_set_effective_from: date = date(2024, 4, 1)
    stage_entered_on: date = date(2024, 6, 1)


@pytest.fixture
def officer_id(db_connection: Connection) -> str:
    return db_connection.execute(
        text(
            """
            INSERT INTO officer (officer_code, display_name, credential_hash)
            VALUES ('stage-officer', 'Stage Officer', 'argon2-placeholder')
            RETURNING id
            """
        )
    ).scalar_one()


@pytest.fixture
def put(db_connection: Connection, officer_id: str):
    import json

    def _put(key: str, value, *, state: str = STATE, act: str | None = ACT,
             effective_from: str = "2024-04-01") -> None:
        db_connection.execute(
            text(
                """
                INSERT INTO policy_config
                    (policy_key, state_key, act_key, effective_from, value, created_by)
                VALUES (:k, :s, :a, :ef, CAST(:v AS jsonb), :o)
                """
            ),
            {"k": key, "s": state, "a": act, "ef": effective_from,
             "v": json.dumps(value), "o": officer_id},
        )

    return _put


@pytest.fixture
def resolver(db_connection: Connection) -> PolicyResolver:
    return PolicyResolver(
        Session(bind=db_connection, join_transaction_mode="create_savepoint")
    )


# ---------------------------------------------------------------------------
# Graph parsing and R5.3 / R5.4
# ---------------------------------------------------------------------------


def test_graph_parses_from_the_policy_value() -> None:
    graph = StageGraph.from_policy_value(FIVE_STAGE)
    assert graph.first_key == "SIA"
    assert graph.successors("PN") == ("DECL", "LAPSED")
    assert graph.is_terminal("POSSESSION")
    assert graph.terminal_keys == ("LAPSED", "POSSESSION")


def test_a_declared_successor_is_permitted() -> None:
    graph = StageGraph.from_policy_value(FIVE_STAGE)
    graph.assert_transition_permitted(current="PN", requested="DECL")


def test_an_undeclared_successor_is_refused_with_the_permitted_set() -> None:
    """R5.4 requires the permitted set to be returned, so an officer learns what is
    possible rather than only what was refused."""
    graph = StageGraph.from_policy_value(FIVE_STAGE)
    with pytest.raises(StageTransitionInvalid) as exc:
        graph.assert_transition_permitted(current="PN", requested="POSSESSION")
    assert exc.value.details["permitted_successors"] == ["DECL", "LAPSED"]
    assert exc.value.details["current_stage"] == "PN"


def test_a_stage_outside_the_graph_refuses_loudly() -> None:
    """The alternative is treating an unknown stage as terminal, which would silently
    stop the case ever being reported as late."""
    graph = StageGraph.from_policy_value(FIVE_STAGE)
    with pytest.raises(StageNotInGraph) as exc:
        graph.stage("NOT_A_STAGE")
    assert "POSSESSION" in exc.value.details["known_stages"]


def test_ordered_keys_follows_reachability_not_declaration_order() -> None:
    """R22.2's dashboard iterates this, so a stage must appear after the stages that
    reach it — otherwise the stage distribution reads in an order the process does
    not follow."""
    graph = StageGraph.from_policy_value(FIVE_STAGE)
    order = graph.ordered_keys()
    assert order.index("SIA") < order.index("PN") < order.index("DECL")
    assert set(order) == set(graph.stages)


# ---------------------------------------------------------------------------
# R28.6 — the period is read as of stage_entered_on, not today
# ---------------------------------------------------------------------------


def test_deadline_is_entry_date_plus_the_configured_period(put, resolver) -> None:
    put(STAGE_SET_KEY, FIVE_STAGE)
    put("period.pn", 365)
    case = FakeCase(stage_key="PN", stage_entered_on=date(2024, 6, 1))
    assert stage_deadline(case, resolver=resolver) == date(2025, 6, 1)


def test_a_later_period_change_does_not_move_an_existing_deadline(put, resolver) -> None:
    """R7.8 and R28.6 together. A case that entered a stage under a 365-day period
    keeps its 365-day deadline after the period is shortened.

    Resolving as of today instead would silently rewrite every open case's deadline
    the moment an administrator changed a period — every one of them wrong, and
    nothing in the system would say so.
    """
    put(STAGE_SET_KEY, FIVE_STAGE)
    put("period.pn", 365, effective_from="2024-04-01")
    put("period.pn", 180, effective_from="2025-01-01")

    entered_before = FakeCase(stage_key="PN", stage_entered_on=date(2024, 6, 1))
    assert stage_deadline(entered_before, resolver=resolver) == date(2025, 6, 1)

    entered_after = FakeCase(stage_key="PN", stage_entered_on=date(2025, 2, 1))
    assert stage_deadline(entered_after, resolver=resolver) == date(2025, 7, 31)


def test_the_graph_is_pinned_at_stage_set_effective_from(put, resolver) -> None:
    """An in-flight case keeps the stage set it started under (§1.2).

    Here a state replaces its five-stage graph with a four-stage one that has no
    'PN'. A case already in PN must keep resolving against the old graph; resolving
    against the current one would raise StageNotInGraph for a case that is
    progressing perfectly normally.
    """
    put(STAGE_SET_KEY, FIVE_STAGE, effective_from="2024-04-01")
    put(STAGE_SET_KEY, FOUR_STAGE_TG, effective_from="2025-01-01")
    put("period.pn", 365)

    in_flight = FakeCase(
        stage_key="PN",
        stage_set_effective_from=date(2024, 4, 1),
        stage_entered_on=date(2024, 6, 1),
    )
    assert stage_deadline(in_flight, resolver=resolver) == date(2025, 6, 1)

    graph = resolve_stage_graph(in_flight, resolver=resolver)
    assert "PN" in graph.stages

    started_later = FakeCase(
        stage_key="NOTIF",
        stage_set_effective_from=date(2025, 1, 1),
        stage_entered_on=date(2025, 2, 1),
    )
    later_graph = resolve_stage_graph(started_later, resolver=resolver)
    assert "PN" not in later_graph.stages
    assert "NOTIF" in later_graph.stages


def test_the_two_dates_are_read_independently(put, resolver) -> None:
    """A case can be pinned to an old graph while its period comes from a newer row.

    This is the case a single-date implementation cannot express, and it is the
    normal one: graphs change rarely, periods change more often, and a case in
    flight is subject to the period in force when it entered its stage.
    """
    put(STAGE_SET_KEY, FIVE_STAGE, effective_from="2024-04-01")
    put("period.pn", 365, effective_from="2024-04-01")
    put("period.pn", 90, effective_from="2025-06-01")

    case = FakeCase(
        stage_key="PN",
        stage_set_effective_from=date(2024, 4, 1),
        stage_entered_on=date(2025, 7, 1),
    )
    assert stage_deadline(case, resolver=resolver) == date(2025, 9, 29)


# ---------------------------------------------------------------------------
# Terminal stages and missing configuration
# ---------------------------------------------------------------------------


def test_a_terminal_stage_has_no_deadline(put, resolver) -> None:
    """Not a missing value: a case at possession has nothing left to be late for."""
    put(STAGE_SET_KEY, FIVE_STAGE)
    case = FakeCase(stage_key="POSSESSION")
    assert stage_deadline(case, resolver=resolver) is None


def test_an_unconfigured_period_refuses_rather_than_defaulting(put, resolver) -> None:
    """Q8 is unconfirmed, so no period is seeded and this is the expected answer.

    The failure mode being avoided: a default of 30 or 90 days would produce a
    deadline that looks entirely reasonable and has no legal basis at all.
    """
    put(STAGE_SET_KEY, FIVE_STAGE)
    case = FakeCase(stage_key="PN")
    with pytest.raises(PolicyValueMissing) as exc:
        stage_deadline(case, resolver=resolver)
    assert exc.value.details["policy_key"] == "period.pn"


def test_an_unconfigured_stage_set_refuses(resolver) -> None:
    case = FakeCase()
    with pytest.raises(PolicyValueMissing) as exc:
        stage_deadline(case, resolver=resolver)
    assert exc.value.details["policy_key"] == STAGE_SET_KEY


# ---------------------------------------------------------------------------
# §4.4 — a second state needs no code change
# ---------------------------------------------------------------------------


def test_a_second_state_with_a_different_act_and_graph_needs_no_code(put, resolver) -> None:
    """The §4.4 claim, exercised. Nothing in the code knows 'NOTIF' or 'TG-LA-2017'."""
    put(STAGE_SET_KEY, FIVE_STAGE, state="IN-MH", act="RFCTLARR-2013")
    put("period.pn", 365, state="IN-MH", act="RFCTLARR-2013")
    put(STAGE_SET_KEY, FOUR_STAGE_TG, state="IN-TG", act="TG-LA-2017")
    put("period.tg.notif", 90, state="IN-TG", act="TG-LA-2017")

    mh = FakeCase(state_key="IN-MH", act_key="RFCTLARR-2013", stage_key="PN")
    tg = FakeCase(state_key="IN-TG", act_key="TG-LA-2017", stage_key="NOTIF")

    assert stage_deadline(mh, resolver=resolver) == date(2025, 6, 1)
    assert stage_deadline(tg, resolver=resolver) == date(2024, 8, 30)

    assert len(resolve_stage_graph(mh, resolver=resolver).stages) == 5
    assert len(resolve_stage_graph(tg, resolver=resolver).stages) == 4


def test_no_stage_enum_or_check_constraint_exists(db_connection: Connection) -> None:
    """R7.2 structurally: the stage vocabulary must not be in the schema.

    Asserted now, before acquisition_case exists (task 8.1), so the table cannot be
    created with an enum in the first place. Task 2.7 owns the general schema guard;
    this is the stage-specific half.
    """
    enums = db_connection.scalars(
        text(
            "SELECT typname FROM pg_type WHERE typtype = 'e' "
            "AND typname ILIKE '%stage%'"
        )
    ).all()
    assert not enums, f"a stage enum exists: {enums}. Stages are configuration."

    checks = db_connection.scalars(
        text(
            """
            SELECT conname FROM pg_constraint
            WHERE contype = 'c' AND pg_get_constraintdef(oid) ILIKE '%stage_key%'
            """
        )
    ).all()
    assert not checks, f"a CHECK constrains stage_key: {checks}"
