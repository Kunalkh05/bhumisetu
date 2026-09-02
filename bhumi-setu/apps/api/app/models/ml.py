"""Machine-learning storage tables (§6.3, task 22.1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Double, ForeignKey, Index, Integer, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = [
    "MLExplanationFactor",
    "MLFeatureRow",
    "MLModelVersion",
    "MLMonitorRun",
    "MLPrediction",
    "MLTrainingRow",
]


class MLFeatureRow(Base):
    """A cache of a pure feature-build over event ids, never a source of truth."""

    __tablename__ = "ml_feature_row"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_case.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reference_t: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    as_of_mode: Mapped[str] = mapped_column(Text, nullable=False)
    feature_set_version: Mapped[str] = mapped_column(Text, nullable=False)
    label_definition_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    features: Mapped[Any] = mapped_column(JSONB, nullable=False)
    consumed_event_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "reference_t",
            "as_of_mode",
            "feature_set_version",
            "purpose",
            name="ml_feature_row_unique_reference",
        ),
    )


class MLTrainingRow(Base):
    """A label attached to a feature row for trainer input."""

    __tablename__ = "ml_training_row"

    feature_row_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ml_feature_row.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    time_to_event_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_observed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    label_definition_version: Mapped[str] = mapped_column(Text, nullable=False)
    split: Mapped[str | None] = mapped_column(Text, nullable=True)


class MLModelVersion(Base):
    """A retained model artifact plus the evidence needed to monitor it."""

    __tablename__ = "ml_model_version"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    feature_set_version: Mapped[str] = mapped_column(Text, nullable=False)
    label_definition_version: Mapped[str] = mapped_column(Text, nullable=False)
    training_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    training_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hyperparameters: Mapped[Any] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[Any] = mapped_column(JSONB, nullable=False)
    baseline_metrics: Mapped[Any] = mapped_column(JSONB, nullable=False)
    train_base_rate: Mapped[float] = mapped_column(Double, nullable=False)
    eval_base_rate: Mapped[float] = mapped_column(Double, nullable=False)
    censored_count: Mapped[int] = mapped_column(Integer, nullable=False)
    censoring_rate: Mapped[float] = mapped_column(Double, nullable=False)
    feature_reference_bins: Mapped[Any] = mapped_column(JSONB, nullable=False)
    promotion_state: Mapped[str] = mapped_column(Text, nullable=False)
    promoted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("officer.id", ondelete="RESTRICT"),
        nullable=True,
    )
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    artifact_object_key: Mapped[str] = mapped_column(Text, nullable=False)
    superseded_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ml_model_version.id", ondelete="RESTRICT"),
        nullable=True,
    )


class MLPrediction(Base):
    """Every generated score, retained by model and feature row for audit."""

    __tablename__ = "ml_prediction"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_case.id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ml_model_version.id", ondelete="RESTRICT"),
        nullable=False,
    )
    feature_row_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ml_feature_row.id", ondelete="RESTRICT"),
        nullable=False,
    )
    risk_probability: Mapped[float] = mapped_column(Double, nullable=False)
    risk_band: Mapped[str] = mapped_column(Text, nullable=False)
    cutoff_source: Mapped[str] = mapped_column(Text, nullable=False)
    cutoff_set_version: Mapped[str] = mapped_column(Text, nullable=False)
    reference_t: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "model_version_id",
            "feature_row_id",
            name="ml_prediction_idempotency",
        ),
        Index("ml_prediction_history", case_id, text("generated_at DESC")),
    )


class MLExplanationFactor(Base):
    """One ranked TreeSHAP-style explanation factor for a prediction."""

    __tablename__ = "ml_explanation_factor"

    prediction_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ml_prediction.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    rank: Mapped[int] = mapped_column(Integer, primary_key=True)
    feature_name: Mapped[str] = mapped_column(Text, nullable=False)
    label_key: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    magnitude: Mapped[float] = mapped_column(Double, nullable=False)


class MLMonitorRun(Base):
    """One calibration or drift monitoring run, including crashed RUNNING rows."""

    __tablename__ = "ml_monitor_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ml_model_version.id", ondelete="RESTRICT"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    withholding_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluable_case_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    results: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
