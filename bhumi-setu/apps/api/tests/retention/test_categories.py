"""The attribute classification registry (§17.1, R32.2).

Two things are load-bearing and are what these tests pin down:

* :func:`category_of` raises rather than defaulting on an unclassified attribute —
  a silent default is how a personal column ships unerased;
* :func:`personal_data_attributes` is *selective*. It must include the personal
  columns and exclude the non-personal ones, because the disjointness guard
  (§5.4) and the field-coverage test (§8.3) both trust it to say which attributes
  are personal. A set that returned everything, or nothing, would make either
  guard useless in a way that still passes.

Task 25.2 makes the map complete over the whole schema with a metadata walk.
"""

from __future__ import annotations

import pytest

from app import models
from app.db.base import all_metadata
from app.retention.categories import (
    AUDIT_EVENT,
    CATEGORY_MAP,
    DOCUMENT_CONTENT,
    LAND_RECORD,
    MODEL_FEATURE,
    NOT_PERSONAL,
    OWNER_CONTACT,
    OWNER_IDENTITY,
    PERSONAL_DATA_CATEGORIES,
    Discriminated,
    Reference,
    category_of,
    personal_data_attributes,
)

ALL_CATEGORIES = {
    AUDIT_EVENT,
    DOCUMENT_CONTENT,
    LAND_RECORD,
    MODEL_FEATURE,
    NOT_PERSONAL,
    OWNER_CONTACT,
    OWNER_IDENTITY,
}


# ---------------------------------------------------------------------------
# category_of: plain entries and the deliberate absence of a default
# ---------------------------------------------------------------------------


def test_a_plain_entry_returns_its_category() -> None:
    assert category_of("ownership_record", "owner_name") == OWNER_IDENTITY
    assert category_of("ownership_record", "contact_mobile") == OWNER_CONTACT
    assert category_of("ml_feature_row", "features") == MODEL_FEATURE


def test_every_column_is_classified() -> None:
    """R32.2 fails at build time when a mapped column lacks a Data_Category."""
    models.load_all_models()
    missing = [
        f"{table.name}.{column.name}"
        for table in all_metadata().sorted_tables
        for column in table.columns
        if (table.name, column.name) not in CATEGORY_MAP
    ]

    assert missing == []


def test_every_plain_category_name_is_known() -> None:
    plain = [
        f"{table}.{column}={entry}"
        for (table, column), entry in CATEGORY_MAP.items()
        if isinstance(entry, str) and entry not in ALL_CATEGORIES
    ]

    assert plain == []


def test_an_unclassified_attribute_raises_keyerror() -> None:
    """No ``.get(..., default)``. The failure is loud on purpose (§17.1)."""
    with pytest.raises(KeyError):
        category_of("ownership_record", "not_a_real_column")
    with pytest.raises(KeyError):
        category_of("table_that_does_not_exist", "whatever")


# ---------------------------------------------------------------------------
# Discriminated: the category depends on another column's value
# ---------------------------------------------------------------------------


def test_discriminated_resolves_from_the_named_column() -> None:
    assert (
        category_of("extracted_field", "extracted_value", {"field_name": "owner_name"})
        == OWNER_IDENTITY
    )
    assert (
        category_of("extracted_field", "extracted_value", {"field_name": "mobile"})
        == OWNER_CONTACT
    )
    assert (
        category_of("extracted_field", "extracted_value", {"field_name": "survey_number"})
        == LAND_RECORD
    )


def test_discriminated_uses_its_explicit_default_for_an_unlisted_value() -> None:
    """The explicit default is a real classification, not the forbidden silent one:
    an extracted field the map does not name is the safe non-erasable LAND_RECORD."""
    assert (
        category_of("extracted_field", "extracted_value", {"field_name": "khasra_no"})
        == LAND_RECORD
    )


def test_discriminated_without_a_row_raises() -> None:
    with pytest.raises(ValueError, match="without the row"):
        category_of("extracted_field", "extracted_value")


def test_discriminated_missing_the_discriminator_column_raises() -> None:
    with pytest.raises(KeyError):
        category_of("extracted_field", "extracted_value", {"something_else": "x"})


# ---------------------------------------------------------------------------
# Reference: the category is carried by the row
# ---------------------------------------------------------------------------


def test_reference_follows_the_named_column() -> None:
    assert (
        category_of("personal_datum", "value_ciphertext", {"data_category": OWNER_CONTACT})
        == OWNER_CONTACT
    )
    assert (
        category_of("personal_datum", "value_ciphertext", {"data_category": OWNER_IDENTITY})
        == OWNER_IDENTITY
    )


def test_reference_without_a_row_raises() -> None:
    with pytest.raises(ValueError, match="without the row"):
        category_of("personal_datum", "value_ciphertext")


def test_reference_missing_the_followed_column_raises() -> None:
    with pytest.raises(KeyError):
        category_of("personal_datum", "value_ciphertext", {"other": "x"})


# ---------------------------------------------------------------------------
# The personal-data set and its selectivity
# ---------------------------------------------------------------------------


def test_personal_data_categories_are_the_erasable_set() -> None:
    """These are exactly Q10's erasable categories; the guards depend on it."""
    assert PERSONAL_DATA_CATEGORIES == frozenset(
        {OWNER_CONTACT, OWNER_IDENTITY, MODEL_FEATURE}
    )
    assert LAND_RECORD not in PERSONAL_DATA_CATEGORIES
    assert NOT_PERSONAL not in PERSONAL_DATA_CATEGORIES


def test_the_map_marks_the_expected_personal_columns() -> None:
    personal = personal_data_attributes(CATEGORY_MAP)
    assert {
        "owner_name",
        "government_identifier",
        "owner_identity_key",
        "contact_mobile",
        "contact_mobile_hash",
        "objector_name",
        "extracted_value",  # Discriminated with personal branches
        "value_ciphertext",  # Reference into personal_datum
        "features",  # MODEL_FEATURE
    } <= personal


def test_personal_data_attributes_excludes_non_personal_entries() -> None:
    """Selectivity, tested on a crafted map so the assertion is exact rather than a
    subset check. A Discriminated with no personal branch is not personal; one with
    any personal branch is; a Reference is; plain non-personal categories are not."""
    sample: dict[tuple[str, str], object] = {
        ("t", "owner"): OWNER_IDENTITY,
        ("t", "share"): LAND_RECORD,
        ("t", "ref_id"): NOT_PERSONAL,
        ("t", "scan"): DOCUMENT_CONTENT,
        ("t", "mixed"): Discriminated(
            on="k", by_value={"a": OWNER_IDENTITY, "b": LAND_RECORD}, default=LAND_RECORD
        ),
        ("t", "only_land"): Discriminated(
            on="k", by_value={"a": LAND_RECORD}, default=LAND_RECORD
        ),
        ("t", "cref"): Reference(follows="data_category"),
    }
    assert personal_data_attributes(sample) == frozenset({"owner", "mixed", "cref"})


def test_personal_data_attributes_of_an_empty_map_is_empty() -> None:
    assert personal_data_attributes({}) == frozenset()
