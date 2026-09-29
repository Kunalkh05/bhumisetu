import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { reraService } from '../../services/reraService';
import { 
  ReraParcelProjectRecord, 
  MilestoneConflictLevel,
  StatutoryNoticeIssued,
  ReraPerformanceStatus,
  ReraZoneAggregatedStatus
} from '../../types/rera';
import { AcquisitionCase } from '../../types';
import { ACQUISITION_ZONES } from '../../data/mockReraData';
import { ReraPerformanceChart } from './ReraPerformanceChart';
import { 
  Building2, 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw, 
  FileText, 
  Search, 
  Filter, 
  MapPin, 
  ExternalLink, 
  Scale, 
  IndianRupee, 
  Clock, 
  Send, 
  Printer, 
  Check, 
  Layers, 
  Users, 
  Landmark, 
  Calendar, 
  ShieldCheck, 
  AlertCircle,
  Copy,
  ChevronDown,
  ChevronUp,
  FileCheck2,
  FileSpreadsheet,
  BarChart3,
  TrendingUp,
  Compass
} from 'lucide-react';
import { formatCurrencyINR, formatDate } from '../../lib/utils';

interface ReraIntegrationHubProps {
  caseRecord?: AcquisitionCase;
  initialSelectedParcelId?: string;
  onNavigateToCase?: (caseId: string) => void;
}

