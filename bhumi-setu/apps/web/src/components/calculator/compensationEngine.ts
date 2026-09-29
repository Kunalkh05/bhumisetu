/**
 * BHUMISETU Compensation Calculator Module
 *
 * Implements the compensation calculation logic as per RFCTLARR Act 2013.
 * Sections 26-30 define the compensation formula:
 *
 * Total Compensation = Market Value + Solatium (100%) + Additional Compensation
 *
 * Where:
 *   Market Value = Higher of (Circle Rate, Average Sale Price, Court Award)
 *   Solatium = 100% of Market Value (Section 30)
 *   Additional Compensation = 12% per annum from notification date (Section 30(3))
 *
 * For rural areas, multiply market value by factor of 1.0 to 2.0
 * as determined by the appropriate Government (Section 26(1)(b)).
 */

export interface CompensationInput {
  /** Land area in square meters */
  landAreaSqm: number;
  /** Circle rate (government registered rate) per sq meter in INR */
  circleRatePerSqm: number;
  /** Average sale price from recent transactions per sq meter in INR */
  avgSalePricePerSqm: number;
  /** Whether the land is in a rural area */
  isRural: boolean;
  /** Rural multiplier factor (1.0 to 2.0), applicable only for rural land */
  ruralMultiplier?: number;
  /** Date of Section 11 notification (preliminary notification) */
  notificationDate: Date;
  /** Date of award under Section 23 */
  awardDate: Date;
  /** Value of any standing structures on the land in INR */
  structureValue?: number;
  /** Value of trees, plants, and standing crops in INR */
  cropsAndTreesValue?: number;
  /** Any damage to movable property or business during acquisition */
  damageToMovableProperty?: number;
  /** Expenses for change of residence (Section 31) */
  resettlementExpenses?: number;
}

export interface CompensationBreakdown {
  /** Higher of circle rate and average sale price */
  marketValuePerSqm: number;
  /** Total market value (market rate × area × rural multiplier if applicable) */
  totalMarketValue: number;
  /** Solatium: 100% of market value as per Section 30(1) */
  solatium: number;
  /** Additional compensation at 12% per annum from notification to award */
  additionalCompensation: number;
  /** Value of structures, crops, trees */
  assetsValue: number;
  /** Resettlement and rehabilitation costs */
  rehabilitationCosts: number;
  /** Grand total compensation payable */
  totalCompensation: number;
  /** Number of months between notification and award */
  monthsBetween: number;
  /** Rural multiplier applied (1.0 for urban) */
  appliedRuralMultiplier: number;
}

/**
 * Calculate the number of full months between two dates.
 */
function monthsDifference(start: Date, end: Date): number {
  const years = end.getFullYear() - start.getFullYear();
  const months = end.getMonth() - start.getMonth();
  return Math.max(0, years * 12 + months);
}

/**
 * Calculate compensation as per RFCTLARR Act 2013, Sections 26-30.
 *
 * @param input - Compensation calculation input parameters
 * @returns Detailed breakdown of the compensation amount
 */
export function calculateCompensation(
  input: CompensationInput,
): CompensationBreakdown {
  // Step 1: Determine market value (higher of circle rate and avg sale price)
  const marketValuePerSqm = Math.max(
    input.circleRatePerSqm,
    input.avgSalePricePerSqm,
  );

  // Step 2: Apply rural multiplier (Section 26(1)(b))
  const appliedRuralMultiplier =
    input.isRural && input.ruralMultiplier
      ? Math.min(2.0, Math.max(1.0, input.ruralMultiplier))
      : 1.0;

  // Step 3: Calculate total market value
  const totalMarketValue =
    marketValuePerSqm * input.landAreaSqm * appliedRuralMultiplier;

  // Step 4: Calculate solatium (100% of market value, Section 30(1))
  const solatium = totalMarketValue;

  // Step 5: Calculate additional compensation (12% per annum, Section 30(3))
  const months = monthsDifference(input.notificationDate, input.awardDate);
  const additionalCompensation =
    totalMarketValue * 0.12 * (months / 12);

  // Step 6: Sum up asset values
  const assetsValue =
    (input.structureValue ?? 0) +
    (input.cropsAndTreesValue ?? 0) +
    (input.damageToMovableProperty ?? 0);

  // Step 7: Rehabilitation costs
  const rehabilitationCosts = input.resettlementExpenses ?? 0;

  // Step 8: Total compensation
  const totalCompensation =
    totalMarketValue +
    solatium +
    additionalCompensation +
    assetsValue +
    rehabilitationCosts;

  return {
    marketValuePerSqm,
    totalMarketValue,
    solatium,
    additionalCompensation,
    assetsValue,
    rehabilitationCosts,
    totalCompensation,
    monthsBetween: months,
    appliedRuralMultiplier,
  };
}

/**
 * Format a currency value in Indian Rupees with commas.
 *
 * Examples:
 *   formatINR(1234567) → "₹12,34,567"
 *   formatINR(100000)  → "₹1,00,000"
 */
export function formatINR(amount: number): string {
  const formatted = amount.toLocaleString('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  });
  return formatted;
}

/**
 * Convert square meters to standard Indian land units.
 */
export function sqmToAcres(sqm: number): number {
  return sqm / 4046.86;
}

export function sqmToHectares(sqm: number): number {
  return sqm / 10000;
}

export function sqmToGuntha(sqm: number): number {
  // 1 Guntha = 101.17 sq meters (Maharashtra standard)
  return sqm / 101.17;
}

export function sqmToBigha(sqm: number): number {
  // 1 Bigha = 2529.29 sq meters (varies by state, using Maharashtra standard)
  return sqm / 2529.29;
}
