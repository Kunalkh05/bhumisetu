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
class SyntheticCaseTimeline:
    case_id: int
    case_reference: str
    events: tuple[SyntheticEvent, ...]


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


def generate_case_timeline(
    *,
    case_index: int,
    event_id_start: int,
    rng: random.Random,
    base_day: date,
    state_key: str = SYNTHETIC_STATE,
    act_key: str = SYNTHETIC_ACT,
    backdated_fraction: float = 0.12,
) -> SyntheticCaseTimeline:
    """Generate one append-ordered case timeline.

    The ordinary stage events are recorded after their occurrence by a mixed lag
    distribution. Some cases also receive a late-recorded objection fact whose
    occurrence predates an event already stored for that case.
    """
    case_id = case_index + 1
    case_reference = f"SYN-{state_key}-{case_id:05d}"
    start_day = base_day + timedelta(days=rng.randint(0, 365 * 3))
    occurrence_days = [start_day]
    for duration in _stage_durations(rng):
        occurrence_days.append(occurrence_days[-1] + timedelta(days=duration))

    events: list[SyntheticEvent] = []
    for offset, ((event_type, stage_key), occurrence_day) in enumerate(
        zip(STAGE_EVENTS, occurrence_days, strict=True)
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

    if rng.random() < backdated_fraction:
        anchor = rng.randint(2, len(events) - 2)
        occurrence_time = events[anchor - 1].occurrence_time + timedelta(days=1)
        recording_time = events[anchor + 1].recording_time + timedelta(days=rng.randint(1, 10))
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
    return SyntheticCaseTimeline(
        case_id=case_id,
        case_reference=case_reference,
        events=ordered,
    )


def generate_district(
    *,
    case_count: int = DEFAULT_CASE_COUNT,
    seed: int = DEFAULT_SEED,
    base_day: date = date(2021, 1, 1),
    state_key: str = SYNTHETIC_STATE,
    act_key: str = SYNTHETIC_ACT,
    backdated_fraction: float = 0.12,
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
            backdated_fraction=backdated_fraction,
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=DEFAULT_CASE_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=Path("synthetic-events.jsonl"))
    parser.add_argument("--state-key", default=SYNTHETIC_STATE)
    parser.add_argument("--act-key", default=SYNTHETIC_ACT)
    parser.add_argument("--backdated-fraction", type=float, default=0.12)
    args = parser.parse_args()

    timelines = generate_district(
        case_count=args.cases,
        seed=args.seed,
        state_key=args.state_key,
        act_key=args.act_key,
        backdated_fraction=args.backdated_fraction,
    )
    count = write_jsonl(timelines, args.out)
    print(json.dumps({"cases": len(timelines), "events": count, "out": str(args.out)}))


if __name__ == "__main__":
    main()
