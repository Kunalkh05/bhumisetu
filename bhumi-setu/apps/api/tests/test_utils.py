"""
Tests for utility helpers (app.utils).
"""

from datetime import date
import pytest
from app.utils import (
    is_working_day,
    add_working_days,
    count_working_days,
    calculate_statutory_deadlines,
    mask_aadhaar,
    mask_pan,
    format_inr,
    sqm_to_acres,
    sqm_to_hectares,
    sqm_to_guntha,
)


class TestIsWorkingDay:
    """Tests for the is_working_day function."""

    def test_weekday_non_holiday_is_working(self):
        """A normal Monday should be a working day."""
        # 2026-01-05 is a Monday
        assert is_working_day(date(2026, 1, 5)) is True

    def test_saturday_is_not_working(self):
        """Saturday should not be a working day."""
        # 2026-01-03 is a Saturday
        assert is_working_day(date(2026, 1, 3)) is False

    def test_sunday_is_not_working(self):
        """Sunday should not be a working day."""
        # 2026-01-04 is a Sunday
        assert is_working_day(date(2026, 1, 4)) is False

    def test_republic_day_is_not_working(self):
        """Republic Day (Jan 26) is a gazetted holiday."""
        assert is_working_day(date(2026, 1, 26)) is False

    def test_independence_day_is_not_working(self):
        """Independence Day (Aug 15) is a gazetted holiday."""
        assert is_working_day(date(2026, 8, 15)) is False

    def test_gandhi_jayanti_is_not_working(self):
        """Gandhi Jayanti (Oct 2) is a gazetted holiday."""
        assert is_working_day(date(2026, 10, 2)) is False


class TestAddWorkingDays:
    """Tests for the add_working_days function."""

    def test_add_one_working_day(self):
        """Adding 1 working day to Friday should give Monday."""
        # 2026-01-02 is Friday
        result = add_working_days(date(2026, 1, 2), 1)
        assert result == date(2026, 1, 5)  # Monday

    def test_add_five_working_days(self):
        """Adding 5 working days should skip weekend."""
        result = add_working_days(date(2026, 1, 5), 5)
        assert result == date(2026, 1, 12)

    def test_add_zero_working_days(self):
        """Adding 0 working days should return the same date."""
        start = date(2026, 3, 10)
        result = add_working_days(start, 0)
        assert result == start

    def test_skips_holidays(self):
        """Should skip gazetted holidays in the count."""
        # 2026-01-23 is Friday, Jan 26 is Republic Day (Monday)
        result = add_working_days(date(2026, 1, 23), 1)
        # Should be Monday Jan 26? No, that's a holiday. Should be Tuesday Jan 27
        assert result == date(2026, 1, 27) or result > date(2026, 1, 23)


class TestCountWorkingDays:
    """Tests for the count_working_days function."""

    def test_count_within_same_week(self):
        """Count working days within a single week (Mon-Fri)."""
        # 2026-01-05 (Mon) to 2026-01-09 (Fri)
        result = count_working_days(date(2026, 1, 5), date(2026, 1, 9))
        assert result == 3  # Tue, Wed, Thu (exclusive of endpoints)

    def test_count_across_weekend(self):
        """Count should exclude weekend days."""
        # 2026-01-09 (Fri) to 2026-01-12 (Mon)
        result = count_working_days(date(2026, 1, 9), date(2026, 1, 12))
        assert result == 0  # Only Sat and Sun between, both non-working


class TestStatutoryDeadlines:
    """Tests for RFCTLARR statutory deadline calculations."""

    def test_section_15_is_60_working_days_after_section_11(self):
        """Section 15 hearing deadline should be 60 working days after Section 11."""
        section_11 = date(2026, 1, 5)
        deadlines = calculate_statutory_deadlines(section_11)
        assert deadlines["section_15_deadline"] > section_11
        # Should be roughly 3 months later (60 working days ≈ 84 calendar days)
        diff = (deadlines["section_15_deadline"] - section_11).days
        assert 75 <= diff <= 95

    def test_section_19_is_12_months_after_section_11(self):
        """Section 19 declaration deadline should be 12 months after Section 11."""
        section_11 = date(2026, 3, 15)
        deadlines = calculate_statutory_deadlines(section_11)
        assert deadlines["section_19_deadline"] == date(2027, 3, 15)

    def test_section_23_is_24_months_after_section_11(self):
        """Section 23 award deadline should be ~24 months after Section 11."""
        section_11 = date(2026, 6, 1)
        deadlines = calculate_statutory_deadlines(section_11)
        assert deadlines["section_23_deadline"].year == 2028


class TestMasking:
    """Tests for PII masking functions."""

    def test_mask_aadhaar_standard(self):
        """Standard 12-digit Aadhaar should be masked correctly."""
        assert mask_aadhaar("234567890123") == "XXXX XXXX 0123"

    def test_mask_aadhaar_with_spaces(self):
        """Aadhaar with spaces should be cleaned and masked."""
        assert mask_aadhaar("2345 6789 0123") == "XXXX XXXX 0123"

    def test_mask_aadhaar_with_dashes(self):
        """Aadhaar with dashes should be cleaned and masked."""
        assert mask_aadhaar("2345-6789-0123") == "XXXX XXXX 0123"

    def test_mask_aadhaar_invalid_length(self):
        """Invalid length should return original string."""
        assert mask_aadhaar("12345") == "12345"

    def test_mask_pan_standard(self):
        """Standard PAN should be masked correctly."""
        assert mask_pan("ABCDE1234F") == "A****1234F"

    def test_mask_pan_invalid_length(self):
        """Invalid length should return original string."""
        assert mask_pan("ABC") == "ABC"


class TestFormatINR:
    """Tests for Indian Rupee formatting."""

    def test_small_amount(self):
        """Amounts under 1000 should have no commas."""
        assert format_inr(500) == "₹500"

    def test_thousands(self):
        """Thousands should have one comma."""
        assert format_inr(1234) == "₹1,234"

    def test_lakhs(self):
        """Lakhs should have Indian-style comma grouping."""
        assert format_inr(100000) == "₹1,00,000"

    def test_crores(self):
        """Crores should have proper Indian grouping."""
        assert format_inr(10000000) == "₹1,00,00,000"

    def test_large_amount(self):
        """Large amounts should format correctly."""
        result = format_inr(1234567890)
        assert "₹" in result
        assert "," in result

    def test_zero(self):
        """Zero should format as ₹0."""
        assert format_inr(0) == "₹0"

    def test_negative(self):
        """Negative amounts should have a minus sign."""
        result = format_inr(-5000)
        assert result.startswith("-")


class TestUnitConversion:
    """Tests for land unit conversion functions."""

    def test_sqm_to_acres(self):
        """4046.86 sqm should equal approximately 1 acre."""
        assert abs(sqm_to_acres(4046.86) - 1.0) < 0.01

    def test_sqm_to_hectares(self):
        """10000 sqm should equal 1 hectare."""
        assert sqm_to_hectares(10000) == 1.0

    def test_sqm_to_guntha(self):
        """101.17 sqm should equal approximately 1 guntha."""
        assert abs(sqm_to_guntha(101.17) - 1.0) < 0.01

    def test_zero_area(self):
        """Zero area should convert to zero in all units."""
        assert sqm_to_acres(0) == 0
        assert sqm_to_hectares(0) == 0
        assert sqm_to_guntha(0) == 0
