"""Fixture policy configuration for synthetic data (task 21.3).

These rows are seed artifacts consumed by synthetic replay/training tests. They
are not Alembic migrations and are not product-code defaults.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

PLATFORM_WIDE = "*"
SYNTHETIC_STATE = "SYNTH-MH"
SYNTHETIC_ACT = "RFCTLARR_2013"
DPDP_ACT = "DPDP_2023"
EFFECTIVE_FROM = date(2021, 1, 1)

RFCTLARR_BASELINE_PERIODS = {
    "period.sia_completion": 180,
    "period.expert_group_appraisal": 60,
    "period.preliminary_notification_after_sia": 365,
    "period.objection_window": 60,
    "period.declaration_after_preliminary_notification": 365,
    "period.award_after_declaration": 365,
    "period.statutory_notice_response": 60,
    "period.objection_disposal_target": 60,
}

SYNTHETIC_RETENTION_PERIODS = {
    "retention.period.OWNER_CONTACT": 1095,
    "retention.period.OWNER_IDENTITY": 2920,
    "retention.period.MODEL_FEATURE": 1825,
    "retention.period.LAND_RECORD": None,
    "retention.period.DOCUMENT_CONTENT": None,
    "retention.period.AUDIT_EVENT": None,
}


@dataclass(frozen=True)
class PolicyFixtureRow:
    policy_key: str
    state_key: str
    act_key: str | None
    effective_from: date
    value: Any
    review_required: bool
    comment: str
    justification_report_id: int | None = None


def synthetic_stage_set() -> dict[str, object]:
    return {
        "initial": "intake",
        "stages": [
            {
                "key": "intake",
                "label_key": "stage.intake",
                "successors": ["preliminary_notice"],
                "period_key": "period.sia_completion",
                "terminal": False,
            },
            {
                "key": "preliminary_notice",
                "label_key": "stage.preliminary_notice",
                "successors": ["objection_window"],
                "period_key": "period.objection_window",
                "terminal": False,
            },
            {
                "key": "objection_window",
                "label_key": "stage.objection_window",
                "successors": ["award_draft"],
                "period_key": "period.declaration_after_preliminary_notification",
                "terminal": False,
            },
            {
                "key": "award_draft",
                "label_key": "stage.award_draft",
                "successors": ["award_final"],
                "period_key": "period.award_after_declaration",
                "terminal": False,
            },
            {
                "key": "award_final",
                "label_key": "stage.award_final",
                "successors": ["closed"],
                "period_key": "period.statutory_notice_response",
                "terminal": False,
            },
            {
                "key": "closed",
                "label_key": "stage.closed",
                "successors": [],
                "period_key": None,
                "terminal": True,
            },
        ],
    }


def label_definition() -> dict[str, object]:
    return {
        "version": "synthetic-delay-v1",
        "formulation": "binary_delay",
        "stage_transitions_in_scope": [["intake", "closed"]],
        "deadline_baseline": "configured_stage_deadline",
        "baseline_fallback": "censor",
        "horizon_days": 210,
        "censoring": "exclude_from_train_eval",
    }


def synthetic_state_fixture_rows() -> tuple[PolicyFixtureRow, ...]:
    rows = [
        PolicyFixtureRow(
            "policy.stage_set",
            SYNTHETIC_STATE,
            SYNTHETIC_ACT,
            EFFECTIVE_FROM,
            synthetic_stage_set(),
            False,
            "Synthetic state stage graph for replay and training fixtures.",
        ),
        PolicyFixtureRow(
            "risk.band_cutoffs",
            SYNTHETIC_STATE,
            SYNTHETIC_ACT,
            EFFECTIVE_FROM,
            {"LOW": 0.25, "MEDIUM": 0.50, "HIGH": 0.75, "CRITICAL": 1.0},
            False,
            "Synthetic risk-band cutoffs.",
        ),
        PolicyFixtureRow(
            "priority.weights",
            SYNTHETIC_STATE,
            SYNTHETIC_ACT,
            EFFECTIVE_FROM,
            {"risk": 0.45, "deadline": 0.30, "value": 0.15, "issue": 0.10},
            False,
            "Synthetic priority weights.",
        ),
        PolicyFixtureRow(
            "model.promotion_thresholds",
            SYNTHETIC_STATE,
            SYNTHETIC_ACT,
            EFFECTIVE_FROM,
            {"min_auprc": 0.45, "max_brier": 0.20, "max_ece": 0.08},
            False,
            "Synthetic model promotion thresholds.",
        ),
        PolicyFixtureRow(
            "model.monitoring_thresholds",
            SYNTHETIC_STATE,
            SYNTHETIC_ACT,
            EFFECTIVE_FROM,
            {"max_ece": 0.10, "max_psi": 0.20, "min_rows": 500},
            False,
            "Synthetic monitoring thresholds.",
        ),
        PolicyFixtureRow(
            "ml.label_definition",
            SYNTHETIC_STATE,
            SYNTHETIC_ACT,
            EFFECTIVE_FROM,
            label_definition(),
            False,
            "Synthetic delay label definition.",
        ),
        PolicyFixtureRow(
            "citizen.timeline.visible_events",
            SYNTHETIC_STATE,
            SYNTHETIC_ACT,
            EFFECTIVE_FROM,
            ["CASE_CREATED", "STAGE_ENTERED", "OBJECTION_RECEIVED", "CASE_TERMINAL"],
            False,
            "Synthetic citizen-visible event set.",
        ),
        PolicyFixtureRow(
            "retention.sweep_enabled",
            SYNTHETIC_STATE,
            DPDP_ACT,
            EFFECTIVE_FROM,
            False,
            False,
            "Synthetic retention sweep remains disabled unless a test enables it.",
        ),
    ]
    for key, days in RFCTLARR_BASELINE_PERIODS.items():
        rows.append(
            PolicyFixtureRow(
                key,
                SYNTHETIC_STATE,
                SYNTHETIC_ACT,
                EFFECTIVE_FROM,
                days,
                False,
                "Synthetic state statutory period fixture.",
            )
        )
    for key, days in SYNTHETIC_RETENTION_PERIODS.items():
        rows.append(
            PolicyFixtureRow(
                key,
                SYNTHETIC_STATE,
                DPDP_ACT,
                EFFECTIVE_FROM,
                days,
                False,
                "Synthetic-state-only DPDP retention fixture.",
            )
        )
    for key, value in {
        "ocr.threshold.review": 0.60,
        "ocr.threshold.auto_accept": 0.92,
        "ocr.threshold.manual_entry": 0.35,
    }.items():
        rows.append(
            PolicyFixtureRow(
                key,
                SYNTHETIC_STATE,
                SYNTHETIC_ACT,
                EFFECTIVE_FROM,
                value,
                False,
                "Synthetic OCR threshold tied to the synthetic accuracy report.",
                justification_report_id=1,
            )
        )
    return tuple(rows)


def platform_baseline_rows() -> tuple[PolicyFixtureRow, ...]:
    return tuple(
        PolicyFixtureRow(
            key,
            PLATFORM_WIDE,
            SYNTHETIC_ACT,
            EFFECTIVE_FROM,
            days,
            True,
            "# review-required before production use",
        )
        for key, days in RFCTLARR_BASELINE_PERIODS.items()
    )


def all_policy_fixture_rows() -> tuple[PolicyFixtureRow, ...]:
    return (*platform_baseline_rows(), *synthetic_state_fixture_rows())


def _json_ready(row: PolicyFixtureRow) -> dict[str, object]:
    data = asdict(row)
    data["effective_from"] = row.effective_from.isoformat()
    return data


def write_jsonl(rows: Iterable[PolicyFixtureRow], path: Path) -> int:
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_json_ready(row), sort_keys=True) + "\n")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("synthetic-policy-config.jsonl"))
    args = parser.parse_args()
    rows = all_policy_fixture_rows()
    count = write_jsonl(rows, args.out)
    print(json.dumps({"rows": count, "out": str(args.out)}))


if __name__ == "__main__":
    main()
