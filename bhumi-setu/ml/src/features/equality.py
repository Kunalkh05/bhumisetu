"""Train/serve feature-row equality checks for production monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import ActorType, Event, Provenance
from app.models.ml import MLFeatureRow
from features.api import build_training_row

__all__ = [
    "RECENT_INFERENCE_WINDOW_SECONDS",
    "RederivationDivergence",
    "RederivationReport",
    "recent_inference_window_start",
    "verify_recent_inference_rows",
]

RECENT_INFERENCE_WINDOW_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class RederivationDivergence:
    feature_row_id: int
    case_id: int
    stored_hash: str
    rebuilt_hash: str


@dataclass(frozen=True)
class RederivationReport:
    checked_count: int
    divergences: tuple[RederivationDivergence, ...]

    @property
    def ok(self) -> bool:
        return not self.divergences

    def to_json(self) -> dict[str, Any]:
        return {
            "checked_count": self.checked_count,
            "ok": self.ok,
            "divergences": [divergence.__dict__ for divergence in self.divergences],
        }


def recent_inference_window_start(now: datetime) -> datetime:
    return now - timedelta(seconds=RECENT_INFERENCE_WINDOW_SECONDS)


def verify_recent_inference_rows(
    session: Session,
    *,
    now: datetime | None = None,
) -> RederivationReport:
    """Rebuild recent inference rows through the training entry point."""
    now = now or datetime.now(UTC)
    rows = tuple(
        session.execute(
            select(MLFeatureRow)
            .where(
                MLFeatureRow.purpose == "INFERENCE",
                MLFeatureRow.created_at >= recent_inference_window_start(now),
            )
            .order_by(MLFeatureRow.id)
        ).scalars()
    )

    divergences: list[RederivationDivergence] = []
    for stored in rows:
        rebuilt = build_training_row(
            session,
            stored.case_id,
            stored.reference_t,
            stored.feature_set_version,
        )
        if rebuilt.content_hash == stored.content_hash:
            continue
        divergence = RederivationDivergence(
            feature_row_id=stored.id,
            case_id=stored.case_id,
            stored_hash=stored.content_hash,
            rebuilt_hash=rebuilt.content_hash,
        )
        divergences.append(divergence)
        _record_divergence(session, stored, divergence, now)

    if divergences:
        session.flush()
    return RederivationReport(checked_count=len(rows), divergences=tuple(divergences))


def _record_divergence(
    session: Session,
    stored: MLFeatureRow,
    divergence: RederivationDivergence,
    now: datetime,
) -> None:
    payload = {
        "feature_row_id": divergence.feature_row_id,
        "case_id": divergence.case_id,
        "stored_hash": divergence.stored_hash,
        "rebuilt_hash": divergence.rebuilt_hash,
        "feature_set_version": stored.feature_set_version,
        "reference_t": stored.reference_t.isoformat(),
    }
    session.add(
        Event(
            event_type="TRAIN_SERVE_FEATURE_DIVERGENCE",
            entity_type="ml_feature_row",
            entity_id=stored.id,
            case_id=stored.case_id,
            actor_type=ActorType.SYSTEM,
            actor_id="ml.train_serve_rederive",
            occurrence_time=now,
            payload=payload,
            has_pd_refs=False,
            provenance=Provenance.SYSTEM,
        )
    )
    session.add(
        Event(
            event_type="MODEL_MONITORING_UNAVAILABLE",
            entity_type="ml_feature_row",
            entity_id=stored.id,
            case_id=stored.case_id,
            actor_type=ActorType.SYSTEM,
            actor_id="ml.train_serve_rederive",
            occurrence_time=now,
            payload={
                **payload,
                "reason": "TRAIN_SERVE_FEATURE_DIVERGENCE",
            },
            has_pd_refs=False,
            provenance=Provenance.SYSTEM,
        )
    )
