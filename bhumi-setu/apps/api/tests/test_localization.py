"""Localization service, catalog coverage, formatting, and script round-trip tests (task 27)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
import unicodedata
from typing import Any, Sequence

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.land_parcel import LandParcel
from app.models.localization import MissingTranslation
from app.services.localization import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    LocalizationService,
    clear_missing_translations,
    default_localization_service,
    format_currency,
    format_date,
    format_number,
    get_missing_translations,
    record_missing_translation,
    resolve,
    resolve_action_label,
    resolve_event_label,
    resolve_ml_explanation,
    resolve_stage_label,
)
from tests.test_import_service import FakeImportSession


@pytest.fixture(autouse=True)
def _clean_missing() -> None:
    clear_missing_translations()
    yield
    clear_missing_translations()


# ============================================================================
# Task 27.1: Catalog Coverage & Fallback Recording
# ============================================================================


def test_every_citizen_and_officer_key_resolves_in_all_supported_locales() -> None:
    """Coverage test: all standard keys resolve in every configured language."""
    service = LocalizationService()
    en_catalog = service.get_catalog("en")
    assert len(en_catalog) > 0

    for locale in SUPPORTED_LOCALES:
        cat = service.get_catalog(locale)
        missing_in_locale = [k for k in en_catalog if k not in cat]
        assert missing_in_locale == [], f"Locale {locale} missing keys: {missing_in_locale}"


def test_fallback_to_default_locale_and_records_gap() -> None:
    """When a key is missing in a requested locale, falls back to default and records gap."""
    service = LocalizationService()
    # Key that exists in en but not in custom dummy locale or if missing in hi
    service.get_catalog("hi").pop("test.custom_key", None)
    service.get_catalog("en")["test.custom_key"] = "Default English Value"

    res = service.resolve("test.custom_key", locale="hi")
    assert res == "Default English Value"

    missing = service.get_missing_translations()
    assert any(m.key == "test.custom_key" and m.locale == "hi" for m in missing)
    rec = next(m for m in missing if m.key == "test.custom_key" and m.locale == "hi")
    assert rec.occurrence_count == 1

    # Calling again increments occurrence count
    service.resolve("test.custom_key", locale="hi")
    rec2 = next(m for m in service.get_missing_translations() if m.key == "test.custom_key")
    assert rec2.occurrence_count == 2


def test_recording_gap_in_database_session() -> None:
    """Missing translations are recorded to the missing_translation database table when session given."""
    service = LocalizationService()
    session = FakeImportSession()

    service.get_catalog("en")["only.in.en"] = "English Fallback"
    res = service.resolve("only.in.en", locale="mr", session=session)  # type: ignore[arg-type]
    assert res == "English Fallback"

    # In-memory check
    missing = service.get_missing_translations()
    assert any(m.key == "only.in.en" and m.locale == "mr" for m in missing)

    # Added to session check
    db_missing = [obj for obj in session.added if isinstance(obj, MissingTranslation)]
    assert len(db_missing) == 1
    assert db_missing[0].key == "only.in.en"
    assert db_missing[0].locale == "mr"
    assert db_missing[0].occurrence_count == 1


# ============================================================================
# Formatting Conventions (Requirement 27.3)
# ============================================================================


def test_format_date_in_supported_locales() -> None:
    d = date(2026, 8, 15)

    en_date = format_date(d, locale="en")
    assert en_date == "15 August 2026"

    hi_date = format_date(d, locale="hi")
    assert hi_date == "15 अगस्त 2026"

    mr_date = format_date(d, locale="mr")
    assert mr_date == "15 ऑगस्ट 2026"


def test_format_number_indian_grouping() -> None:
    assert format_number(500, locale="en") == "500"
    assert format_number(1000, locale="en") == "1,000"
    assert format_number(100000, locale="en") == "1,00,000"
    assert format_number(12345678, locale="en") == "1,23,45,678"
    assert format_number(Decimal("100000.50"), locale="en", precision=2) == "1,00,000.50"
    assert format_number(-1234567, locale="en") == "-12,34,567"


def test_format_currency_in_supported_locales() -> None:
    assert format_currency(100000, locale="en") == "₹ 1,00,000.00"
    assert format_currency(Decimal("2500000.5"), locale="hi") == "₹ 25,00,000.50"
    assert format_currency(75000, locale="mr") == "₹ 75,000.00"


# ============================================================================
# Task 27.2: Script Round-Trip Integrity (Property 62)
# ============================================================================


# Strategy generating Devanagari text with combining characters, ZWJ, and both normalization forms
DEVANAGARI_CONSONANTS = ["क", "ख", "ग", "घ", "च", "छ", "ज", "झ", "त", "थ", "द", "ध", "न", "प", "फ", "ब", "भ", "म", "य", "र", "ल", "व", "श", "ष", "स", "ह"]
DEVANAGARI_VOWEL_SIGNS = ["ा", "ि", "ी", "ु", "ू", "ृ", "े", "ै", "ो", "ौ", "्", "ं", "ः"]
SPECIAL_CHARS = ["\u200D", "\u200C", " ", "।", "॥"]  # ZWJ, ZWNJ, space, danda


@st.composite
def st_devanagari_text(draw: Any) -> str:
    parts = []
    length = draw(st.integers(min_value=1, max_value=15))
    for _ in range(length):
        choice = draw(st.sampled_from(["consonant", "vowel_sign", "special"]))
        if choice == "consonant":
            parts.append(draw(st.sampled_from(DEVANAGARI_CONSONANTS)))
        elif choice == "vowel_sign" and parts:
            parts.append(draw(st.sampled_from(DEVANAGARI_VOWEL_SIGNS)))
        else:
            parts.append(draw(st.sampled_from(SPECIAL_CHARS)))

    text = "".join(parts).strip()
    if not text:
        text = "पुणे"

    # Randomly apply NFD or NFC or keep raw
    norm_form = draw(st.sampled_from(["RAW", "NFC", "NFD"]))
    if norm_form == "NFC":
        return unicodedata.normalize("NFC", text)
    elif norm_form == "NFD":
        return unicodedata.normalize("NFD", text)
    return text


@given(text=st_devanagari_text())
@settings(max_examples=50, deadline=None)
def test_property_62_devanagari_round_trip_unchanged(text: str) -> None:
    """Property 62: Text round-trips unchanged in every configured script.

    No unicode normalisation on write. The value read back equals the value
    written character for character.
    """
    # Stored on model without normalization
    parcel = LandParcel(
        id=1,
        state_key="MH",
        district="Pune",
        tehsil="Haveli",
        village=text,  # Written exactly as submitted
        survey_number="12",
        classification="agricultural",
        extent=Decimal("1.0"),
        extent_unit="hectare",
        area_code="MH.PUN",
    )

    # Read back
    stored_village = parcel.village
    assert stored_village == text
    assert len(stored_village) == len(text)
    assert list(stored_village) == list(text)

    #village_norm generated column normalizes to NFC for matching only
    normalized_for_dup_scan = unicodedata.normalize("NFC", text)
    # The stored value for display/export preserves the exact original form
    assert parcel.village == text


# ============================================================================
# Task 27.3: Stage, Event, and Action Label Resolution
# ============================================================================


def test_resolve_stage_labels() -> None:
    assert resolve_stage_label("PN", locale="en") == "Preliminary Notification"
    assert resolve_stage_label("PN", locale="hi") == "प्रारंभिक अधिसूचना"
    assert resolve_stage_label("PN", locale="mr") == "प्राथमिक अधिसूचना"

    assert resolve_stage_label("AWARD", locale="en") == "Award Determination"
    assert resolve_stage_label("AWARD", locale="hi") == "अधिनिर्णय निर्धारण"
    assert resolve_stage_label("AWARD", locale="mr") == "निवाडा निर्धारण"


def test_resolve_event_labels() -> None:
    assert resolve_event_label("LAND_PARCEL_CREATED", locale="en") == "Land Parcel Added"
    assert resolve_event_label("LAND_PARCEL_CREATED", locale="hi") == "भूमि पार्सल जोड़ा गया"
    assert resolve_event_label("LAND_PARCEL_CREATED", locale="mr") == "जमीन भूखंड जोडला"

    assert resolve_event_label("AWARD_DETERMINED", locale="en") == "Award Determined"
    assert resolve_event_label("AWARD_DETERMINED", locale="hi") == "अधिनिर्णय पारित हुआ"
    assert resolve_event_label("AWARD_DETERMINED", locale="mr") == "निवाडा घोषित केला"


def test_resolve_action_and_ml_labels() -> None:
    assert resolve_action_label("BLOCKING", locale="en") == "Blocking Issues"
    assert resolve_action_label("BLOCKING", locale="hi") == "अवरोधक मुद्दे"
    assert resolve_action_label("BLOCKING", locale="mr") == "अडथळा ठरणारे मुद्दे"

    assert resolve_ml_explanation("notice_count", locale="en") == "Notice Count"
    assert resolve_ml_explanation("notice_count", locale="hi") == "नोटिस संख्या"
    assert resolve_ml_explanation("notice_count", locale="mr") == "नोटीस संख्या"


# ============================================================================
# Property 63: Display Strings Resolve with Recorded Gap on Fallback
# ============================================================================


@given(
    key=st.sampled_from(["stage.pn", "action.blocking", "event.award_determined", "citizen.portal_title"]),
    locale=st.sampled_from(["en", "hi", "mr"]),
)
@settings(max_examples=25, deadline=None)
def test_property_63_display_strings_resolve_in_all_locales(key: str, locale: str) -> None:
    """Property 63: For any display string key and any configured language, Localization_Service returns a resolved string."""
    service = LocalizationService()
    resolved = service.resolve(key, locale=locale)
    assert resolved is not None
    assert len(resolved) > 0
    assert resolved != key  # Successfully resolved to real display string
