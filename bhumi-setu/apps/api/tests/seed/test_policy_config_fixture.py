"""Fixture policy configuration tests (task 21.3)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def _policy_fixture() -> ModuleType:
    root = Path(__file__).resolve().parents[4]
    path = root / "scripts" / "seed" / "policy_config.py"
    spec = importlib.util.spec_from_file_location("policy_config_seed", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fixture_contains_synthetic_state_configuration_surface() -> None:
    fixture = _policy_fixture()

    rows = fixture.synthetic_state_fixture_rows()
    keys = {row.policy_key for row in rows}

    assert "policy.stage_set" in keys
    assert "ml.label_definition" in keys
    assert "citizen.timeline.visible_events" in keys
    assert "risk.band_cutoffs" in keys
    assert "priority.weights" in keys
    assert "model.promotion_thresholds" in keys
    assert "model.monitoring_thresholds" in keys
    assert {"ocr.threshold.review", "ocr.threshold.auto_accept", "ocr.threshold.manual_entry"}.issubset(keys)


def test_platform_baseline_has_only_review_required_rfctlarr_periods() -> None:
    fixture = _policy_fixture()

    rows = fixture.platform_baseline_rows()

    assert rows
    assert all(row.state_key == fixture.PLATFORM_WIDE for row in rows)
    assert all(row.act_key == fixture.SYNTHETIC_ACT for row in rows)
    assert all(row.policy_key.startswith("period.") for row in rows)
    assert all(row.review_required for row in rows)
    assert all("review-required" in row.comment for row in rows)


def test_no_retention_period_is_seeded_platform_wide() -> None:
    fixture = _policy_fixture()

    platform_rows = fixture.platform_baseline_rows()
    synthetic_rows = fixture.synthetic_state_fixture_rows()

    assert not any(row.policy_key.startswith("retention.period.") for row in platform_rows)
    retention_rows = [row for row in synthetic_rows if row.policy_key.startswith("retention.period.")]
    assert retention_rows
    assert all(row.state_key == fixture.SYNTHETIC_STATE for row in retention_rows)
    assert all(row.act_key == fixture.DPDP_ACT for row in retention_rows)


def test_retention_sweep_ships_disabled_even_in_fixture() -> None:
    fixture = _policy_fixture()

    [sweep] = [
        row
        for row in fixture.synthetic_state_fixture_rows()
        if row.policy_key == "retention.sweep_enabled"
    ]

    assert sweep.value is False
    assert sweep.state_key == fixture.SYNTHETIC_STATE
    assert sweep.act_key == fixture.DPDP_ACT


def test_ocr_threshold_fixture_rows_carry_a_report_reference() -> None:
    fixture = _policy_fixture()

    thresholds = [
        row
        for row in fixture.synthetic_state_fixture_rows()
        if row.policy_key.startswith("ocr.threshold.")
    ]

    assert thresholds
    assert all(row.justification_report_id == 1 for row in thresholds)


def test_policy_fixture_jsonl_writer(tmp_path: Path) -> None:
    fixture = _policy_fixture()
    out = tmp_path / "policy.jsonl"
    rows = fixture.all_policy_fixture_rows()

    written = fixture.write_jsonl(rows, out)
    decoded = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]

    assert written == len(rows)
    assert decoded
    assert all("effective_from" in row for row in decoded)
    assert all("policy_key" in row for row in decoded)
