"""``policy_config`` storage and the R28.4 resolution query (§4.1).

The resolution rules interact, and the interactions are where a plausible
implementation goes wrong:

* a state override beats the platform default **for the same date**;
* but only if the override is already in force — a state row effective *after* the
  requested date must lose to the platform default, not win by being
  state-specific;
* and among eligible rows the latest effective_from wins.

The two-query implementation this design rejects gets the second bullet wrong and
looks correct in every test that does not include it.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import Connection, text

from app.services.policy import resolve_raw
from sqlalchemy.orm import Session

STATE = "IN-MH"
ACT = "RFCTLARR-2013"
KEY = "period.pn.to_declaration"


@pytest.fixture
def officer_id(db_connection: Connection) -> str:
    return db_connection.execute(
        text(
            """
            INSERT INTO officer (officer_code, display_name, credential_hash)
            VALUES ('test-officer', 'Test Officer', 'argon2-placeholder')
            RETURNING id
            """
        )
    ).scalar_one()


@pytest.fixture
def put(db_connection: Connection, officer_id: str):
    """Insert one policy version. Returns the row id."""

    def _put(
        key: str,
        value: str,
        *,
        state: str = STATE,
        act: str | None = ACT,
        effective_from: str = "2024-04-01",
        report_id: int | None = None,
    ) -> int:
        return db_connection.execute(
            text(
                """
                INSERT INTO policy_config
                    (policy_key, state_key, act_key, effective_from, value,
                     justification_report_id, created_by)
                VALUES
                    (:key, :state, :act, :ef, CAST(:value AS jsonb), :report, :officer)
                RETURNING id
                """
            ),
            {
                "key": key,
                "state": state,
                "act": act,
                "ef": effective_from,
                "value": value,
                "report": report_id,
                "officer": officer_id,
            },
        ).scalar_one()

    return _put


@pytest.fixture
def session(db_connection: Connection) -> Session:
    return Session(bind=db_connection, join_transaction_mode="create_savepoint")


def get(session: Session, key: str = KEY, *, as_of: str, state: str = STATE, act: str | None = ACT):
    return resolve_raw(
        session, key, state=state, act=act, as_of=date.fromisoformat(as_of)
    )


# ---------------------------------------------------------------------------
# R28.4 — the value effective on a date
# ---------------------------------------------------------------------------


def test_returns_the_value_in_force_on_the_date(put, session: Session) -> None:
    put(KEY, "365", effective_from="2024-04-01")
    assert get(session, as_of="2024-06-01") == 365


def test_a_row_not_yet_in_force_is_invisible(put, session: Session) -> None:
    put(KEY, "365", effective_from="2024-04-01")
    assert get(session, as_of="2024-03-31") is None


def test_latest_effective_row_at_or_before_the_date_wins(put, session: Session) -> None:
    put(KEY, "365", effective_from="2024-04-01")
    put(KEY, "180", effective_from="2025-04-01")
    assert get(session, as_of="2024-12-31") == 365, "read the future row"
    assert get(session, as_of="2025-04-01") == 180, "boundary is inclusive"
    assert get(session, as_of="2026-01-01") == 180


def test_missing_key_resolves_to_none(session: Session) -> None:
    """R28.5's refusal is built on this returning nothing, not on a default."""
    assert get(session, key="period.nonexistent", as_of="2024-06-01") is None


# ---------------------------------------------------------------------------
# State precedence — the part that breaks under a two-query implementation
# ---------------------------------------------------------------------------


def test_state_override_beats_platform_default_on_the_same_date(
    put, session: Session
) -> None:
    put(KEY, "365", state="*", effective_from="2024-04-01")
    put(KEY, "180", state=STATE, effective_from="2024-04-01")
    assert get(session, as_of="2024-06-01") == 180


def test_platform_default_applies_to_a_state_with_no_override(
    put, session: Session
) -> None:
    put(KEY, "365", state="*", effective_from="2024-04-01")
    assert get(session, as_of="2024-06-01", state="IN-KA") == 365


def test_a_state_override_not_yet_in_force_loses_to_the_platform_default(
    put, session: Session
) -> None:
    """The case a fallback implementation gets wrong.

    "Read the state row, and if there is none read the platform row" returns the
    platform value here too — by accident, because its state query found nothing.
    But change the dates so the state row *is* in force and the same code returns
    the state value; the two paths only agree when the fallback never triggers.
    The single ORDER BY is right in both directions for the same reason.
    """
    put(KEY, "365", state="*", effective_from="2024-04-01")
    put(KEY, "180", state=STATE, effective_from="2025-04-01")
    assert get(session, as_of="2024-06-01") == 365, "future state row must not win"
    assert get(session, as_of="2025-06-01") == 180, "state row wins once in force"


