import { CaseStage } from './index';

export type ReraProjectStatus = 
  | 'REGISTERED_ACTIVE' 
  | 'REVOKED' 
  | 'EXPIRED' 
  | 'COMPLETED_OCCUPIED' 
  | 'UNDER_INVESTIGATION' 
  | 'LAPSED_DEFAULT';

export type ReraProjectType = 
  | 'Residential Plotted Layout' 
  | 'Plotted Layout Development'
  | 'Group Housing / High-Rise' 
  | 'Commercial Boulevard & Logistics' 
  | 'Mixed-Use Township' 
  | 'Industrial Park';

export type ReraPerformanceStatus = 
  | 'ON_TRACK' 
  | 'DELAYED' 
  | 'COMPLETED' 
  | 'LAPSED_DEFAULT';

export interface ReraZoneAggregatedStatus {
  zoneId: string;
  zoneName: string;
  zoneNameHi: string;
  district: string;
  majorProjectCorridor: string;
  totalProjects: number;
  onTrackCount: number;
  delayedCount: number;
  completedCount: number;
  lapsedCount: number;
  totalAreaOverlapHa: number;
  totalAllotteesImpacted: number;
  totalEscrowINR: number;
  averageProgressPct: number;
  sec11BreachesCount: number;
  projects: ReraParcelProjectRecord[];
}

export interface ReraQuarterlyReport {
  quarter: string;
  financialYear: string;
  civilWorkPct: number;
  servicesPct: number;
  filedOn: string;
  complianceNote: string;
  caCertificateRef?: string;
  engineerCertificateRef?: string;
}

export interface ReraLitigationRecord {
  caseNo: string;
  complainant: string;
  forum: 'RERA Authority (Sec 31)' | 'RERA Appellate Tribunal (REAT)' | 'High Court Writ' | 'Consumer Disputes Commission';
  subject: string;
  status: 'PENDING' | 'DISPOSED' | 'STAY_GRANTED';
  interimStayActive: boolean;
  orderSummary?: string;
  filingDate: string;
  nextHearingDate?: string;
}

export interface ReraEscrowAudit {
  bankName: string;
  branch: string;
  accountMasked: string;
  ifscCode: string;
  designated70PctDepositBalance: number; // in INR
  totalEstimatedProjectCost: number;
  actualIncurredExpense: number;
  caCertDate: string;
  engineerCertDate: string;
  isEscrowCompliant: boolean;
  registeredMortgageBank?: string;
  mortgageChargeAmountINR?: number;
}

export interface ReraAllotteeSummary {
  totalUnitsSanctioned: number;
  unitsBooked: number;
  registeredAgreementsForSale: number;
  allotteesCount: number;
  buyerAssociationName?: string;
  committedHandoverDate: string;
  totalFundsCollectedINR: number;
}

export type MilestoneConflictLevel = 
  | 'CRITICAL_BLOCKER' 
  | 'HIGH_RISK' 
  | 'MODERATE_WARNING' 
  | 'COMPLIANT_CLEAR';

export type ConflictCategory = 
  | 'SECTION_11_4_BREACH' 
  | 'POSSESSION_CLASH' 
  | 'ALLOTTEE_ENCUMBRANCE' 
  | 'ESCROW_MORTGAGE_CHARGE' 
  | 'RESIDENTIAL_RESETTLEMENT' 
  | 'NO_ADVERSE_CONFLICT';

export interface MilestoneCrossReferenceAnalysis {
  caseMilestone: CaseStage;
  caseMilestoneLabel: string;
  caseDeadline: string;
  conflictLevel: MilestoneConflictLevel;
  conflictCategory: ConflictCategory;
  conflictTitle: string;
  conflictTitleHi: string;
  conflictDetails: string;
  legalBasis: string;
  statutoryRiskScore: number; // 0 to 100
  allotteeSolatiumExposureINR: number;
  sec11_4_ViolationDetected: boolean;
  sec11_4_Details?: string;
  recommendedActions: {
    id: string;
    label: string;
    labelHi: string;
    actionType: 
      | 'ISSUE_FREEZE_NOTICE' 
      | 'SUMMON_PROMOTER' 
      | 'NOTIFY_ESCROW_BANK' 
      | 'TRANSFER_TO_SEC15_OBJECTIONS' 
      | 'INSPECT_JOINT_CADASTRAL' 
      | 'INTERVENE_IN_TRIBUNAL';
    urgency: 'IMMEDIATE' | 'HIGH' | 'ROUTINE';
    statutoryRemedy: string;
  }[];
}

export interface StatutoryNoticeIssued {
  noticeId: string;
  type: string;
  issuedOn: string;
  recipient: string;
  status: 'SERVED' | 'PENDING_ACKNOWLEDGEMENT' | 'DISPATCHED';
  speedPostTracking?: string;
  summary: string;
}

export interface ReraParcelProjectRecord {
  id: string;
  parcelId: string;
  surveyNumber: string;
  caseId: string;
  caseReference: string;
  reraRegistrationNo: string;
  projectName: string;
  projectNameHi: string;
  promoterName: string;
  promoterType: 'Individual / Proprietor' | 'LLP / Partnership' | 'Private Limited Company' | 'Public Limited';
  promoterContact: string;
  promoterAddress: string;
  stateReraPortal: 'MahaRERA (Maharashtra)' | 'UP RERA (Uttar Pradesh)' | 'GujRERA (Gujarat)' | 'K-RERA (Karnataka)' | 'Central RERA Node';
  projectType: ReraProjectType;
  projectStatus: ReraProjectStatus;
  sanctioningAuthority: string;
  sanctionOrderNo: string;
  sanctionDate: string;
  totalProjectAreaHa: number;
  overlappingAreaWithParcelHa: number;
  overlapPercentage: number;
  cadastralSurveyNumbersListed: string[];
  registrationDate: string;
  originalCompletionDate: string;
  revisedCompletionDate: string;
  physicalProgressPct: number;
  escrowAudit: ReraEscrowAudit;
  allottees: ReraAllotteeSummary;
  quarterlyReports: ReraQuarterlyReport[];
  litigations: ReraLitigationRecord[];
  crossReference: MilestoneCrossReferenceAnalysis;
  acquisitionZoneId: string;
  acquisitionZoneName: string;
  performanceStatus: ReraPerformanceStatus;
  delayMonths?: number;
  lastApiSyncTimestamp: string;
  apiLatencyMs: number;
  apiStatus: 'LIVE_SYNCED' | 'REFRESHING' | 'STALE' | 'VERIFIED_SIGNATURE';
  certDigestSha256: string;
  officerNotes?: string;
  officialNoticesServed?: StatutoryNoticeIssued[];
}
