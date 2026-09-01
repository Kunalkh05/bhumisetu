"""Concrete validation rules (task 13.3)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from app.services.validation import ChunkRuleContext
from app.services.validation.rules import (
    AWARD_TOTAL_RULE_ID,
    AREA_DIVERGENCE_RULE_ID,
    DEFAULT_RULES,
    DUPLICATE_OWNERSHIP_RULE_ID,
    DUPLICATE_PARCEL_RULE_ID,
    PARCEL_OVERLAP_RULE_ID,
    SHARE_SUM_RULE_ID,
    area_divergence_rule,
    award_total_rule,
    cross_document_consistency_rule,
    date_chronology_rule,
    duplicate_ownership_overlap_rule,
    duplicate_parcel_identity_rule,
    parcel_overlap_rule,
    required_field_rule,
    share_sum_rule,
)


def test_required_field_rule_names_missing_field_and_entity() -> None:
    rule = required_field_rule("land_parcel", "survey_number")
    violations = list(
        rule.evaluate(
            ChunkRuleContext(
                case_id=1,
                rows={"land_parcel": ({"id": 7, "survey_number": " "},)},
            )
        )
    )

    assert violations[0].offending_entities == (("land_parcel", 7),)
    assert violations[0].observed_values["field"] == "survey_number"


def test_date_chronology_rule_flags_later_date_before_predecessor() -> None:
    rule = date_chronology_rule("statutory_notice", "response_deadline", "issue_date")
    violations = list(
        rule.evaluate(
            ChunkRuleContext(
                case_id=1,
                rows={
                    "statutory_notice": (
                        {
                            "id": 3,
                            "issue_date": date(2024, 5, 10),
                            "response_deadline": date(2024, 5, 1),
                        },
                    )
                },
            )
        )
    )

    assert violations[0].offending_entities == (("statutory_notice", 3),)


def test_duplicate_parcel_identity_folds_empty_subdivision() -> None:
    rule = duplicate_parcel_identity_rule()
    ctx = ChunkRuleContext(
        case_id=1,
        rows={
            "land_parcel": (
                _parcel(1, sub_division=None),
                _parcel(2, sub_division=""),
                _parcel(3, survey_number="88"),
            )
        },
    )

    violations = list(rule.evaluate(ctx))

    assert len(violations) == 1
    assert violations[0].rule_id == DUPLICATE_PARCEL_RULE_ID
    assert violations[0].offending_entities == (("land_parcel", 1), ("land_parcel", 2))


def test_duplicate_ownership_overlap_is_per_owner_and_parcel() -> None:
    rule = duplicate_ownership_overlap_rule()
    ctx = ChunkRuleContext(
        case_id=1,
        rows={
            "ownership_record": (
                _ownership(1, parcel_id=4, owner_identity_key="owner-a", valid_from=date(2024, 1, 1), valid_to=date(2024, 3, 1)),
                _ownership(2, parcel_id=4, owner_identity_key="owner-a", valid_from=date(2024, 2, 1), valid_to=None),
                _ownership(3, parcel_id=4, owner_identity_key="owner-b", valid_from=date(2024, 2, 1), valid_to=None),
            )
        },
    )

    violations = list(rule.evaluate(ctx))

    assert len(violations) == 1
    assert violations[0].rule_id == DUPLICATE_OWNERSHIP_RULE_ID
    assert violations[0].offending_entities == (("ownership_record", 1), ("ownership_record", 2))


def test_share_sum_rule_uses_decimal_tolerance() -> None:
    rule = share_sum_rule()
    inside = ChunkRuleContext(
        case_id=1,
        rows={
            "ownership_record": (
                _ownership(1, share=Decimal("0.50005")),
                _ownership(2, share=Decimal("0.49995")),
            )
        },
    )
    outside = ChunkRuleContext(
        case_id=1,
        rows={
            "ownership_record": (
                _ownership(1, share=Decimal("0.5002")),
                _ownership(2, share=Decimal("0.5000")),
            )
        },
    )

    assert list(rule.evaluate(inside)) == []
    violations = list(rule.evaluate(outside))
    assert violations[0].rule_id == SHARE_SUM_RULE_ID
    assert violations[0].observed_values["share_sum"] == "1.0002"
    assert violations[0].observed_values["tolerance"] == "0.0001"


def test_award_total_rule_uses_cent_tolerance_and_names_award_and_components() -> None:
    rule = award_total_rule()
    ctx = ChunkRuleContext(
        case_id=1,
        rows={
            "award": ({"id": 10, "total_amount": Decimal("100.00")},),
            "award_component": (
                {"id": 20, "award_id": 10, "amount": Decimal("60.00")},
                {"id": 21, "award_id": 10, "amount": Decimal("40.02")},
            ),
        },
    )

    violations = list(rule.evaluate(ctx))

    assert violations[0].rule_id == AWARD_TOTAL_RULE_ID
    assert violations[0].offending_entities == (
        ("award", 10),
        ("award_component", 20),
        ("award_component", 21),
    )
    assert violations[0].observed_values["delta"] == "0.02"


def test_area_divergence_rule_converts_recorded_extent_to_square_metres() -> None:
    rule = area_divergence_rule()
    inside = ChunkRuleContext(
        case_id=1,
        rows={
            "land_parcel": (
                {
                    "id": 7,
                    "extent": Decimal("2"),
                    "extent_unit": "hectare",
                    "geodesic_area_sqm": Decimal("21000"),
                },
            )
        },
    )
    outside = ChunkRuleContext(
        case_id=1,
        rows={
            "land_parcel": (
                {
                    "id": 7,
                    "extent": Decimal("2"),
                    "extent_unit": "acre",
                    "geodesic_area_sqm": Decimal("9000"),
                },
            )
        },
    )

    assert list(rule.evaluate(inside)) == []
    violations = list(rule.evaluate(outside))
    assert violations[0].rule_id == AREA_DIVERGENCE_RULE_ID
    assert violations[0].offending_entities == (("land_parcel", 7),)
    assert violations[0].observed_values["tolerance"] == "0.05"


def test_parcel_overlap_rule_names_both_parcels_above_fraction() -> None:
    rule = parcel_overlap_rule()
    ctx = ChunkRuleContext(
        case_id=1,
        rows={
            "parcel_overlap": (
                {
                    "left_parcel_id": 4,
                    "right_parcel_id": 5,
                    "overlap_fraction": Decimal("0.0100"),
                },
                {
                    "left_parcel_id": 5,
                    "right_parcel_id": 6,
                    "overlap_fraction": Decimal("0.0101"),
                },
            )
        },
    )

    violations = list(rule.evaluate(ctx))

    assert len(violations) == 1
    assert violations[0].rule_id == PARCEL_OVERLAP_RULE_ID
    assert violations[0].offending_entities == (("land_parcel", 5), ("land_parcel", 6))
    assert violations[0].observed_values["tolerance"] == "0.01"


def test_default_rules_include_geometry_validation_rules() -> None:
    rule_ids = {rule.rule_id for rule in DEFAULT_RULES}

    assert AREA_DIVERGENCE_RULE_ID in rule_ids
    assert PARCEL_OVERLAP_RULE_ID in rule_ids


def test_cross_document_consistency_groups_same_case_field() -> None:
    rule = cross_document_consistency_rule()
    ctx = ChunkRuleContext(
        case_id=1,
        rows={
            "extracted_field": (
                {"id": 1, "field_key": "owner_name", "document_id": 4, "admitted_value": "Asha"},
                {"id": 2, "field_key": "owner_name", "document_id": 5, "admitted_value": "Ravi"},
                {"id": 3, "field_key": "survey_number", "document_id": 5, "admitted_value": "77"},
            )
        },
    )

    violations = list(rule.evaluate(ctx))

    assert len(violations) == 1
    assert violations[0].offending_entities == (("extracted_field", 1), ("extracted_field", 2))
    assert violations[0].observed_values["field_key"] == "owner_name"


@given(
    first=st.decimals(
        min_value=Decimal("0.000000"),
        max_value=Decimal("1.500000"),
        places=6,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_property_share_sum_issue_exists_exactly_outside_tolerance(first: Decimal) -> None:
    second = Decimal("1") - first
    for bump, should_violate in (
        (Decimal("0.0001"), False),
        (Decimal("0.000101"), True),
    ):
        ctx = ChunkRuleContext(
            case_id=1,
            rows={
                "ownership_record": (
                    _ownership(1, share=first),
                    _ownership(2, share=second + bump),
                )
            },
        )

        violations = list(share_sum_rule().evaluate(ctx))

        assert bool(violations) is should_violate
        if violations:
            assert violations[0].rule_id == SHARE_SUM_RULE_ID
            assert violations[0].offending_entities == (
                ("ownership_record", 1),
                ("ownership_record", 2),
            )
            assert "detected_at" not in violations[0].observed_values


@given(
    total=st.decimals(
        min_value=Decimal("0.00"),
        max_value=Decimal("1000000.00"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_property_award_total_issue_exists_exactly_outside_tolerance(total: Decimal) -> None:
    for bump, should_violate in ((Decimal("0.01"), False), (Decimal("0.02"), True)):
        ctx = ChunkRuleContext(
            case_id=1,
            rows={
                "award": ({"id": 10, "total_amount": total},),
                "award_component": (
                    {"id": 20, "award_id": 10, "amount": total},
                    {"id": 21, "award_id": 10, "amount": bump},
                ),
            },
        )

        violations = list(award_total_rule().evaluate(ctx))

        assert bool(violations) is should_violate
        if violations:
            violation = violations[0]
            assert violation.rule_id == AWARD_TOTAL_RULE_ID
            assert violation.offending_entities[0] == ("award", 10)
            assert violation.observed_values["tolerance"] == "0.01"
            assert violation.observed_values["delta"] == str(bump)


@given(
    extent=st.decimals(
        min_value=Decimal("1.0000"),
        max_value=Decimal("10000.0000"),
        places=4,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_property_area_divergence_issue_exists_exactly_outside_tolerance(
    extent: Decimal,
) -> None:
    recorded_sqm = extent * Decimal("10000")
    for multiplier, should_violate in (
        (Decimal("1.05"), False),
        (Decimal("1.050001"), True),
    ):
        ctx = ChunkRuleContext(
            case_id=1,
            rows={
                "land_parcel": (
                    {
                        "id": 7,
                        "extent": extent,
                        "extent_unit": "hectare",
                        "geodesic_area_sqm": recorded_sqm * multiplier,
                    },
                )
            },
        )

        violations = list(area_divergence_rule().evaluate(ctx))

        assert bool(violations) is should_violate
        if violations:
            assert violations[0].offending_entities == (("land_parcel", 7),)


def _parcel(
    id: int,
    *,
    survey_number: str = "77",
    sub_division: str | None = None,
) -> dict[str, object]:
    return {
        "id": id,
        "state_key": "MH",
        "district": "Pune",
        "tehsil": "Haveli",
        "village": "Mulshi",
        "village_norm": "Mulshi",
        "survey_number": survey_number,
        "sub_division": sub_division,
    }


def _ownership(
    id: int,
    *,
    parcel_id: int = 4,
    owner_identity_key: str = "owner-a",
    share: Decimal = Decimal("0.5"),
    valid_from: date = date(2024, 1, 1),
    valid_to: date | None = None,
) -> dict[str, object]:
    return {
        "id": id,
        "parcel_id": parcel_id,
        "owner_identity_key": owner_identity_key,
        "share": share,
        "valid_from": valid_from,
        "valid_to": valid_to,
    }