export const ReraIntegrationHub: React.FC<ReraIntegrationHubProps> = ({
  caseRecord,
  initialSelectedParcelId,
  onNavigateToCase
}) => {
  const { selectedCase, language, addToast, currentUser } = useApp();
  const c = caseRecord || selectedCase;

  const [records, setRecords] = useState<ReraParcelProjectRecord[]>([]);
  const [zoneData, setZoneData] = useState<ReraZoneAggregatedStatus[]>([]);
  const [selectedZoneFilter, setSelectedZoneFilter] = useState<string>('ALL');
  const [selectedPerformanceStatus, setSelectedPerformanceStatus] = useState<ReraPerformanceStatus | 'ALL'>('ALL');
  const [scopeMode, setScopeMode] = useState<'ALL_ZONES' | 'CASE_ONLY'>('ALL_ZONES');
  const [isChartVisible, setIsChartVisible] = useState<boolean>(true);

  const [selectedParcelFilter, setSelectedParcelFilter] = useState<string>(initialSelectedParcelId || 'ALL');
  const [conflictFilter, setConflictFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [lastSyncTime, setLastSyncTime] = useState<string>(new Date().toLocaleTimeString());
  
  // Selected project for detailed modal/action
  const [activeProjectForNotice, setActiveProjectForNotice] = useState<ReraParcelProjectRecord | null>(null);
  const [noticeType, setNoticeType] = useState<string>('Section 11(4) Prohibitory Notice against Unit Alienation');
  const [noticeRecipient, setNoticeRecipient] = useState<string>('');
  const [noticeSummary, setNoticeSummary] = useState<string>('');
  
  // Printable report modal
  const [showDossierModal, setShowDossierModal] = useState<boolean>(false);
  const [expandedProjectId, setExpandedProjectId] = useState<string | null>(null);
  const [activeDetailTab, setActiveDetailTab] = useState<'OVERVIEW' | 'FINANCIAL' | 'ALLOTTEES' | 'QPR_LITIGATION' | 'NOTICES'>('OVERVIEW');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    const loadRecords = () => {
      const allRecs = reraService.getAllRecords();
      const caseRecs = reraService.getRecordsByCase(c.id);
      setRecords(scopeMode === 'CASE_ONLY' ? caseRecs : allRecs);
      setZoneData(reraService.getAggregatedZoneStatus());
      if (caseRecs.length > 0 && !expandedProjectId) {
        setExpandedProjectId(caseRecs[0].id);
      }
    };

    loadRecords();
    const unsubscribe = reraService.subscribe(loadRecords);
    return () => unsubscribe();
  }, [c.id, scopeMode]);

  useEffect(() => {
    if (initialSelectedParcelId) {
      setSelectedParcelFilter(initialSelectedParcelId);
      const match = records.find(r => r.parcelId === initialSelectedParcelId);
      if (match) {
        setExpandedProjectId(match.id);
      }
    }
  }, [initialSelectedParcelId, records]);

  const handleLiveSync = async () => {
    setIsSyncing(true);
    try {
      await reraService.syncAllForCase(c.id);
      setLastSyncTime(new Date().toLocaleTimeString());
      addToast({
        type: 'success',
        message: 'MahaRERA Real-Time Gateway Sync Completed. 4 Cadastral parcels verified with digital SHA-256 stamp.',
        messageHi: 'रेरा रियल-टाइम गेटवे सिंक्रोनाइज़ेशन पूर्ण। डिजिटल हस्ताक्षर सहित भूखंड सत्यापित।',
      });
    } catch {
      addToast({
        type: 'error',
        message: 'Failed to establish handshake with State RERA API Gateway.',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDispatchNotice = () => {
    if (!activeProjectForNotice) return;
    try {
      const recipient = noticeRecipient || activeProjectForNotice.promoterName;
      const summary = noticeSummary || `Statutory injunction under Section 11(4) RFCTLARR Act restraining further sales or alienation on ${activeProjectForNotice.surveyNumber}.`;
      
      const notice = reraService.issueStatutoryNotice(
        activeProjectForNotice.id,
        noticeType,
        recipient,
        summary
      );

      addToast({
        type: 'success',
        message: `Official Notice ${notice.noticeId} dispatched via Speed Post (${notice.speedPostTracking}) and registered in immutable audit log.`,
        messageHi: `सांविधिक नोटिस ${notice.noticeId} स्पीड पोस्ट द्वारा प्रेषित किया गया।`,
      });

      setActiveProjectForNotice(null);
      setNoticeRecipient('');
      setNoticeSummary('');
    } catch {
      addToast({
        type: 'error',
        message: 'Could not record statutory notice dispatch.',
      });
    }
  };

  // Filter records
  const filteredRecords = records.filter(r => {
    if (selectedZoneFilter !== 'ALL' && r.acquisitionZoneId !== selectedZoneFilter) {
      return false;
    }
    if (selectedPerformanceStatus !== 'ALL' && r.performanceStatus !== selectedPerformanceStatus) {
      return false;
    }
    if (selectedParcelFilter !== 'ALL' && r.parcelId !== selectedParcelFilter) {
      return false;
    }
    if (conflictFilter !== 'ALL' && r.crossReference.conflictLevel !== conflictFilter) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = r.projectName.toLowerCase().includes(q);
      const matchPromoter = r.promoterName.toLowerCase().includes(q);
      const matchReg = r.reraRegistrationNo.toLowerCase().includes(q);
      const matchSurvey = r.surveyNumber.toLowerCase().includes(q);
      const matchZone = r.acquisitionZoneName?.toLowerCase().includes(q);
      if (!matchName && !matchPromoter && !matchReg && !matchSurvey && !matchZone) {
        return false;
      }
    }
    return true;
  });

  // KPI Calculations
  const totalParcelsWithRera = new Set(records.map(r => r.parcelId)).size;
  const criticalConflictsCount = records.filter(r => r.crossReference.conflictLevel === 'CRITICAL_BLOCKER').length;
  const sec11ViolationsCount = records.filter(r => r.crossReference.sec11_4_ViolationDetected).length;
  const totalAllotteesAffected = records.reduce((sum, r) => sum + r.allottees.allotteesCount, 0);
  const totalSolatiumExposure = records.reduce((sum, r) => sum + r.crossReference.allotteeSolatiumExposureINR, 0);
  const totalEscrowMonitored = records.reduce((sum, r) => sum + r.escrowAudit.designated70PctDepositBalance, 0);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner: GIGW S3WaaS Bar */}
      <div className="bg-white border border-slate-200 rounded-xs shadow-xs overflow-hidden">
        <div className="tiranga-strip" />
        
        <div className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 bg-[#f8fafc]">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 bg-[#0b3866] text-white font-mono text-[10px] font-bold tracking-wider uppercase rounded-xs">
                Real-Time Statutory Gateway
              </span>
              <span className="flex items-center gap-1 text-[11px] text-emerald-800 font-semibold bg-emerald-50 px-2 py-0.5 border border-emerald-200 rounded-xs">
                <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
                MahaRERA API Node v3.4 Active (SSL 1.3 Verified)
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                Sync: {lastSyncTime}
              </span>
            </div>
            
            <h2 className="text-lg sm:text-xl font-bold text-[#002642] flex items-center gap-2">
              <Building2 className="w-5 h-5 text-[#f37021]" />
              <span>RERA Real-Time Status &amp; Statutory Milestone Cross-Referencing</span>
            </h2>
            
            <p className="text-xs text-slate-600">
              Cross-referencing registered Real Estate Regulatory Authority projects against RFCTLARR Act 2013 acquisition stages, Section 11(4) alienation restrictions, and third-party allottee interests.
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={handleLiveSync}
              disabled={isSyncing}
              className="gov-button-classic text-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              title="Query State RERA API Gateway for fresh project telemetry"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
              <span>{isSyncing ? 'Syncing...' : 'Live Re-Sync Feeds'}</span>
            </button>

            <button
              onClick={() => setShowDossierModal(true)}
              className="gov-button-outline text-xs flex items-center gap-1.5 cursor-pointer bg-white"
            >
              <Printer className="w-3.5 h-3.5 text-[#0b3866]" />
              <span>Statutory Dossier</span>
            </button>
          </div>
        </div>

        {/* Real-Time Telemetry & KPI Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 divide-x divide-y sm:divide-y-0 divide-slate-200 bg-white">
          <div className="p-3.5 text-center">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Parcels Scanned</div>
            <div className="text-lg sm:text-xl font-bold text-[#002642] mt-0.5">
              {c.parcels.length} <span className="text-xs font-normal text-slate-500">Parcels</span>
            </div>
            <div className="text-[10px] text-blue-800 font-medium mt-0.5">
              {totalParcelsWithRera} Overlapping RERA
            </div>
          </div>

          <div className="p-3.5 text-center bg-red-50/50">
            <div className="text-[11px] font-semibold text-red-900 uppercase tracking-wider">Sec 11(4) Violations</div>
            <div className="text-lg sm:text-xl font-bold text-red-700 mt-0.5">
              {sec11ViolationsCount} <span className="text-xs font-normal text-red-600">Flagged</span>
            </div>
            <div className="text-[10px] text-red-700 font-medium mt-0.5">
              Post-Gazette Sales
            </div>
          </div>

          <div className="p-3.5 text-center bg-amber-50/50">
            <div className="text-[11px] font-semibold text-amber-900 uppercase tracking-wider">Critical Conflicts</div>
            <div className="text-lg sm:text-xl font-bold text-amber-700 mt-0.5">
              {criticalConflictsCount}
            </div>
            <div className="text-[10px] text-amber-800 font-medium mt-0.5">
              Vesting / Handover Clashes
            </div>
          </div>

          <div className="p-3.5 text-center">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Allottees Bound</div>
            <div className="text-lg sm:text-xl font-bold text-[#002642] mt-0.5">
              {totalAllotteesAffected} <span className="text-xs font-normal text-slate-500">Buyers</span>
            </div>
            <div className="text-[10px] text-slate-500 font-medium mt-0.5">
              Across Active Projects
            </div>
          </div>

          <div className="p-3.5 text-center">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Solatium Exposure</div>
            <div className="text-lg sm:text-xl font-bold text-[#f37021] mt-0.5">
              {formatCurrencyINR(totalSolatiumExposure)}
            </div>
            <div className="text-[10px] text-slate-500 font-medium mt-0.5">
              Sec 31/Solatium Risk
            </div>
          </div>

          <div className="p-3.5 text-center bg-emerald-50/30">
            <div className="text-[11px] font-semibold text-emerald-900 uppercase tracking-wider">Escrow Monitored</div>
            <div className="text-lg sm:text-xl font-bold text-emerald-800 mt-0.5">
              {formatCurrencyINR(totalEscrowMonitored)}
            </div>
            <div className="text-[10px] text-emerald-700 font-medium mt-0.5">
              70% Mandated Escrow
            </div>
          </div>
        </div>
      </div>

      {/* Case Stage Synchronization Callout */}
      <div className="bg-[#0b3866] text-white p-4 rounded-xs border-l-4 border-[#f37021] shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Scale className="w-5 h-5 text-[#f37021] flex-shrink-0" />
          <div className="text-xs">
            <span className="font-bold tracking-wide uppercase text-amber-300">
              Active Statutory Case Milestone:
            </span>{' '}
            <span className="font-semibold underline decoration-[#f37021]">
              {c.stage.replace('STAGE_', 'Stage ')} ({c.caseReference})
            </span>
            <span className="mx-2">•</span>
            <span>Statutory Target Date: <strong>{formatDate(c.stageDeadline)}</strong></span>
            <span className="mx-2">•</span>
            <span>Village: <strong>{c.village} ({c.tehsil}, {c.district})</strong></span>
          </div>
        </div>

        <div className="text-xs flex items-center gap-2">
          <span className="text-blue-200">Total Project Sanction:</span>
          <span className="font-mono font-bold text-white">{formatCurrencyINR(c.sanctionedBudget)}</span>
        </div>
      </div>

      {/* RERA Project Performance Visualization Bar Chart Component */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-[#0b3866]" />
            <span className="text-xs font-bold text-[#002642] uppercase tracking-wider">
              Land Acquisition Corridor Performance Analysis
            </span>
            <span className="text-[10px] bg-slate-200 font-mono font-semibold text-slate-700 px-1.5 py-0.2 rounded-2xs">
              MahaRERA Live Registry
            </span>
          </div>

          <button
            onClick={() => setIsChartVisible(!isChartVisible)}
            className="text-xs text-[#0b3866] hover:text-[#082d52] font-semibold flex items-center gap-1 cursor-pointer"
          >
            <span>{isChartVisible ? 'Hide Performance Chart' : 'Show Performance Chart'}</span>
            {isChartVisible ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {isChartVisible && (
          <ReraPerformanceChart
            zoneData={zoneData}
            selectedZoneId={selectedZoneFilter === 'ALL' ? undefined : selectedZoneFilter}
            onSelectZone={(zoneId) => setSelectedZoneFilter(zoneId || 'ALL')}
            selectedStatus={selectedPerformanceStatus}
            onSelectStatus={(st) => setSelectedPerformanceStatus(st)}
          />
        )}
      </div>

      {/* Search & Filter Toolbar */}
      <div className="bg-white border border-slate-200 rounded-xs p-3.5 shadow-xs space-y-3">
        {/* Row 1: Scope toggle & quick count */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1">
              <Compass className="w-3.5 h-3.5 text-[#0b3866]" />
              Surveillance Scope:
            </span>
            <div className="flex items-center bg-slate-100 p-0.5 rounded-xs border border-slate-200 text-xs">
              <button
                onClick={() => {
                  setScopeMode('ALL_ZONES');
                  setSelectedParcelFilter('ALL');
                }}
                className={`px-3 py-1 font-semibold rounded-xs transition-colors cursor-pointer ${
                  scopeMode === 'ALL_ZONES'
                    ? 'bg-[#0b3866] text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                All Corridors ({reraService.getAllRecords().length} Schemes)
              </button>
              <button
                onClick={() => setScopeMode('CASE_ONLY')}
                className={`px-3 py-1 font-semibold rounded-xs transition-colors cursor-pointer ${
                  scopeMode === 'CASE_ONLY'
                    ? 'bg-[#0b3866] text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                This Case Only ({reraService.getRecordsByCase(c.id).length} Overlapping)
              </button>
            </div>
          </div>

          <div className="text-xs text-slate-500 font-medium">
            Showing <strong>{filteredRecords.length}</strong> of {records.length} projects matching active filters
          </div>
        </div>

        {/* Row 2: Filter Dropdowns */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[280px]">
            {/* Zone Filter Dropdown */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="font-bold text-slate-600">Zone:</span>
              <select
                value={selectedZoneFilter}
                onChange={(e) => setSelectedZoneFilter(e.target.value)}
                className="bg-slate-50 border border-slate-300 text-xs font-semibold px-2.5 py-1.5 rounded-xs text-[#0b3866] focus:outline-none focus:ring-1 focus:ring-[#0b3866]"
              >
                <option value="ALL">All Acquisition Zones</option>
                {ACQUISITION_ZONES.map(z => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Performance Status Dropdown */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="font-bold text-slate-600">Status:</span>
              <select
                value={selectedPerformanceStatus}
                onChange={(e) => setSelectedPerformanceStatus(e.target.value as any)}
                className="bg-slate-50 border border-slate-300 text-xs font-semibold px-2.5 py-1.5 rounded-xs text-[#0b3866] focus:outline-none focus:ring-1 focus:ring-[#0b3866]"
              >
                <option value="ALL">All Performance Statuses</option>
                <option value="ON_TRACK">On-Track Progress</option>
                <option value="DELAYED">Delayed Handover</option>
                <option value="COMPLETED">Completed / OC</option>
                <option value="LAPSED_DEFAULT">Lapsed / Default</option>
              </select>
            </div>

            {/* Parcel Filter Dropdown (in Case mode) */}
            {scopeMode === 'CASE_ONLY' && (
              <div className="flex items-center gap-1.5 text-xs">
                <span className="font-bold text-slate-600">Parcel:</span>
                <select
                  value={selectedParcelFilter}
                  onChange={(e) => setSelectedParcelFilter(e.target.value)}
                  className="bg-slate-50 border border-slate-300 text-xs font-semibold px-2.5 py-1.5 rounded-xs text-[#0b3866] focus:outline-none focus:ring-1 focus:ring-[#0b3866]"
                >
                  <option value="ALL">All Case Parcels ({c.parcels.length})</option>
                  {c.parcels.map(p => {
                    const hasRera = records.some(r => r.parcelId === p.id);
                    return (
                      <option key={p.id} value={p.id}>
                        {p.surveyNumber} ({p.extent} {p.extentUnit}) {hasRera ? '• RERA Registered' : '• Clear'}
                      </option>
                    );
                  })}
                </select>
              </div>
            )}

            {/* Conflict Severity Filter */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="font-bold text-slate-600">Severity:</span>
              <select
                value={conflictFilter}
                onChange={(e) => setConflictFilter(e.target.value)}
                className="bg-slate-50 border border-slate-300 text-xs font-semibold px-2.5 py-1.5 rounded-xs text-[#0b3866] focus:outline-none focus:ring-1 focus:ring-[#0b3866]"
              >
                <option value="ALL">All Conflict Levels</option>
                <option value="CRITICAL_BLOCKER">Critical Blocker (Sec 11(4))</option>
                <option value="HIGH_RISK">High Risk (Litigation / Valuation)</option>
                <option value="MODERATE_WARNING">Moderate Warning (Boundary)</option>
                <option value="COMPLIANT_CLEAR">Compliant Clear</option>
              </select>
            </div>

            {/* Reset Filters button if any active */}
            {(selectedZoneFilter !== 'ALL' || selectedPerformanceStatus !== 'ALL' || conflictFilter !== 'ALL' || selectedParcelFilter !== 'ALL' || searchQuery.trim()) && (
              <button
                onClick={() => {
                  setSelectedZoneFilter('ALL');
                  setSelectedPerformanceStatus('ALL');
                  setConflictFilter('ALL');
                  setSelectedParcelFilter('ALL');
                  setSearchQuery('');
                }}
                className="text-xs text-red-700 hover:text-red-900 font-semibold underline px-1 cursor-pointer"
              >
                Reset Filters
              </button>
            )}
          </div>

          {/* Free Text Search */}
          <div className="relative min-w-[240px]">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search RERA Reg No, Project, Promoter..."
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-xs focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#0b3866]"
            />
          </div>
        </div>
      </div>

      {/* Main Records List & Dossier Cards */}
      {filteredRecords.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xs p-8 text-center space-y-3">
          <Building2 className="w-10 h-10 text-slate-400 mx-auto" />
          <h3 className="text-sm font-bold text-slate-700">No RERA Projects Found Matching Selected Criteria</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            The queried land parcels do not contain any overlapping real-estate schemes registered under the Real Estate Regulatory Authority, or active filters have excluded them.
          </p>
          <button
            onClick={() => {
              setSelectedParcelFilter('ALL');
              setConflictFilter('ALL');
              setSearchQuery('');
            }}
            className="gov-button-outline text-xs px-3 py-1.5"
          >
            Reset All Filters
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredRecords.map((r) => {
            const isExpanded = expandedProjectId === r.id;
            const conflict = r.crossReference;

            const conflictBadgeClass = 
              conflict.conflictLevel === 'CRITICAL_BLOCKER' 
                ? 'bg-red-100 text-red-900 border-red-300' 
                : conflict.conflictLevel === 'HIGH_RISK'
                ? 'bg-amber-100 text-amber-900 border-amber-300'
                : conflict.conflictLevel === 'MODERATE_WARNING'
                ? 'bg-blue-100 text-blue-900 border-blue-300'
                : 'bg-emerald-100 text-emerald-900 border-emerald-300';

            return (
              <div 
                key={r.id} 
                className="bg-white border border-slate-200 rounded-xs shadow-xs overflow-hidden transition-all"
              >
                {/* Card Header Strip */}
                <div className={`p-4 border-b ${
                  conflict.conflictLevel === 'CRITICAL_BLOCKER' ? 'bg-red-50/40 border-red-200' : 'bg-slate-50/70 border-slate-200'
                }`}>
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        {/* RERA Registration Tag */}
                        <div className="flex items-center bg-white border border-slate-300 rounded-xs px-2 py-0.5 text-xs font-mono font-bold text-[#0b3866]">
                          <span>{r.reraRegistrationNo}</span>
                          <button
                            onClick={() => handleCopy(r.reraRegistrationNo, r.id)}
                            className="ml-1.5 text-slate-400 hover:text-slate-700"
                            title="Copy RERA ID"
                          >
                            {copiedId === r.id ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                          </button>
                        </div>

                        {/* State RERA Portal */}
                        <span className="text-[11px] font-semibold text-slate-600 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-xs">
                          {r.stateReraPortal}
                        </span>

                        {/* Acquisition Zone Tag */}
                        <span className="text-[11px] font-semibold text-slate-700 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-xs flex items-center gap-1">
                          <Compass className="w-3 h-3 text-[#0b3866]" />
                          <span>{r.acquisitionZoneName}</span>
                        </span>

                        {/* Performance Status Badge */}
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-xs border uppercase tracking-wider flex items-center gap-1 ${
                          r.performanceStatus === 'ON_TRACK' ? 'bg-emerald-50 text-emerald-800 border-emerald-300' :
                          r.performanceStatus === 'DELAYED' ? 'bg-amber-50 text-amber-900 border-amber-300' :
                          r.performanceStatus === 'COMPLETED' ? 'bg-blue-50 text-blue-900 border-blue-300' :
                          'bg-red-50 text-red-900 border-red-300'
                        }`}>
                          {r.performanceStatus === 'ON_TRACK' && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                          {r.performanceStatus === 'DELAYED' && <Clock className="w-3 h-3 text-amber-600" />}
                          {r.performanceStatus === 'COMPLETED' && <Building2 className="w-3 h-3 text-[#0b3866]" />}
                          {r.performanceStatus === 'LAPSED_DEFAULT' && <ShieldAlert className="w-3 h-3 text-red-600" />}
                          <span>{r.performanceStatus.replace('_', ' ')}</span>
                          {r.delayMonths && r.delayMonths > 0 ? (
                            <span className="font-mono text-[9px] bg-amber-200/80 px-1 py-0.2 rounded-2xs font-bold text-amber-950">
                              +{r.delayMonths} mo delay
                            </span>
                          ) : null}
                        </span>

                        {/* Project Type */}
                        <span className="text-[11px] font-medium text-slate-600">
                          {r.projectType}
                        </span>

                        {/* Conflict Badge */}
                        <span className={`text-[10px] font-bold px-2 py-0.5 border rounded-xs uppercase tracking-wider flex items-center gap-1 ${conflictBadgeClass}`}>
                          {conflict.conflictLevel === 'CRITICAL_BLOCKER' && <ShieldAlert className="w-3 h-3 text-red-600" />}
                          {conflict.conflictLevel === 'HIGH_RISK' && <AlertTriangle className="w-3 h-3 text-amber-600" />}
                          {conflict.conflictLevel === 'MODERATE_WARNING' && <Clock className="w-3 h-3 text-blue-600" />}
                          {conflict.conflictLevel.replace('_', ' ')}
                        </span>

                        {/* Sec 11(4) Violation Tag */}
                        {conflict.sec11_4_ViolationDetected && (
                          <span className="text-[10px] font-bold px-2 py-0.5 bg-red-700 text-white rounded-xs animate-pulse">
                            ⚠️ SEC 11(4) ALIENATION BREACH
                          </span>
                        )}
                      </div>

                      <h3 className="text-base sm:text-lg font-bold text-[#002642]">
                        {r.projectName}
                      </h3>

                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600">
                        <span><strong>Promoter:</strong> {r.promoterName} ({r.promoterType})</span>
                        <span>•</span>
                        <span><strong>Land Parcel:</strong> <span className="font-mono font-bold text-[#0b3866]">{r.surveyNumber}</span></span>
                        <span>•</span>
                        <span><strong>Cadastral Overlap:</strong> <span className="font-bold text-[#f37021]">{r.overlappingAreaWithParcelHa} Ha ({r.overlapPercentage}%)</span></span>
                        <span>•</span>
                        <span><strong>Physical Progress:</strong> <span className="font-mono font-bold text-emerald-800">{r.physicalProgressPct}%</span></span>
                      </div>
                    </div>

                    {/* Quick Action Trigger */}
                    <div className="flex items-center gap-2 self-start lg:self-center">
                      <button
                        onClick={() => {
                          setActiveProjectForNotice(r);
                          setNoticeRecipient(r.promoterName);
                          setNoticeSummary(`Prohibitory order under Section 11(4) RFCTLARR Act restraining further sale, agreement or mortgage on ${r.surveyNumber}.`);
                        }}
                        className="gov-button-saffron text-xs py-1.5 px-3 flex items-center gap-1 cursor-pointer"
                      >
                        <Send className="w-3 h-3" />
                        <span>Issue Statutory Notice</span>
                      </button>

                      <button
                        onClick={() => setExpandedProjectId(isExpanded ? null : r.id)}
                        className="p-1.5 bg-white border border-slate-300 rounded-xs hover:bg-slate-100 text-[#0b3866] transition-colors"
                        title={isExpanded ? 'Collapse report' : 'Expand full dossier'}
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Statutory Milestone Cross-Reference Alert Box */}
                <div className="p-4 border-b border-slate-200 bg-slate-50/50">
                  <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 pb-3 border-b border-slate-200">
                    <div>
                      <div className="flex items-center gap-2">
                        <Scale className="w-4 h-4 text-[#0b3866]" />
                        <h4 className="text-xs font-bold text-[#002642] uppercase tracking-wider">
                          Acquisition Milestone Cross-Reference Analysis
                        </h4>
                      </div>
                      <p className="text-xs font-semibold text-slate-800 mt-0.5">
                        {conflict.conflictTitle}
                      </p>
                    </div>

                    <div className="flex items-center gap-4 text-xs font-medium">
                      <div className="text-right">
                        <div className="text-[10px] text-slate-500 uppercase">Statutory Risk Score</div>
                        <div className="font-mono font-bold text-red-700 text-sm">
                          {conflict.statutoryRiskScore} / 100
                        </div>
                      </div>
                      <div className="text-right border-l pl-4 border-slate-300">
                        <div className="text-[10px] text-slate-500 uppercase">Allottee Solatium Risk</div>
                        <div className="font-mono font-bold text-[#0b3866] text-sm">
                          {formatCurrencyINR(conflict.allotteeSolatiumExposureINR)}
                        </div>
                      </div>
                    </div>
                  </div>

                  <p className="text-xs text-slate-700 leading-relaxed mt-3 bg-white p-3 border border-slate-200 rounded-xs">
                    {conflict.conflictDetails}
                  </p>

                  {/* Section 11(4) Violation Callout if present */}
                  {conflict.sec11_4_ViolationDetected && (
                    <div className="mt-3 p-3 bg-red-50 border border-red-300 rounded-xs text-xs text-red-900 flex items-start gap-2.5">
                      <AlertCircle className="w-4 h-4 text-red-700 flex-shrink-0 mt-0.5" />
                      <div>
                        <strong>Section 11(4) RFCTLARR Violation Confirmed:</strong> {conflict.sec11_4_Details}
                        <div className="mt-1 text-[11px] text-red-800">
                          Legal Remedy: All transactions executed subsequent to Gazette Notification (2026-07-15) are statutorily null and void ab initio against CALA.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Recommended Statutory Actions */}
                  <div className="mt-3 space-y-2">
                    <div className="text-[11px] font-bold uppercase text-slate-600 tracking-wider">
                      Prescribed CALA Statutory Interventions:
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {conflict.recommendedActions.map(act => (
                        <div 
                          key={act.id} 
                          className="p-2.5 bg-white border border-slate-200 rounded-xs text-xs space-y-1 hover:border-[#0b3866] transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-[#0b3866]">{act.label}</span>
                            <span className={`px-1.5 py-0.2 text-[9px] font-bold rounded-xs ${
                              act.urgency === 'IMMEDIATE' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
                            }`}>
                              {act.urgency}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-600">{act.statutoryRemedy}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Collapsible Details Drawer */}
                {isExpanded && (
                  <div className="p-4 space-y-4">
                    {/* Navigation tabs inside the dossier */}
                    <div className="flex overflow-x-auto border-b border-slate-200 gap-1 pb-1">
                      {[
                        { id: 'OVERVIEW', label: 'Cadastral & Overlap', icon: Layers },
                        { id: 'FINANCIAL', label: '70% Escrow & Bank Charges', icon: Landmark },
                        { id: 'ALLOTTEES', label: 'Allottees & Handover', icon: Users },
                        { id: 'QPR_LITIGATION', label: 'QPR & Litigations', icon: Scale },
                        { id: 'NOTICES', label: `Served Notices (${r.officialNoticesServed?.length || 0})`, icon: FileCheck2 },
                      ].map(tab => {
                        const Icon = tab.icon;
                        const isActive = activeDetailTab === tab.id;
                        return (
                          <button
                            key={tab.id}
                            onClick={() => setActiveDetailTab(tab.id as any)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-t-xs whitespace-nowrap transition-colors ${
                              isActive 
                                ? 'bg-[#0b3866] text-white' 
                                : 'text-slate-600 hover:bg-slate-100 hover:text-[#0b3866]'
                            }`}
                          >
                            <Icon className="w-3.5 h-3.5" />
                            <span>{tab.label}</span>
                          </button>
                        );
                      })}
                    </div>

                    {/* Tab 1: Cadastral & Overlap */}
                    {activeDetailTab === 'OVERVIEW' && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs space-y-2">
                          <h5 className="font-bold text-[#0b3866] uppercase text-[11px]">RERA Project Approval Data</h5>
                          <div className="divide-y divide-slate-200">
                            <div className="py-1.5 flex justify-between">
                              <span className="text-slate-500">Sanctioning Authority:</span>
                              <span className="font-semibold text-slate-800">{r.sanctioningAuthority}</span>
                            </div>
                            <div className="py-1.5 flex justify-between">
                              <span className="text-slate-500">Sanction Order No:</span>
                              <span className="font-mono font-semibold text-slate-800">{r.sanctionOrderNo}</span>
                            </div>
                            <div className="py-1.5 flex justify-between">
                              <span className="text-slate-500">Sanction Approval Date:</span>
                              <span className="font-semibold text-slate-800">{formatDate(r.sanctionDate)}</span>
                            </div>
                            <div className="py-1.5 flex justify-between">
                              <span className="text-slate-500">RERA Registration Validity:</span>
                              <span className="font-semibold text-slate-800">{formatDate(r.registrationDate)} to {formatDate(r.revisedCompletionDate)}</span>
                            </div>
                            <div className="py-1.5 flex justify-between">
                              <span className="text-slate-500">Promoter Office Address:</span>
                              <span className="font-medium text-slate-700 text-right max-w-[240px]">{r.promoterAddress}</span>
                            </div>
                          </div>
                        </div>

                        <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs space-y-2">
                          <h5 className="font-bold text-[#0b3866] uppercase text-[11px]">Spatial Overlap Quantification</h5>
                          <div className="space-y-2">
                            <div>
                              <div className="flex justify-between text-xs mb-1">
                                <span className="text-slate-600">Acquisition Overlap Ratio:</span>
                                <span className="font-bold text-[#0b3866]">{r.overlapPercentage}% ({r.overlappingAreaWithParcelHa} Ha / {r.totalProjectAreaHa} Ha total)</span>
                              </div>
                              <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden">
                                <div 
                                  className="bg-[#f37021] h-full"
                                  style={{ width: `${r.overlapPercentage}%` }}
                                />
                              </div>
                            </div>

                            <div className="pt-2 border-t border-slate-200">
                              <div className="text-[11px] font-semibold text-slate-600">Notified Cadastral Survey Numbers:</div>
                              <ul className="list-disc list-inside mt-1 text-slate-700 space-y-0.5 font-mono text-[11px]">
                                {r.cadastralSurveyNumbersListed.map((s, idx) => (
                                  <li key={idx}>{s}</li>
                                ))}
                              </ul>
                            </div>

                            <div className="pt-2 border-t border-slate-200 flex justify-between items-center text-[11px]">
                              <span className="text-slate-500">SHA-256 Digital Certificate:</span>
                              <span className="font-mono text-slate-600 truncate max-w-[180px]" title={r.certDigestSha256}>
                                {r.certDigestSha256.slice(0, 16)}...
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Tab 2: Financial & Escrow */}
                    {activeDetailTab === 'FINANCIAL' && (
                      <div className="space-y-3 text-xs">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs">
                            <div className="text-slate-500 text-[11px]">Designated 70% Escrow Account</div>
                            <div className="font-mono font-bold text-base text-[#0b3866] mt-1">
                              {formatCurrencyINR(r.escrowAudit.designated70PctDepositBalance)}
                            </div>
                            <div className="text-[10px] text-slate-500 mt-1">
                              {r.escrowAudit.bankName} ({r.escrowAudit.accountMasked})
                            </div>
                          </div>

                          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs">
                            <div className="text-slate-500 text-[11px]">Total Estimated Project Cost</div>
                            <div className="font-mono font-bold text-base text-slate-800 mt-1">
                              {formatCurrencyINR(r.escrowAudit.totalEstimatedProjectCost)}
                            </div>
                            <div className="text-[10px] text-slate-500 mt-1">
                              Incurred: {formatCurrencyINR(r.escrowAudit.actualIncurredExpense)}
                            </div>
                          </div>

                          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs">
                            <div className="text-slate-500 text-[11px]">Registered Mortgage / Bank Charge</div>
                            <div className="font-mono font-bold text-base text-red-700 mt-1">
                              {r.escrowAudit.mortgageChargeAmountINR ? formatCurrencyINR(r.escrowAudit.mortgageChargeAmountINR) : 'Nil Registered'}
                            </div>
                            <div className="text-[10px] text-slate-500 mt-1">
                              Charge Holder: {r.escrowAudit.registeredMortgageBank || 'None'}
                            </div>
                          </div>
                        </div>

                        <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-xs text-[11px] text-blue-900 flex items-start gap-2">
                          <ShieldCheck className="w-4 h-4 text-[#0b3866] flex-shrink-0 mt-0.5" />
                          <div>
                            <strong>Statutory Escrow Pre-Vesting Directive:</strong> Under Section 11(4) of the RFCTLARR Act 2013, the CALA is empowered to direct the Escrow Bank ({r.escrowAudit.bankName}) to freeze releases pertaining to overlapping land until final Section 23 Award determination.
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Tab 3: Allottees & Handover */}
                    {activeDetailTab === 'ALLOTTEES' && (
                      <div className="space-y-3 text-xs">
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs text-center">
                            <div className="text-slate-500 text-[10px] uppercase">Sanctioned Units</div>
                            <div className="font-bold text-base text-slate-800">{r.allottees.totalUnitsSanctioned}</div>
                          </div>
                          <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs text-center">
                            <div className="text-slate-500 text-[10px] uppercase">Units Booked / Sold</div>
                            <div className="font-bold text-base text-[#0b3866]">{r.allottees.unitsBooked}</div>
                          </div>
                          <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs text-center">
                            <div className="text-slate-500 text-[10px] uppercase">Agreements for Sale</div>
                            <div className="font-bold text-base text-emerald-800">{r.allottees.registeredAgreementsForSale}</div>
                          </div>
                          <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs text-center">
                            <div className="text-slate-500 text-[10px] uppercase">Committed Possession</div>
                            <div className="font-bold text-xs text-red-700 mt-1">{formatDate(r.allottees.committedHandoverDate)}</div>
                          </div>
                        </div>

                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-xs text-[11px] text-amber-900 space-y-1">
                          <div className="font-bold">Third-Party Consumer Protection Clashing:</div>
                          <p>
                            Promoter has collected <strong>{formatCurrencyINR(r.allottees.totalFundsCollectedINR)}</strong> from {r.allottees.allotteesCount} allottees with promised possession by {formatDate(r.allottees.committedHandoverDate)}. If land vests in the State under Section 19/38 prior to building completion, allottees become eligible to seek statutory intervention under RFCTLARR Section 31 (Resettlement &amp; Rehabilitation) or lodge claims before the Land Acquisition Authority.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Tab 4: QPR & Litigations */}
                    {activeDetailTab === 'QPR_LITIGATION' && (
                      <div className="space-y-4 text-xs">
                        {/* Quarterly Reports */}
                        <div>
                          <h6 className="font-bold text-slate-800 mb-2 uppercase text-[11px]">Quarterly Progress Reports (QPR) Audit</h6>
                          <div className="overflow-x-auto">
                            <table className="gov-table">
                              <thead>
                                <tr>
                                  <th>Quarter</th>
                                  <th>Filing Date</th>
                                  <th>Civil Work %</th>
                                  <th>Services %</th>
                                  <th>Engineer / CA Compliance Note</th>
                                </tr>
                              </thead>
                              <tbody>
                                {r.quarterlyReports.map((qpr, idx) => (
                                  <tr key={idx}>
                                    <td className="font-bold text-[#0b3866]">{qpr.quarter}</td>
                                    <td>{formatDate(qpr.filedOn)}</td>
                                    <td className="font-mono font-bold text-emerald-800">{qpr.civilWorkPct}%</td>
                                    <td className="font-mono">{qpr.servicesPct}%</td>
                                    <td className="text-slate-600">{qpr.complianceNote}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>

                        {/* Litigations */}
                        <div>
                          <h6 className="font-bold text-slate-800 mb-2 uppercase text-[11px]">RERA Tribunal &amp; Court Litigations</h6>
                          {r.litigations.length === 0 ? (
                            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs text-slate-500 text-xs">
                              No active complaints or tribunal stay orders registered against this project.
                            </div>
                          ) : (
                            <div className="space-y-2">
                              {r.litigations.map((lit, idx) => (
                                <div key={idx} className="p-3 bg-red-50/50 border border-red-200 rounded-xs space-y-1">
                                  <div className="flex justify-between items-center">
                                    <span className="font-bold text-red-900">{lit.caseNo} — {lit.forum}</span>
                                    <span className="px-1.5 py-0.2 bg-red-100 text-red-800 font-bold text-[10px] rounded-xs">
                                      {lit.interimStayActive ? 'ACTIVE STAY ORDER' : lit.status}
                                    </span>
                                  </div>
                                  <div className="text-slate-700"><strong>Complainant:</strong> {lit.complainant}</div>
                                  <div className="text-slate-600"><strong>Subject:</strong> {lit.subject}</div>
                                  {lit.orderSummary && (
                                    <div className="text-slate-800 text-[11px] bg-white p-2 rounded-xs border border-red-100 mt-1">
                                      <strong>Tribunal Order:</strong> {lit.orderSummary}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Tab 5: Served Notices */}
                    {activeDetailTab === 'NOTICES' && (
                      <div className="space-y-3 text-xs">
                        <div className="flex justify-between items-center">
                          <h6 className="font-bold text-slate-800 uppercase text-[11px]">Official Statutory Notices Dispatched</h6>
                          <button
                            onClick={() => {
                              setActiveProjectForNotice(r);
                              setNoticeRecipient(r.promoterName);
                            }}
                            className="gov-button-saffron text-[11px] py-1 px-2.5 flex items-center gap-1 cursor-pointer"
                          >
                            <Send className="w-3 h-3" />
                            <span>Issue New Notice</span>
                          </button>
                        </div>

                        {!r.officialNoticesServed || r.officialNoticesServed.length === 0 ? (
                          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xs text-center text-slate-500">
                            No official notices served yet for this project.
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {r.officialNoticesServed.map(not => (
                              <div key={not.noticeId} className="p-3 bg-white border border-slate-200 rounded-xs space-y-1">
                                <div className="flex justify-between items-center">
                                  <span className="font-bold text-[#0b3866]">{not.noticeId} • {not.type}</span>
                                  <span className="px-1.5 py-0.2 bg-emerald-100 text-emerald-800 font-bold text-[10px] rounded-xs">
                                    {not.status}
                                  </span>
                                </div>
                                <div className="text-slate-600">Recipient: <strong>{not.recipient}</strong> • Issued: {formatDate(not.issuedOn)}</div>
                                <div className="text-slate-700">{not.summary}</div>
                                {not.speedPostTracking && (
                                  <div className="text-[11px] font-mono text-blue-800">
                                    Speed Post Consignment: <strong>{not.speedPostTracking}</strong> (Department of Posts Electronic Booking)
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Issue Statutory Notice */}
      {activeProjectForNotice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-2xs animate-in fade-in">
          <div className="bg-white border border-slate-300 max-w-xl w-full shadow-2xl rounded-xs overflow-hidden">
            <div className="bg-[#002642] text-white p-4 flex justify-between items-center border-b-2 border-[#f37021]">
              <div className="flex items-center gap-2">
                <Scale className="w-4 h-4 text-[#f37021]" />
                <span className="font-bold text-sm">Issue Statutory Land Acquisition Notice</span>
              </div>
              <button
                onClick={() => setActiveProjectForNotice(null)}
                className="px-2 py-0.5 bg-white/10 hover:bg-white/20 text-white font-bold text-xs rounded-xs"
              >
                ✕ Close
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xs text-amber-900">
                <strong>Project:</strong> {activeProjectForNotice.projectName} ({activeProjectForNotice.reraRegistrationNo})
                <br />
                <strong>Parcel:</strong> {activeProjectForNotice.surveyNumber} ({activeProjectForNotice.caseReference})
              </div>

              <div className="space-y-1">
                <label className="font-bold text-slate-700">Notice Statutory Provision:</label>
                <select
                  value={noticeType}
                  onChange={(e) => setNoticeType(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 p-2 rounded-xs font-semibold text-[#0b3866]"
                >
                  <option value="Section 11(4) Prohibitory Notice against Unit Alienation">Section 11(4) Prohibition against Unit Sale / Encumbrance</option>
                  <option value="Section 21 Individual Notice to Promoter & Allottee Body">Section 21 Notice to Appear & Submit Claims</option>
                  <option value="Section 11(4) Directive to Escrow Bank">Directive to RERA Escrow Bank to Freeze Overlapping Deposits</option>
                  <option value="Summons for Joint Cadastral Inspection (DILR & RERA)">Summons for Joint Cadastral Boundary Delineation</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-bold text-slate-700">Notice Recipient:</label>
                <input
                  type="text"
                  value={noticeRecipient || activeProjectForNotice.promoterName}
                  onChange={(e) => setNoticeRecipient(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 p-2 rounded-xs"
                  placeholder="Promoter / Bank Manager Name"
                />
              </div>

              <div className="space-y-1">
                <label className="font-bold text-slate-700">Statutory Grounds &amp; Requisition Details:</label>
                <textarea
                  rows={4}
                  value={noticeSummary}
                  onChange={(e) => setNoticeSummary(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 p-2 rounded-xs text-slate-800"
                  placeholder="Specify statutory provisions, survey boundaries, and consequence of default under RFCTLARR Act 2013..."
                />
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs text-[11px] text-slate-600">
                Notice will be digitally dispatched under the authority of <strong>{currentUser.name} ({currentUser.designation})</strong>, registered with postal barcode, and logged in the immutable audit registry.
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  onClick={() => setActiveProjectForNotice(null)}
                  className="gov-button-outline py-1.5 px-3 text-xs"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDispatchNotice}
                  className="gov-button-classic py-1.5 px-4 text-xs flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Dispatch Statutory Notice</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Official Statutory Cross-Reference Report (Dossier) */}
      {showDossierModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-2xs animate-in fade-in overflow-y-auto">
          <div className="bg-white border border-slate-400 max-w-4xl w-full shadow-2xl rounded-xs overflow-hidden my-6">
            <div className="bg-[#002642] text-white p-4 flex justify-between items-center border-b-2 border-[#f37021]">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#f37021]" />
                <span className="font-bold text-sm">OFFICIAL STATUTORY RERA-RFCTLARR CROSS-REFERENCE DOSSIER</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="px-2.5 py-1 bg-white/20 hover:bg-white/30 text-white font-bold text-xs rounded-xs flex items-center gap-1 cursor-pointer"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print Dossier</span>
                </button>
                <button
                  onClick={() => setShowDossierModal(false)}
                  className="px-2 py-0.5 bg-white/10 hover:bg-white/20 text-white font-bold text-xs rounded-xs cursor-pointer"
                >
                  ✕ Close
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6 text-xs text-slate-800 font-sans print:p-0">
              {/* Government Header Stamp */}
              <div className="text-center border-b-2 border-[#0b3866] pb-4 space-y-1">
                <div className="font-bold text-xs tracking-widest text-[#0b3866] uppercase">
                  GOVERNMENT OF MAHARASHTRA • REVENUE &amp; FOREST DEPARTMENT
                </div>
                <div className="font-extrabold text-sm text-[#002642]">
                  OFFICE OF THE COMPETENT AUTHORITY FOR LAND ACQUISITION (CALA)
                </div>
                <div className="text-[11px] text-slate-600">
                  Cadastral Cross-Referencing &amp; Statutory Due Diligence Report u/s 11(4) &amp; 15 RFCTLARR Act 2013 read with RERA Act 2016
                </div>
              </div>

              {/* Case Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-50 p-3 border border-slate-200">
                <div>
                  <span className="text-slate-500 text-[10px]">CASE REFERENCE:</span>
                  <div className="font-mono font-bold text-[#0b3866]">{c.caseReference}</div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px]">PROJECT / CORRIDOR:</span>
                  <div className="font-bold">{c.projectName}</div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px]">VILLAGE &amp; TALUKA:</span>
                  <div>{c.village}, {c.tehsil}, {c.district}</div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px]">CURRENT STAGE:</span>
                  <div className="font-bold text-[#f37021]">{c.stage}</div>
                </div>
              </div>

              {/* Section 11(4) Legal Certificate Box */}
              <div className="p-3.5 bg-red-50/70 border border-red-300 rounded-xs space-y-1">
                <div className="font-bold text-red-900 uppercase text-[11px]">
                  STATUTORY RESTRAINT CERTIFICATION UNDER SECTION 11(4)
                </div>
                <p className="text-[11px] text-red-800 leading-normal">
                  "Section 11(4) mandates that no person shall make any transaction or cause any transaction of land specified in the preliminary notification or create any encumbrances on such land from the date of publication of notification."
                  <br />
                  Real-time query of the MahaRERA registry confirms <strong>{sec11ViolationsCount}</strong> project(s) entered into alienation or booking commitments post-publication date (2026-07-15).
                </p>
              </div>

              {/* Table of RERA Projects Identified */}
              <div>
                <h5 className="font-bold text-[#0b3866] uppercase text-xs mb-2">Overlapping RERA Project Register</h5>
                <table className="gov-table">
                  <thead>
                    <tr>
                      <th>Survey No</th>
                      <th>RERA Reg No</th>
                      <th>Project &amp; Promoter</th>
                      <th>Overlap Area</th>
                      <th>Buyers</th>
                      <th>Milestone Clash Assessment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map(r => (
                      <tr key={r.id}>
                        <td className="font-bold font-mono text-[#0b3866]">{r.surveyNumber}</td>
                        <td className="font-mono">{r.reraRegistrationNo}</td>
                        <td>
                          <strong>{r.projectName}</strong>
                          <div className="text-[10px] text-slate-500">{r.promoterName}</div>
                        </td>
                        <td className="font-mono">{r.overlappingAreaWithParcelHa} Ha ({r.overlapPercentage}%)</td>
                        <td className="font-mono">{r.allottees.allotteesCount} allottees</td>
                        <td>
                          <span className="font-semibold text-red-700">{r.crossReference.conflictLevel}</span>
                          <div className="text-[10px] text-slate-600">{r.crossReference.conflictTitle}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Signatures & Certification */}
              <div className="pt-8 grid grid-cols-2 gap-8 text-center text-xs">
                <div className="border-t border-slate-300 pt-2">
                  <div className="font-bold text-slate-800">Shri Vikram Patil</div>
                  <div className="text-slate-500 text-[11px]">District Inspector of Land Records (DILR)</div>
                  <div className="text-[10px] text-slate-400 font-mono">Cadastral Demarcation Verification</div>
                </div>

                <div className="border-t border-slate-300 pt-2">
                  <div className="font-bold text-slate-800">{currentUser.name}</div>
                  <div className="text-slate-500 text-[11px]">{currentUser.designation}</div>
                  <div className="text-[10px] text-slate-400 font-mono">Competent Authority for Land Acquisition (CALA)</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
