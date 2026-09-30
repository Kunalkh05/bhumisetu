/**
 * BHUMISETU Platform - Backend API Integration Service
 * 
 * Provides unified, typed communication with the FastAPI backend service
 * at http://localhost:8000 (/api). Supports automatic fallback and synchronization
 * between live backend database records and local high-fidelity state.
 */

import { AcquisitionCase, UserSession, CaseStage, RiskBand, ImportBatch, DataSubjectRequest } from '../types';

export const API_BASE_URL = '/api';

export interface BackendConnectionStatus {
  connected: boolean;
  statusText: string;
  latencyMs?: number;
  lastChecked?: string;
  appEnv?: string;
}

class BackendApiService {
  private isConnected = false;
  private sessionToken: string | null = null;
  private csrfToken: string | null = null;
  private listeners: ((status: BackendConnectionStatus) => void)[] = [];

  constructor() {
    // Attempt health check on init
    this.checkHealth().catch(() => {});
  }

  public subscribeStatus(listener: (status: BackendConnectionStatus) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notifyStatus(status: BackendConnectionStatus) {
    this.listeners.forEach(l => l(status));
  }

  /**
   * Probes the FastAPI /healthz endpoint
   */
  public async checkHealth(): Promise<BackendConnectionStatus> {
    const startTime = performance.now();
    try {
      const response = await fetch('/healthz', {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      }).catch(async () => {
        // Fallback to /api/healthz if proxied under /api
        return await fetch(`${API_BASE_URL}/healthz`);
      });

      const latencyMs = Math.round(performance.now() - startTime);

      if (response.ok) {
        this.isConnected = true;
        const status: BackendConnectionStatus = {
          connected: true,
          statusText: 'Connected (FastAPI :8000)',
          latencyMs,
          lastChecked: new Date().toLocaleTimeString(),
          appEnv: 'development'
        };
        this.notifyStatus(status);
        return status;
      }
    } catch {
      // Backend is offline / unreachable
    }

    this.isConnected = false;
    const status: BackendConnectionStatus = {
      connected: false,
      statusText: 'Standalone / Simulation Mode',
      lastChecked: new Date().toLocaleTimeString()
    };
    this.notifyStatus(status);
    return status;
  }

  public getConnected(): boolean {
    return this.isConnected;
  }

  /**
   * Sets persona session credentials with backend auth
   */
  public async setPersonaSession(user: UserSession): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/persona`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          userId: user.id,
          name: user.name,
          role: user.role,
          jurisdiction: user.jurisdiction,
          isCitizen: Boolean(user.isCitizen)
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.sessionToken) {
          this.sessionToken = data.sessionToken;
        }
        if (data.csrfToken) {
          this.csrfToken = data.csrfToken;
        }
        return true;
      }
    } catch {
      // Fallback
    }
    return false;
  }

  /**
   * Helper for authenticated API calls with cookie & bearer header
   */
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T | null> {
    try {
      const headers = new Headers(options.headers || {});
      headers.set('Accept', 'application/json');
      
      if (this.sessionToken) {
        headers.set('Authorization', `Bearer ${this.sessionToken}`);
      }
      if (this.csrfToken) {
        headers.set('x-csrf-token', this.csrfToken);
      }

      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
        credentials: 'include'
      });

      if (!res.ok) {
        return null;
      }

      return await res.json() as T;
    } catch {
      return null;
    }
  }

  // ==========================================
  // Officer Endpoints
  // ==========================================

  /**
   * Fetch Officer Dashboard aggregates from GET /api/officer/dashboard
   */
  public async getDashboardMetrics(): Promise<any | null> {
    return this.request<any>('/officer/dashboard');
  }

  /**
   * Fetch live list of cases from GET /api/officer/cases
   */
  public async getCases(): Promise<any[] | null> {
    return this.request<any[]>('/officer/cases');
  }

  /**
   * Fetch a single case workspace from GET /api/officer/cases/{id}/workspace
   */
  public async getCaseWorkspace(caseId: string | number): Promise<any | null> {
    const numericId = typeof caseId === 'number' ? caseId : parseInt(caseId.replace(/\D/g, ''), 10) || 1;
    return this.request<any>(`/officer/cases/${numericId}/workspace`);
  }

  /**
   * Fetch case timeline events from GET /api/officer/cases/{id}/timeline
   */
  public async getCaseTimeline(caseId: string | number): Promise<any[] | null> {
    const numericId = typeof caseId === 'number' ? caseId : parseInt(caseId.replace(/\D/g, ''), 10) || 1;
    return this.request<any[]>(`/officer/cases/${numericId}/timeline`);
  }

  /**
   * Transition statutory stage via POST /api/officer/cases/{id}/stage
   */
  public async transitionCaseStage(caseId: string | number, newStage: CaseStage): Promise<boolean> {
    const numericId = typeof caseId === 'number' ? caseId : parseInt(caseId.replace(/\D/g, ''), 10) || 1;
    const res = await this.request<any>(`/officer/cases/${numericId}/stage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        new_stage: newStage,
        occurrence_time: new Date().toISOString()
      })
    });
    return Boolean(res);
  }

  /**
   * Fetch AI Intervention Queue from GET /api/officer/queue
   */
  public async getInterventionQueue(): Promise<any | null> {
    return this.request<any>('/officer/queue');
  }

  /**
   * Dispose AI recommended action via POST /api/officer/queue/{case_id}/actions/{action_id}/disposition
   */
  public async disposeRecommendedAction(
    caseId: string | number,
    actionId: string,
    disposition: 'ACCEPTED' | 'REJECTED' | 'DEFERRED',
    reason: string
  ): Promise<boolean> {
    const numericId = typeof caseId === 'number' ? caseId : parseInt(caseId.replace(/\D/g, ''), 10) || 1;
    const res = await this.request<any>(`/officer/queue/${numericId}/actions/${actionId}/disposition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        disposition,
        reason,
        occurrence_time: new Date().toISOString(),
        expected_version: 1
      })
    });
    return Boolean(res);
  }

  /**
   * Override case delay risk via POST /api/officer/predictions/{case_id}/override
   */
  public async overrideRiskBand(caseId: string | number, newRiskBand: RiskBand, reason: string): Promise<boolean> {
    const numericId = typeof caseId === 'number' ? caseId : parseInt(caseId.replace(/\D/g, ''), 10) || 1;
    const res = await this.request<any>(`/officer/predictions/${numericId}/override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        overridden_value: newRiskBand,
        reason,
        occurrence_time: new Date().toISOString()
      })
    });
    return Boolean(res);
  }

  /**
   * Fetch open statutory validation issues from GET /api/officer/issues
   */
  public async getValidationIssues(): Promise<any[] | null> {
    return this.request<any[]>('/officer/issues');
  }

  /**
   * Waive a statutory validation issue via POST /api/officer/issues/{issue_id}/waive
   */
  public async waiveValidationIssue(issueId: string | number, reason: string): Promise<boolean> {
    const numericId = typeof issueId === 'number' ? issueId : parseInt(issueId.replace(/\D/g, ''), 10) || 1;
    const res = await this.request<any>(`/officer/issues/${numericId}/waive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reason,
        expected_version: 1
      })
    });
    return Boolean(res);
  }

  /**
   * Query PostGIS land parcels within bounding box from GET /api/officer/gis/parcels
   */
  public async getGisParcelsInBbox(bbox: string): Promise<any | null> {
    return this.request<any>(`/officer/gis/parcels?bbox=${encodeURIComponent(bbox)}`);
  }

  /**
   * Query full-fidelity parcel geometry from GET /api/officer/gis/parcels/{parcel_id}/geometry
   */
  public async getParcelGeometry(parcelId: number): Promise<any | null> {
    return this.request<any>(`/officer/gis/parcels/${parcelId}/geometry`);
  }

  /**
   * Fetch DPDP Act 2023 DSAR requests from GET /api/officer/dsar
   */
  public async getDsarQueue(): Promise<any[] | null> {
    return this.request<any[]>('/officer/dsar');
  }

  /**
   * Dispose DSAR request via POST /api/officer/dsar/{id}/disposal
   */
  public async disposeDsarRequest(requestId: string | number, notes: string): Promise<boolean> {
    const numericId = typeof requestId === 'number' ? requestId : parseInt(requestId.replace(/\D/g, ''), 10) || 1;
    const res = await this.request<any>(`/officer/dsar/${numericId}/disposal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        notes,
        action: 'APPROVED'
      })
    });
    return Boolean(res);
  }

  /**
   * Submit Bulk Land Record Import via POST /api/officer/imports
   */
  public async submitBulkImport(rows: any[]): Promise<any | null> {
    return this.request<any>('/officer/imports', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rows: rows.map((r, i) => ({
          ordinal: i + 1,
          entity_type: 'parcel',
          payload: r
        }))
      })
    });
  }

  // ==========================================
  // Citizen Endpoints
  // ==========================================

  /**
   * Citizen case query via GET /api/citizen/case
   */
  public async getCitizenCase(): Promise<any | null> {
    return this.request<any>('/citizen/case');
  }

  /**
   * Submit citizen objection via POST /api/citizen/objection
   */
  public async submitCitizenObjection(payload: {
    caseId: string;
    objectorName: string;
    contact: string;
    surveyNumber: string;
    groundsCategory: string;
    substance: string;
  }): Promise<any | null> {
    return this.request<any>('/citizen/objection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  }

  /**
   * Submit citizen DPDP Data Subject Request via POST /api/citizen/correction
   */
  public async submitCitizenDsr(payload: {
    caseRef: string;
    citizenName: string;
    mobile: string;
    type: string;
    targetField?: string;
    assertedValue?: string;
  }): Promise<any | null> {
    return this.request<any>('/citizen/correction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  }
}

export const backendApi = new BackendApiService();
