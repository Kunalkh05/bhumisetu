from __future__ import annotations

import inspect
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
    DeadlineBaseline,
    LabelDefinition,
    label_row,
    resolve_deadline,
)

T = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)


class _Resolver:
    def __init__(self, values: dict[str, int]) -> None:
        self.values = values
        self.calls: list[tuple[str, str, str | None, date]] = []

    def get(self, key: str, *, state: str, act: str | None, as_of: date) -> int:
        self.calls.append((key, state, act, as_of))
        return self.values[key]


def _definition(**overrides) -> LabelDefinition:
    values = {
        "version": "delay-v1",
        "formulation": "BINARY_STAGE_EXIT",
        "stage_transitions_in_scope": ("PN->DECLARATION",),
        "deadline_baseline": DeadlineBaseline(
            kind="STATUTORY_PERIOD",
            period_key="period.pn.to_declaration",
        ),
        "baseline_fallback": None,
        "horizon_days": 60,
        "censoring": "EXCLUDE",
    }
    values.update(overrides)
    return LabelDefinition(**values)


def _view(*, exit_at: datetime | None = None) -> AsOfView:
    stages = [StageEntry(1, "PN", datetime(2026, 1, 1, 9, tzinfo=timezone.utc))]
    if exit_at is not None:
        stages.append(StageEntry(2, "DECLARATION", exit_at))
    return AsOfView(
        case_id=42,
        t=T,
        mode=AsOfMode.OCCURRED_BY,
        stage_history=tuple(stages),
        notices=(),
        objections=(),
        parcels=(),
        awards=(),
        issues=(),
        documents=(),
        consumed_event_ids=tuple(entry.event_id for entry in stages),
    )


def test_label_row_is_pure_by_signature() -> None:
    signature = inspect.signature(label_row)

    rendered = str(signature)
    assert "session" not in rendered.lower()
    assert "resolver" not in rendered.lower()
    assert "now" in signature.parameters
    assert "deadline" in signature.parameters


def test_label_row_returns_not_delayed_with_survival_ready_fields() -> None:
    outcome = label_row(
        _view(exit_at=datetime(2026, 2, 1, 9, tzinfo=timezone.utc)),
        T,
        definition=_definition(),
        deadline=date(2026, 2, 5),
        now=date(2026, 4, 1),
    )

    assert outcome.label == "NOT_DELAYED"
    assert outcome.time_to_event_days == 17
    assert outcome.event_observed is True
    assert outcome.reason == "EXITED_BY_DEADLINE"
    assert outcome.label_definition_version == "delay-v1"


def test_label_row_marks_missing_or_late_exit_as_delayed() -> None:
    late = label_row(
        _view(exit_at=datetime(2026, 2, 10, 9, tzinfo=timezone.utc)),
        T,
        definition=_definition(),
        deadline=date(2026, 2, 5),
        now=date(2026, 4, 1),
    )
    missing = label_row(
        _view(),
        T,
        definition=_definition(),
        deadline=date(2026, 2, 5),
        now=date(2026, 4, 1),
    )

    assert late.label == "DELAYED"
    assert late.time_to_event_days == 26
    assert late.event_observed is True
    assert missing.label == "DELAYED"
    assert missing.time_to_event_days is None
    assert missing.event_observed is False


@pytest.mark.parametrize(
    ("deadline", "now", "reason"),
    [
        (date(2026, 2, 5), date(2026, 2, 1), "HORIZON_NOT_ELAPSED"),
        (date(2026, 4, 1), date(2026, 4, 1), "DEADLINE_BEYOND_HORIZON"),
        (None, date(2026, 4, 1), "DEADLINE_BEYOND_HORIZON"),
    ],
)
def test_label_row_censors_when_the_horizon_or_deadline_prevents_labelling(
    deadline: date | None,
    now: date,
    reason: str,
) -> None:
    outcome = label_row(
        _view(),
        T,
        definition=_definition(),
        deadline=deadline,
        now=now,
    )

    assert outcome.label == "CENSORED"
    assert outcome.event_observed is False
    assert outcome.reason == reason


def test_resolve_deadline_uses_baseline_configuration_outside_label_row() -> None:
    resolver = _Resolver({"period.pn.to_declaration": 35})

    deadline = resolve_deadline(
        _view(),
        definition=_definition(),
        resolver=resolver,
        state="IN-MH",
        act="RFCTLARR-2013",
        as_of=date(2026, 1, 15),
    )

    assert deadline == date(2026, 2, 5)
    assert resolver.calls == [
        ("period.pn.to_declaration", "IN-MH", "RFCTLARR-2013", date(2026, 1, 15))
    ]


def test_definition_refuses_missing_q1_knobs() -> None:
    with pytest.raises(ValueError, match="version"):
        _definition(version="")
    with pytest.raises(ValueError, match="horizon_days"):
        _definition(horizon_days=0)
    with pytest.raises(ValueError, match="period_key"):
        DeadlineBaseline(kind="STATUTORY_PERIOD")
