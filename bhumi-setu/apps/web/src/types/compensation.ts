/**
 * Compensation-related type definitions for the BHUMISETU calculator module.
 */

/** Land classification as per RFCTLARR Act 2013 */
export type LandClassification =
  | 'agricultural'
  | 'residential'
  | 'commercial'
  | 'industrial'
  | 'wasteland'
  | 'forest'
  | 'government';

/** Compensation status in the acquisition workflow */
export type CompensationStatus =
  | 'pending_valuation'
  | 'valuation_complete'
  | 'objection_filed'
  | 'objection_resolved'
  | 'award_declared'
  | 'payment_initiated'
  | 'payment_complete'
  | 'disputed';

/** Land measurement units used in India */
export type LandUnit =
  | 'sqm'        // Square meters
  | 'sqft'       // Square feet
  | 'acres'      // Acres
  | 'hectares'   // Hectares
  | 'guntha'     // Guntha (Maharashtra)
  | 'bigha'      // Bigha (varies by state)
  | 'are'        // Are (100 sq meters)
  | 'cent';      // Cent (South India)

/** Compensation component as per Section 26-30 */
export interface CompensationComponent {
  label: string;
  amount: number;
  section: string;
  description: string;
}

/** Full compensation record for a land parcel */
export interface CompensationRecord {
  id: string;
  caseId: string;
  parcelId: string;
  surveyNumber: string;
  landClassification: LandClassification;
  areaSqm: number;
  marketValuePerSqm: number;
  ruralMultiplier: number;
  components: CompensationComponent[];
  totalAmount: number;
  status: CompensationStatus;
  awardDate?: string;
  paymentDate?: string;
  bankAccountVerified: boolean;
  createdAt: string;
  updatedAt: string;
}

/** Valuation method used to determine market value */
export type ValuationMethod =
  | 'circle_rate'
  | 'average_sale_price'
  | 'court_award'
  | 'collector_assessment';

/** Market value assessment for a land parcel */
export interface MarketAssessment {
  surveyNumber: string;
  circleRate: number;
  averageSalePrice: number;
  courtAwardValue?: number;
  selectedMethod: ValuationMethod;
  finalMarketValue: number;
  assessmentDate: string;
  assessedBy: string;
}

/** Rehabilitation and resettlement entitlements per Schedule II */
export interface RehabilitationEntitlement {
  /** Affected family identifier */
  familyId: string;
  /** Type of entitlement */
  type: 'land' | 'employment' | 'annuity' | 'housing' | 'training';
  /** Description of the entitlement */
  description: string;
  /** Monetary value if applicable */
  monetaryValue?: number;
  /** Whether the entitlement has been disbursed */
  disbursed: boolean;
  /** Date of disbursement */
  disbursementDate?: string;
}
