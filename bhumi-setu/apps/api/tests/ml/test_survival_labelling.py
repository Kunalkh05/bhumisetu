from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.db.event_log import AsOfMode

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.asof import AsOfView, StageEntry  # noqa: E402
from labelling.definition import (  # noqa: E402
    STATUTORY_WINDOW_DAYS_SEC11_TO_SEC19,
    STATUTORY_WINDOW_DAYS_SEC19_TO_AWARD,
    TRANSITION_CASE_INITIATION_TO_MILESTONE,
    TRANSITION_SECTION_11_TO_SECTION_19,
    TRANSITION_SECTION_19_TO_AWARD,
    LabelOutcome,
    label_row,
    survival_definition,
)


def _make_view(
    stages: list[tuple[int, str, datetime]],
    *,
    case_id: int = 101,
    t: datetime | None = None,
) -> AsOfView:
    stage_entries = tuple(
        StageEntry(event_id=ev_id, stage_key=k, occurrence_time=occ)
        for ev_id, k, occ in stages
    )
    ref_t = t or (stage_entries[-1].occurrence_time if stage_entries else datetime(2026, 1, 1, tzinfo=timezone.utc))
    return AsOfView(
        case_id=case_id,
        t=ref_t,
        mode=AsOfMode.OCCURRED_BY,
        stage_history=stage_entries,
        notices=(),
        objections=(),
        parcels=(),
        awards=(),
        issues=(),
        documents=(),
        consumed_event_ids=tuple(s.event_id for s in stage_entries),
    )


# 1. Event occurs before cutoff: T > 0, E = 1
def test_event_occurs_before_cutoff() -> None:
    entry_dt = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    exit_dt = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)
    cutoff = date(2026, 5, 1)

    view = _make_view([
        (1, "SECTION_11", entry_dt),
        (2, "SECTION_19", exit_dt),
    ])
    defn = survival_definition(TRANSITION_SECTION_11_TO_SECTION_19)

    outcome = label_row(
        view,
        entry_dt,
        definition=defn,
        deadline=date(2026, 12, 31),
        now=cutoff,
    )

    assert outcome.event_observed is True
    assert outcome.time_to_event_days == 59  # Jan 1 to March 1 (non-leap: 31 + 28 = 59)
    assert outcome.time_to_event_days > 0
    assert outcome.label == "NOT_DELAYED"
    assert outcome.reason == "EXITED_BY_DEADLINE"


# 2. Event occurs exactly at entry: T = 0, E = 1
def test_event_occurs_exactly_at_entry() -> None:
    entry_dt = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    exit_dt = datetime(2026, 1, 1, 14, tzinfo=timezone.utc)  # Same calendar date
    cutoff = date(2026, 5, 1)

    view = _make_view([
        (1, "SECTION_11", entry_dt),
        (2, "SECTION_19", exit_dt),
    ])
    defn = survival_definition(TRANSITION_SECTION_11_TO_SECTION_19)

    outcome = label_row(
        view,
        entry_dt,
        definition=defn,
        deadline=date(2026, 12, 31),
        now=cutoff,
    )

    assert outcome.event_observed is True
    assert outcome.time_to_event_days == 0
    assert outcome.label == "NOT_DELAYED"
    assert outcome.reason == "EXITED_BY_DEADLINE"


# 3. No event before cutoff: T > 0, E = 0 (RIGHT-CENSORED)
def test_no_event_before_cutoff() -> None:
    entry_dt = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    cutoff = date(2026, 5, 1)

    view = _make_view([
        (1, "SECTION_11", entry_dt),
    ])
    defn = survival_definition(TRANSITION_SECTION_11_TO_SECTION_19)

    outcome = label_row(
        view,
        entry_dt,
        definition=defn,
        deadline=date(2026, 12, 31),
        now=cutoff,
    )

    assert outcome.event_observed is False
    assert outcome.time_to_event_days == 120  # Jan 1 to May 1 (31+28+31+30 = 120)
    assert outcome.time_to_event_days > 0
    assert outcome.label == "CENSORED"
    assert outcome.reason == "RIGHT_CENSORED"


# 4. Censored case retains duration (NOT None)
def test_censored_case_retains_duration() -> None:
    entry_dt = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    cutoff = date(2026, 7, 1)

    view = _make_view([
        (1, "SECTION_11", entry_dt),
    ])
    defn = survival_definition(TRANSITION_SECTION_11_TO_SECTION_19)

    outcome = label_row(
        view,
        entry_dt,
        definition=defn,
        deadline=date(2026, 12, 31),
        now=cutoff,
    )

    assert outcome.time_to_event_days is not None
    assert outcome.time_to_event_days == 181
    assert outcome.event_observed is False
    assert outcome.label == "CENSORED"


# 5. Future event after cutoff does not become an observed event
def test_future_event_after_cutoff_does_not_become_observed_event() -> None:
    entry_dt = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    future_exit_dt = datetime(2026, 8, 1, 10, tzinfo=timezone.utc)
    cutoff = date(2026, 5, 1)  # Cutoff is BEFORE the future exit

    view = _make_view([
        (1, "SECTION_11", entry_dt),
        (2, "SECTION_19", future_exit_dt),
    ])
    defn = survival_definition(TRANSITION_SECTION_11_TO_SECTION_19)

    outcome = label_row(
        view,
        entry_dt,
        definition=defn,
        deadline=date(2026, 12, 31),
        now=cutoff,
    )

    # Must be right-censored at cutoff date, NOT an observed event
    assert outcome.event_observed is False
    assert outcome.time_to_event_days == 120
    assert outcome.label == "CENSORED"
    assert outcome.reason == "RIGHT_CENSORED"


