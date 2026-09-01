"""Declarative attribute classification — the one registry (§17.1).

Every stored attribute belongs to exactly one ``Data_Category`` (R32.2). That
assignment is data, not logic scattered through services: one dict keyed by
``(table, column)``, in one file, so the retention sweep, the redaction gate, the
DSAR response, and the feature-disjointness guard all read the same source rather
than four drifting copies.

Why a raised ``KeyError`` rather than a default
----------------------------------------------

:func:`category_of` looks the attribute up with ``CATEGORY_MAP[(table, column)]``
and lets a missing key raise. There is deliberately no ``.get(..., default)``. A
default would classify an unmapped column as *something* — and if that something
were "not personal", a newly added ``contact_mobile`` column would be treated as
non-personal and never erased, silently. Failing loud is the point: task 25.2
turns this into a build failure by walking ``Base.metadata`` and asserting every
column has an entry. Until then the loud failure is a runtime ``KeyError``, which
is still far better than a wrong answer.

Two entry kinds beyond a plain category
---------------------------------------

Most attributes map to a fixed category string. Two do not, and both resolve from
the stored row rather than from ``(table, column)`` alone:

* :class:`Discriminated` — the category depends on the value of another column.
  ``extracted_field.extracted_value`` is ``OWNER_IDENTITY`` when the extracted
  ``field_name`` is ``owner_name`` but ``LAND_RECORD`` when it is
  ``survey_number``. Its explicit ``default`` is *not* the forbidden silent
  default above: it is a deliberate classification for extracted fields the map
  does not name specifically, chosen as the safe non-erasable ``LAND_RECORD``.
* :class:`Reference` — the category is carried by the row itself, in another
  column. ``personal_datum.value_ciphertext`` holds a value of whatever
  ``data_category`` its row records, so the category *follows* that column.

Scope at task 3.3
-----------------

This file carries the **personal-data entries** the event log must externalise —
owner identity and contact attributes, the objector's name, the value-dependent
extracted field, the ``personal_datum`` referent, and the ML feature row — plus
the mechanism above. It is **not** yet complete over the whole schema; most of the
entities these entries name (``ownership_record``, ``objection``,
``extracted_field``, ``ml_feature_row``) are declared in later tasks, and the map
is keyed by string tuples precisely so a classification can be recorded before its
table exists. Task 25.2 completes the map to full schema coverage and adds the
metadata-walk test that fails the build on any unclassified column.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "NOT_PERSONAL",
    "OWNER_CONTACT",
    "OWNER_IDENTITY",
    "MODEL_FEATURE",
    "LAND_RECORD",
    "DOCUMENT_CONTENT",
    "AUDIT_EVENT",
    "PERSONAL_DATA_CATEGORIES",
    "Discriminated",
    "Reference",
    "CATEGORY_MAP",
    "category_of",
    "personal_data_attributes",
]

# ---------------------------------------------------------------------------
# Data_Category names (Q10, resolved as the maintainer default)
# ---------------------------------------------------------------------------

#: The classification for an attribute that holds no personal data. Spelled out
#: rather than left implicit so 25.2's completeness walk can require a *positive*
#: classification for every column — silence is never "not personal".
NOT_PERSONAL = "NOT_PERSONAL_DATA"

# Personal data about a data subject. These are the erasable categories.
OWNER_CONTACT = "OWNER_CONTACT"
OWNER_IDENTITY = "OWNER_IDENTITY"
MODEL_FEATURE = "MODEL_FEATURE"

# Statutory record, retained without expiry (R32.11).
LAND_RECORD = "LAND_RECORD"
DOCUMENT_CONTENT = "DOCUMENT_CONTENT"
AUDIT_EVENT = "AUDIT_EVENT"

#: The categories that denote personal data. These are exactly Q10's erasable set
#: (``retention.erasable_categories`` defaults to this), and that is not a
#: coincidence: an attribute is "personal" for the purpose of the guards below
#: precisely because its value can be erased, and a feature or an unannotated
#: response field built on an erasable value is the failure those guards prevent.
#: Whether a category is *actually* erased at runtime is a ``Policy_Config``
#: decision (§17.2); this static set is what "personal" means to the code.
PERSONAL_DATA_CATEGORIES: frozenset[str] = frozenset(
    {OWNER_CONTACT, OWNER_IDENTITY, MODEL_FEATURE}
)


# ---------------------------------------------------------------------------
# The two value-dependent entry kinds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Discriminated:
    """A category decided by the value of another column on the same row.

    ``on`` names the discriminator column; ``by_value`` maps its value to a
    category; ``default`` classifies any value not listed. The default is an
    intentional classification (see the module docstring), not the silent default
    that :func:`category_of` refuses.
    """

    on: str
    by_value: Mapping[str, str]
    default: str

    def resolve(self, row: Mapping[str, Any] | None) -> str:
        if row is None:
            raise ValueError(
                f"cannot classify a Discriminated attribute without the row: "
                f"the category depends on column {self.on!r}"
            )
        # row[self.on] raises KeyError if the discriminator is absent — the right
        # failure, since the attribute genuinely cannot be classified without it.
        return self.by_value.get(row[self.on], self.default)

    def possible_categories(self) -> frozenset[str]:
        """Every category this entry could resolve to, used by the guards to decide
        whether the attribute is *potentially* personal."""
        return frozenset(self.by_value.values()) | {self.default}


@dataclass(frozen=True)
class Reference:
    """A category carried by the row itself, in the column named by ``follows``.

    Used for ``personal_datum.value_ciphertext``, whose row records its own
    ``data_category``. A ``personal_datum`` row only ever holds a personal
    category by construction, so an attribute classified this way is treated as
    personal by the guards below.
    """

    follows: str

    def resolve(self, row: Mapping[str, Any] | None) -> str:
        if row is None:
            raise ValueError(
                f"cannot classify a Reference attribute without the row: "
                f"the category is carried by column {self.follows!r}"
            )
        return row[self.follows]


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

#: The personal-data entries the event log must externalise, plus the two
#: value-dependent entries. Not yet complete over the schema — see the module
#: docstring and task 25.2. Keyed by ``(table, column)`` string tuples, so an
#: entry can be recorded before its table's model exists.
CATEGORY_MAP: dict[tuple[str, str], str | Discriminated | Reference] = {
    # ownership_record — the landowner's identity and contact details (§17.1).
    ("ownership_record", "owner_name"): OWNER_IDENTITY,
    ("ownership_record", "government_identifier"): OWNER_IDENTITY,
    ("ownership_record", "owner_identity_key"): OWNER_IDENTITY,
    ("ownership_record", "contact_mobile"): OWNER_CONTACT,
    ("ownership_record", "contact_mobile_hash"): OWNER_CONTACT,
    # objection — the objector is a person.
    ("objection", "objector_name"): OWNER_IDENTITY,
    # document — the object itself contains record scans and OCR source content.
    ("document", "object_key"): DOCUMENT_CONTENT,
    ("document", "original_filename"): LAND_RECORD,
    # extracted_field — value-dependent: the category is decided by which field
    # was extracted, so it is resolved from the row.
    ("extracted_field", "extracted_value"): Discriminated(
        on="field_name",
        by_value={
            "owner_name": OWNER_IDENTITY,
            "father_name": OWNER_IDENTITY,
            "mobile": OWNER_CONTACT,
            "aadhaar": OWNER_IDENTITY,
            "survey_number": LAND_RECORD,
            "extent": LAND_RECORD,
        },
        default=LAND_RECORD,
    ),
    ("extracted_field", "original_extracted_value"): Discriminated(
        on="field_name",
        by_value={
            "owner_name": OWNER_IDENTITY,
            "father_name": OWNER_IDENTITY,
            "mobile": OWNER_CONTACT,
            "aadhaar": OWNER_IDENTITY,
            "survey_number": LAND_RECORD,
            "extent": LAND_RECORD,
        },
        default=LAND_RECORD,
    ),
    ("extraction", "full_text"): DOCUMENT_CONTENT,
    ("holdout_document", "object_key"): DOCUMENT_CONTENT,
    ("holdout_label", "expected_value"): Discriminated(
        on="field_name",
        by_value={
            "owner_name": OWNER_IDENTITY,
            "father_name": OWNER_IDENTITY,
            "mobile": OWNER_CONTACT,
            "aadhaar": OWNER_IDENTITY,
            "survey_number": LAND_RECORD,
            "extent": LAND_RECORD,
        },
        default=LAND_RECORD,
    ),
    # ml feature rows are erasable personal data under Q10 (MODEL_FEATURE); a
    # feature must never derive from another feature's stored value either.
    ("ml_feature_row", "features"): MODEL_FEATURE,
    # personal_datum — the referent's category is the one recorded on its row.
    ("personal_datum", "value_ciphertext"): Reference(follows="data_category"),
}


def category_of(
    table: str, column: str, row: Mapping[str, Any] | None = None
) -> str:
    """Return the ``Data_Category`` assigned to ``table.column`` (R32.2).

    Raises ``KeyError`` if the attribute is unclassified — there is no silent
    default. For a value-dependent entry (:class:`Discriminated` or
    :class:`Reference`), ``row`` supplies the values the category is resolved
    from; omitting it for such an entry raises ``ValueError``.
    """
    entry = CATEGORY_MAP[(table, column)]
    if isinstance(entry, (Discriminated, Reference)):
        return entry.resolve(row)
    return entry


def _entry_is_personal(entry: str | Discriminated | Reference) -> bool:
    """Whether an entry classifies its attribute as (potentially) personal data.

    A :class:`Discriminated` entry is personal if *any* value it can resolve to is
    personal — a feature reading such an attribute might read a personal value. A
    :class:`Reference` follows a category column that, for the only current use,
    always holds a personal category, so it is treated as personal.
    """
    if isinstance(entry, Discriminated):
        return bool(entry.possible_categories() & PERSONAL_DATA_CATEGORIES)
    if isinstance(entry, Reference):
        return True
    return entry in PERSONAL_DATA_CATEGORIES


def personal_data_attributes(
    category_map: Mapping[tuple[str, str], str | Discriminated | Reference]
) -> frozenset[str]:
    """The set of attribute (column) names classified as personal data.

    Returned as bare column names, because that is what a feature extractor's
    ``source_attributes`` and a ``GatedModel``'s field names are stated in, and
    both the disjointness guard (§5.4) and the field-coverage test (§8.3)
    intersect against this set. Using column names is deliberately conservative:
    a name that is personal in any table is treated as personal everywhere it
    appears as a source, which fails safe for a guard whose whole job is to block.
    """
    return frozenset(
        column
        for (_table, column), entry in category_map.items()
        if _entry_is_personal(entry)
    )
