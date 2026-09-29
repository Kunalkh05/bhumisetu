/**
 * Historical Cadastral Survey & Encroachment Detection Types
 * Models archival revenue department surveys (1970s Settlement Revision)
 * and spatial encroachment patterns against current DGPS / satellite parcels.
 */

export type EncroachmentSeverity = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'NIL';

export type EncroachedLandClassification = 
  | 'PWD_ROW_RESERVE'          // Unauthorized expansion into statutory highway / road reserve
  | 'GOVT_GAIRAN_GRAZING'      // Encroachment into Village Common Grazing / Poramboke land
  | 'NATURAL_NALA_BUFFER'      // Encroachment or stream diversion into natural water drainage course
  | 'ADJACENT_ROAD_MARGIN'     // Encroachment into village arterial road margin
  | 'BOUND_DRIFT_AGRICULTURAL' // Subtle field bund creep into neighboring state land
  | 'CLEAN_VERIFIED';          // Boundaries match 1974 survey within statutory tolerance

export interface HistoricalBoundaryStone {
  id: string;
  stoneNumber: number;
  label: string;
  labelHi: string;
  originalPosition: [number, number]; // [lat, lng]
  currentStatus: 'VERIFIED_INTACT' | 'DISPLACED' | 'MISSING_DESTROYED';
  displacementMeters?: number;
  notes: string;
}

export interface HistoricalCadastralParcel {
  id: string;
  currentParcelId: string;
  surveyNumber1974: string;           // e.g. "Old Survey No. 84, Hissa 2"
  surveyNumber1974Hi: string;
  currentSurveyNumber: string;        // e.g. "Gat No. 142/A"
  village: string;
  sheetNumber: string;                // Archival cadastral sheet e.g. "Settlement Sheet No. 14"
  surveyYear: number;                 // 1974
  extent1974Ha: number;
  extent1974Gunthas: number;
  coordinates1974: [number, number][]; // Archival survey polygon coordinates
  landClass1974: string;
  boundaryStones: HistoricalBoundaryStone[];
  archivalSource: string;
}

export interface EncroachmentDetectionRecord {
  id: string;
  parcelId: string;
  currentSurveyNumber: string;
  historicalSurveyNumber1974: string;
  village: string;
  hasEncroachment: boolean;
  severity: EncroachmentSeverity;
  encroachmentAreaSqM: number;
  encroachmentAreaHa: number;
  expansionPercentage: number;        // e.g. +17.06%
  encroachedLandType: EncroachedLandClassification;
  encroachedLandTypeLabel: string;
  encroachedLandTypeLabelHi: string;
  encroachmentPolygon: [number, number][]; // Exact spatial slice where encroachment is detected
  historicalGeom1974: [number, number][];
  currentGeom2024: [number, number][];
  displacedStonesCount: number;
  statutoryViolation: string;
  description: string;
  descriptionHi: string;
  solatiumDeductionEstInr: number;    // Ineligible solatium amount under RFCTLARR 2013
  recommendedAction: string;
  recommendedActionHi: string;
  fieldInspectionStatus: 'PENDING_JOINT_MEASUREMENT' | 'SURVEYOR_FLAGGED' | 'NOTICE_DRAFTED' | 'CLEARED';
  detectedDate: string;
}

export interface HistoricalSurveyMetadata {
  surveyYear: number;
  surveyTitle: string;
  surveyTitleHi: string;
  surveyAgency: string;
  surveyAgencyHi: string;
  sheetNumber: string;
  tehsil: string;
  district: string;
  geodeticDatum: string;
  digitizationStandard: string;
  totalParcelsAudited: number;
  encroachmentsFoundCount: number;
  totalEncroachedAreaSqM: number;
}
