"""Configured validation rules for task 13.3.

Rules operate on ``RuleContext`` rows, so the same functions run against database
lookups and preloaded import chunks. Severity remains configuration-owned: every
rule carries only a policy key, and ``ValidationEngine`` resolves that key at the
case's state/date.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Callable, Iterable, Mapping, Sequence

from app.services.validation import Rule, RuleContext, Violation

__all__ = [
    "AWARD_TOTAL_RULE_ID",
    "AREA_DIVERGENCE_RULE_ID",
    "DEFAULT_RULES",
    "DUPLICATE_OWNERSHIP_RULE_ID",
    "DUPLICATE_PARCEL_RULE_ID",
    "PARCEL_OVERLAP_RULE_ID",
    "SHARE_SUM_RULE_ID",
    "area_divergence_rule",
    "award_total_rule",
    "cross_document_consistency_rule",
    "date_chronology_rule",
    "duplicate_ownership_overlap_rule",
    "duplicate_parcel_identity_rule",
    "parcel_overlap_rule",
    "required_field_rule",
    "share_sum_rule",
    "tolerance_rule",
]

SHARE_SUM_RULE_ID = "share_sum"
AWARD_TOTAL_RULE_ID = "award_total"
DUPLICATE_PARCEL_RULE_ID = "duplicate_parcel_identity"
DUPLICATE_OWNERSHIP_RULE_ID = "duplicate_ownership_overlap"
AREA_DIVERGENCE_RULE_ID = "area_divergence"
PARCEL_OVERLAP_RULE_ID = "parcel_overlap"

SHARE_SUM_TOLERANCE = Decimal("0.0001")
AWARD_TOTAL_TOLERANCE = Decimal("0.01")
AREA_DIVERGENCE_FRACTION = Decimal("0.05")
PARCEL_OVERLAP_FRACTION = Decimal("0.01")
SQM_PER_HECTARE = Decimal("10000")
SQM_PER_ACRE = Decimal("4046.8564224")
ONE = Decimal("1")


def _severity_key(rule_id: str) -> str:
    return f"validation.severity.{rule_id}"


def required_field_rule(
    entity_type: str,
    field: str,
    *,
    rule_id: str | None = None,
) -> Rule:
    rid = rule_id or f"required_field.{entity_type}.{field}"

    def evaluate(context: RuleContext) -> Iterable[Violation]:
        for row in context.values(entity_type):
            value = row.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                yield Violation(
                    rid,
                    ((_entity_ref(entity_type, row)),),
                    {"entity_type": entity_type, "field": field, "value": value},
                )

    return Rule(rid, "required-field", _severity_key(rid), evaluate)


def date_chronology_rule(
    entity_type: str,
    later_field: str,
    earlier_field: str,
    *,
    rule_id: str | None = None,
) -> Rule:
    rid = rule_id or f"date_chronology.{entity_type}.{earlier_field}.{later_field}"

    def evaluate(context: RuleContext) -> Iterable[Violation]:
        for row in context.values(entity_type):
            earlier = row.get(earlier_field)
            later = row.get(later_field)
            if isinstance(earlier, date) and isinstance(later, date) and later < earlier:
                yield Violation(
                    rid,
                    ((_entity_ref(entity_type, row)),),
                    {earlier_field: earlier.isoformat(), later_field: later.isoformat()},
                )

    return Rule(rid, "date-chronology", _severity_key(rid), evaluate)


def cross_document_consistency_rule(
    *,
    entity_type: str = "extracted_field",
    value_field: str = "admitted_value",
    field_key: str = "field_key",
    document_key: str = "document_id",
    rule_id: str = "cross_document_consistency",
) -> Rule:
    def evaluate(context: RuleContext) -> Iterable[Violation]:
        grouped: dict[object, list[Mapping[str, object]]] = defaultdict(list)
        for row in context.values(entity_type):
            grouped[row.get(field_key)].append(row)
        for key, rows in grouped.items():
            values_by_document = {
                row.get(document_key): _normalise_value(row.get(value_field))
                for row in rows
                if row.get(document_key) is not None
            }
            if len(set(values_by_document.values())) > 1:
                yield Violation(
                    rule_id,
                    tuple(_entity_ref(entity_type, row) for row in rows),
                    {"field_key": key, "values_by_document": values_by_document},
                )

    return Rule(rule_id, "cross-document-consistency", _severity_key(rule_id), evaluate)


def duplicate_parcel_identity_rule() -> Rule:
    def evaluate(context: RuleContext) -> Iterable[Violation]:
        grouped: dict[tuple[object, ...], list[Mapping[str, object]]] = defaultdict(list)
        for row in context.values("land_parcel"):
            key = (
                row.get("state_key"),
                row.get("district"),
                row.get("tehsil"),
                _normalise_value(row.get("village_norm") or row.get("village")),
                row.get("survey_number"),
                row.get("sub_division") or "",
            )
            grouped[key].append(row)
        for key, rows in grouped.items():
            if len(rows) > 1:
                yield Violation(
                    DUPLICATE_PARCEL_RULE_ID,
                    tuple(_entity_ref("land_parcel", row) for row in rows),
                    {"identity": key},
                )

    return Rule(
        DUPLICATE_PARCEL_RULE_ID,
        "duplicate-parcel",
        _severity_key(DUPLICATE_PARCEL_RULE_ID),
        evaluate,
    )


def duplicate_ownership_overlap_rule() -> Rule:
    def evaluate(context: RuleContext) -> Iterable[Violation]:
        grouped: dict[tuple[object, object], list[Mapping[str, object]]] = defaultdict(list)
        for row in context.values("ownership_record"):
            owner_key = row.get("owner_identity_key")
            if owner_key is None:
                continue
            grouped[(row.get("parcel_id"), owner_key)].append(row)
        for (parcel_id, owner_key), rows in grouped.items():
            ordered = sorted(rows, key=lambda row: (row.get("valid_from") or date.min, row.get("id") or 0))
            for index, left in enumerate(ordered):
                for right in ordered[index + 1 :]:
                    if _date_ranges_overlap(left.get("valid_from"), left.get("valid_to"), right.get("valid_from"), right.get("valid_to")):
                        yield Violation(
                            DUPLICATE_OWNERSHIP_RULE_ID,
                            (_entity_ref("ownership_record", left), _entity_ref("ownership_record", right)),
                            {"parcel_id": parcel_id, "owner_identity_key": owner_key},
                        )

    return Rule(
        DUPLICATE_OWNERSHIP_RULE_ID,
        "duplicate-ownership-overlap",
        _severity_key(DUPLICATE_OWNERSHIP_RULE_ID),
        evaluate,
    )


def tolerance_rule(
    *,
    rule_id: str,
    entity_type: str,
    observed_label: str,
    tolerance: Decimal,
    target: Decimal = Decimal("0"),
    rows: Callable[[RuleContext], Iterable[Sequence[Mapping[str, object]]]],
    observed: Callable[[Sequence[Mapping[str, object]]], Decimal | None],
) -> Rule:
    def evaluate(context: RuleContext) -> Iterable[Violation]:
        for group_rows in rows(context):
            value = observed(group_rows)
            if value is None:
                continue
            delta = abs(value - target)
            if delta > tolerance:
                yield Violation(
                    rule_id,
                    tuple(_entity_ref(entity_type, row) for row in group_rows),
                    {
                        observed_label: str(value),
                        "target": str(target),
                        "tolerance": str(tolerance),
                        "delta": str(delta),
                    },
                )

    return Rule(rule_id, "tolerance", _severity_key(rule_id), evaluate)


def share_sum_rule() -> Rule:
    def rows(context: RuleContext) -> Iterable[Sequence[Mapping[str, object]]]:
        grouped: dict[object, list[Mapping[str, object]]] = defaultdict(list)
        for row in context.values("ownership_record"):
            if row.get("valid_to") is None:
                grouped[row.get("parcel_id")].append(row)
        return tuple(tuple(group) for group in grouped.values() if group)

    def observed(group_rows: Sequence[Mapping[str, object]]) -> Decimal | None:
        return _decimal_sum(row.get("share") for row in group_rows)

    return tolerance_rule(
        rule_id=SHARE_SUM_RULE_ID,
        entity_type="ownership_record",
        observed_label="share_sum",
        target=ONE,
        tolerance=SHARE_SUM_TOLERANCE,
        rows=rows,
        observed=observed,
    )


def award_total_rule() -> Rule:
    def evaluate(context: RuleContext) -> Iterable[Violation]:
        awards = {row.get("id"): row for row in context.values("award")}
        components: dict[object, list[Mapping[str, object]]] = defaultdict(list)
        for component in context.values("award_component"):
            components[component.get("award_id")].append(component)
        for award_id, group in components.items():
            award = awards.get(award_id)
            if award is None:
                continue
            component_sum = _decimal_sum(row.get("amount") for row in group)
            total = _to_decimal(award.get("total_amount"))
            if component_sum is None or total is None:
                continue
            delta_value = component_sum - total
            delta = abs(delta_value)
            if delta > AWARD_TOTAL_TOLERANCE:
                yield Violation(
                    AWARD_TOTAL_RULE_ID,
                    (
                        _entity_ref("award", award),
                        *(_entity_ref("award_component", row) for row in group),
                    ),
                    {
                        "component_minus_total": str(delta_value),
                        "target": "0",
                        "tolerance": str(AWARD_TOTAL_TOLERANCE),
                        "delta": str(delta),
                    },
                )

    return Rule(
        AWARD_TOTAL_RULE_ID,
        "tolerance",
        _severity_key(AWARD_TOTAL_RULE_ID),
        evaluate,
    )


def area_divergence_rule() -> Rule:
    def rows(context: RuleContext) -> Iterable[Sequence[Mapping[str, object]]]:
        return tuple((row,) for row in context.values("land_parcel"))

    def observed(group_rows: Sequence[Mapping[str, object]]) -> Decimal | None:
        [row] = group_rows
        recorded_sqm = _extent_to_sqm(row.get("extent"), row.get("extent_unit"))
        geodesic_sqm = _to_decimal(row.get("geodesic_area_sqm"))
        if recorded_sqm is None or geodesic_sqm is None or recorded_sqm == 0:
            return None
        return abs(geodesic_sqm - recorded_sqm) / recorded_sqm

    return tolerance_rule(
        rule_id=AREA_DIVERGENCE_RULE_ID,
        entity_type="land_parcel",
        observed_label="area_divergence_fraction",
        target=Decimal("0"),
        tolerance=AREA_DIVERGENCE_FRACTION,
        rows=rows,
        observed=observed,
    )


def parcel_overlap_rule() -> Rule:
    def evaluate(context: RuleContext) -> Iterable[Violation]:
        for row in context.values("parcel_overlap"):
            fraction = _to_decimal(row.get("overlap_fraction"))
            if fraction is None or fraction <= PARCEL_OVERLAP_FRACTION:
                continue
            left_id = int(row["left_parcel_id"])
            right_id = int(row["right_parcel_id"])
            yield Violation(
                PARCEL_OVERLAP_RULE_ID,
                (("land_parcel", left_id), ("land_parcel", right_id)),
                {
                    "left_parcel_id": left_id,
                    "right_parcel_id": right_id,
                    "overlap_fraction": str(fraction),
                    "tolerance": str(PARCEL_OVERLAP_FRACTION),
                },
            )

    return Rule(
        PARCEL_OVERLAP_RULE_ID,
        "tolerance",
        _severity_key(PARCEL_OVERLAP_RULE_ID),
        evaluate,
    )


DEFAULT_RULES: tuple[Rule, ...] = (
    duplicate_parcel_identity_rule(),
    duplicate_ownership_overlap_rule(),
    share_sum_rule(),
    award_total_rule(),
    area_divergence_rule(),
    parcel_overlap_rule(),
    cross_document_consistency_rule(),
)


def _entity_ref(entity_type: str, row: Mapping[str, object]) -> tuple[str, int]:
    return (entity_type, int(row["id"]))


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _decimal_sum(values: Iterable[object]) -> Decimal | None:
    total = Decimal("0")
    for value in values:
        decimal = _to_decimal(value)
        if decimal is None:
            return None
        total += decimal
    return total


def _extent_to_sqm(extent: object, unit: object) -> Decimal | None:
    value = _to_decimal(extent)
    if value is None or not isinstance(unit, str):
        return None
    normalised = unit.strip().lower()
    if normalised in {"hectare", "hectares", "ha"}:
        return value * SQM_PER_HECTARE
    if normalised in {"acre", "acres"}:
        return value * SQM_PER_ACRE
    return None


def _normalise_value(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _date_ranges_overlap(
    left_from: object,
    left_to: object,
    right_from: object,
    right_to: object,
) -> bool:
    if not isinstance(left_from, date) or not isinstance(right_from, date):
        return False
    left_end = left_to if isinstance(left_to, date) else date.max
    right_end = right_to if isinstance(right_to, date) else date.max
    return left_from <= right_end and right_from <= left_end
