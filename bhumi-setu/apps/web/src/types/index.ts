export type Role = 
  | 'DISTRICT_COLLECTOR' 
  | 'LAO' // Land Acquisition Officer
  | 'SURVEY_OFFICER' 
  | 'CITIZEN';

export type OfficerTab = 
  | 'DASHBOARD'
  | 'CASE_WORKSPACE'
  | 'GIS_MAP'
  | 'INTERVENTION_QUEUE'
  | 'OCR_REVIEW'
  | 'VALIDATION_QUEUE'
  | 'MODEL_OBSERVABILITY'
  | 'BULK_IMPORT'
  | 'DPDP_RETENTION'
  | 'AUDIT_LOG'
  | 'RERA_GATEWAY';

export * from './rera';
export * from './cadastralHistory';

export interface UserSession {
  id: string;
  name: string;
  nameHi: string;
  role: Role;
  designation: string;
  designationHi: string;
  email?: string;
  mobile?: string;
  jurisdiction: string[]; // e.g. ['Pune', 'Nashik', 'Haveli']
  permissions: {
    canTransitionStage: boolean;
    canWaiveBlockingValidation: boolean;
    canDisbursePayout: boolean;
    canSubmitBulkImport: boolean;
    canAdministerModel: boolean;
    canConfigurePolicy: boolean;
    canCorrectOcr: boolean;
    canDisposeDSR: boolean;
  };
  expiresAt: string;
  isCitizen?: boolean;
  caseReference?: string;
}

export type CaseStage =
  | 'STAGE_1_SIA' // Social Impact Assessment
  | 'STAGE_2_PRELIM_NOTIF' // Section 11 Preliminary Notification
  | 'STAGE_3_OBJECTIONS' // Section 15 Hearing & Objections
  | 'STAGE_4_DECLARATION' // Section 19 Declaration of Acquisition
  | 'STAGE_5_AWARD_COMPENSATION' // Section 23 Compensation Award Determination
  | 'STAGE_6_DISBURSEMENT' // Section 37/38 DBT Payouts & Possession
  | 'STAGE_7_COMPLETED'; // Land Possession Handed Over to Authority

export type RiskBand = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'NOT_SCORED';

export interface ExplanationFactor {
  featureName: string;
  label: string;
  labelHi: string;
  direction: 'INCREASES_DELAY' | 'DECREASES_DELAY';
  magnitude: number; // e.g. 0.28
  description: string;
}

export interface RecommendedAction {
  id: string;
  title: string;
  titleHi: string;
  reason: string;
  urgency: 'HIGH' | 'MEDIUM' | 'LOW';
  actionType: 'RESOLVE_VALIDATION' | 'DISPOSE_OBJECTION' | 'CORRECT_OCR' | 'ISSUE_NOTICE' | 'RELEASE_PAYOUT';
  disposition?: 'ACCEPTED' | 'REJECTED' | 'DEFERRED';
  dispositionNote?: string;
  actedBy?: string;
  actedAt?: string;
}

export interface OfficerOverride {
  overriddenAt: string;
  officerId: string;
  officerName: string;
  originalRiskBand: RiskBand;
  newRiskBand: RiskBand;
  reason: string;
}

export interface LandParcel {
  id: string;
  state: string;
  district: string;
  tehsil: string;
  village: string;
  surveyNumber: string; // e.g. "Gat No. 142/A"
  subDivision: string;
  classification: 'Agricultural' | 'Non-Agricultural (Commercial)' | 'Residential' | 'Barren';
  extent: number; // in Hectares or Gunthas
  extentUnit: 'Hectares' | 'Acres' | 'Gunthas' | 'Sq. Meters';
  coordinates: [number, number][]; // Polygon geometry
  geodesicAreaComputed?: number;
  center: [number, number];
}

export interface OwnershipRecord {
  id: string;
  parcelId: string;
  ownerName: string;
  ownerNameHi: string;
  governmentIdentifierMasked: string; // e.g. "XXXX-XXXX-8921"
  panMasked?: string;
  contactNumber: string; // e.g. "+91 98765 43210"
  ownershipShare: number; // 0.0 - 1.0 (Sum must equal 1.0 per parcel)
  interestType: 'Sole Owner' | 'Co-Sharer' | 'Tenant/Karta' | 'Mortgagee';
  validityStart: string;
  validityEnd?: string;
  bankAccountMasked?: string;
  ifscCode?: string;
}

