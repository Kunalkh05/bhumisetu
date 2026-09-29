/**
 * Constants for RFCTLARR Act 2013 statutory timelines.
 *
 * These constants define the mandatory timelines for each stage of
 * land acquisition as specified in the Right to Fair Compensation
 * and Transparency in Land Acquisition, Rehabilitation and
 * Resettlement Act, 2013.
 */

/** Statutory timeline limits in calendar days */
export const STATUTORY_TIMELINES = {
  /** Section 4: Social Impact Assessment - maximum duration */
  SIA_MAX_DURATION_DAYS: 180, // 6 months

  /** Section 6: Expert Group review of SIA - maximum duration */
  EXPERT_GROUP_REVIEW_DAYS: 60,

  /** Section 7: Examination by appropriate Government */
  GOVT_EXAMINATION_DAYS: 30,

  /** Section 11: Preliminary notification validity */
  SECTION_11_VALIDITY_MONTHS: 12,

  /** Section 15: Hearing of objections - minimum notice period */
  OBJECTION_HEARING_NOTICE_DAYS: 30,

  /** Section 15: Deadline for hearing objections after Section 11 */
  OBJECTION_HEARING_DEADLINE_DAYS: 60,

  /** Section 19: Declaration - must be within 12 months of Section 11 */
  SECTION_19_DEADLINE_MONTHS: 12,

  /** Section 23: Award - must be within 12 months of Section 19 */
  SECTION_23_DEADLINE_MONTHS: 12,

  /** Section 25: Possession - notice period before taking possession */
  POSSESSION_NOTICE_DAYS: 60,

  /** Section 30(3): Interest rate on additional compensation */
  ADDITIONAL_COMPENSATION_RATE: 0.12, // 12% per annum

  /** Section 30(1): Solatium percentage of market value */
  SOLATIUM_PERCENTAGE: 1.0, // 100% of market value

  /** Section 64: Temporary acquisition - maximum period in years */
  TEMPORARY_ACQUISITION_MAX_YEARS: 3,

  /** Section 77: Urgency clause - additional compensation percentage */
  URGENCY_ADDITIONAL_COMPENSATION: 0.75, // 75% of market value
} as const;

/** Rural area multiplier bounds as per Section 26(1)(b) */
export const RURAL_MULTIPLIER = {
  MIN: 1.0,
  MAX: 2.0,
  DEFAULT: 1.0,
} as const;

/** Case stage sequence in the acquisition workflow */
export const CASE_STAGES = [
  'sia_initiated',
  'sia_completed',
  'expert_review',
  'govt_approval',
  'section_11_notification',
  'objection_hearing',
  'section_19_declaration',
  'survey_measurement',
  'valuation',
  'section_23_award',
  'payment',
  'possession',
  'completed',
] as const;

export type CaseStage = (typeof CASE_STAGES)[number];

/** Human-readable labels for each case stage */
export const CASE_STAGE_LABELS: Record<CaseStage, string> = {
  sia_initiated: 'SIA Initiated',
  sia_completed: 'SIA Completed',
  expert_review: 'Expert Group Review',
  govt_approval: 'Government Approval',
  section_11_notification: 'Section 11 Notification',
  objection_hearing: 'Objection Hearing',
  section_19_declaration: 'Section 19 Declaration',
  survey_measurement: 'Survey & Measurement',
  valuation: 'Valuation',
  section_23_award: 'Section 23 Award',
  payment: 'Payment',
  possession: 'Possession',
  completed: 'Completed',
};

/** Maharashtra-specific district codes */
export const MAHARASHTRA_DISTRICTS: Record<string, string> = {
  'MH-MU': 'Mumbai City',
  'MH-MS': 'Mumbai Suburban',
  'MH-TH': 'Thane',
  'MH-PU': 'Pune',
  'MH-NG': 'Nagpur',
  'MH-AU': 'Aurangabad',
  'MH-NS': 'Nashik',
  'MH-KO': 'Kolhapur',
  'MH-SO': 'Solapur',
  'MH-SA': 'Sangli',
  'MH-ST': 'Satara',
  'MH-RT': 'Ratnagiri',
  'MH-SI': 'Sindhudurg',
  'MH-RG': 'Raigad',
  'MH-PL': 'Palghar',
  'MH-AH': 'Ahmednagar',
  'MH-BH': 'Bhandara',
  'MH-BU': 'Buldhana',
  'MH-CH': 'Chandrapur',
  'MH-DH': 'Dhule',
  'MH-GA': 'Gadchiroli',
  'MH-GO': 'Gondia',
  'MH-HI': 'Hingoli',
  'MH-JA': 'Jalgaon',
  'MH-JN': 'Jalna',
  'MH-LA': 'Latur',
  'MH-NA': 'Nanded',
  'MH-ND': 'Nandurbar',
  'MH-OS': 'Osmanabad',
  'MH-PA': 'Parbhani',
  'MH-WA': 'Wardha',
  'MH-WS': 'Washim',
  'MH-YA': 'Yavatmal',
  'MH-AM': 'Amravati',
  'MH-AK': 'Akola',
  'MH-BI': 'Beed',
};

/** API route constants */
export const API_ROUTES = {
  HEALTH: '/api/health',
  AUTH_LOGIN: '/api/v1/auth/login',
  AUTH_REFRESH: '/api/v1/auth/refresh',
  CASES: '/api/v1/cases',
  CASE_BY_ID: (id: string) => `/api/v1/cases/${id}`,
  CASE_WORKSPACE: (id: string) => `/api/v1/cases/${id}/workspace`,
  PARCELS: '/api/v1/parcels',
  DOCUMENTS: '/api/v1/documents',
  DOCUMENT_UPLOAD: '/api/v1/documents/upload',
  NOTICES: '/api/v1/notices',
  DASHBOARD: '/api/v1/dashboard',
  PREDICTIONS: '/api/v1/predictions',
  GIS: '/api/v1/gis',
  CITIZEN_SEARCH: '/api/v1/citizen/search',
  CITIZEN_CASE: (id: string) => `/api/v1/citizen/cases/${id}`,
  RETENTION_DSR: '/api/v1/retention/dsr',
} as const;
