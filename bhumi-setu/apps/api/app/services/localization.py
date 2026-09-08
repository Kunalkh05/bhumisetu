"""Localization service, catalogs, formatting, and gap recording (tasks 27.1 - 27.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.localization import MissingTranslation

__all__ = [
    "DEFAULT_LOCALE",
    "SUPPORTED_LOCALES",
    "LocalizationService",
    "MissingTranslationRecord",
    "clear_missing_translations",
    "default_localization_service",
    "format_currency",
    "format_date",
    "format_number",
    "get_missing_translations",
    "record_missing_translation",
    "resolve",
    "resolve_action_label",
    "resolve_event_label",
    "resolve_ml_explanation",
    "resolve_stage_label",
]

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "hi", "mr")

DEVANAGARI_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")

MONTH_NAMES: dict[str, dict[int, str]] = {
    "en": {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December",
    },
    "hi": {
        1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल",
        5: "मई", 6: "जून", 7: "जुलाई", 8: "अगस्त",
        9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर",
    },
    "mr": {
        1: "जानेवारी", 2: "फेब्रुवारी", 3: "मार्च", 4: "एप्रिल",
        5: "मे", 6: "जून", 7: "जुलै", 8: "ऑगस्ट",
        9: "सप्टेंबर", 10: "ऑक्टोबर", 11: "नोव्हेंबर", 12: "डिसेंबर",
    },
}

CURRENCY_SYMBOLS: dict[str, str] = {
    "en": "₹",
    "hi": "₹",
    "mr": "₹",
}


@dataclass(frozen=True)
class MissingTranslationRecord:
    key: str
    locale: str
    first_seen_at: datetime
    occurrence_count: int


class LocalizationService:
    def __init__(
        self,
        catalog_dir: Path | None = None,
        default_locale: str = DEFAULT_LOCALE,
    ) -> None:
        self._catalog_dir = catalog_dir or (Path(__file__).resolve().parents[1] / "locales")
        self._default_locale = default_locale
        self._catalogs: dict[str, dict[str, str]] = {}
        self._missing: dict[tuple[str, str], MissingTranslationRecord] = {}
        self._load_catalogs()

    def _load_catalogs(self) -> None:
        if not self._catalog_dir.exists():
            return
        for loc in SUPPORTED_LOCALES:
            cat_path = self._catalog_dir / f"{loc}.json"
            if cat_path.exists():
                try:
                    with cat_path.open("r", encoding="utf-8") as f:
                        self._catalogs[loc] = json.load(f)
                except Exception:
                    self._catalogs[loc] = {}
            else:
                self._catalogs[loc] = {}

    def get_catalog(self, locale: str) -> dict[str, str]:
        if locale not in self._catalogs:
            self._load_catalogs()
        return self._catalogs.get(locale, {})

    def resolve(
        self,
        key: str,
        locale: str = DEFAULT_LOCALE,
        params: Mapping[str, Any] | None = None,
        session: Session | None = None,
    ) -> str:
        target_locale = locale if locale in SUPPORTED_LOCALES else self._default_locale
        catalog = self.get_catalog(target_locale)

        if key in catalog:
            raw = catalog[key]
            return raw.format(**params) if params else raw

        # Key missing in requested locale -> record gap and fallback to default
        self.record_missing_translation(key, target_locale, session=session)

        default_catalog = self.get_catalog(self._default_locale)
        if key in default_catalog:
            raw = default_catalog[key]
            return raw.format(**params) if params else raw

        # Key missing even in default catalog
        if target_locale != self._default_locale:
            self.record_missing_translation(key, self._default_locale, session=session)
        return key.format(**params) if params else key

    def format_date(self, d: date | datetime, locale: str = DEFAULT_LOCALE) -> str:
        loc = locale if locale in SUPPORTED_LOCALES else self._default_locale
        month_map = MONTH_NAMES.get(loc, MONTH_NAMES[self._default_locale])
        month_name = month_map.get(d.month, str(d.month))
        return f"{d.day} {month_name} {d.year}"

    def format_number(
        self,
        n: int | float | Decimal,
        locale: str = DEFAULT_LOCALE,
        precision: int | None = None,
        use_devanagari_digits: bool = False,
    ) -> str:
        if isinstance(n, (float, int)):
            d = Decimal(str(n))
        else:
            d = n

        is_neg = d < 0
        d = abs(d)
        if precision is not None:
            s = f"{d:.{precision}f}"
        else:
            s = f"{d:f}" if d == d.to_integral() else f"{d}"

        if "." in s:
            integer_part, dec_part = s.split(".", 1)
            suffix = f".{dec_part}"
        else:
            integer_part = s
            suffix = ""

        if len(integer_part) <= 3:
            grouped = integer_part
        else:
            last3 = integer_part[-3:]
            rem = integer_part[:-3]
            parts = []
            while rem:
                parts.append(rem[-2:])
                rem = rem[:-2]
            parts.reverse()
            grouped = ",".join(parts) + "," + last3

        formatted = f"{'-' if is_neg else ''}{grouped}{suffix}"
        if use_devanagari_digits or (locale in {"hi", "mr"} and use_devanagari_digits):
            return formatted.translate(DEVANAGARI_DIGITS)
        return formatted

    def format_currency(
        self,
        amount: int | float | Decimal,
        locale: str = DEFAULT_LOCALE,
        precision: int = 2,
        use_devanagari_digits: bool = False,
    ) -> str:
        loc = locale if locale in SUPPORTED_LOCALES else self._default_locale
        symbol = CURRENCY_SYMBOLS.get(loc, "₹")
        num_str = self.format_number(
            amount,
            locale=loc,
            precision=precision,
            use_devanagari_digits=use_devanagari_digits,
        )
        return f"{symbol} {num_str}"

    def record_missing_translation(
        self,
        key: str,
        locale: str,
        *,
        session: Session | None = None,
        now: datetime | None = None,
    ) -> None:
        occurred = now or datetime.now(timezone.utc)
        record = self._missing.get((key, locale))
        if record is None:
            new_record = MissingTranslationRecord(
                key=key,
                locale=locale,
                first_seen_at=occurred,
                occurrence_count=1,
            )
            self._missing[(key, locale)] = new_record
        else:
            new_record = MissingTranslationRecord(
                key=key,
                locale=locale,
                first_seen_at=record.first_seen_at,
                occurrence_count=record.occurrence_count + 1,
            )
            self._missing[(key, locale)] = new_record

        if session is not None:
            try:
                db_record = session.execute(
                    select(MissingTranslation).where(
                        MissingTranslation.key == key,
                        MissingTranslation.locale == locale,
                    )
                ).scalar_one_or_none()
                if db_record is None:
                    db_record = MissingTranslation(
                        key=key,
                        locale=locale,
                        first_seen_at=occurred,
                        occurrence_count=1,
                    )
                    session.add(db_record)
                else:
                    db_record.occurrence_count += 1
                session.flush()
            except Exception:
                pass

    def get_missing_translations(
        self, session: Session | None = None
    ) -> list[MissingTranslationRecord]:
        if session is not None:
            try:
                records = list(
                    session.execute(
                        select(MissingTranslation).order_by(
                            MissingTranslation.occurrence_count.desc()
                        )
                    ).scalars()
                )
                if records:
                    return [
                        MissingTranslationRecord(
                            key=r.key,
                            locale=r.locale,
                            first_seen_at=r.first_seen_at,
                            occurrence_count=r.occurrence_count,
                        )
                        for r in records
                    ]
            except Exception:
                pass
        return sorted(self._missing.values(), key=lambda r: -r.occurrence_count)

    def clear_missing_translations(self) -> None:
        self._missing.clear()

    def resolve_stage_label(
        self,
        stage_key: str,
        locale: str = DEFAULT_LOCALE,
        label_key: str | None = None,
    ) -> str:
        key = label_key or f"stage.{stage_key.lower()}"
        return self.resolve(key, locale=locale)

    def resolve_event_label(
        self,
        event_type: str,
        locale: str = DEFAULT_LOCALE,
        label_key: str | None = None,
    ) -> str:
        key = label_key or f"event.{event_type.lower()}"
        return self.resolve(key, locale=locale)

    def resolve_action_label(
        self,
        action_key: str,
        locale: str = DEFAULT_LOCALE,
        label_key: str | None = None,
    ) -> str:
        key = label_key or f"action.{action_key.lower()}"
        return self.resolve(key, locale=locale)

    def resolve_ml_explanation(
        self,
        feature_name: str,
        locale: str = DEFAULT_LOCALE,
        label_key: str | None = None,
    ) -> str:
        key = label_key or f"ml.feature.{feature_name.lower()}"
        return self.resolve(key, locale=locale)


default_localization_service = LocalizationService()

resolve = default_localization_service.resolve
format_date = default_localization_service.format_date
format_number = default_localization_service.format_number
format_currency = default_localization_service.format_currency
record_missing_translation = default_localization_service.record_missing_translation
get_missing_translations = default_localization_service.get_missing_translations
clear_missing_translations = default_localization_service.clear_missing_translations
resolve_stage_label = default_localization_service.resolve_stage_label
resolve_event_label = default_localization_service.resolve_event_label
resolve_action_label = default_localization_service.resolve_action_label
resolve_ml_explanation = default_localization_service.resolve_ml_explanation
