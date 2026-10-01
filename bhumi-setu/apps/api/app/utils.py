"""
Utility helpers for the BHUMISETU API.

Provides common functions used across services including
date calculations, formatting, and statutory timeline helpers.
"""

from datetime import date, timedelta
from typing import Optional


# Indian national gazetted holidays for 2026
GAZETTED_HOLIDAYS_2026 = frozenset([
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 10),   # Maha Shivaratri
    date(2026, 3, 17),   # Holi
    date(2026, 3, 30),   # Id-ul-Fitr
    date(2026, 4, 2),    # Good Friday
    date(2026, 4, 6),    # Ram Navami
    date(2026, 4, 14),   # Dr. Ambedkar Jayanti
    date(2026, 4, 21),   # Mahavir Jayanti
    date(2026, 5, 1),    # May Day
    date(2026, 5, 25),   # Buddha Purnima
    date(2026, 6, 6),    # Id-ul-Zuha (Bakrid)
    date(2026, 7, 6),    # Muharram
    date(2026, 8, 15),   # Independence Day
    date(2026, 8, 16),   # Janmashtami
    date(2026, 9, 5),    # Milad-un-Nabi
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra
    date(2026, 11, 9),   # Diwali
    date(2026, 11, 11),  # Guru Nanak Jayanti
    date(2026, 12, 25),  # Christmas
])


def is_working_day(d: date) -> bool:
    """Check if a date is a government working day (not weekend or holiday)."""
    if d.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    return d not in GAZETTED_HOLIDAYS_2026


def add_working_days(start: date, days: int) -> date:
    """
    Add a specified number of working days to a date.
    Skips weekends and gazetted holidays.

    Used for calculating statutory deadlines under RFCTLARR Act.
    """
    step_day = 1
    current = start
    added = 0
    while added < days:
        current += timedelta(days=step_day)
        if is_working_day(current):
            added += 1
    return current


def count_working_days(start: date, end: date) -> int:
    """Count working days between two dates (exclusive of both endpoints)."""
    step_day = 1
    count = 0
    current = start + timedelta(days=step_day)
    while current < end:
        if is_working_day(current):
            count += 1
        current += timedelta(days=step_day)
    return count


def calculate_statutory_deadlines(section_11_date: date) -> dict:
    """
    Calculate key RFCTLARR statutory deadlines from Section 11 notification date.

    Returns dict with deadline dates for:
    - section_15: Hearing objections (60 working days)
    - section_19: Declaration (12 months)
    - section_23: Award (12 months after Section 19)
    - possession: Taking possession (60 working days after award)
    """
    section_19 = date(
        section_11_date.year + 1,
        section_11_date.month,
        min(section_11_date.day, 28),  # Handle month-end edge cases
    )
    section_23 = date(
        section_19.year + 1,
        section_19.month,
        min(section_19.day, 28),
    )
    return {
        "section_11": section_11_date,
        "section_15_deadline": add_working_days(section_11_date, 60),
        "section_19_deadline": section_19,
        "section_23_deadline": section_23,
        "possession_deadline": add_working_days(section_23, 60),
    }


def mask_aadhaar(aadhaar: str) -> str:
    """Mask an Aadhaar number, showing only last 4 digits."""
    cleaned = aadhaar.replace(" ", "").replace("-", "")
    if len(cleaned) != 12:
        return aadhaar
    return f"XXXX XXXX {cleaned[-4:]}"


def mask_pan(pan: str) -> str:
    """Mask a PAN number, showing first and last 5 characters."""
    if len(pan) != 10:
        return pan
    return f"{pan[0]}****{pan[5:]}"


def format_inr(amount: float) -> str:
    """
    Format amount in Indian Rupee format with commas.

    Examples:
        format_inr(1234567) → '₹12,34,567'
        format_inr(100000) → '₹1,00,000'
    """
    if amount < 0:
        return f"-{format_inr(-amount)}"

    amount_int = int(round(amount))
    s = str(amount_int)

    if len(s) <= 3:
        return f"₹{s}"

    # Last 3 digits
    result = s[-3:]
    s = s[:-3]

    # Group remaining digits in pairs
    while s:
        result = s[-2:] + "," + result
        s = s[:-2]

    return f"₹{result}"


def sqm_to_acres(sqm: float) -> float:
    """Convert square meters to acres."""
    return sqm / 4046.86


def sqm_to_hectares(sqm: float) -> float:
    """Convert square meters to hectares."""
    return sqm / 10000.0


def sqm_to_guntha(sqm: float) -> float:
    """Convert square meters to guntha (Maharashtra standard: 1 guntha = 101.17 sqm)."""
    return sqm / 101.17
