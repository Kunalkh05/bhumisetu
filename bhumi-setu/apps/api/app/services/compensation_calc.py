"""
Compensation calculation service for RFCTLARR Act 2013.

Implements Sections 26-30 of the Right to Fair Compensation and
Transparency in Land Acquisition, Rehabilitation and Resettlement Act.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, List
from app.utils import format_inr


@dataclass
class CompensationComponent:
    """Individual component of the total compensation."""
    label: str
    amount: float
    section: str
    description: str


@dataclass
class CompensationBreakdown:
    """Full compensation breakdown with all components."""
    market_value_per_sqm: float
    total_market_value: float
    solatium: float
    additional_compensation: float
    assets_value: float
    rehabilitation_costs: float
    total_compensation: float
    months_between: int
    applied_rural_multiplier: float
    components: List[CompensationComponent]


@dataclass
class CompensationInput:
    """Input parameters for compensation calculation."""
    land_area_sqm: float
    circle_rate_per_sqm: float
    avg_sale_price_per_sqm: float
    is_rural: bool = False
    rural_multiplier: float = 1.0
    notification_date: Optional[date] = None
    award_date: Optional[date] = None
    structure_value: float = 0.0
    crops_and_trees_value: float = 0.0
    damage_to_movable: float = 0.0
    resettlement_expenses: float = 0.0


def _months_difference(start: date, end: date) -> int:
    """Calculate the number of full months between two dates."""
    years = end.year - start.year
    months = end.month - start.month
    return max(0, years * 12 + months)


def calculate_compensation(inp: CompensationInput) -> CompensationBreakdown:
    """
    Calculate compensation as per RFCTLARR Act 2013, Sections 26-30.

    Args:
        inp: Compensation calculation input parameters

    Returns:
        Detailed breakdown of the compensation amount

    Section 26: Market value = Higher of (circle rate, avg sale price)
    Section 26(1)(b): Rural multiplier (1.0 to 2.0)
    Section 30(1): Solatium = 100% of market value
    Section 30(3): Additional compensation = 12% per annum from notification
    """
    # Step 1: Market value (higher of circle rate and avg sale price)
    market_value_per_sqm = max(inp.circle_rate_per_sqm, inp.avg_sale_price_per_sqm)

    # Step 2: Rural multiplier
    applied_multiplier = 1.0
    if inp.is_rural:
        applied_multiplier = min(2.0, max(1.0, inp.rural_multiplier))

    # Step 3: Total market value
    total_market_value = market_value_per_sqm * inp.land_area_sqm * applied_multiplier

    # Step 4: Solatium (100% of market value)
    solatium = total_market_value

    # Step 5: Additional compensation (12% p.a.)
    months = 0
    additional_compensation = 0.0
    if inp.notification_date and inp.award_date:
        months = _months_difference(inp.notification_date, inp.award_date)
        additional_compensation = total_market_value * 0.12 * (months / 12)

    # Step 6: Asset values
    assets_value = (
        inp.structure_value +
        inp.crops_and_trees_value +
        inp.damage_to_movable
    )

    # Step 7: Rehabilitation costs
    rehabilitation_costs = inp.resettlement_expenses

    # Step 8: Total
    total_compensation = (
        total_market_value +
        solatium +
        additional_compensation +
        assets_value +
        rehabilitation_costs
    )

    # Build component list for transparency
    components = [
        CompensationComponent(
            label="Market Value",
            amount=total_market_value,
            section="Section 26",
            description=f"Higher of circle rate ({format_inr(inp.circle_rate_per_sqm)}/sqm) "
                       f"and avg sale price ({format_inr(inp.avg_sale_price_per_sqm)}/sqm)",
        ),
        CompensationComponent(
            label="Solatium",
            amount=solatium,
            section="Section 30(1)",
            description="100% of market value",
        ),
        CompensationComponent(
            label="Additional Compensation",
            amount=additional_compensation,
            section="Section 30(3)",
            description=f"12% per annum for {months} months",
        ),
    ]
    if assets_value > 0:
        components.append(CompensationComponent(
            label="Assets Value",
            amount=assets_value,
            section="Section 26(1)",
            description="Structures, crops, trees, and movable property",
        ))
    if rehabilitation_costs > 0:
        components.append(CompensationComponent(
            label="Rehabilitation & Resettlement",
            amount=rehabilitation_costs,
            section="Section 31",
            description="Resettlement expenses and rehabilitation costs",
        ))

    return CompensationBreakdown(
        market_value_per_sqm=market_value_per_sqm,
        total_market_value=total_market_value,
        solatium=solatium,
        additional_compensation=additional_compensation,
        assets_value=assets_value,
        rehabilitation_costs=rehabilitation_costs,
        total_compensation=total_compensation,
        months_between=months,
        applied_rural_multiplier=applied_multiplier,
        components=components,
    )
