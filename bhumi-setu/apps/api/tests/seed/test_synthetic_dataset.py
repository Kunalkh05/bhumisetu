"""Synthetic dataset timeline tests (task 21.1)."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import timedelta
from pathlib import Path
from types import ModuleType


def _synthetic() -> ModuleType:
    root = Path(__file__).resolve().parents[4]
    path = root / "scripts" / "seed" / "synthetic.py"
    spec = importlib.util.spec_from_file_location("synthetic_seed", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_default_generator_produces_a_10000_case_district() -> None:
    synthetic = _synthetic()

    timelines = synthetic.generate_district(seed=7)
    events = tuple(synthetic.iter_events(timelines))

    assert len(timelines) == 10_000
    assert len(events) >= 60_000
    assert {timeline.case_id for timeline in timelines} == set(range(1, 10_001))
    assert all(timeline.events for timeline in timelines)


def test_recording_lag_distribution_includes_on_time_and_late_records() -> None:
    synthetic = _synthetic()

    timelines = synthetic.generate_district(case_count=400, seed=11)
    lags = [
        (event.recording_time - event.occurrence_time).days
        for event in synthetic.iter_events(timelines)
    ]

    assert min(lags) >= 0
    assert any(lag <= 3 for lag in lags)
    assert any(4 <= lag <= 14 for lag in lags)
    assert any(lag >= 15 for lag in lags)


def test_backdated_events_make_occurred_by_and_knowable_at_distinguishable() -> None:
    synthetic = _synthetic()

    timelines = synthetic.generate_district(case_count=200, seed=13, backdated_fraction=0.35)
    backdated = [
        event
        for event in synthetic.iter_events(timelines)
        if event.backdated
    ]
    assert backdated

    event = backdated[0]
    timeline = timelines[event.case_id - 1]
    as_of = event.occurrence_time + timedelta(hours=1)

    occurred_ids = {row.id for row in synthetic.occurred_by(timeline.events, as_of)}
    knowable_ids = {row.id for row in synthetic.knowable_at(timeline.events, as_of)}

    assert event.id in occurred_ids
    assert event.id not in knowable_ids
    assert occurred_ids != knowable_ids


def test_jsonl_writer_preserves_append_order_and_two_timestamps(tmp_path: Path) -> None:
    synthetic = _synthetic()
    out = tmp_path / "synthetic-events.jsonl"
    timelines = synthetic.generate_district(case_count=3, seed=19, backdated_fraction=1.0)

    written = synthetic.write_jsonl(timelines, out)
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]

    assert written == len(rows)
    assert rows
    assert rows == sorted(rows, key=lambda row: (row["case_id"], row["recording_time"], row["id"]))
    assert all(row["occurrence_time"] <= row["recording_time"] for row in rows)