export interface StatutoryNotice {
  id: string;
  noticeType: 'Section 4 SIA' | 'Section 11 Prelim Notification' | 'Section 19 Declaration' | 'Section 21 Individual Notice' | 'Section 38 Possession Notice';
  issuingAuthority: string;
  issueDate: string;
  publicationMode: 'Gazette & Local Newspapers' | 'Gram Panchayat Notice Board' | 'Registered Post' | 'Portal';
  responseDeadline: string;
  serviceDate?: string;
  serviceMode?: 'Speed Post' | 'Direct Affixture' | 'Personal Hand Delivery';
  recipientOwnerId?: string;
  isBreached: boolean;
  daysRemaining: number;
}

export interface Objection {
  id: string;
  caseId: string;
  parcelId: string;
  objectorName: string;
  objectorContact: string;
  receiptDate: string;
  groundsCategory: 'Valuation & Compensation' | 'Measurement / Boundary Dispute' | 'Ownership / Title Claim' | 'Environmental / Religious Structure';
  substance: string;
  isWithinWindow: boolean;
  disposalState: 'PENDING' | 'ACCEPTED' | 'REJECTED' | 'OVERDUE';
  disposalDate?: string;
  disposalReasons?: string;
  decidingOfficer?: string;
}

export interface AwardComponent {
  id: string;
  label: string;
  labelHi: string;
  amount: number;
}

export interface Award {
  id: string;
  caseId: string;
  ownershipRecordId: string;
  ownerName: string;
  components: AwardComponent[];
  totalAmount: number;
  currency: string;
  determinationDate: string;
  determiningAuthority: string;
  disbursementState: 'UNPAID' | 'PART_PAID' | 'FULLY_PAID';
}

export interface Payout {
  id: string;
  awardId: string;
  amount: number;
  payoutDate: string;
  instrumentReference: string; // e.g. "DBT/PFMS/2024/991204"
  beneficiaryName: string;
  bankAccountMasked: string;
  ifsc: string;
  status: 'SUCCESS' | 'PROCESSING' | 'FAILED';
}

export type ReviewState = 'AUTO_ACCEPTED' | 'PENDING_REVIEW' | 'CORRECTED' | 'CONFIRMED' | 'MANUAL_ENTRY_REQUIRED';

export interface BoundingBox {
  pageNumber: number;
  x: number; // percentage or normalized 0-100
  y: number;
  width: number;
  height: number;
}

export interface ExtractedField {
  id: string;
  fieldName: string;
  fieldLabel: string;
  fieldLabelHi: string;
  extractedValue: string;
  originalExtractedValue: string;
  confidence: number; // 0.0 - 1.0
  reviewState: ReviewState;
  boundingBox: BoundingBox;
  correctedBy?: string;
  correctedAt?: string;
}

export interface DocumentRecord {
  id: string;
  caseId: string;
  title: string;
  documentType: '7/12 Extract (Record of Rights)' | 'Sale Deed (Kharedikhat)' | 'Section 11 Gazette Notification' | 'Joint Measurement Survey Map' | 'Aadhaar / KYC Verification' | 'Bank Passbook / Mandate';
  filename: string;
  fileSize: number; // bytes
  fileSizeFormatted: string;
  contentType: 'application/pdf' | 'image/png' | 'image/jpeg';
  uploadDate: string;
  uploadedBy: string;
  checksum: string;
  processingState: 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'EXTRACTION_FAILED' | 'REJECTED_LOW_QUALITY';
  detectedScript: 'Devanagari' | 'Latin' | 'Marathi' | 'Hindi';
  extractedFields: ExtractedField[];
  previewUrl?: string;
}

export type ValidationSeverity = 'BLOCKING' | 'MAJOR' | 'MINOR' | 'ADVISORY';
export type ResolutionState = 'OPEN' | 'RESOLVED_BY_CORRECTION' | 'WAIVED';

export interface ValidationIssue {
  id: string;
  ruleId: string;
  ruleTitle: string;
  severity: ValidationSeverity;
  affectedEntity: string;
  entityId: string;
  description: string;
  observedValues: string;
  detectedAt: string;
  resolutionState: ResolutionState;
  waiverReason?: string;
  waivedBy?: string;
  waivedAt?: string;
}

