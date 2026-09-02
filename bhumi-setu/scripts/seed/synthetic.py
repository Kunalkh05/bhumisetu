"""Synthetic event timelines for point-in-time replay (task 21.1).

The generator produces append-ordered event streams for a synthetic district.
Each event has both occurrence and recording timestamps; a configured fraction
is deliberately backdated so `OCCURRED_BY` and `KNOWABLE_AT` differ in tests.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_CASE_COUNT = 10_000
DEFAULT_SEED = 21_001
SYNTHETIC_STATE = "SYNTH-MH"
SYNTHETIC_ACT = "RFCTLARR_2013"
SYNTHETIC_DISTRICT = "SYNTH-DISTRICT-001"
SHARE_TOLERANCE = 0.0001

STAGE_EVENTS: tuple[tuple[str, str], ...] = (
    ("CASE_CREATED", "intake"),
    ("STAGE_ENTERED", "preliminary_notice"),
    ("STAGE_ENTERED", "objection_window"),
    ("STAGE_ENTERED", "award_draft"),
    ("STAGE_ENTERED", "award_final"),
    ("CASE_TERMINAL", "closed"),
)


@dataclass(frozen=True)
class SyntheticEvent:
    id: int
    case_id: int
    case_reference: str
    state_key: str
    act_key: str
    entity_type: str
    entity_id: int
    event_type: str
    stage_key: str
    occurrence_time: datetime
    recording_time: datetime
    payload: dict[str, object]
    backdated: bool = False


@dataclass(frozen=True)
class SyntheticParcel:
    id: int
    case_id: int
    survey_number: str
    village: str
    extent: float
    extent_unit: str
    geom: dict[str, object]


@dataclass(frozen=True)
class SyntheticOwnershipRecord:
    id: int
    parcel_id: int
    owner_identity_key: str
    share: float
    contact_mobile_hash: str


@dataclass(frozen=True)
class SyntheticAward:
    id: int
    ownership_record_id: int
    market_value: float
    solatium: float
    interest: float
    total_amount: float
    component_sum_consistent: bool


@dataclass(frozen=True)
class SyntheticDocumentExtraction:
    id: int
    case_id: int
    document_type: str
    recognized_script: str
    confidence: float


@dataclass(frozen=True)
class SyntheticLabel:
    outcome: str
    reference_t: datetime
    event_observed: bool
    terminal_time: datetime | None
    deadline_time: datetime


@dataclass(frozen=True)
class SyntheticCaseTimeline:
    case_id: int
    case_reference: str
    district_code: str
    events: tuple[SyntheticEvent, ...]
    parcels: tuple[SyntheticParcel, ...]
    ownership_records: tuple[SyntheticOwnershipRecord, ...]
    awards: tuple[SyntheticAward, ...]
    document_extractions: tuple[SyntheticDocumentExtraction, ...]
    label: SyntheticLabel


def _at_noon(day: date) -> datetime:
    return datetime.combine(day, time(hour=12), tzinfo=timezone.utc)


def _lag_days(rng: random.Random) -> int:
    draw = rng.random()
    if draw < 0.70:
        return rng.randint(0, 3)
    if draw < 0.90:
        return rng.randint(4, 14)
    return rng.randint(15, 60)


def _stage_durations(rng: random.Random) -> list[int]:
    return [
        rng.randint(3, 12),
        rng.randint(20, 45),
        rng.randint(30, 90),
        rng.randint(20, 75),
        rng.randint(10, 35),
    ]


def _parcel_geometry(rng: random.Random, case_id: int, index: int) -> dict[str, object]:
    lon = 73.20 + (case_id % 100) * 0.005 + rng.random() * 0.001
    lat = 18.10 + ((case_id // 100) % 100) * 0.005 + rng.random() * 0.001
    size = 0.001 + (index * 0.0002)
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [round(lon, 6), round(lat, 6)],
                [round(lon + size, 6), round(lat, 6)],
                [round(lon + size, 6), round(lat + size, 6)],
                [round(lon, 6), round(lat + size, 6)],
                [round(lon, 6), round(lat, 6)],
            ]
        ],
    }


def _shares(rng: random.Random, owners: int, inconsistent: bool) -> list[float]:
    cuts = sorted(rng.random() for _ in range(owners - 1))
    shares = [right - left for left, right in zip([0.0, *cuts], [*cuts, 1.0], strict=True)]
    target = 1.0 + (rng.choice([-0.04, 0.04]) if inconsistent else 0.0)
    scaled = [round(share * target, 6) for share in shares]
    scaled[-1] = round(target - sum(scaled[:-1]), 6)
    return scaled


def _case_material(
    *,
    rng: random.Random,
    case_id: int,
) -> tuple[
    tuple[SyntheticParcel, ...],
    tuple[SyntheticOwnershipRecord, ...],
    tuple[SyntheticAward, ...],
    tuple[SyntheticDocumentExtraction, ...],
]:
    parcels: list[SyntheticParcel] = []
    ownership_records: list[SyntheticOwnershipRecord] = []
    awards: list[SyntheticAward] = []
    documents: list[SyntheticDocumentExtraction] = []

    parcel_count = rng.randint(1, 7)
    next_owner_id = case_id * 100
    for parcel_index in range(parcel_count):
        parcel_id = case_id * 10 + parcel_index
        parcels.append(
            SyntheticParcel(
                id=parcel_id,
                case_id=case_id,
                survey_number=f"SYN/{case_id:05d}/{parcel_index + 1}",
                village=f"Synthetic Village {(case_id % 37) + 1}",
                extent=round(rng.uniform(0.05, 9.95), 4),
                extent_unit="hectare",
                geom=_parcel_geometry(rng, case_id, parcel_index),
            )
        )

        owner_count = rng.randint(1, 4)
        inconsistent_share_sum = rng.random() < 0.18
        for share in _shares(rng, owner_count, inconsistent_share_sum):
            ownership_id = next_owner_id
            next_owner_id += 1
            ownership_records.append(
                SyntheticOwnershipRecord(
                    id=ownership_id,
                    parcel_id=parcel_id,
                    owner_identity_key=f"owner-{ownership_id}",
                    share=share,
                    contact_mobile_hash=f"hmac:{ownership_id:08x}",
                )
            )

            market_value = round(rng.uniform(50_000, 2_000_000), 2)
            solatium = round(market_value * 0.10, 2)
            interest = round(market_value * rng.uniform(0.01, 0.08), 2)
            consistent = rng.random() >= 0.12
            total = round(market_value + solatium + interest, 2)
            if not consistent:
                total = round(total + rng.choice([-500.0, 750.0, 1250.0]), 2)
            awards.append(
                SyntheticAward(
                    id=ownership_id,
                    ownership_record_id=ownership_id,
                    market_value=market_value,
                    solatium=solatium,
                    interest=interest,
                    total_amount=total,
                    component_sum_consistent=consistent,
                )
            )

    for index, document_type in enumerate(("notice", "sale_deed", "award", "identity")):
        documents.append(
            SyntheticDocumentExtraction(
                id=case_id * 10 + index,
                case_id=case_id,
                document_type=document_type,
                recognized_script=rng.choice(("Devanagari", "Latin")),
                confidence=round(rng.betavariate(1.4, 1.4), 4),
            )
        )

    return tuple(parcels), tuple(ownership_records), tuple(awards), tuple(documents)


def _label_for(
    *,
    events: Sequence[SyntheticEvent],
    occurrence_days: Sequence[date],
    rng: random.Random,
    closed: bool,
) -> SyntheticLabel:
    deadline_time = _at_noon(occurrence_days[0] + timedelta(days=165))
    reference_t = _at_noon(occurrence_days[0] + timedelta(days=rng.randint(150, 260)))
    terminal = next((event for event in events if event.event_type == "CASE_TERMINAL"), None)
    terminal_time = terminal.occurrence_time if terminal else None
    if closed and terminal_time is not None:
        outcome = "DELAYED" if terminal_time > deadline_time else "NOT_DELAYED"
        event_observed = True
    else:
        outcome = "CENSORED"
        event_observed = False
    return SyntheticLabel(
        outcome=outcome,
        reference_t=reference_t,
        event_observed=event_observed,
        terminal_time=terminal_time,
        deadline_time=deadline_time,
    )


def generate_case_timeline(
    *,
    case_index: int,
    event_id_start: int,
    rng: random.Random,
    base_day: date,
    state_key: str = SYNTHETIC_STATE,
    act_key: str = SYNTHETIC_ACT,
    district_code: str = SYNTHETIC_DISTRICT,
    backdated_fraction: float = 0.12,
    closed_fraction: float = 0.90,
) -> SyntheticCaseTimeline:
    """Generate one append-ordered case timeline.

    The ordinary stage events are recorded after their occurrence by a mixed lag
    distribution. Some cases also receive a late-recorded objection fact whose
    occurrence predates an event already stored for that case.
    """
    case_id = case_index + 1
    case_reference = f"SYN-{state_key}-{case_id:05d}"
    start_day = base_day + timedelta(days=rng.randint(0, 365 * 3))
    closed = rng.random() < closed_fraction
    occurrence_days = [start_day]
    for duration in _stage_durations(rng):
        occurrence_days.append(occurrence_days[-1] + timedelta(days=duration))

    events: list[SyntheticEvent] = []
    stage_count = len(STAGE_EVENTS) if closed else rng.randint(2, len(STAGE_EVENTS) - 1)
    for offset, ((event_type, stage_key), occurrence_day) in enumerate(
        zip(STAGE_EVENTS[:stage_count], occurrence_days[:stage_count], strict=True)
    ):
        occurrence_time = _at_noon(occurrence_day)
        recording_time = occurrence_time + timedelta(days=_lag_days(rng), hours=rng.randint(0, 8))
        events.append(
            SyntheticEvent(
                id=event_id_start + offset,
                case_id=case_id,
                case_reference=case_reference,
                state_key=state_key,
                act_key=act_key,
                entity_type="acquisition_case",
                entity_id=case_id,
                event_type=event_type,
                stage_key=stage_key,
                occurrence_time=occurrence_time,
                recording_time=recording_time,
                payload={"stage_key": {"to": stage_key}},
            )
        )

    if rng.random() < backdated_fraction and len(events) >= 3:
        anchor = rng.randint(1, len(events) - 1)
        occurrence_time = events[anchor - 1].occurrence_time + timedelta(days=1)
        recording_anchor = events[anchor]
        recording_time = recording_anchor.recording_time + timedelta(days=rng.randint(1, 10))
        events.append(
            SyntheticEvent(
                id=event_id_start + len(events),
                case_id=case_id,
                case_reference=case_reference,
                state_key=state_key,
                act_key=act_key,
                entity_type="objection",
                entity_id=case_id * 10,
                event_type="OBJECTION_RECEIVED",
                stage_key=events[anchor - 1].stage_key,
                occurrence_time=occurrence_time,
                recording_time=recording_time,
                payload={"late_recorded": {"to": True}},
                backdated=True,
            )
        )

    ordered = tuple(sorted(events, key=lambda event: (event.recording_time, event.id)))
    parcels, ownership_records, awards, documents = _case_material(rng=rng, case_id=case_id)
    return SyntheticCaseTimeline(
        case_id=case_id,
        case_reference=case_reference,
        district_code=district_code,
        events=ordered,
        parcels=parcels,
        ownership_records=ownership_records,
        awards=awards,
        document_extractions=documents,
        label=_label_for(events=events, occurrence_days=occurrence_days, rng=rng, closed=closed),
    )


def generate_district(
    *,
    case_count: int = DEFAULT_CASE_COUNT,
    seed: int = DEFAULT_SEED,
    base_day: date = date(2021, 1, 1),
    state_key: str = SYNTHETIC_STATE,
    act_key: str = SYNTHETIC_ACT,
    district_code: str = SYNTHETIC_DISTRICT,
    backdated_fraction: float = 0.12,
    closed_fraction: float = 0.90,
) -> tuple[SyntheticCaseTimeline, ...]:
    rng = random.Random(seed)
    timelines: list[SyntheticCaseTimeline] = []
    next_event_id = 1
    for case_index in range(case_count):
        timeline = generate_case_timeline(
            case_index=case_index,
            event_id_start=next_event_id,
            rng=rng,
            base_day=base_day,
            state_key=state_key,
            act_key=act_key,
            district_code=district_code,
            backdated_fraction=backdated_fraction,
            closed_fraction=closed_fraction,
        )
        timelines.append(timeline)
        next_event_id += len(timeline.events)
    return tuple(timelines)


def iter_events(timelines: Iterable[SyntheticCaseTimeline]) -> Iterable[SyntheticEvent]:
    for timeline in timelines:
        yield from timeline.events


def occurred_by(events: Sequence[SyntheticEvent], as_of: datetime) -> tuple[SyntheticEvent, ...]:
    return tuple(
        sorted(
            (event for event in events if event.occurrence_time <= as_of),
            key=lambda event: (event.occurrence_time, event.id),
        )
    )


def knowable_at(events: Sequence[SyntheticEvent], as_of: datetime) -> tuple[SyntheticEvent, ...]:
    return tuple(
        sorted(
            (
                event
                for event in events
                if event.occurrence_time <= as_of and event.recording_time <= as_of
            ),
            key=lambda event: (event.occurrence_time, event.id),
        )
    )


def _json_ready(event: SyntheticEvent) -> dict[str, object]:
    row = asdict(event)
    row["occurrence_time"] = event.occurrence_time.isoformat()
    row["recording_time"] = event.recording_time.isoformat()
    return row


def write_jsonl(timelines: Iterable[SyntheticCaseTimeline], path: Path) -> int:
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in iter_events(timelines):
            handle.write(json.dumps(_json_ready(event), sort_keys=True) + "\n")
            count += 1
    return count


def write_case_jsonl(timelines: Iterable[SyntheticCaseTimeline], path: Path) -> int:
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for timeline in timelines:
            row = asdict(timeline)
            for event in row["events"]:
                event["occurrence_time"] = event["occurrence_time"].isoformat()
                event["recording_time"] = event["recording_time"].isoformat()
            label = row["label"]
            label["reference_t"] = label["reference_t"].isoformat()
            label["deadline_time"] = label["deadline_time"].isoformat()
            if label["terminal_time"] is not None:
                label["terminal_time"] = label["terminal_time"].isoformat()
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=DEFAULT_CASE_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=Path("synthetic-events.jsonl"))
    parser.add_argument("--state-key", default=SYNTHETIC_STATE)
    parser.add_argument("--act-key", default=SYNTHETIC_ACT)
    parser.add_argument("--backdated-fraction", type=float, default=0.12)
    parser.add_argument("--closed-fraction", type=float, default=0.90)
    parser.add_argument("--case-out", type=Path)
    args = parser.parse_args()

    timelines = generate_district(
        case_count=args.cases,
        seed=args.seed,
        state_key=args.state_key,
        act_key=args.act_key,
        backdated_fraction=args.backdated_fraction,
        closed_fraction=args.closed_fraction,
    )
    count = write_jsonl(timelines, args.out)
    case_count = write_case_jsonl(timelines, args.case_out) if args.case_out else None
    print(
        json.dumps(
            {
                "cases": len(timelines),
                "case_rows": case_count,
                "events": count,
                "out": str(args.out),
            }
        )
    )


if __name__ == "__main__":
    main()
