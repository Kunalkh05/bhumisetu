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
    assert len(events) >= 50_000
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


def test_default_generator_has_non_degenerate_label_outcomes() -> None:
    synthetic = _synthetic()

    timelines = synthetic.generate_district(seed=23)
    outcomes = [timeline.label.outcome for timeline in timelines]

    assert outcomes.count("DELAYED") >= 1_000
    assert outcomes.count("NOT_DELAYED") >= 1_000
    assert outcomes.count("CENSORED") >= 500
    assert outcomes.count("DELAYED") + outcomes.count("NOT_DELAYED") >= 8_000
    assert {timeline.district_code for timeline in timelines} == {synthetic.SYNTHETIC_DISTRICT}


def test_case_material_spans_shapes_needed_for_training_and_validation() -> None:
    synthetic = _synthetic()

    timelines = synthetic.generate_district(case_count=600, seed=29)
    parcels = [parcel for timeline in timelines for parcel in timeline.parcels]
    ownership = [row for timeline in timelines for row in timeline.ownership_records]
    awards = [award for timeline in timelines for award in timeline.awards]
    documents = [doc for timeline in timelines for doc in timeline.document_extractions]

    assert parcels
    assert ownership
    assert awards
    assert documents
    assert all(parcel.geom["type"] == "Polygon" for parcel in parcels)

    share_sums: dict[int, float] = {}
    for row in ownership:
        share_sums[row.parcel_id] = share_sums.get(row.parcel_id, 0.0) + row.share
    assert any(abs(total - 1.0) <= synthetic.SHARE_TOLERANCE for total in share_sums.values())
    assert any(abs(total - 1.0) > synthetic.SHARE_TOLERANCE for total in share_sums.values())

    assert any(award.component_sum_consistent for award in awards)
    assert any(not award.component_sum_consistent for award in awards)
    assert min(doc.confidence for doc in documents) < 0.20
    assert max(doc.confidence for doc in documents) > 0.80


def test_case_jsonl_writer_emits_training_ready_case_rows(tmp_path: Path) -> None:
    synthetic = _synthetic()
    out = tmp_path / "synthetic-cases.jsonl"
    timelines = synthetic.generate_district(case_count=4, seed=31)

    written = synthetic.write_case_jsonl(timelines, out)
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]

    assert written == 4
    assert len(rows) == 4
    assert {"events", "parcels", "ownership_records", "awards", "document_extractions", "label"}.issubset(rows[0])
