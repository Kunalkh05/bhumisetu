"""Point-in-time survival snapshot generator for BHUMISETU (LOOP 3).

Constructs leakage-safe historical observations representing:
"What did BHUMISETU know about this acquisition case at time T?"

Reuses existing AsOfView, AsOfMode, and feature extractors.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from app.db.event_log import AsOfMode
from app.models.event import Event
from features.asof import AsOfView, NoticeState, StageEntry, _fold
from features.extractors import (
    CURRENT_FEATURE_SET_VERSION,
    AwardRecordedExtractor,
    DaysInCurrentStageExtractor,
    DaysSinceLatestNoticeExtractor,
    NoticeCountExtractor,
)
from features.value import FeatureValue
from labelling.definition import (
    STATUTORY_WINDOW_DAYS_SEC11_TO_SEC19,
    STATUTORY_WINDOW_DAYS_SEC19_TO_AWARD,
    TRANSITION_CASE_INITIATION_TO_MILESTONE,
    TRANSITION_SECTION_11_TO_SECTION_19,
    TRANSITION_SECTION_19_TO_AWARD,
)
from features.survival_features import (
    BOOLEAN_FEATURE_COLUMNS,
    CATEGORICAL_FEATURE_COLUMNS,
    FEATURE_COLUMNS,
    IDENTIFIER_COLUMNS,
    MISSING_ATTRIBUTE_COLUMNS,
    MISSING_REASON_COLUMNS,
    NUMERICAL_FEATURE_COLUMNS,
    PURGED_FEATURE_COLUMNS,
    SAFE_PREDICTOR_COLUMNS,
    TARGET_COLUMNS,
    TARGET_METADATA_COLUMNS,
    TRAINING_TARGET_COLUMNS,
    assert_target_feature_disjointness,
    export_survival_training_features_to_csv,
    export_survival_training_targets_to_csv,
)

__all__ = [
    "BOOLEAN_FEATURE_COLUMNS",
    "CATEGORICAL_FEATURE_COLUMNS",
    "FEATURE_COLUMNS",
    "IDENTIFIER_COLUMNS",
    "MISSING_ATTRIBUTE_COLUMNS",
    "MISSING_REASON_COLUMNS",
    "NUMERICAL_FEATURE_COLUMNS",
    "PURGED_FEATURE_COLUMNS",
    "SAFE_PREDICTOR_COLUMNS",
    "SurvivalSnapshot",
    "TARGET_COLUMNS",
    "TARGET_METADATA_COLUMNS",
    "TRAINING_TARGET_COLUMNS",
    "assert_target_feature_disjointness",
    "compute_point_in_time_features",
    "export_feature_manifest_to_csv",
    "export_survival_feature_matrix_to_csv",
    "export_survival_features_to_csv",
    "export_survival_snapshots_to_csv",
    "export_survival_targets_to_csv",
    "export_survival_training_features_to_csv",
    "export_survival_training_targets_to_csv",
    "generate_all_survival_snapshots",
    "generate_snapshots_for_case",
    "generate_snapshot_data_quality_report",
]

DEFAULT_CHECKPOINTS_SEC11_19 = (90, 180, 270)
DEFAULT_CHECKPOINTS_SEC19_AWARD = (90, 180, 270, 365)
DEFAULT_CHECKPOINTS_INITIATION = (90, 180, 270, 365, 730)


@dataclass(frozen=True)
class SurvivalSnapshot:
    """A point-in-time survival observation at reference date T."""

    # Target & Identification Metadata (EXCLUDED from predictive model features)
    case_id: str
    snapshot_id: str
    snapshot_date: str  # YYYY-MM-DD
    transition: str
    entry_date: str     # YYYY-MM-DD
    current_stage: str
    duration_at_risk_days: int
    event_observed: bool
    event_date: str     # YYYY-MM-DD or ""
    censoring_date: str # YYYY-MM-DD or ""

    # Point-in-time features (safe for training, knowable strictly as of snapshot_date)
    derived_days_since_case_initiation: int
    derived_days_in_current_stage: int
    derived_days_since_latest_notice: int | None
    derived_notice_count: int
    derived_statutory_sec19_proximity_ratio: float | None
    extension_count: int
    has_statutory_extension: bool
    award_recorded: bool

    # Administrative & Context Features (known at initiation)
    district: str
    taluka: str
    village: str
    acquiring_authority: str
    act_key: str
    derived_project_type: str
    derived_is_direct_purchase: bool

    # Missing Attributes (Preserving exact statutory missingness)
    objection_count: int | None
    parcel_count: int | None
    open_issue_count: int | None
    notified_area_hectares: float | None
    affected_landowner_count: int | None
    compensation_amount_inr: float | None

    # Missing Reason Audit Fields
    missing_reason_objection_count: str
    missing_reason_parcel_count: str
    missing_reason_open_issue_count: str
    missing_reason_compensation: str
    missing_reason_land_area: str
    missing_reason_notified_area: str
    missing_reason_affected_landowners: str
    missing_reason_latest_notice: str | None
    missing_reason_sec19_proximity: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_date(val: str | None) -> date | None:
    if not val or val.strip() == "":
        return None
    return datetime.strptime(val.strip(), "%Y-%m-%d").date()


def _to_event_obj(raw: Mapping[str, Any], event_idx: int) -> Event:
    """Convert clean event dict into canonical Event domain model."""
    event_date_str = raw["event_date"]
    rec_date_str = raw.get("recording_date") or event_date_str
    occ_dt = datetime.strptime(event_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    rec_dt = datetime.strptime(rec_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    event_type = raw["event_type"].strip().upper()
    entity_type = "acquisition_case"
    payload: dict[str, Any] = {"stage_key": {"to": event_type}}

    if event_type in {"SECTION_11", "GENERAL_NOTICE", "DIRECT_PURCHASE", "SECTION_19", "SECTION_21"}:
        payload["notice_type"] = event_type
    elif event_type == "AWARD":
        entity_type = "award"
        payload["award_type"] = "FINAL"
    elif event_type == "EXTENSION":
        entity_type = "statutory_extension"
        payload["extension"] = True

    return Event(
        id=event_idx,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=event_idx,
        case_id=int(raw["case_id"].split("_")[-1]) if "_" in raw["case_id"] else 1,
        actor_type="SYSTEM",
        actor_id="collectorate",
        occurrence_time=occ_dt,
        recording_time=rec_dt,
        payload=payload,
        has_pd_refs=False,
    )


def compute_point_in_time_features(
    case_meta: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    snapshot_date: date,
    *,
    mode: AsOfMode | str = AsOfMode.KNOWABLE_AT,
) -> dict[str, Any]:
    """Compute features using ONLY events knowable on or before snapshot_date."""
    mode = AsOfMode(mode)
    ref_dt = datetime.combine(snapshot_date, datetime.max.time(), tzinfo=timezone.utc)

    # 1. Filter events strictly by occurrence_time and recording_time
    known_events: list[Mapping[str, Any]] = []
    for e in events:
        ed = _parse_date(e["event_date"])
        rd = _parse_date(e.get("recording_date")) or ed
        if ed is None:
            continue
        if mode == AsOfMode.KNOWABLE_AT:
            if ed <= snapshot_date and (rd is None or rd <= snapshot_date):
                known_events.append(e)
        else:  # OCCURRED_BY
            if ed <= snapshot_date:
                known_events.append(e)

    # Sort chronologically
    known_events.sort(key=lambda x: (x["event_date"], x.get("recording_date", x["event_date"])))

    # 2. Stage history & Current Stage
    stage_events = [
        e for e in known_events
        if e["event_type"].upper() in {
            "SECTION_11", "SECTION_19", "SECTION_21", "AWARD",
            "DIRECT_PURCHASE", "GENERAL_NOTICE", "STAGE_ENTERED",
        }
    ]
    if stage_events:
        current_stage = stage_events[-1]["event_type"].upper()
        current_stage_date = _parse_date(stage_events[-1]["event_date"]) or snapshot_date
    else:
        current_stage = "INITIATION"
        current_stage_date = snapshot_date

    derived_days_in_current_stage = max(0, (snapshot_date - current_stage_date).days)

    # 3. Days since case initiation
    all_known_dates = [_parse_date(e["event_date"]) for e in known_events]
    valid_dates = [d for d in all_known_dates if d is not None]
    initiation_date = min(valid_dates) if valid_dates else snapshot_date
    derived_days_since_case_initiation = max(0, (snapshot_date - initiation_date).days)

    # 4. Notice features
    notices = [
        e for e in known_events
        if e["event_type"].upper() in {
            "SECTION_11", "SECTION_19", "SECTION_21", "GENERAL_NOTICE", "DIRECT_PURCHASE"
        }
    ]
    derived_notice_count = len(notices)
    if notices:
        latest_notice_date = max(_parse_date(n["event_date"]) or snapshot_date for n in notices)
        derived_days_since_latest_notice: int | None = max(0, (snapshot_date - latest_notice_date).days)
        missing_reason_latest_notice = None
    else:
        derived_days_since_latest_notice = None
        missing_reason_latest_notice = "NO_NOTICE_EVENT"

    # 5. Statutory Section 19 Proximity Ratio (365 days window from Section 11)
    s11_events = [e for e in known_events if e["event_type"].upper() == "SECTION_11"]
    if s11_events:
        s11_date = _parse_date(s11_events[0]["event_date"])
        if s11_date:
            days_since_s11 = max(0, (snapshot_date - s11_date).days)
            derived_statutory_sec19_proximity_ratio: float | None = round(
                min(1.0, days_since_s11 / float(STATUTORY_WINDOW_DAYS_SEC11_TO_SEC19)), 4
            )
            missing_reason_sec19_proximity = None
        else:
            derived_statutory_sec19_proximity_ratio = None
            missing_reason_sec19_proximity = "NOT_APPLICABLE_PRE_SEC11"
    else:
        derived_statutory_sec19_proximity_ratio = None
        missing_reason_sec19_proximity = "NOT_APPLICABLE_PRE_SEC11"

    # 6. Extensions
    extension_events = [e for e in known_events if e["event_type"].upper() == "EXTENSION"]
    extension_count = len(extension_events)
    has_statutory_extension = extension_count > 0

    # 7. Award status
    award_events = [e for e in known_events if e["event_type"].upper() == "AWARD"]
    award_recorded = len(award_events) > 0

    return {
        "current_stage": current_stage,
        "derived_days_since_case_initiation": derived_days_since_case_initiation,
        "derived_days_in_current_stage": derived_days_in_current_stage,
        "derived_days_since_latest_notice": derived_days_since_latest_notice,
        "derived_notice_count": derived_notice_count,
        "derived_statutory_sec19_proximity_ratio": derived_statutory_sec19_proximity_ratio,
        "extension_count": extension_count,
        "has_statutory_extension": has_statutory_extension,
        "award_recorded": award_recorded,
        # Administrative & Case Metadata
        "district": case_meta.get("district", ""),
        "taluka": case_meta.get("taluka", ""),
        "village": case_meta.get("village", ""),
        "acquiring_authority": case_meta.get("acquiring_authority", ""),
        "act_key": case_meta.get("act_key", "RFCTLARR_2013"),
        "derived_project_type": case_meta.get("derived_project_type", "Rural Infrastructure"),
        "derived_is_direct_purchase": str(case_meta.get("derived_is_direct_purchase", "False")).lower() == "true",
        # Missing Attributes (Preserving exact missingness semantics)
        "objection_count": None,
        "parcel_count": None,
        "open_issue_count": None,
        "notified_area_hectares": None,
        "affected_landowner_count": None,
        "compensation_amount_inr": None,
        "missing_reason_objection_count": "NOT_PUBLISHED_IN_GAZETTE",
        "missing_reason_parcel_count": "NOT_PUBLISHED_IN_STRUCTURED_DATA",
        "missing_reason_open_issue_count": "NOT_APPLICABLE_IN_REAL_DATA",
        "missing_reason_compensation": "NOT_APPLICABLE_PRE_AWARD",
        "missing_reason_land_area": "UNPARSED_SCHEDULE_TABLE",
        "missing_reason_notified_area": "UNPARSED_SCHEDULE_TABLE",
        "missing_reason_affected_landowners": "NOT_PUBLISHED_IN_STRUCTURED_DATA",
        "missing_reason_latest_notice": missing_reason_latest_notice,
        "missing_reason_sec19_proximity": missing_reason_sec19_proximity,
    }


def generate_snapshots_for_case(
    case_meta: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    transition: str,
    *,
    cutoff_date: date,
    checkpoints: Sequence[int] | None = None,
    mode: AsOfMode | str = AsOfMode.KNOWABLE_AT,
) -> list[SurvivalSnapshot]:
    """Generate all valid point-in-time snapshots for a given case and transition."""
    case_id = case_meta["case_id"]

    # 1. Resolve transition entry date and exit date
    if transition == TRANSITION_SECTION_11_TO_SECTION_19:
        entry_date = _parse_date(case_meta.get("section_11_date"))
        exit_date = _parse_date(case_meta.get("section_19_date"))
        default_cps = DEFAULT_CHECKPOINTS_SEC11_19
    elif transition == TRANSITION_SECTION_19_TO_AWARD:
        entry_date = _parse_date(case_meta.get("section_19_date"))
        exit_date = _parse_date(case_meta.get("award_date"))
        default_cps = DEFAULT_CHECKPOINTS_SEC19_AWARD
    elif transition == TRANSITION_CASE_INITIATION_TO_MILESTONE:
        entry_date = _parse_date(case_meta.get("first_notice_date"))
        # Milestone is either Section 19 or Award (first reached)
        s19 = _parse_date(case_meta.get("section_19_date"))
        award = _parse_date(case_meta.get("award_date"))
        milestones = [m for m in (s19, award) if m is not None]
        exit_date = min(milestones) if milestones else None
        default_cps = DEFAULT_CHECKPOINTS_INITIATION
    else:
        raise ValueError(f"Unsupported transition: {transition}")

    if entry_date is None:
        return []  # Case never entered this transition

    # 2. Determine target outcome and horizon end
    if exit_date is not None and exit_date <= cutoff_date:
        event_observed = True
        event_date_str = exit_date.strftime("%Y-%m-%d")
        censoring_date_str = ""
        horizon_end = exit_date
    else:
        event_observed = False
        event_date_str = ""
        censoring_date_str = cutoff_date.strftime("%Y-%m-%d")
        horizon_end = cutoff_date

    # For a predictive survival snapshot, snapshot_date must strictly precede horizon_end
    if horizon_end <= entry_date:
        return []

    # 3. Choose snapshot dates strictly before horizon_end
    cps = checkpoints if checkpoints is not None else default_cps
    snap_dates: set[date] = {entry_date}

    # Add intermediate event dates occurring strictly between entry_date and horizon_end
    for e in events:
        ed = _parse_date(e["event_date"])
        if ed and entry_date < ed < horizon_end:
            snap_dates.add(ed)

    # Add scheduled checkpoints strictly between entry_date and horizon_end
    for cp in cps:
        cp_date = entry_date + timedelta(days=cp)
        if entry_date < cp_date < horizon_end:
            snap_dates.add(cp_date)

    snapshots: list[SurvivalSnapshot] = []
    for s_date in sorted(snap_dates):
        # Landmark survival duration: remaining time-to-event from snapshot_date
        duration_at_risk = (horizon_end - s_date).days
        if duration_at_risk <= 0:
            continue  # Exclude any on-event or post-event observations

        # Unique snapshot ID
        date_str = s_date.strftime("%Y%m%d")
        trans_short = transition.replace("SECTION_", "S").replace("_TO_", "_")
        snapshot_id = f"SNP_{case_id}_{trans_short}_{date_str}"

        # Calculate point-in-time features strictly as of s_date
        feats = compute_point_in_time_features(case_meta, events, s_date, mode=mode)

        snap = SurvivalSnapshot(
            case_id=case_id,
            snapshot_id=snapshot_id,
            snapshot_date=s_date.strftime("%Y-%m-%d"),
            transition=transition,
            entry_date=entry_date.strftime("%Y-%m-%d"),
            current_stage=feats["current_stage"],
            duration_at_risk_days=duration_at_risk,
            event_observed=event_observed,
            event_date=event_date_str,
            censoring_date=censoring_date_str,
            derived_days_since_case_initiation=feats["derived_days_since_case_initiation"],
            derived_days_in_current_stage=feats["derived_days_in_current_stage"],
            derived_days_since_latest_notice=feats["derived_days_since_latest_notice"],
            derived_notice_count=feats["derived_notice_count"],
            derived_statutory_sec19_proximity_ratio=feats["derived_statutory_sec19_proximity_ratio"],
            extension_count=feats["extension_count"],
            has_statutory_extension=feats["has_statutory_extension"],
            award_recorded=feats["award_recorded"],
            district=feats["district"],
            taluka=feats["taluka"],
            village=feats["village"],
            acquiring_authority=feats["acquiring_authority"],
            act_key=feats["act_key"],
            derived_project_type=feats["derived_project_type"],
            derived_is_direct_purchase=feats["derived_is_direct_purchase"],
            objection_count=feats["objection_count"],
            parcel_count=feats["parcel_count"],
            open_issue_count=feats["open_issue_count"],
            notified_area_hectares=feats["notified_area_hectares"],
            affected_landowner_count=feats["affected_landowner_count"],
            compensation_amount_inr=feats["compensation_amount_inr"],
            missing_reason_objection_count=feats["missing_reason_objection_count"],
            missing_reason_parcel_count=feats["missing_reason_parcel_count"],
            missing_reason_open_issue_count=feats["missing_reason_open_issue_count"],
            missing_reason_compensation=feats["missing_reason_compensation"],
            missing_reason_land_area=feats["missing_reason_land_area"],
            missing_reason_notified_area=feats["missing_reason_notified_area"],
            missing_reason_affected_landowners=feats["missing_reason_affected_landowners"],
            missing_reason_latest_notice=feats["missing_reason_latest_notice"],
            missing_reason_sec19_proximity=feats["missing_reason_sec19_proximity"],
        )
        snapshots.append(snap)

    return snapshots


def generate_all_survival_snapshots(
    cases: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    *,
    cutoff_date: date | None = None,
    mode: AsOfMode | str = AsOfMode.KNOWABLE_AT,
) -> list[SurvivalSnapshot]:
    """Generate snapshots across all cases and all three survival transitions."""
    events_by_case: dict[str, list[Mapping[str, Any]]] = {}
    all_dates: list[date] = []
    for e in events:
        cid = e["case_id"]
        events_by_case.setdefault(cid, []).append(e)
        ed = _parse_date(e["event_date"])
        if ed:
            all_dates.append(ed)

    canonical_cutoff = cutoff_date or (max(all_dates) if all_dates else date.today())

    transitions = [
        TRANSITION_SECTION_11_TO_SECTION_19,
        TRANSITION_SECTION_19_TO_AWARD,
        TRANSITION_CASE_INITIATION_TO_MILESTONE,
    ]

    all_snapshots: list[SurvivalSnapshot] = []
    seen_combinations: set[tuple[str, str, str]] = set()

    for c in cases:
        cid = c["case_id"]
        c_events = events_by_case.get(cid, [])
        for trans in transitions:
            snaps = generate_snapshots_for_case(
                c, c_events, trans, cutoff_date=canonical_cutoff, mode=mode
            )
            for s in snaps:
                combo = (s.case_id, s.snapshot_date, s.transition)
                if combo in seen_combinations:
                    continue  # Guard against duplicates
                seen_combinations.add(combo)
                all_snapshots.append(s)

    all_snapshots.sort(key=lambda s: (s.transition, s.snapshot_date, s.case_id))
    return all_snapshots


def export_survival_snapshots_to_csv(
    snapshots: Sequence[SurvivalSnapshot],
    target_path: str | Path,
) -> None:
    """Export snapshots to CSV."""
    if not snapshots:
        return
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(asdict(snapshots[0]).keys())
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in snapshots:
            writer.writerow(s.to_dict())


def export_survival_features_to_csv(
    snapshots: Sequence[SurvivalSnapshot],
    target_path: str | Path,
) -> None:
    """Export pure predictor features and missingness reason columns with index keys."""
    if not snapshots:
        return
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(IDENTIFIER_COLUMNS) + list(FEATURE_COLUMNS) + list(MISSING_REASON_COLUMNS)
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in snapshots:
            d = s.to_dict()
            row = {col: d[col] if d.get(col) is not None else "" for col in fieldnames}
            writer.writerow(row)


def export_survival_targets_to_csv(
    snapshots: Sequence[SurvivalSnapshot],
    target_path: str | Path,
) -> None:
    """Export survival target outcomes and horizon dates with index keys."""
    if not snapshots:
        return
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(IDENTIFIER_COLUMNS) + list(TARGET_COLUMNS)
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in snapshots:
            d = s.to_dict()
            row = {col: d[col] if d.get(col) is not None else "" for col in fieldnames}
            writer.writerow(row)


def export_survival_feature_matrix_to_csv(
    snapshots: Sequence[SurvivalSnapshot],
    target_path: str | Path,
) -> None:
    """Export clean predictor feature matrix (strictly features + index keys; target columns excluded)."""
    if not snapshots:
        return
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(IDENTIFIER_COLUMNS) + list(FEATURE_COLUMNS)
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in snapshots:
            d = s.to_dict()
            row = {col: d[col] if d.get(col) is not None else "" for col in fieldnames}
            writer.writerow(row)


def export_feature_manifest_to_csv(
    snapshots: Sequence[SurvivalSnapshot],
    target_path: str | Path,
) -> None:
    """Generate and write the feature manifest documenting availability, rules, and leakage risk."""
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    total_count = len(snapshots)

    # Define feature metadata specifications for all 22 candidate features
    specs: list[dict[str, Any]] = [
        {
            "feature_name": "derived_days_since_case_initiation",
            "feature_type": "TEMPORAL",
            "source": "EventLog.occurrence_time (earliest notice)",
            "calculation": "max(0, (snapshot_date - earliest_notice_date).days)",
            "availability_rule": "Days between earliest recorded notification and snapshot_date T",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "derived_days_in_current_stage",
            "feature_type": "TEMPORAL",
            "source": "EventLog.occurrence_time (current stage entry)",
            "calculation": "max(0, (snapshot_date - current_stage_date).days)",
            "availability_rule": "Days between current stage entry and snapshot_date T",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "derived_days_since_latest_notice",
            "feature_type": "TEMPORAL",
            "source": "EventLog.occurrence_time (notices)",
            "calculation": "max(0, (snapshot_date - latest_notice_date).days)",
            "availability_rule": "Days since latest statutory notice occurring on or before T",
            "missingness_reason": "NO_NOTICE_EVENT",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "derived_notice_count",
            "feature_type": "TEMPORAL",
            "source": "EventLog count(statutory_notice)",
            "calculation": "count(notices where occurrence_time <= T and recording_time <= T)",
            "availability_rule": "Cumulative count of notices published on or before T",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "derived_statutory_sec19_proximity_ratio",
            "feature_type": "STATUTORY",
            "source": "EventLog Section 11 date",
            "calculation": "min(1.0, (snapshot_date - s11_date).days / 365.0)",
            "availability_rule": "Proximity ratio to statutory 365-day Section 19 limit as of T",
            "missingness_reason": "NOT_APPLICABLE_PRE_SEC11",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "extension_count",
            "feature_type": "STATUTORY",
            "source": "EventLog EXTENSION orders",
            "calculation": "count(extension orders where occurrence_time <= T and recording_time <= T)",
            "availability_rule": "Cumulative count of statutory extensions granted on or before T",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "has_statutory_extension",
            "feature_type": "STATUTORY",
            "source": "EventLog EXTENSION orders",
            "calculation": "extension_count > 0",
            "availability_rule": "Boolean indicator if extension_count > 0 on or before T",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "award_recorded",
            "feature_type": "AWARD",
            "source": "EventLog AWARD events",
            "calculation": "count(award events where occurrence_time <= T and recording_time <= T) > 0",
            "availability_rule": "Boolean indicator if an Award was published on or before T",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "FALSE",
            "leakage_risk": "MEDIUM",
            "rejection_reason": "REJECTED_ZERO_VARIANCE_PRE_EVENT_LEAKAGE_RISK",
        },
        {
            "feature_name": "current_stage",
            "feature_type": "CATEGORICAL",
            "source": "EventLog stage history",
            "calculation": "most recent stage entry event where occurrence_time <= T",
            "availability_rule": "Current active statutory stage as of T",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "district",
            "feature_type": "ADMINISTRATIVE",
            "source": "AcquisitionCase.district",
            "calculation": "case_meta.district",
            "availability_rule": "Jurisdictional Collectorate",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "taluka",
            "feature_type": "ADMINISTRATIVE",
            "source": "AcquisitionCase.taluka",
            "calculation": "case_meta.taluka",
            "availability_rule": "Taluka revenue administrative unit",
            "missingness_reason": "UNPARSED_SCHEDULE_TABLE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "village",
            "feature_type": "ADMINISTRATIVE",
            "source": "AcquisitionCase.village",
            "calculation": "case_meta.village",
            "availability_rule": "Revenue village / mouza name",
            "missingness_reason": "UNPARSED_SCHEDULE_TABLE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "acquiring_authority",
            "feature_type": "ADMINISTRATIVE",
            "source": "AcquisitionCase.acquiring_authority",
            "calculation": "case_meta.acquiring_authority",
            "availability_rule": "Acquiring government body / administration",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "act_key",
            "feature_type": "ADMINISTRATIVE",
            "source": "AcquisitionCase.act_key",
            "calculation": "case_meta.act_key",
            "availability_rule": "Governing statutory act",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "derived_project_type",
            "feature_type": "ADMINISTRATIVE",
            "source": "Project description extraction",
            "calculation": "case_meta.derived_project_type",
            "availability_rule": "Project category inferred from public notice text",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "derived_is_direct_purchase",
            "feature_type": "ADMINISTRATIVE",
            "source": "Notice title & negotiation keywords",
            "calculation": "case_meta.derived_is_direct_purchase",
            "availability_rule": "Private negotiation / direct purchase proceeding indicator",
            "missingness_reason": "NONE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "TRUE",
            "leakage_risk": "LOW",
            "rejection_reason": "NONE",
        },
        {
            "feature_name": "objection_count",
            "feature_type": "MISSING_ATTRIBUTE",
            "source": "Section 15 objection register",
            "calculation": "None (preserved as NULL)",
            "availability_rule": "Landowner objection records",
            "missingness_reason": "NOT_PUBLISHED_IN_GAZETTE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "FALSE",
            "leakage_risk": "LOW",
            "rejection_reason": "REJECTED_ZERO_COVERAGE_UNPUBLISHED",
        },
        {
            "feature_name": "parcel_count",
            "feature_type": "MISSING_ATTRIBUTE",
            "source": "Cadastral survey schedule",
            "calculation": "None (preserved as NULL)",
            "availability_rule": "Survey numbers published in gazette schedule table",
            "missingness_reason": "NOT_PUBLISHED_IN_STRUCTURED_DATA",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "FALSE",
            "leakage_risk": "LOW",
            "rejection_reason": "REJECTED_ZERO_COVERAGE_UNPUBLISHED",
        },
        {
            "feature_name": "open_issue_count",
            "feature_type": "MISSING_ATTRIBUTE",
            "source": "Administrative issue tracker",
            "calculation": "None (preserved as NULL)",
            "availability_rule": "Internal collectorate operational issues",
            "missingness_reason": "NOT_APPLICABLE_IN_REAL_DATA",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "FALSE",
            "leakage_risk": "LOW",
            "rejection_reason": "REJECTED_NOT_APPLICABLE_REAL_DATA",
        },
        {
            "feature_name": "notified_area_hectares",
            "feature_type": "MISSING_ATTRIBUTE",
            "source": "Gazette notification schedule",
            "calculation": "None (preserved as NULL)",
            "availability_rule": "Total land area specified in hectares",
            "missingness_reason": "UNPARSED_SCHEDULE_TABLE",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "FALSE",
            "leakage_risk": "LOW",
            "rejection_reason": "REJECTED_ZERO_COVERAGE_UNPARSED",
        },
        {
            "feature_name": "affected_landowner_count",
            "feature_type": "MISSING_ATTRIBUTE",
            "source": "Cadastral landowner schedule",
            "calculation": "None (preserved as NULL)",
            "availability_rule": "Count of distinct affected persons listed in schedule",
            "missingness_reason": "NOT_PUBLISHED_IN_STRUCTURED_DATA",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "FALSE",
            "leakage_risk": "LOW",
            "rejection_reason": "REJECTED_ZERO_COVERAGE_UNPUBLISHED",
        },
        {
            "feature_name": "compensation_amount_inr",
            "feature_type": "MISSING_ATTRIBUTE",
            "source": "Section 23 award statement",
            "calculation": "None (preserved as NULL)",
            "availability_rule": "Total compensation determined in award",
            "missingness_reason": "NOT_APPLICABLE_PRE_AWARD",
            "point_in_time_safe": "TRUE",
            "allowed_for_survival_training": "FALSE",
            "leakage_risk": "LOW",
            "rejection_reason": "REJECTED_ZERO_COVERAGE_POST_AWARD",
        },
    ]

    manifest_rows: list[dict[str, Any]] = []
    for spec in specs:
        fname = spec["feature_name"]
        non_null_count = sum(1 for s in snapshots if getattr(s, fname, None) is not None and getattr(s, fname) != "")
        coverage_pct = round((non_null_count / total_count) * 100.0, 1) if total_count > 0 else 0.0
        row = dict(spec)
        row["coverage"] = f"{coverage_pct}%"
        manifest_rows.append(row)

    manifest_fields = [
        "feature_name",
        "feature_type",
        "source",
        "calculation",
        "availability_rule",
        "coverage",
        "missingness_reason",
        "point_in_time_safe",
        "allowed_for_survival_training",
        "leakage_risk",
        "rejection_reason",
    ]

    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=manifest_fields)
        writer.writeheader()
        for r in manifest_rows:
            writer.writerow(r)


def generate_snapshot_data_quality_report(
    snapshots: Sequence[SurvivalSnapshot],
) -> dict[str, Any]:
    """Calculate summary statistics separately for each survival transition."""
    transitions = [
        TRANSITION_SECTION_11_TO_SECTION_19,
        TRANSITION_SECTION_19_TO_AWARD,
        TRANSITION_CASE_INITIATION_TO_MILESTONE,
    ]

    report: dict[str, Any] = {}
    for trans in transitions:
        group = [s for s in snapshots if s.transition == trans]
        unique_cases = len(set(s.case_id for s in group))
        obs_count = sum(1 for s in group if s.event_observed)
        cens_count = sum(1 for s in group if not s.event_observed)
        dates = [s.snapshot_date for s in group]
        earliest_snap = min(dates) if dates else "N/A"
        latest_snap = max(dates) if dates else "N/A"

        # Unique combinations to verify zero duplicates
        combos = set((s.case_id, s.snapshot_date) for s in group)
        duplicate_count = len(group) - len(combos)

        # Feature non-null coverage
        coverage_info: dict[str, str] = {}
        for feat in [
            "derived_days_in_current_stage",
            "derived_notice_count",
            "derived_statutory_sec19_proximity_ratio",
            "extension_count",
            "award_recorded",
            "objection_count",
            "parcel_count",
        ]:
            non_null = sum(1 for s in group if getattr(s, feat) is not None)
            pct = round((non_null / len(group)) * 100.0, 1) if group else 0.0
            coverage_info[feat] = f"{pct}%"

        report[trans] = {
            "cases": unique_cases,
            "total_snapshots": len(group),
            "observed_events": obs_count,
            "censored_observations": cens_count,
            "earliest_snapshot": earliest_snap,
            "latest_snapshot": latest_snap,
            "duplicate_snapshots": duplicate_count,
            "coverage": coverage_info,
        }

    return report