def test_an_older_state_override_still_beats_a_newer_platform_default(
    put, session: Session
) -> None:
    """State precedence is stronger than recency, which is what §4.1's sort order
    says: state first, then date. A state that has set its own period does not
    silently lose it because the platform default was revised later."""
    put(KEY, "180", state=STATE, effective_from="2024-04-01")
    put(KEY, "365", state="*", effective_from="2025-04-01")
    assert get(session, as_of="2026-01-01") == 180


# ---------------------------------------------------------------------------
# act_key
# ---------------------------------------------------------------------------


def test_act_specific_and_act_null_values_do_not_collide(put, session: Session) -> None:
    put("retention.period.OWNER_CONTACT", "1095", act=None)
    put(KEY, "365", act=ACT)
    assert get(session, key="retention.period.OWNER_CONTACT", as_of="2024-06-01", act=None) == 1095
    assert get(session, as_of="2024-06-01", act=ACT) == 365


def test_a_value_is_not_visible_under_a_different_act(put, session: Session) -> None:
    put(KEY, "365", act=ACT)
    assert get(session, as_of="2024-06-01", act="TG-LA-2017") is None


# ---------------------------------------------------------------------------
# Uniqueness and R28.9
# ---------------------------------------------------------------------------


def test_two_versions_of_one_key_on_the_same_date_are_refused(
    put, session: Session
) -> None:
    put(KEY, "365", effective_from="2024-04-01")
    with pytest.raises(Exception, match="policy_config_unique_version"):
        put(KEY, "180", effective_from="2024-04-01")


def test_null_act_does_not_escape_uniqueness(put) -> None:
    """The reason uniqueness keys on coalesce(act_key, '').

    NULL is not equal to NULL, so a plain unique constraint over act_key would
    accept both of these — and the resolve query would then return whichever the
    planner happened to reach first, which is a value that changes between runs.
    """
    put("retention.period.OWNER_CONTACT", "1095", act=None)
    with pytest.raises(Exception, match="policy_config_unique_version"):
        put("retention.period.OWNER_CONTACT", "2190", act=None)


def test_ocr_threshold_without_a_report_reference_is_refused(put) -> None:
    """R28.9: a threshold change must cite the report stating its precision."""
    with pytest.raises(Exception, match="ocr_threshold_requires_report"):
        put("ocr.threshold.auto_accept", "0.95")


def test_a_non_ocr_key_needs_no_report_reference(put, session: Session) -> None:
    put(KEY, "365")
    assert get(session, as_of="2024-06-01") == 365


def test_policy_rows_require_an_author(db_connection: Connection) -> None:
    """R28.3 records who changed a statutory value; a row with no author would
    leave a period change unattributable."""
    with pytest.raises(Exception, match="null value in column .created_by."):
        db_connection.execute(
            text(
                """
                INSERT INTO policy_config
                    (policy_key, state_key, act_key, effective_from, value, created_by)
                VALUES ('x', '*', NULL, '2024-04-01', '1'::jsonb, NULL)
                """
            )
        )


# ---------------------------------------------------------------------------
# jsonb value shapes
# ---------------------------------------------------------------------------


def test_value_holds_more_than_a_number(put, session: Session) -> None:
    """One jsonb column carries a day count, a weight map and the stage graph.

    A typed column per shape would make every new kind of policy value a
    migration, which is the thing §4.4 exists to avoid.
    """
    put("priority.weights", '{"risk": 0.5, "deadline": 0.3, "value": 0.2}')
    put(
        "policy.stage_set",
        '{"stages": [{"key": "SIA", "successors": ["PN"], "terminal": false},'
        ' {"key": "PN", "successors": [], "terminal": true}]}',
    )
    weights = get(session, key="priority.weights", as_of="2024-06-01")
    assert weights == {"risk": 0.5, "deadline": 0.3, "value": 0.2}
    graph = get(session, key="policy.stage_set", as_of="2024-06-01")
    assert [s["key"] for s in graph["stages"]] == ["SIA", "PN"]


def test_resolution_uses_the_resolve_index(db_connection: Connection, put) -> None:
    put(KEY, "365")
    db_connection.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        db_connection.scalars(
            text(
                """
                EXPLAIN SELECT value FROM policy_config
                 WHERE policy_key = 'period.pn.to_declaration'
                   AND state_key IN ('IN-MH', '*')
                   AND coalesce(act_key, '') = 'RFCTLARR-2013'
                   AND effective_from <= '2024-06-01'
                 ORDER BY (state_key = 'IN-MH') DESC, effective_from DESC
                 LIMIT 1
                """
            )
        )
    )
    assert "policy_config_resolve" in plan or "policy_config_unique_version" in plan, plan
