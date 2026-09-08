"""Disabled-by-default personal-data erasure sweep (task 25.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Iterable, Mapping

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.base import all_metadata
from app.db.event_log import EventLog
from app.models.acquisition_case import AcquisitionCase
from app.models.award import Award
from app.models.case_parcel import CaseParcel
from app.models.document import Document
from app.models.event import Event, Provenance
from app.models.extraction import ExtractedField, Extraction
from app.models.ml import MLFeatureRow
from app.models.ownership_record import OwnershipRecord
from app.models.payout import Payout
from app.models.personal_datum import PersonalDatum
from app.retention.categories import (
    CATEGORY_MAP,
    PERSONAL_DATA_CATEGORIES,
    Discriminated,
    Reference,
)
from app.retention.projection import (
    record_retention_withholding,
    retention_period_key,
)
from app.services.policy import PolicyResolver

__all__ = [
    "ErasableAttributeTarget",
    "RetentionSweepResult",
    "SYSTEM_RETENTION_ACTOR",
    "due_for_erasure",
    "erase_target",
    "run_retention_sweep",
    "sweep_enabled",
]

SWEEP_ENABLED_KEY = "retention.sweep_enabled"
ERASABLE_CATEGORIES_KEY = "retention.erasable_categories"


@dataclass(frozen=True)
class _SystemRetentionActor:
    kind: str = "SYSTEM"
    id: str = "retention-sweep"


SYSTEM_RETENTION_ACTOR = _SystemRetentionActor()


@dataclass(frozen=True)
class ErasableAttributeTarget:
    table_name: str
    column_name: str
    data_category: str


@dataclass(frozen=True)
class RetentionSweepResult:
    enabled: bool
    scanned: int = 0
    erased: int = 0
    withheld: int = 0


def sweep_enabled(
    resolver: PolicyResolver,
    *,
    today: date,
    state: str = "*",
    act: str | None = None,
) -> bool:
    """Return true only when policy explicitly enables irreversible erasure."""

    return resolver.try_get(SWEEP_ENABLED_KEY, state=state, act=act, as_of=today) is True


def due_for_erasure() -> tuple[ErasableAttributeTarget, ...]:
    """Derive nullable entity-column targets from ``CATEGORY_MAP``.

    ``personal_datum`` is the second sweep arm and is handled separately. A
    nullable-column filter keeps non-null keys or statutory record columns from
    being nulled while still making new nullable personal columns visible here
    without adding them to another list.
    """

    metadata = all_metadata()
    targets: list[ErasableAttributeTarget] = []
    for (table_name, column_name), entry in CATEGORY_MAP.items():
        if table_name == PersonalDatum.__tablename__:
            continue
        table = metadata.tables.get(table_name)
        if table is None or column_name not in table.c:
            continue
        column = table.c[column_name]
        if not column.nullable:
            continue
        for category in _possible_categories(entry):
            if category in PERSONAL_DATA_CATEGORIES:
                targets.append(
                    ErasableAttributeTarget(
                        table_name=table_name,
                        column_name=column_name,
                        data_category=category,
                    )
                )
    return tuple(sorted(targets, key=lambda item: (item.table_name, item.column_name, item.data_category)))


def run_retention_sweep(
    session: Session,
    *,
    today: date,
    resolver: PolicyResolver,
    actor: Any = SYSTEM_RETENTION_ACTOR,
    targets: Iterable[ErasableAttributeTarget] | None = None,
) -> RetentionSweepResult:
    if not sweep_enabled(resolver, today=today):
        return RetentionSweepResult(enabled=False)

    allowed_categories = _erasable_categories(resolver, today=today)
    scanned = erased = withheld = 0
    for target in tuple(targets) if targets is not None else due_for_erasure():
        if target.data_category not in allowed_categories:
            continue
        for candidate in _entity_candidates(session, target):
            scanned += 1
            did_erase, did_withhold = erase_target(
                session,
                candidate,
                target=target,
                today=today,
                resolver=resolver,
                actor=actor,
            )
            erased += int(did_erase)
            withheld += int(did_withhold)

    for candidate in _personal_datum_candidates(session, allowed_categories):
        scanned += 1
        did_erase, did_withhold = erase_personal_datum(
            session,
            candidate,
            today=today,
            resolver=resolver,
            actor=actor,
        )
        erased += int(did_erase)
        withheld += int(did_withhold)

    session.flush()
    return RetentionSweepResult(enabled=True, scanned=scanned, erased=erased, withheld=withheld)


def erase_target(
    session: Session,
    candidate: Mapping[str, Any],
    *,
    target: ErasableAttributeTarget,
    today: date,
    resolver: PolicyResolver,
    actor: Any = SYSTEM_RETENTION_ACTOR,
) -> tuple[bool, bool]:
    value = candidate["value"]
    if value is None:
        return (False, False)

    retention_start = candidate["retention_start"]
    if retention_start is None:
        _withhold(session, candidate, target=target, reason="RETENTION_START_UNDETERMINED")
        return (False, True)

    start_date = retention_start.date()
    period_days = resolver.try_get(
        retention_period_key(target.data_category),
        state=candidate["state_key"],
        act=candidate["act_key"],
        as_of=start_date,
    )
    if period_days is None:
        _withhold(session, candidate, target=target, reason="RETENTION_PERIOD_MISSING")
        return (False, True)
    if start_date + timedelta(days=int(period_days)) > today:
        return (False, False)

    entity = _load_entity(session, target.table_name, int(candidate["entity_id"]))
    prior = getattr(entity, target.column_name)
    if prior is None:
        return (False, False)
    setattr(entity, target.column_name, None)
    event = EventLog.append(
        session,
        event_type="PERSONAL_DATA_ERASED",
        entity=entity,
        actor=actor,
        changes={
            "erased_entity_id": (None, int(candidate["entity_id"])),
            "attribute_name": (None, target.column_name),
            "data_category": (None, target.data_category),
            "erasure_time": (None, _erasure_time(today).isoformat()),
        },
        occurrence_time=_erasure_time(today),
        provenance=Provenance.SYSTEM,
        case_id=candidate["case_id"],
    )
    _erase_personal_datum_rows(
        session,
        entity_type=target.table_name,
        entity_id=int(candidate["entity_id"]),
        attribute_name=target.column_name,
        data_category=target.data_category,
        erased_at=_erasure_time(today),
        event_id=event.id,
    )
    return (True, False)


def erase_personal_datum(
    session: Session,
    candidate: Mapping[str, Any],
    *,
    today: date,
    resolver: PolicyResolver,
    actor: Any = SYSTEM_RETENTION_ACTOR,
) -> tuple[bool, bool]:
    target = ErasableAttributeTarget(
        table_name=candidate["entity_type"],
        column_name=candidate["attribute_name"],
        data_category=candidate["data_category"],
    )
    if candidate["retention_start"] is None:
        _withhold(session, candidate, target=target, reason="RETENTION_START_UNDETERMINED")
        return (False, True)

    start_date = candidate["retention_start"].date()
    period_days = resolver.try_get(
        retention_period_key(candidate["data_category"]),
        state=candidate["state_key"],
        act=candidate["act_key"],
        as_of=start_date,
    )
    if period_days is None:
        _withhold(session, candidate, target=target, reason="RETENTION_PERIOD_MISSING")
        return (False, True)
    if start_date + timedelta(days=int(period_days)) > today:
        return (False, False)

    entity = _load_entity(session, candidate["entity_type"], int(candidate["entity_id"]))
    event = EventLog.append(
        session,
        event_type="PERSONAL_DATA_ERASED",
        entity=entity,
        actor=actor,
        changes={
            "erased_entity_id": (None, int(candidate["entity_id"])),
            "attribute_name": (None, candidate["attribute_name"]),
            "data_category": (None, candidate["data_category"]),
            "erasure_time": (None, _erasure_time(today).isoformat()),
        },
        occurrence_time=_erasure_time(today),
        provenance=Provenance.SYSTEM,
        case_id=candidate["case_id"],
    )
    _erase_personal_datum_rows(
        session,
        entity_type=candidate["entity_type"],
        entity_id=int(candidate["entity_id"]),
        attribute_name=candidate["attribute_name"],
        data_category=candidate["data_category"],
        erased_at=_erasure_time(today),
        event_id=event.id,
    )
    return (True, False)


def _entity_candidates(
    session: Session,
    target: ErasableAttributeTarget,
) -> tuple[Mapping[str, Any], ...]:
    metadata = all_metadata()
    table = metadata.tables[target.table_name]
    case_query = _case_query_for_table(target.table_name, table.c.id)
    if case_query is None:
        return ()

    stmt = (
        select(
            table.c.id.label("entity_id"),
            table.c[target.column_name].label("value"),
            case_query.c.case_id,
            case_query.c.state_key,
            case_query.c.act_key,
            case_query.c.retention_start,
        )
        .select_from(table.join(case_query, case_query.c.entity_id == table.c.id))
        .where(table.c[target.column_name].is_not(None))
    )
    if isinstance(CATEGORY_MAP[(target.table_name, target.column_name)], Discriminated):
        stmt = stmt.where(table.c.field_name.in_(_values_for_category(target)))
    return tuple(session.execute(stmt).mappings())


def _personal_datum_candidates(
    session: Session,
    allowed_categories: frozenset[str],
) -> tuple[Mapping[str, Any], ...]:
    branches = []
    for entity_type in sorted(_SUPPORTED_ENTITY_CLASSES):
        table = all_metadata().tables[entity_type]
        case_query = _case_query_for_table(entity_type, table.c.id)
        if case_query is None:
            continue
        branches.append(
            select(
                PersonalDatum.id.label("personal_datum_id"),
                PersonalDatum.entity_type,
                PersonalDatum.entity_id,
                PersonalDatum.attribute_name,
                PersonalDatum.data_category,
                case_query.c.case_id,
                case_query.c.state_key,
                case_query.c.act_key,
                case_query.c.retention_start,
            )
            .select_from(PersonalDatum.__table__.join(
                case_query,
                and_(
                    PersonalDatum.entity_type == entity_type,
                    PersonalDatum.entity_id == case_query.c.entity_id,
                ),
            ))
            .where(
                PersonalDatum.erased_at.is_(None),
                PersonalDatum.data_category.in_(allowed_categories),
            )
        )
    rows: list[Mapping[str, Any]] = []
    for branch in branches:
        rows.extend(session.execute(branch).mappings())
    return tuple(rows)


def _case_query_for_table(table_name: str, entity_id_column):
    if table_name == OwnershipRecord.__tablename__:
        return (
            select(
                entity_id_column.label("entity_id"),
                AcquisitionCase.id.label("case_id"),
                AcquisitionCase.state_key,
                AcquisitionCase.act_key,
                AcquisitionCase.is_terminal,
                AcquisitionCase.terminal_event_id,
                Event.occurrence_time.label("retention_start"),
            )
            .join(CaseParcel, CaseParcel.parcel_id == OwnershipRecord.parcel_id)
            .join(AcquisitionCase, AcquisitionCase.id == CaseParcel.case_id)
            .join(Event, Event.id == AcquisitionCase.terminal_event_id, isouter=True)
            .subquery()
        )
    if table_name == Payout.__tablename__:
        return (
            select(
                entity_id_column.label("entity_id"),
                AcquisitionCase.id.label("case_id"),
                AcquisitionCase.state_key,
                AcquisitionCase.act_key,
                Event.occurrence_time.label("retention_start"),
            )
            .join(Award, Award.id == Payout.award_id)
            .join(OwnershipRecord, OwnershipRecord.id == Award.ownership_record_id)
            .join(CaseParcel, CaseParcel.parcel_id == OwnershipRecord.parcel_id)
            .join(AcquisitionCase, AcquisitionCase.id == CaseParcel.case_id)
            .join(Event, Event.id == AcquisitionCase.terminal_event_id, isouter=True)
            .subquery()
        )
    if table_name == ExtractedField.__tablename__:
        return (
            select(
                entity_id_column.label("entity_id"),
                AcquisitionCase.id.label("case_id"),
                AcquisitionCase.state_key,
                AcquisitionCase.act_key,
                Event.occurrence_time.label("retention_start"),
            )
            .join(Extraction, Extraction.id == ExtractedField.extraction_id)
            .join(Document, Document.id == Extraction.document_id)
            .join(
                CaseParcel,
                and_(Document.case_id.is_(None), CaseParcel.parcel_id == Document.parcel_id),
                isouter=True,
            )
            .join(AcquisitionCase, AcquisitionCase.id == func.coalesce(Document.case_id, CaseParcel.case_id))
            .join(Event, Event.id == AcquisitionCase.terminal_event_id, isouter=True)
            .subquery()
        )
    if table_name == MLFeatureRow.__tablename__:
        return (
            select(
                entity_id_column.label("entity_id"),
                AcquisitionCase.id.label("case_id"),
                AcquisitionCase.state_key,
                AcquisitionCase.act_key,
                Event.occurrence_time.label("retention_start"),
            )
            .join(AcquisitionCase, AcquisitionCase.id == MLFeatureRow.case_id)
            .join(Event, Event.id == AcquisitionCase.terminal_event_id, isouter=True)
            .subquery()
        )
    return None


def _withhold(
    session: Session,
    candidate: Mapping[str, Any],
    *,
    target: ErasableAttributeTarget,
    reason: str,
) -> None:
    record_retention_withholding(
        session,
        entity_type=target.table_name,
        entity_id=int(candidate["entity_id"]),
        attribute_name=target.column_name,
        data_category=target.data_category,
        reason=reason,
        retention_start=candidate["retention_start"],
        policy_key=retention_period_key(target.data_category),
    )


def _erase_personal_datum_rows(
    session: Session,
    *,
    entity_type: str,
    entity_id: int,
    attribute_name: str,
    data_category: str,
    erased_at: datetime,
    event_id: int,
) -> None:
    rows = session.execute(
        select(PersonalDatum).where(
            PersonalDatum.entity_type == entity_type,
            PersonalDatum.entity_id == entity_id,
            PersonalDatum.attribute_name == attribute_name,
            PersonalDatum.data_category == data_category,
            PersonalDatum.erased_at.is_(None),
        )
    ).scalars()
    for row in rows:
        row.value_ciphertext = None
        row.erased_at = erased_at
        row.erasure_event_id = event_id


def _erasable_categories(resolver: PolicyResolver, *, today: date) -> frozenset[str]:
    configured = resolver.try_get(
        ERASABLE_CATEGORIES_KEY,
        state="*",
        act=None,
        as_of=today,
    )
    if configured is None:
        return PERSONAL_DATA_CATEGORIES
    return frozenset(configured) & PERSONAL_DATA_CATEGORIES


def _possible_categories(entry: str | Discriminated | Reference) -> frozenset[str]:
    if isinstance(entry, Discriminated):
        return entry.possible_categories()
    if isinstance(entry, Reference):
        return PERSONAL_DATA_CATEGORIES
    return frozenset({entry})


def _values_for_category(target: ErasableAttributeTarget) -> tuple[str, ...]:
    entry = CATEGORY_MAP[(target.table_name, target.column_name)]
    if not isinstance(entry, Discriminated):
        return ()
    return tuple(
        value
        for value, category in entry.by_value.items()
        if category == target.data_category
    )


def _load_entity(session: Session, table_name: str, entity_id: int) -> Any:
    model = _SUPPORTED_ENTITY_CLASSES[table_name]
    entity = session.get(model, entity_id, populate_existing=True)
    if entity is None:
        raise LookupError(f"{table_name} {entity_id} disappeared during retention sweep")
    return entity


def _erasure_time(today: date) -> datetime:
    return datetime(today.year, today.month, today.day, tzinfo=UTC)


_SUPPORTED_ENTITY_CLASSES = {
    OwnershipRecord.__tablename__: OwnershipRecord,
    Payout.__tablename__: Payout,
    ExtractedField.__tablename__: ExtractedField,
    MLFeatureRow.__tablename__: MLFeatureRow,
}
