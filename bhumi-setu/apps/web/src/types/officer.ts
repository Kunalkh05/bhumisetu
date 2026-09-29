/**
 * Officer-related type definitions for the BHUMISETU officer portal.
 */

/** Officer designation levels in the land acquisition hierarchy */
export type OfficerDesignation =
  | 'collector'
  | 'additional_collector'
  | 'sub_divisional_officer'
  | 'tehsildar'
  | 'naib_tehsildar'
  | 'revenue_inspector'
  | 'talathi'
  | 'surveyor'
  | 'data_entry_operator';

/** Officer status in the system */
export type OfficerStatus = 'active' | 'on_leave' | 'transferred' | 'retired' | 'suspended';

/** Permission levels for RBAC */
export type PermissionLevel =
  | 'read'
  | 'write'
  | 'approve'
  | 'admin';

/** Officer profile information */
export interface OfficerProfile {
  id: string;
  name: string;
  designation: OfficerDesignation;
  department: string;
  district: string;
  taluka: string;
  email: string;
  mobile: string;
  status: OfficerStatus;
  permissions: PermissionLevel[];
  assignedCases: number;
  completedCases: number;
  joinedAt: string;
  lastActiveAt: string;
}

/** Case assignment to an officer */
export interface CaseAssignment {
  caseId: string;
  officerId: string;
  role: 'primary' | 'support' | 'reviewer';
  assignedAt: string;
  dueDate?: string;
  status: 'active' | 'completed' | 'reassigned';
}

/** Officer workload summary for dashboard */
export interface WorkloadSummary {
  totalAssigned: number;
  inProgress: number;
  pendingReview: number;
  overdue: number;
  completedThisMonth: number;
  averageCompletionDays: number;
}

/** Audit log entry for officer actions */
export interface OfficerAuditEntry {
  id: string;
  officerId: string;
  action: string;
  resourceType: 'case' | 'document' | 'parcel' | 'notice' | 'compensation';
  resourceId: string;
  details: Record<string, unknown>;
  ipAddress: string;
  timestamp: string;
}

/** Transfer record for officer jurisdiction changes */
export interface TransferRecord {
  officerId: string;
  fromDistrict: string;
  fromTaluka: string;
  toDistrict: string;
  toTaluka: string;
  effectiveDate: string;
  orderNumber: string;
  casesTransferred: number;
}