export interface AcquisitionCase {
  id: string;
  caseReference: string; // e.g. "MH-PUN-2024-NH48-0042"
  projectId: string;
  projectName: string;
  projectNameHi: string;
  state: string;
  district: string;
  tehsil: string;
  village: string;
  stage: CaseStage;
  stageStartDate: string;
  stageDeadline: string;
  daysRemaining: number;
  isBreached: boolean;
  totalParcelsCount: number;
  totalExtentHa: number;
  totalAwardedAmount: number;
  totalDisbursedAmount: number;
  sanctionedBudget: number;
  parcels: LandParcel[];
  ownershipRecords: OwnershipRecord[];
  notices: StatutoryNotice[];
  objections: Objection[];
  awards: Award[];
  payouts: Payout[];
  documents: DocumentRecord[];
  validationIssues: ValidationIssue[];
  // ML delay scoring
  riskProbability: number; // 0.0 to 1.0
  riskBand: RiskBand;
  priorityScore: number; // 0 to 100
  explanationFactors: ExplanationFactor[];
  recommendedActions: RecommendedAction[];
  officerOverride?: OfficerOverride;
  lastScoredAt: string;
  modelVersion: string;
  // Citizen next expected step
  nextExpectedStep: string;
  nextExpectedStepHi: string;
}

export interface ProjectRecord {
  id: string;
  name: string;
  nameHi: string;
  implementingAuthority: string; // e.g. "National Highways Authority of India (NHAI)"
  administrativeArea: string;
  purposeCategory: 'National Highway Expansion' | 'Freight Corridor Railway' | 'Airport Infrastructure' | 'Renewable Energy Hub';
  sanctionedExtentHa: number;
  totalCases: number;
  activeCases: number;
  completedCases: number;
  totalBudgetINR: number;
}

export interface AuditEvent {
  id: string;
  caseId?: string;
  actorId: string;
  actorName: string;
  actorRole: Role;
  eventType: 
    | 'CASE_CREATED'
    | 'STAGE_TRANSITION'
    | 'DOCUMENT_UPLOADED'
    | 'EXTRACTION_COMPLETED'
    | 'OCR_FIELD_CORRECTED'
    | 'OCR_FIELD_CONFIRMED'
    | 'VALIDATION_ISSUE_DETECTED'
    | 'VALIDATION_ISSUE_WAIVED'
    | 'VALIDATION_ISSUE_RESOLVED'
    | 'NOTICE_ISSUED'
    | 'DEADLINE_APPROACHING'
    | 'DEADLINE_BREACHED'
    | 'OBJECTION_RECORDED'
    | 'OBJECTION_DISPOSED'
    | 'AWARD_DETERMINED'
    | 'PAYOUT_RECORDED'
    | 'OFFICER_OVERRIDE_RECORDED'
    | 'RECOMMENDED_ACTION_ACCEPTED'
    | 'IMPORT_BATCH_COMMITTED'
    | 'DATA_ACCESS_REQUEST_SERVED'
    | 'PERSONAL_DATA_ERASED'
    | 'CITIZEN_SESSION_ISSUED';
  entityType: string;
  entityId: string;
  occurrenceTime: string;
  details: string;
  priorValue?: string;
  newValue?: string;
}

export interface ImportBatchRow {
  rowNumber: number;
  entityType: 'Land_Parcel' | 'Ownership_Record' | 'Document';
  surveyNumber: string;
  ownerName: string;
  extentHa: string;
  share: string;
  status: 'VALID' | 'COMMITTED' | 'REJECTED';
  rejectionRule?: string;
  errorMessage?: string;
}

export interface ImportBatch {
  id: string;
  batchNumber: string;
  submittedBy: string;
  submittedAt: string;
  totalRows: number;
  committedRows: number;
  rejectedRows: number;
  status: 'COMPLETED' | 'IN_PROGRESS' | 'FAILED';
  rows: ImportBatchRow[];
}

export interface DataSubjectRequest {
  id: string;
  requestType: 'ACCESS_REQUEST' | 'CORRECTION_REQUEST';
  caseReference: string;
  citizenName: string;
  mobile: string;
  submittedAt: string;
  status: 'PENDING' | 'SERVED' | 'DISPOSED_BY_OFFICER';
  targetField?: string;
  currentValue?: string;
  assertedValue?: string;
  disposalNotes?: string;
  completedAt?: string;
}

export interface ModelObservabilityStats {
  modelVersion: string;
  promotedAt: string;
  promotedBy: string;
  prAuc: number;
  rocAuc: number;
  brierScore: number;
  eceCalibration: number;
  precisionRecallLift: number;
  trainingLabelBaseRate: number;
  evaluationLabelBaseRate: number;
  censoredRowCount: number;
  censoringRate: number;
  realizedDelayRate: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
  predictedMeanProbability: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
  featureDriftPSI: {
    featureName: string;
    psiValue: number;
    status: 'NORMAL' | 'MODERATE' | 'SIGNIFICANT_DRIFT';
  }[];
  retrainingStatus: 'ACTIVE' | 'NEEDS_RETRAINING' | 'HEALTHY';
}
