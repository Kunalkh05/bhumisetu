import { ReraParcelProjectRecord, StatutoryNoticeIssued, ReraZoneAggregatedStatus } from '../types/rera';
import { INITIAL_RERA_RECORDS, ACQUISITION_ZONES, AcquisitionZoneInfo } from '../data/mockReraData';
import { AcquisitionCase } from '../types';

class ReraIntegrationService {
  private records: ReraParcelProjectRecord[] = [...INITIAL_RERA_RECORDS];
  private zones: AcquisitionZoneInfo[] = [...ACQUISITION_ZONES];
  private listeners: (() => void)[] = [];

  public subscribe(listener: () => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notify() {
    this.listeners.forEach(l => l());
  }

  public getAllRecords(): ReraParcelProjectRecord[] {
    return [...this.records];
  }

  public getAllZones(): AcquisitionZoneInfo[] {
    return [...this.zones];
  }

  public getRecordsByCase(caseId: string): ReraParcelProjectRecord[] {
    return this.records.filter(r => r.caseId === caseId);
  }

  public getRecordsByZone(zoneId: string): ReraParcelProjectRecord[] {
    return this.records.filter(r => r.acquisitionZoneId === zoneId);
  }

  public getRecordByParcel(parcelId: string): ReraParcelProjectRecord | undefined {
    return this.records.find(r => r.parcelId === parcelId);
  }

  /**
   * Computes aggregated project status distributions across active land acquisition zones
   */
  public getAggregatedZoneStatus(): ReraZoneAggregatedStatus[] {
    return this.zones.map(zone => {
      const zoneProjects = this.records.filter(r => r.acquisitionZoneId === zone.id);
      const onTrackCount = zoneProjects.filter(r => r.performanceStatus === 'ON_TRACK').length;
      const delayedCount = zoneProjects.filter(r => r.performanceStatus === 'DELAYED').length;
      const completedCount = zoneProjects.filter(r => r.performanceStatus === 'COMPLETED').length;
      const lapsedCount = zoneProjects.filter(r => r.performanceStatus === 'LAPSED_DEFAULT').length;
      
      const totalAreaOverlapHa = zoneProjects.reduce((sum, r) => sum + r.overlappingAreaWithParcelHa, 0);
      const totalAllotteesImpacted = zoneProjects.reduce((sum, r) => sum + r.allottees.allotteesCount, 0);
      const totalEscrowINR = zoneProjects.reduce((sum, r) => sum + r.escrowAudit.designated70PctDepositBalance, 0);
      const avgProgress = zoneProjects.length > 0 
        ? Math.round(zoneProjects.reduce((sum, r) => sum + r.physicalProgressPct, 0) / zoneProjects.length)
        : 0;
      const sec11BreachesCount = zoneProjects.filter(r => r.crossReference.sec11_4_ViolationDetected).length;

      return {
        zoneId: zone.id,
        zoneName: zone.name,
        zoneNameHi: zone.nameHi,
        district: zone.district,
        majorProjectCorridor: zone.corridor,
        totalProjects: zoneProjects.length,
        onTrackCount,
        delayedCount,
        completedCount,
        lapsedCount,
        totalAreaOverlapHa: Number(totalAreaOverlapHa.toFixed(2)),
        totalAllotteesImpacted,
        totalEscrowINR,
        averageProgressPct: avgProgress,
        sec11BreachesCount,
        projects: zoneProjects,
      };
    });
  }

  /**
   * Simulates a live real-time API call to the State RERA Registry Gateway
   * Returns latency, verified sha-256 certificate digest, and latest timestamp
   */
  public async fetchRealTimeReport(recordId: string): Promise<ReraParcelProjectRecord> {
    // Simulate real network trip to state RERA gateway
    await new Promise(resolve => setTimeout(resolve, 600 + Math.random() * 400));

    const index = this.records.findIndex(r => r.id === recordId);
    if (index === -1) {
      throw new Error(`RERA Record with ID ${recordId} not found.`);
    }

    const rec = this.records[index];
    const updated: ReraParcelProjectRecord = {
      ...rec,
      lastApiSyncTimestamp: new Date().toISOString(),
      apiLatencyMs: Math.floor(110 + Math.random() * 80),
      apiStatus: 'LIVE_SYNCED',
      certDigestSha256: Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join(''),
    };

    this.records[index] = updated;
    this.notify();
    return updated;
  }

  /**
   * Refreshes all records for a given case via parallel gateway query
   */
  public async syncAllForCase(caseId: string): Promise<ReraParcelProjectRecord[]> {
    await new Promise(resolve => setTimeout(resolve, 800));
    const now = new Date().toISOString();

    this.records = this.records.map(r => {
      if (r.caseId === caseId) {
        return {
          ...r,
          lastApiSyncTimestamp: now,
          apiLatencyMs: Math.floor(95 + Math.random() * 60),
          apiStatus: 'LIVE_SYNCED',
        };
      }
      return r;
    });

    this.notify();
    return this.getRecordsByCase(caseId);
  }

  /**
   * Issue a statutory notice under RFCTLARR Act 2013 (e.g. Section 11(4) prohibition or Sec 21)
   */
  public issueStatutoryNotice(
    recordId: string, 
    type: string, 
    recipient: string, 
    summary: string
  ): StatutoryNoticeIssued {
    const record = this.records.find(r => r.id === recordId);
    if (!record) {
      throw new Error(`Record ${recordId} not found.`);
    }

    const newNotice: StatutoryNoticeIssued = {
      noticeId: `RERA-NOTIF-${Date.now().toString().slice(-6)}`,
      type,
      issuedOn: new Date().toISOString().split('T')[0],
      recipient,
      status: 'DISPATCHED',
      speedPostTracking: `SP${Math.floor(100000000 + Math.random() * 900000000)}IN`,
      summary,
    };

    record.officialNoticesServed = [
      newNotice,
      ...(record.officialNoticesServed || []),
    ];

    this.notify();
    return newNotice;
  }

  /**
   * Update officer legal observation notes
   */
  public updateOfficerNotes(recordId: string, notes: string): void {
    const record = this.records.find(r => r.id === recordId);
    if (record) {
      record.officerNotes = notes;
      this.notify();
    }
  }

  /**
   * Cross-reference helper to compute milestone clashes dynamically if case stage changes
   */
  public recalculateCrossReference(caseRecord: AcquisitionCase) {
    this.records = this.records.map(rec => {
      if (rec.caseId !== caseRecord.id) return rec;

      return {
        ...rec,
        crossReference: {
          ...rec.crossReference,
          caseMilestone: caseRecord.stage,
          caseDeadline: caseRecord.stageDeadline,
        },
      };
    });
    this.notify();
  }

  /**
   * Search external state RERA registry for arbitrary query
   */
  public searchExternalRegistry(query: string) {
    const q = query.toLowerCase().trim();
    if (!q) return [];

    return this.records.filter(r => 
      r.projectName.toLowerCase().includes(q) ||
      r.promoterName.toLowerCase().includes(q) ||
      r.reraRegistrationNo.toLowerCase().includes(q) ||
      r.surveyNumber.toLowerCase().includes(q) ||
      r.cadastralSurveyNumbersListed.some(s => s.toLowerCase().includes(q))
    );
  }
}

export const reraService = new ReraIntegrationService();