# 6. Missing entry date is rejected
def test_missing_entry_date_is_rejected() -> None:
    view = _make_view([])  # Empty stage history
    defn = survival_definition(TRANSITION_SECTION_11_TO_SECTION_19)

    with pytest.raises(ValueError, match="Missing stage entry date"):
        label_row(
            view,
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            definition=defn,
            deadline=None,
            now=date(2026, 5, 1),
        )


# 7. Event date before entry date is rejected
def test_event_date_before_entry_date_is_rejected() -> None:
    entry_dt = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)
    contradictory_exit_dt = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)

    view = _make_view([
        (1, "SECTION_11", entry_dt),
        (2, "SECTION_19", contradictory_exit_dt),
    ])
    defn = survival_definition(TRANSITION_SECTION_11_TO_SECTION_19)

    with pytest.raises(ValueError, match="cannot precede entry date"):
        label_row(
            view,
            entry_dt,
            definition=defn,
            deadline=None,
            now=date(2026, 5, 1),
        )


# 8. Negative durations are impossible (cutoff precedes entry)
def test_negative_durations_are_impossible() -> None:
    entry_dt = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)
    cutoff = date(2026, 1, 1)  # Cutoff before entry!

    view = _make_view([
        (1, "SECTION_11", entry_dt),
    ])
    defn = survival_definition(TRANSITION_SECTION_11_TO_SECTION_19)

    with pytest.raises(ValueError, match="cannot precede stage entry date"):
        label_row(
            view,
            entry_dt,
            definition=defn,
            deadline=None,
            now=cutoff,
        )


# 9. SECTION_19_TO_AWARD transition (observed and right-censored)
def test_section_19_to_award_transition() -> None:
    s11_dt = datetime(2025, 3, 1, 10, tzinfo=timezone.utc)
    s19_dt = datetime(2025, 8, 1, 10, tzinfo=timezone.utc)
    award_dt = datetime(2026, 4, 1, 10, tzinfo=timezone.utc)
    cutoff = date(2026, 6, 1)

    # Case A: Observed Award
    view_observed = _make_view([
        (1, "SECTION_11", s11_dt),
        (2, "SECTION_19", s19_dt),
        (3, "AWARD", award_dt),
    ])
    defn = survival_definition(TRANSITION_SECTION_19_TO_AWARD)

    outcome_obs = label_row(
        view_observed,
        s19_dt,
        definition=defn,
        deadline=date(2026, 8, 1),
        now=cutoff,
    )
    assert outcome_obs.event_observed is True
    assert outcome_obs.time_to_event_days == 243  # Aug 1, 2025 to April 1, 2026
    assert outcome_obs.label == "NOT_DELAYED"

    # Case B: Ongoing / Right-Censored Award
    view_censored = _make_view([
        (1, "SECTION_11", s11_dt),
        (2, "SECTION_19", s19_dt),
    ])
    outcome_cens = label_row(
        view_censored,
        s19_dt,
        definition=defn,
        deadline=date(2026, 8, 1),
        now=cutoff,
    )
    assert outcome_cens.event_observed is False
    assert outcome_cens.time_to_event_days == 304  # Aug 1, 2025 to June 1, 2026
    assert outcome_cens.label == "CENSORED"
    assert outcome_cens.reason == "RIGHT_CENSORED"


# 10. CASE_INITIATION_TO_MILESTONE transition
def test_case_initiation_to_milestone() -> None:
    init_dt = datetime(2025, 1, 10, 10, tzinfo=timezone.utc)
    s19_dt = datetime(2025, 9, 15, 10, tzinfo=timezone.utc)
    cutoff = date(2026, 1, 1)

    view = _make_view([
        (1, "GENERAL_NOTICE", init_dt),
        (2, "SECTION_19", s19_dt),
    ])
    defn = survival_definition(TRANSITION_CASE_INITIATION_TO_MILESTONE)

    outcome = label_row(
        view,
        init_dt,
        definition=defn,
        deadline=None,
        now=cutoff,
    )
    assert outcome.event_observed is True
    assert outcome.time_to_event_days == 248  # Jan 10, 2025 to Sep 15, 2025
    assert outcome.label == "NOT_DELAYED"


# 11. Cross-compatibility: Synthetic aliases (PN -> DECLARATION)
def test_synthetic_aliases_work_with_survival_definition() -> None:
    entry_dt = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    exit_dt = datetime(2026, 2, 1, 10, tzinfo=timezone.utc)
    cutoff = date(2026, 4, 1)

    # Uses synthetic keys PN and DECLARATION
    view = _make_view([
        (1, "PN", entry_dt),
        (2, "DECLARATION", exit_dt),
    ])
    defn = survival_definition("PN->DECLARATION")

    outcome = label_row(
        view,
        entry_dt,
        definition=defn,
        deadline=date(2026, 2, 5),
        now=cutoff,
    )
    assert outcome.event_observed is True
    assert outcome.time_to_event_days == 31  # 2026-02-01 - 2026-01-01
    assert outcome.label == "NOT_DELAYED"
