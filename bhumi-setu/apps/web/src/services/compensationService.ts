/**
 * Compensation service for the BHUMISETU platform.
 * Handles API calls for compensation calculation and records.
 */

import type {
  CompensationRecord,
  MarketAssessment,
  RehabilitationEntitlement,
} from '../types/compensation';

const API_BASE = import.meta.env.VITE_API_URL || '';

/**
 * Calculate compensation for a land parcel via the backend API.
 */
export async function calculateCompensationAPI(params: {
  caseId: string;
  parcelId: string;
  circleRatePerSqm: number;
  avgSalePricePerSqm: number;
  isRural: boolean;
  ruralMultiplier?: number;
}): Promise<CompensationRecord> {
  const response = await fetch(`${API_BASE}/api/v1/compensation/calculate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Get compensation record for a specific case.
 */
export async function getCompensationByCaseId(
  caseId: string,
): Promise<CompensationRecord[]> {
  const response = await fetch(
    `${API_BASE}/api/v1/cases/${caseId}/compensation`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Get market assessment for a parcel.
 */
export async function getMarketAssessment(
  parcelId: string,
): Promise<MarketAssessment> {
  const response = await fetch(
    `${API_BASE}/api/v1/parcels/${parcelId}/assessment`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Get rehabilitation entitlements for an affected family.
 */
export async function getRehabilitationEntitlements(
  caseId: string,
  familyId: string,
): Promise<RehabilitationEntitlement[]> {
  const response = await fetch(
    `${API_BASE}/api/v1/cases/${caseId}/rehabilitation/${familyId}`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) throw response;
  return response.json();
}

/**
 * Update compensation status (officer action).
 */
export async function updateCompensationStatus(
  compensationId: string,
  status: string,
  notes?: string,
): Promise<CompensationRecord> {
  const response = await fetch(
    `${API_BASE}/api/v1/compensation/${compensationId}/status`,
    {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status, notes }),
    },
  );

  if (!response.ok) throw response;
  return response.json();
}
