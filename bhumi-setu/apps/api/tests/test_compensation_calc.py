"""
Tests for the compensation calculation service.
"""

from datetime import date
import pytest
from app.services.compensation_calc import (
    calculate_compensation,
    CompensationInput,
    CompensationBreakdown,
)


class TestBasicCompensation:
    """Tests for basic compensation calculation."""

    def test_market_value_uses_higher_rate(self):
        """Market value should use the higher of circle rate and avg sale price."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=8000,
        )
        result = calculate_compensation(inp)
        assert result.market_value_per_sqm == 8000

    def test_market_value_with_circle_rate_higher(self):
        """Should use circle rate when it's higher."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=10000,
            avg_sale_price_per_sqm=7000,
        )
        result = calculate_compensation(inp)
        assert result.market_value_per_sqm == 10000

    def test_total_market_value_calculation(self):
        """Total market value = rate × area."""
        inp = CompensationInput(
            land_area_sqm=200,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
        )
        result = calculate_compensation(inp)
        assert result.total_market_value == 200 * 5000

    def test_solatium_is_100_percent(self):
        """Solatium should equal 100% of market value per Section 30(1)."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
        )
        result = calculate_compensation(inp)
        assert result.solatium == result.total_market_value


class TestRuralMultiplier:
    """Tests for rural area multiplier (Section 26(1)(b))."""

    def test_urban_land_has_multiplier_1(self):
        """Non-rural land should have multiplier 1.0."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
            is_rural=False,
        )
        result = calculate_compensation(inp)
        assert result.applied_rural_multiplier == 1.0

    def test_rural_multiplier_applied(self):
        """Rural multiplier should increase total market value."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
            is_rural=True,
            rural_multiplier=1.5,
        )
        result = calculate_compensation(inp)
        assert result.applied_rural_multiplier == 1.5
        assert result.total_market_value == 100 * 5000 * 1.5

    def test_rural_multiplier_capped_at_2(self):
        """Rural multiplier should not exceed 2.0."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
            is_rural=True,
            rural_multiplier=3.0,
        )
        result = calculate_compensation(inp)
        assert result.applied_rural_multiplier == 2.0

    def test_rural_multiplier_minimum_1(self):
        """Rural multiplier should not be less than 1.0."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
            is_rural=True,
            rural_multiplier=0.5,
        )
        result = calculate_compensation(inp)
        assert result.applied_rural_multiplier == 1.0


class TestAdditionalCompensation:
    """Tests for additional compensation at 12% p.a. (Section 30(3))."""

    def test_12_months_additional_compensation(self):
        """12 months should yield 12% additional compensation."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=10000,
            avg_sale_price_per_sqm=10000,
            notification_date=date(2026, 1, 1),
            award_date=date(2027, 1, 1),
        )
        result = calculate_compensation(inp)
        expected = 100 * 10000 * 0.12  # 12% of 10,00,000
        assert abs(result.additional_compensation - expected) < 1.0

    def test_no_dates_means_no_additional(self):
        """Without dates, additional compensation should be 0."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=10000,
            avg_sale_price_per_sqm=10000,
        )
        result = calculate_compensation(inp)
        assert result.additional_compensation == 0.0

    def test_24_months_additional_compensation(self):
        """24 months should yield 24% additional compensation."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=10000,
            avg_sale_price_per_sqm=10000,
            notification_date=date(2026, 1, 1),
            award_date=date(2028, 1, 1),
        )
        result = calculate_compensation(inp)
        expected = 100 * 10000 * 0.24  # 24% of 10,00,000
        assert abs(result.additional_compensation - expected) < 1.0


class TestAssetAndRehabilitation:
    """Tests for additional asset values and rehabilitation costs."""

    def test_structure_value_included(self):
        """Structure value should be added to total."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
            structure_value=200000,
        )
        result = calculate_compensation(inp)
        assert result.assets_value == 200000

    def test_all_asset_types_summed(self):
        """All asset types should be summed."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
            structure_value=100000,
            crops_and_trees_value=50000,
            damage_to_movable=25000,
        )
        result = calculate_compensation(inp)
        assert result.assets_value == 175000

    def test_rehabilitation_costs_included(self):
        """Resettlement expenses should be included in total."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
            resettlement_expenses=50000,
        )
        result = calculate_compensation(inp)
        assert result.rehabilitation_costs == 50000

    def test_total_includes_all_components(self):
        """Total should include market value + solatium + additional + assets + rehab."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
            notification_date=date(2026, 1, 1),
            award_date=date(2027, 1, 1),
            structure_value=100000,
            resettlement_expenses=50000,
        )
        result = calculate_compensation(inp)
        expected = (
            result.total_market_value +
            result.solatium +
            result.additional_compensation +
            result.assets_value +
            result.rehabilitation_costs
        )
        assert abs(result.total_compensation - expected) < 1.0


class TestComponentBreakdown:
    """Tests for the compensation component breakdown list."""

    def test_minimum_three_components(self):
        """Should always have at least 3 components (market, solatium, additional)."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
        )
        result = calculate_compensation(inp)
        assert len(result.components) >= 3

    def test_assets_component_when_nonzero(self):
        """Assets component should appear when value > 0."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
            structure_value=100000,
        )
        result = calculate_compensation(inp)
        labels = [c.label for c in result.components]
        assert "Assets Value" in labels

    def test_rehab_component_when_nonzero(self):
        """Rehabilitation component should appear when expenses > 0."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
            resettlement_expenses=50000,
        )
        result = calculate_compensation(inp)
        labels = [c.label for c in result.components]
        assert "Rehabilitation & Resettlement" in labels

    def test_components_reference_sections(self):
        """Each component should reference the relevant Act section."""
        inp = CompensationInput(
            land_area_sqm=100,
            circle_rate_per_sqm=5000,
            avg_sale_price_per_sqm=5000,
        )
        result = calculate_compensation(inp)
        for comp in result.components:
            assert comp.section.startswith("Section")
