"""Deterministic, leakage-safe temporal and case-aware cohort split for survival models (LOOP 6).

Implements the Case-Level Temporal Inception Cohort Split strategy:
1. Calculates case_entry_date = min(snapshot_date) for every unique acquisition case.
2. Orders cases chronologically by case_entry_date.
3. Partitions cases using a deterministic calendar cutoff date (default: '2026-05-01').
4. Enforces strict case-level disjointness:
   - train_case_ids ∩ eval_case_ids = ∅
   - max(train case_entry_date) < min(eval case_entry_date)
5. Partitions all snapshots and transitions strictly based on case cohort membership.
6. Retains all right-censored observations (event_observed=False) without modification.
7. Generates perfectly aligned train/eval feature and target artifacts with identical keys.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from features.survival_features import (
    IDENTIFIER_COLUMNS,
    SAFE_PREDICTOR_COLUMNS,
    TRAINING_TARGET_COLUMNS,
    assert_target_feature_disjointness,
)

__all__ = [
    "DEFAULT_TEMPORAL_CUTOFF_DATE",
    "SurvivalTemporalSplit",
    "case_aware_temporal_split",
    "compute_case_entry_dates",
    "export_survival_split_artifacts",
    "generate_survival_split_report",
    "load_survival_split_artifacts",
]

DEFAULT_TEMPORAL_CUTOFF_DATE = "2026-05-01"


def _extract_field(item: Any, field_name: str) -> Any:
    """Extract a named field from a dataclass, dict, or object."""
    if isinstance(item, dict):
        return item.get(field_name)
    return getattr(item, field_name, None)


def compute_case_entry_dates(records: Iterable[Any]) -> dict[str, str]:
    """Compute case_entry_date = min(snapshot_date) for each unique case_id.
    
    Guarantees deterministic, reproducible ordering.
    """
    case_dates: dict[str, str] = {}
    for r in records:
        cid = _extract_field(r, "case_id")
        if not cid:
            continue
        # Use snapshot_date; fallback to entry_date if snapshot_date not present
        sdate = _extract_field(r, "snapshot_date") or _extract_field(r, "entry_date")
        if not sdate:
            continue
        sdate_str = str(sdate)[:10]
        if cid not in case_dates or sdate_str < case_dates[cid]:
            case_dates[cid] = sdate_str
    return dict(sorted(case_dates.items()))


@dataclass(frozen=True)
class SurvivalTemporalSplit:
    """Represents a validated case-aware chronological train/eval split."""

    cutoff_date: str
    train_case_ids: tuple[str, ...]
    eval_case_ids: tuple[str, ...]
    case_entry_dates: Mapping[str, str]
    train_records: tuple[Any, ...]
    eval_records: tuple[Any, ...]

    def __post_init__(self) -> None:
        """Validate core split invariants upon instantiation."""
        train_set = set(self.train_case_ids)
        eval_set = set(self.eval_case_ids)

        # Invariant 1: Strict case disjointness
        overlap = train_set.intersection(eval_set)
        if overlap:
            raise ValueError(f"Case overlap detected between train and eval: {sorted(overlap)}")

        # Invariant 2: Temporal boundary enforcement
        if self.train_case_ids and self.eval_case_ids:
            train_dates = [self.case_entry_dates[c] for c in self.train_case_ids]
            eval_dates = [self.case_entry_dates[c] for c in self.eval_case_ids]
            max_train = max(train_dates)
            min_eval = min(eval_dates)
            if max_train >= min_eval:
                raise ValueError(
                    f"Temporal leakage violation: max train entry date ({max_train}) "
                    f"is not strictly earlier than min eval entry date ({min_eval})"
                )

        # Invariant 3: Record membership alignment
        for r in self.train_records:
            cid = _extract_field(r, "case_id")
            if cid not in train_set:
                raise ValueError(f"Train record case_id '{cid}' not in train_case_ids!")
        for r in self.eval_records:
            cid = _extract_field(r, "case_id")
            if cid not in eval_set:
                raise ValueError(f"Eval record case_id '{cid}' not in eval_case_ids!")

    @property
    def train_count(self) -> int:
        return len(self.train_records)

    @property
    def eval_count(self) -> int:
        return len(self.eval_records)

    @property
    def total_count(self) -> int:
        return self.train_count + self.eval_count

    @property
    def train_case_count(self) -> int:
        return len(self.train_case_ids)

    @property
    def eval_case_count(self) -> int:
        return len(self.eval_case_ids)

    @property
    def total_case_count(self) -> int:
        return self.train_case_count + self.eval_case_count

    @property
    def max_train_entry_date(self) -> str | None:
        if not self.train_case_ids:
            return None
        return max(self.case_entry_dates[c] for c in self.train_case_ids)

    @property
    def min_eval_entry_date(self) -> str | None:
        if not self.eval_case_ids:
            return None
        return min(self.case_entry_dates[c] for c in self.eval_case_ids)


def case_aware_temporal_split(
    records: Sequence[Any],
    *,
    cutoff_date: str = DEFAULT_TEMPORAL_CUTOFF_DATE,
    case_entry_dates: Mapping[str, str] | None = None,
) -> SurvivalTemporalSplit:
    """Split survival snapshots or feature/target rows using a case-level temporal cutoff.
    
    All snapshots for a given case are assigned to either TRAIN or EVAL based on
    whether the case's earliest entry date is strictly earlier than cutoff_date.
    
    Guarantees:
    - TRAIN case IDs ∩ EVAL case IDs = ∅
    - max(train entry date) < min(eval entry date)
    - Fully deterministic and reproducible (no random seeds)
    """
    if case_entry_dates is None:
        case_entry_dates = compute_case_entry_dates(records)

    train_cases = []
    eval_cases = []
    for cid, entry_dt in sorted(case_entry_dates.items()):
        if entry_dt < cutoff_date:
            train_cases.append(cid)
        else:
            eval_cases.append(cid)

    train_set = set(train_cases)
    eval_set = set(eval_cases)

    train_records = []
    eval_records = []
    for r in records:
        cid = _extract_field(r, "case_id")
        if cid in train_set:
            train_records.append(r)
        elif cid in eval_set:
            eval_records.append(r)
        else:
            raise ValueError(f"Record with unknown case_id '{cid}' not found in case entry dates")

    return SurvivalTemporalSplit(
        cutoff_date=cutoff_date,
        train_case_ids=tuple(train_cases),
        eval_case_ids=tuple(eval_cases),
        case_entry_dates=dict(case_entry_dates),
        train_records=tuple(train_records),
        eval_records=tuple(eval_records),
    )


def export_survival_split_artifacts(
    snapshots: Sequence[Any],
    output_dir: str | Path,
    *,
    cutoff_date: str = DEFAULT_TEMPORAL_CUTOFF_DATE,
    case_entry_dates: Mapping[str, str] | None = None,
) -> dict[str, Path]:
    """Export the 4 canonical split artifacts required by LOOP 6.
    
    Files generated:
    - survival_train_features.csv: Safe predictor features for training cohort.
    - survival_train_targets.csv: Target durations and event indicators for training cohort.
    - survival_eval_features.csv: Safe predictor features for evaluation cohort.
    - survival_eval_targets.csv: Target durations and event indicators for evaluation cohort.
    
    Each feature/target pair has identical row keys: (case_id, snapshot_id, transition).
    """
    assert_target_feature_disjointness()

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    split = case_aware_temporal_split(
        snapshots,
        cutoff_date=cutoff_date,
        case_entry_dates=case_entry_dates,
    )

    feature_cols = list(IDENTIFIER_COLUMNS) + list(SAFE_PREDICTOR_COLUMNS)
    target_cols = list(IDENTIFIER_COLUMNS) + list(TRAINING_TARGET_COLUMNS)

    def _write_csv(path: Path, rows: Sequence[Any], columns: list[str]) -> None:
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for r in rows:
                row_dict = {}
                for col in columns:
                    val = _extract_field(r, col)
                    row_dict[col] = "" if val is None else str(val)
                writer.writerow(row_dict)

    train_feat_path = out_path / "survival_train_features.csv"
    train_targ_path = out_path / "survival_train_targets.csv"
    eval_feat_path = out_path / "survival_eval_features.csv"
    eval_targ_path = out_path / "survival_eval_targets.csv"

    _write_csv(train_feat_path, split.train_records, feature_cols)
    _write_csv(train_targ_path, split.train_records, target_cols)
    _write_csv(eval_feat_path, split.eval_records, feature_cols)
    _write_csv(eval_targ_path, split.eval_records, target_cols)

    return {
        "train_features": train_feat_path,
        "train_targets": train_targ_path,
        "eval_features": eval_feat_path,
        "eval_targets": eval_targ_path,
    }


def load_survival_split_artifacts(
    output_dir: str | Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """Load the 4 split artifacts from disk for verification or downstream training."""
    dir_path = Path(output_dir)
    paths = [
        dir_path / "survival_train_features.csv",
        dir_path / "survival_train_targets.csv",
        dir_path / "survival_eval_features.csv",
        dir_path / "survival_eval_targets.csv",
    ]
    results = []
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"Split artifact not found: {p}")
        with open(p, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            results.append(list(reader))
    return results[0], results[1], results[2], results[3]


def generate_survival_split_report(split: SurvivalTemporalSplit) -> dict[str, Any]:
    """Generate comprehensive summary statistics for the temporal split."""
    train_rows = split.train_records
    eval_rows = split.eval_records

    def _event_obs(r: Any) -> bool:
        v = _extract_field(r, "event_observed")
        return str(v).lower() in ("true", "1")

    train_obs = sum(1 for r in train_rows if _event_obs(r))
    train_cens = len(train_rows) - train_obs
    eval_obs = sum(1 for r in eval_rows if _event_obs(r))
    eval_cens = len(eval_rows) - eval_obs

    train_snap_dates = [_extract_field(r, "snapshot_date") for r in train_rows if _extract_field(r, "snapshot_date")]
    eval_snap_dates = [_extract_field(r, "snapshot_date") for r in eval_rows if _extract_field(r, "snapshot_date")]

    transitions = sorted({
        _extract_field(r, "transition")
        for r in list(train_rows) + list(eval_rows)
        if _extract_field(r, "transition")
    })

    transition_breakdown: dict[str, dict[str, Any]] = {}
    for t in transitions:
        t_tr = [r for r in train_rows if _extract_field(r, "transition") == t]
        t_ev = [r for r in eval_rows if _extract_field(r, "transition") == t]
        tr_o = sum(1 for r in t_tr if _event_obs(r))
        tr_c = len(t_tr) - tr_o
        ev_o = sum(1 for r in t_ev if _event_obs(r))
        ev_c = len(t_ev) - ev_o
        tr_cases = len(set(_extract_field(r, "case_id") for r in t_tr))
        ev_cases = len(set(_extract_field(r, "case_id") for r in t_ev))

        transition_breakdown[t] = {
            "train_cases": tr_cases,
            "train_snapshots": len(t_tr),
            "train_observed": tr_o,
            "train_censored": tr_c,
            "eval_cases": ev_cases,
            "eval_snapshots": len(t_ev),
            "eval_observed": ev_o,
            "eval_censored": ev_c,
        }

    return {
        "cutoff_date": split.cutoff_date,
        "total_cases": split.total_case_count,
        "train_cases": split.train_case_count,
        "eval_cases": split.eval_case_count,
        "train_case_pct": round(split.train_case_count / split.total_case_count * 100.0, 2) if split.total_case_count else 0.0,
        "eval_case_pct": round(split.eval_case_count / split.total_case_count * 100.0, 2) if split.total_case_count else 0.0,
        "total_snapshots": split.total_count,
        "train_snapshots": split.train_count,
        "eval_snapshots": split.eval_count,
        "train_snapshot_pct": round(split.train_count / split.total_count * 100.0, 2) if split.total_count else 0.0,
        "eval_snapshot_pct": round(split.eval_count / split.total_count * 100.0, 2) if split.total_count else 0.0,
        "train_case_entry_range": (
            min(split.case_entry_dates[c] for c in split.train_case_ids) if split.train_case_ids else "N/A",
            split.max_train_entry_date or "N/A",
        ),
        "eval_case_entry_range": (
            split.min_eval_entry_date or "N/A",
            max(split.case_entry_dates[c] for c in split.eval_case_ids) if split.eval_case_ids else "N/A",
        ),
        "train_snapshot_date_range": (min(train_snap_dates), max(train_snap_dates)) if train_snap_dates else ("N/A", "N/A"),
        "eval_snapshot_date_range": (min(eval_snap_dates), max(eval_snap_dates)) if eval_snap_dates else ("N/A", "N/A"),
        "train_observed": train_obs,
        "train_censored": train_cens,
        "train_censoring_rate": round(train_cens / len(train_rows) * 100.0, 2) if train_rows else 0.0,
        "eval_observed": eval_obs,
        "eval_censored": eval_cens,
        "eval_censoring_rate": round(eval_cens / len(eval_rows) * 100.0, 2) if eval_rows else 0.0,
        "case_overlap": len(set(split.train_case_ids).intersection(set(split.eval_case_ids))),
        "transitions": transition_breakdown,
    }
