"""Educational Kaplan-Meier Estimator — NOT a production survival library.

Implemented strictly using the Python standard library (no numpy, no pandas, no scipy, no lifelines).

Mathematical Formulation:
    S(t) = ∏_{t_i ≤ t} (1 - d_i / n_i)

Where:
    t_i: Distinct, sorted event times where at least one event occurred (d_i > 0).
    n_i: Number of subjects at risk immediately before event time t_i (duration ≥ t_i).
    d_i: Number of observed events at event time t_i.
    c_i: Number of right-censored observations in the interval [t_i, t_{i+1}).

Tie Handling Convention:
    When an event and a censoring observation occur at the exact same duration T:
    1. Both are counted in the risk set n(T) because the censored subject was observed at risk up to T.
    2. The events d(T) are processed first at time T, reducing the survival probability S(T).
    3. The censored observations exit the risk set immediately after T, and do not contribute to risk sets for t > T.

Censoring Handling:
    Observations censored at duration C < t_i exit the risk set prior to t_i and are not included in n_i.
    Arithmetic balance is preserved across every event interval: n_{i+1} = n_i - d_i - c_i.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

LABEL = "Educational Kaplan-Meier estimator — not production survival library"


@dataclass(frozen=True)
class KaplanMeierTableEntry:
    """A single row in the Kaplan-Meier lifecycle survival table."""

    time: int | float
    number_at_risk: int
    number_events: int
    number_censored: int
    survival_probability: float
    cumulative_hazard: float
    standard_error: float
    confidence_interval_lower: float
    confidence_interval_upper: float


@dataclass(frozen=True)
class KaplanMeierModel:
    """Fitted Kaplan-Meier model containing the survival curve and metadata."""

    label: str
    transition: str | None
    total_observations: int
    total_events: int
    total_censored: int
    censored_before_first_event: int
    table: tuple[KaplanMeierTableEntry, ...]

    def predict_survival(self, t: int | float) -> float:
        """Predict S(t) using the non-parametric step-function.
        
        For t < first_event_time: S(t) = 1.0.
        For t_i <= t < t_{i+1}: S(t) = S(t_i).
        For t >= last_event_time: S(t) = S(t_last).
        """
        if not self.table or t < self.table[0].time:
            return 1.0

        current_s = 1.0
        for entry in self.table:
            if t >= entry.time:
                current_s = entry.survival_probability
            else:
                break
        return current_s

    def survival_at_horizons(
        self, horizons: Sequence[int | float] = (30, 90, 180, 365, 730)
    ) -> dict[int | float, float]:
        """Return S(t) evaluated at specific landmark day horizons."""
        return {h: self.predict_survival(h) for h in horizons}

    def summary_table(self) -> list[dict[str, Any]]:
        """Return the event table as a list of dictionaries."""
        return [asdict(e) for e in self.table]

    def export_csv(self, target_path: str | Path) -> Path:
        """Export the survival table to CSV."""
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "time",
            "number_at_risk",
            "number_events",
            "number_censored",
            "survival_probability",
            "cumulative_hazard",
            "standard_error",
            "confidence_interval_lower",
            "confidence_interval_upper",
        ]
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in self.table:
                d = asdict(entry)
                writer.writerow({k: round(v, 6) if isinstance(v, float) else v for k, v in d.items()})
        return path


class EducationalKaplanMeier:
    """Educational implementation of the non-parametric Kaplan-Meier estimator."""

    def __init__(self, label: str = LABEL) -> None:
        self.label = label

    def fit(
        self,
        durations: Sequence[int | float],
        events: Sequence[bool | int],
        *,
        transition: str | None = None,
    ) -> KaplanMeierModel:
        """Fit the Kaplan-Meier survival curve.
        
        Args:
            durations: Non-negative observation durations.
            events: True / 1 if event observed; False / 0 if right-censored.
            transition: Optional transition label for metadata tracking.
        """
        if len(durations) != len(events):
            raise ValueError(
                f"Durations length ({len(durations)}) != events length ({len(events)})"
            )
        if len(durations) == 0:
            raise ValueError("Cannot fit Kaplan-Meier on an empty dataset.")

        clean_events: list[bool] = [bool(e) for e in events]
        clean_durations: list[int | float] = list(durations)

        for d in clean_durations:
            if d < 0:
                raise ValueError(f"Negative duration encountered: {d}")

        total_obs = len(clean_durations)
        total_events = sum(1 for e in clean_events if e)
        total_censored = total_obs - total_events

        # Edge Case: Zero events observed
        if total_events == 0:
            return KaplanMeierModel(
                label=self.label,
                transition=transition,
                total_observations=total_obs,
                total_events=0,
                total_censored=total_censored,
                censored_before_first_event=total_censored,
                table=(),
            )

        # Find all unique sorted event times
        event_times = sorted(set(d for d, e in zip(clean_durations, clean_events) if e))

        # Check for any censorings occurring strictly before the first event
        censored_before_t1 = sum(
            1 for d, e in zip(clean_durations, clean_events) if not e and d < event_times[0]
        )

        table_entries: list[KaplanMeierTableEntry] = []
        current_s = 1.0
        greenwood_sum = 0.0

        for idx, t in enumerate(event_times):
            next_t = event_times[idx + 1] if idx + 1 < len(event_times) else float("inf")

            # Risk set: all individuals whose duration >= t
            n_at_risk = sum(1 for d in clean_durations if d >= t)

            # Events at time t
            d_i = sum(1 for d, e in zip(clean_durations, clean_events) if d == t and e)

            # Censorings in the half-open interval [t, next_t)
            c_i = sum(
                1 for d, e in zip(clean_durations, clean_events) if not e and t <= d < next_t
            )

            # Kaplan-Meier product update
            current_s *= (1.0 - (d_i / n_at_risk))

            # Cumulative hazard H(t) = -log(S(t)) where S(t) > 0
            cum_hazard = -math.log(current_s) if current_s > 0 else float("inf")

            # Greenwood variance estimator
            if n_at_risk > d_i:
                greenwood_sum += d_i / (n_at_risk * (n_at_risk - d_i))
            se = current_s * math.sqrt(greenwood_sum) if current_s > 0 else 0.0

            # 95% Confidence Interval (Wald approximation bounded in [0, 1])
            ci_lower = max(0.0, current_s - 1.96 * se)
            ci_upper = min(1.0, current_s + 1.96 * se)

            table_entries.append(
                KaplanMeierTableEntry(
                    time=t,
                    number_at_risk=n_at_risk,
                    number_events=d_i,
                    number_censored=c_i,
                    survival_probability=current_s,
                    cumulative_hazard=cum_hazard,
                    standard_error=se,
                    confidence_interval_lower=ci_lower,
                    confidence_interval_upper=ci_upper,
                )
            )

        return KaplanMeierModel(
            label=self.label,
            transition=transition,
            total_observations=total_obs,
            total_events=total_events,
            total_censored=total_censored,
            censored_before_first_event=censored_before_t1,
            table=tuple(table_entries),
        )

    def fit_from_csv(
        self,
        csv_path: str | Path,
        *,
        transition: str | None = None,
        duration_col: str = "duration_at_risk_days",
        event_col: str = "event_observed",
        transition_col: str = "transition",
    ) -> KaplanMeierModel:
        """Fit Kaplan-Meier from a training targets CSV file (TRAIN ONLY)."""
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        durations: list[int] = []
        events: list[bool] = []

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if transition and row.get(transition_col) != transition:
                    continue
                d = int(row[duration_col])
                e = row[event_col].strip().lower() in ("true", "1")
                durations.append(d)
                events.append(e)

        return self.fit(durations, events, transition=transition)
