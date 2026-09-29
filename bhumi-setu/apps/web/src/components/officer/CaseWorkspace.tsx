import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  Building2, 
  MapPin, 
  Calendar, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  ArrowRight, 
  ShieldAlert, 
  FileText, 
  IndianRupee, 
  Layers, 
  TrendingUp, 
  UserCheck, 
  Send, 
  Plus, 
  X,
  FileCheck,
  Check,
  Ban,
  Share2,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { formatCurrencyINR, formatDate } from '../../lib/utils';
import { CaseStage, RiskBand } from '../../types';
import { ReraIntegrationHub } from './ReraIntegrationHub';
import { reraService } from '../../services/reraService';

export const CaseWorkspace: React.FC<{ onNavigateToOcr?: () => void }> = ({ onNavigateToOcr }) => {
  const { 
    selectedCase, 
    cases, 
    setSelectedCaseId, 
    transitionCaseStage, 
    disposeObjection, 
    disbursePayout, 
    waiveValidationIssue, 
    resolveValidationIssue, 
    overrideCaseRisk,
    currentUser, 
    language,
    addToast
  } = useApp();

  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'PARCELS' | 'NOTICES' | 'OBJECTIONS' | 'COMPENSATION' | 'VALIDATION' | 'AI_EXPLANATION' | 'RERA_INTEGRATION'>('OVERVIEW');
  const [selectedParcelForRera, setSelectedParcelForRera] = useState<string | undefined>(undefined);
  
  // Transition stage modal
  const [transitionModalOpen, setTransitionModalOpen] = useState(false);
  const [selectedNextStage, setSelectedNextStage] = useState<CaseStage>('STAGE_4_DECLARATION');

  // Objection disposal modal
  const [disposingObjectionId, setDisposingObjectionId] = useState<string | null>(null);
  const [disposalReasons, setDisposalReasons] = useState('');
  const [disposalOutcome, setDisposalOutcome] = useState<'ACCEPTED' | 'REJECTED'>('ACCEPTED');

  // Payout modal
  const [payoutModalOpen, setPayoutModalOpen] = useState(false);
  const [payoutAwardId, setPayoutAwardId] = useState<string>('');
  const [payoutAmount, setPayoutAmount] = useState<number>(0);
  const [payoutRef, setPayoutRef] = useState<string>('');

  // Waiver modal
  const [waivingIssueId, setWaivingIssueId] = useState<string | null>(null);
  const [waiverReason, setWaiverReason] = useState<string>('');

  // AI Override modal
  const [overrideModalOpen, setOverrideModalOpen] = useState(false);
  const [newOverrideBand, setNewOverrideBand] = useState<RiskBand>('MEDIUM');
  const [overrideReason, setOverrideReason] = useState('');

  const c = selectedCase;
  const caseReraRecords = reraService.getRecordsByCase(c.id);
  const sec11ViolationsInCase = caseReraRecords.filter(r => r.crossReference.sec11_4_ViolationDetected).length;

  const stageOrder: CaseStage[] = [
    'STAGE_1_SIA',
    'STAGE_2_PRELIM_NOTIF',
    'STAGE_3_OBJECTIONS',
    'STAGE_4_DECLARATION',
    'STAGE_5_AWARD_COMPENSATION',
    'STAGE_6_DISBURSEMENT',
    'STAGE_7_COMPLETED'
  ];

  const currentStageIndex = stageOrder.indexOf(c.stage);
  const nextStage = currentStageIndex < stageOrder.length - 1 ? stageOrder[currentStageIndex + 1] : null;

  const openBlockingIssues = c.validationIssues.filter(v => v.severity === 'BLOCKING' && v.resolutionState === 'OPEN');

  const handleStageTransition = () => {
    if (!nextStage) return;
    const success = transitionCaseStage(c.id, selectedNextStage);
    if (success) {
      setTransitionModalOpen(false);
    }
  };

  const handleConfirmDisposal = () => {
    if (!disposingObjectionId) return;
    disposeObjection(c.id, disposingObjectionId, disposalOutcome, disposalReasons);
    setDisposingObjectionId(null);
    setDisposalReasons('');
  };

  const handleConfirmPayout = () => {
    if (!payoutAwardId || payoutAmount <= 0) return;
    const success = disbursePayout(c.id, payoutAwardId, payoutAmount, payoutRef);
    if (success) {
      setPayoutModalOpen(false);
      setPayoutAmount(0);
      setPayoutRef('');
    }
  };

  const handleConfirmWaiver = () => {
    if (!waivingIssueId) return;
    const success = waiveValidationIssue(c.id, waivingIssueId, waiverReason);
    if (success) {
      setWaivingIssueId(null);
      setWaiverReason('');
    }
  };

  const handleConfirmOverride = () => {
    overrideCaseRisk(c.id, newOverrideBand, overrideReason);
    setOverrideModalOpen(false);
    setOverrideReason('');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-in fade-in">
      {/* Case Selector Dropdown & Header Card */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
        <div className="flex flex-wrap justify-between items-start gap-4 pb-5 border-b border-slate-100 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              {/* Case Switcher */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-500">Case Ref:</span>
                <select
                  value={c.id}
                  onChange={(e) => setSelectedCaseId(e.target.value)}
                  className="font-mono text-sm font-bold bg-blue-50 dark:bg-blue-950/60 text-blue-900 dark:text-blue-200 border border-blue-300 dark:border-blue-700 rounded-lg px-3 py-1 focus:ring-2 focus:ring-blue-500"
                >
                  {cases.map((cs) => (
                    <option key={cs.id} value={cs.id}>
                      {cs.caseReference} — {cs.village} ({cs.stage.replace('STAGE_', '')})
                    </option>
                  ))}
                </select>
              </div>

              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                c.riskBand === 'CRITICAL' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300 border border-red-300' :
                c.riskBand === 'HIGH' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border border-amber-300' :
                c.riskBand === 'MEDIUM' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border border-blue-300' :
                'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-300'
              }`}>
                {c.riskBand} DELAY RISK ({Math.round(c.riskProbability * 100)}%)
              </span>

              {c.officerOverride && (
                <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300 border border-purple-300">
                  Officer Override: {c.officerOverride.newRiskBand}
                </span>
              )}
            </div>

            <h2 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
              {language === 'en' ? c.projectName : c.projectNameHi}
            </h2>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 dark:text-slate-400 mt-2">
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                <strong>Location:</strong> {c.village}, Tehsil {c.tehsil}, District {c.district}, {c.state}
              </span>
              <span>•</span>
              <span><strong>Extent:</strong> {c.totalExtentHa} Hectares ({c.totalParcelsCount} Parcels)</span>
              <span>•</span>
              <span><strong>Budget:</strong> {formatCurrencyINR(c.sanctionedBudget)}</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setOverrideModalOpen(true)}
              className="px-3 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 text-xs font-bold text-slate-700 dark:text-slate-200 transition-colors"
            >
              {language === 'en' ? 'Override AI Risk' : 'एआई जोखिम ओवरराइड'}
            </button>

            {nextStage && (
              <button
                onClick={() => {
                  setSelectedNextStage(nextStage);
                  setTransitionModalOpen(true);
                }}
                className={`px-4 py-2 rounded-xl text-xs font-black shadow-md flex items-center gap-1.5 transition-all ${
                  openBlockingIssues.length > 0
                    ? 'bg-amber-600 hover:bg-amber-700 text-white'
                    : 'bg-blue-800 hover:bg-blue-900 text-white'
                }`}
              >
                <span>{language === 'en' ? 'Advance Statutory Stage' : 'अगले चरण में बढ़ाएं'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Statutory Stage Progress Steps */}
        <div className="pt-5 overflow-x-auto">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
            {language === 'en' ? 'RFCTLARR Act 2013 Statutory Stage Progress:' : 'भूमि अधिग्रहण सांविधिक चरण प्रगति:'}
          </p>
          <div className="flex items-center justify-between min-w-[700px] gap-2">
            {stageOrder.map((stg, index) => {
              const isPast = index < currentStageIndex;
              const isCurrent = index === currentStageIndex;
              const isFuture = index > currentStageIndex;

              const stageNames: Record<CaseStage, string> = {
                STAGE_1_SIA: '1. Sec 4 SIA',
                STAGE_2_PRELIM_NOTIF: '2. Sec 11 Notif',
                STAGE_3_OBJECTIONS: '3. Sec 15 Hearing',
                STAGE_4_DECLARATION: '4. Sec 19 Decl.',
                STAGE_5_AWARD_COMPENSATION: '5. Sec 23 Award',
                STAGE_6_DISBURSEMENT: '6. Sec 38 Payout',
                STAGE_7_COMPLETED: '7. Handover',
              };

              return (
                <div key={stg} className="flex-1 flex flex-col items-center text-center relative group">
                  {index > 0 && (
                    <div 
                      className={`absolute top-3.5 -left-1/2 w-full h-1 -z-0 ${
                        isPast ? 'bg-emerald-600' : isCurrent ? 'bg-blue-600' : 'bg-slate-200 dark:bg-slate-800'
                      }`} 
                    />
                  )}
                  
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-black z-10 transition-all ${
                      isPast
                        ? 'bg-emerald-600 text-white ring-4 ring-emerald-100 dark:ring-emerald-950'
                        : isCurrent
                        ? 'bg-blue-700 text-white ring-4 ring-blue-100 dark:ring-blue-950 animate-pulse'
                        : 'bg-slate-200 dark:bg-slate-800 text-slate-500'
                    }`}
                  >
                    {isPast ? <Check className="w-4 h-4" /> : index + 1}
                  </div>

                  <span className={`text-[11px] font-bold mt-2 ${
                    isCurrent ? 'text-blue-700 dark:text-blue-300' : isPast ? 'text-slate-800 dark:text-slate-200' : 'text-slate-400'
                  }`}>
                    {stageNames[stg]}
                  </span>

                  {isCurrent && (
                    <span className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold mt-0.5">
                      Deadline: {formatDate(c.stageDeadline)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Blocking Validation Banner if Present */}
      {openBlockingIssues.length > 0 && (
        <div className="p-4 bg-red-50 dark:bg-red-950/60 border-2 border-red-400 dark:border-red-800 rounded-2xl flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <ShieldAlert className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-black text-red-900 dark:text-red-200">
                {language === 'en' 
                  ? `Statutory Transition Blocked: ${openBlockingIssues.length} Blocking Validation Issue(s)` 
                  : `सांविधिक चरण परिवर्तन बाधित: ${openBlockingIssues.length} अवरोधक त्रुटियां`}
              </h4>
              <p className="text-xs text-red-800 dark:text-red-300 mt-0.5">
                {openBlockingIssues.map(i => i.ruleTitle).join(' • ')}
              </p>
            </div>
          </div>
          <button
            onClick={() => setActiveTab('VALIDATION')}
            className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold text-xs whitespace-nowrap"
          >
            {language === 'en' ? 'Resolve Issues' : 'त्रुटियां हल करें'}
          </button>
        </div>
      )}

      {/* Workspace Sub Tabs */}
      <div className="border-b border-slate-200 dark:border-slate-800 flex overflow-x-auto">
        {[
          { id: 'OVERVIEW', label: 'Case Summary & Timeline', count: undefined },
          { id: 'PARCELS', label: 'Land Parcels & 7/12 Owners', count: c.parcels.length },
          { id: 'RERA_INTEGRATION', label: 'RERA Status & Cross-Ref', count: caseReraRecords.length, badgeText: sec11ViolationsInCase > 0 ? `${sec11ViolationsInCase} Violation` : undefined, isDanger: sec11ViolationsInCase > 0 },
          { id: 'NOTICES', label: 'Statutory Notices', count: c.notices.length },
          { id: 'OBJECTIONS', label: 'Sec 15 Objections', count: c.objections.length },
          { id: 'COMPENSATION', label: 'Awards & DBT Payouts', count: c.awards.length },
          { id: 'VALIDATION', label: 'Validation Rules', count: c.validationIssues.length },
          { id: 'AI_EXPLANATION', label: 'AI Delay Explainability', count: c.explanationFactors.length },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-3 text-xs font-bold border-b-2 transition-all whitespace-nowrap flex items-center gap-2 ${
              activeTab === tab.id
                ? 'border-blue-700 text-blue-800 dark:text-blue-300 dark:border-blue-400 bg-blue-50/50 dark:bg-blue-950/20'
                : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                (tab as any).isDanger
                  ? 'bg-red-700 text-white animate-pulse'
                  : 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
              }`}>
                {(tab as any).badgeText ? (tab as any).badgeText : tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Sub Tab 1: OVERVIEW */}
      {activeTab === 'OVERVIEW' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Next Expected Step for Citizen & Public */}
            <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                {language === 'en' ? 'Statutory Next Step (Section 15/19 RFCTLARR)' : 'अगला सांविधिक कदम'}
              </h3>
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                {language === 'en' ? c.nextExpectedStep : c.nextExpectedStepHi}
              </p>
              <div className="pt-2 flex items-center gap-3 text-xs text-slate-500">
                <span><strong>Stage Start:</strong> {formatDate(c.stageStartDate)}</span>
                <span>•</span>
                <span><strong>Stage Deadline:</strong> {formatDate(c.stageDeadline)} ({c.daysRemaining} days remaining)</span>
              </div>
            </div>

            {/* Recommended AI Actions Checklist */}
            <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-amber-500" />
                  {language === 'en' ? 'Priority Recommended Statutory Interventions' : 'प्राथमिक अनुशंसित कानूनी कार्यवाही'}
                </h3>
              </div>

              <div className="space-y-3">
                {c.recommendedActions.map((act) => (
                  <div key={act.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
                          {act.urgency} URGENCY
                        </span>
                        <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                          {language === 'en' ? act.title : act.titleHi}
                        </h4>
                      </div>
                      <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                        {act.reason}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {act.disposition ? (
                        <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                          {act.disposition}
                        </span>
                      ) : (
                        <>
                          <button
                            onClick={() => {
                              if (act.actionType === 'CORRECT_OCR' && onNavigateToOcr) {
                                onNavigateToOcr();
                              } else if (act.actionType === 'DISPOSE_OBJECTION') {
                                setActiveTab('OBJECTIONS');
                              } else {
                                setActiveTab('VALIDATION');
                              }
                            }}
                            className="px-3 py-1.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs transition-colors"
                          >
                            {language === 'en' ? 'Execute Action' : 'कार्रवाई करें'}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Case Stats Column */}
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                {language === 'en' ? 'Compensation & Financial Summary' : 'मुआवजा एवं वित्तीय विवरण'}
              </h3>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600 dark:text-slate-400">Sanctioned Budget:</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">{formatCurrencyINR(c.sanctionedBudget)}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600 dark:text-slate-400">Determined Awards:</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">{formatCurrencyINR(c.totalAwardedAmount)}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600 dark:text-slate-400">PFMS Direct Payout:</span>
                  <span className="font-mono font-bold text-emerald-700 dark:text-emerald-400">{formatCurrencyINR(c.totalDisbursedAmount)}</span>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  onClick={() => {
                    if (c.awards.length > 0) {
                      setPayoutAwardId(c.awards[0].id);
                      setPayoutAmount(Math.max(c.awards[0].totalAmount - c.totalDisbursedAmount, 1000000));
                      setPayoutModalOpen(true);
                    } else {
                      addToast({ type: 'warning', message: 'No recorded awards available for payout.' });
                    }
                  }}
                  className="w-full py-2 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-colors"
                >
                  <IndianRupee className="w-3.5 h-3.5" />
                  <span>{language === 'en' ? 'Disburse Compensation Payout' : 'मुआवजा राशि संवितरित करें'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sub Tab 2: PARCELS & OWNERSHIP RECORDS */}
      {activeTab === 'PARCELS' && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {language === 'en' ? 'Demarcated Land Parcels & 7/12 Co-Sharers' : 'सीमांकित भूखंड एवं 7/12 सह-हिस्सेदार'}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {language === 'en' ? 'Sum of ownership shares per parcel must strictly equal 1.00 ± 0.0001 under Section 11.' : 'प्रति भूखंड सह-स्वामित्व शेयर का योग 1.00 होना अनिवार्य है।'}
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {c.parcels.map((parcel) => {
              const owners = c.ownershipRecords.filter(o => o.parcelId === parcel.id);
              const shareSum = owners.reduce((sum, o) => sum + o.ownershipShare, 0);
              const isShareValid = Math.abs(shareSum - 1.0) <= 0.0001;
              const reraProject = caseReraRecords.find(r => r.parcelId === parcel.id);

              return (
                <div key={parcel.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-3">
                  <div className="flex flex-wrap justify-between items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-sm text-blue-900 dark:text-blue-300">
                        {parcel.surveyNumber}
                      </span>
                      <span className="text-xs text-slate-500">
                        (Sub-division: {parcel.subDivision} • {parcel.classification})
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs">
                      <span><strong>Extent:</strong> {parcel.extent} {parcel.extentUnit}</span>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        isShareValid ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                      }`}>
                        Share Sum: {shareSum.toFixed(2)} / 1.00 {isShareValid ? '✓' : '⚠ Discrepancy'}
                      </span>
                    </div>
                  </div>

                  {/* RERA Real-Time Status Notification on Parcel Card */}
                  {reraProject ? (
                    <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-lg bg-blue-50/80 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-xs">
                      <div className="flex items-center gap-2.5">
                        <Building2 className="w-4 h-4 text-[#f37021] flex-shrink-0" />
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-[#0b3866] dark:text-blue-300">Overlapping RERA Project:</span>
                            <span className="font-semibold text-slate-900 dark:text-slate-100">{reraProject.projectName}</span>
                            <span className="font-mono font-bold text-slate-600 dark:text-slate-400">({reraProject.reraRegistrationNo})</span>
                            {reraProject.crossReference.sec11_4_ViolationDetected && (
                              <span className="bg-red-100 text-red-800 text-[10px] font-bold px-1.5 py-0.2 rounded">
                                ⚠️ Sec 11(4) Violation
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-600 dark:text-slate-400 mt-0.5">
                            Cadastral Overlap: <strong>{reraProject.overlappingAreaWithParcelHa} Ha ({reraProject.overlapPercentage}%)</strong> • 
                            Conflict Level: <strong className={reraProject.crossReference.conflictLevel === 'CRITICAL_BLOCKER' ? 'text-red-600' : 'text-amber-600'}>{reraProject.crossReference.conflictLevel}</strong> • 
                            Allottees Affected: <strong>{reraProject.allottees.allotteesCount} Buyers</strong>
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={() => {
                          setSelectedParcelForRera(parcel.id);
                          setActiveTab('RERA_INTEGRATION');
                        }}
                        className="px-3 py-1.5 bg-[#f37021] hover:bg-[#d95a10] text-white font-bold text-xs rounded-lg flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        <span>View RERA Cross-Ref</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between p-2 rounded-lg bg-slate-100/60 dark:bg-slate-800/30 border border-slate-200 dark:border-slate-700 text-[11px] text-slate-600 dark:text-slate-400">
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                        <span>RERA Nil Encumbrance: No overlapping registered builder projects recorded on this parcel.</span>
                      </div>
                      <button
                        onClick={() => {
                          setSelectedParcelForRera(parcel.id);
                          setActiveTab('RERA_INTEGRATION');
                        }}
                        className="text-blue-700 dark:text-blue-400 hover:underline font-semibold"
                      >
                        Verify Gateway
                      </button>
                    </div>
                  )}

                  {/* Owners Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="text-slate-500 border-b border-slate-200 dark:border-slate-700">
                          <th className="py-2 px-2">Owner Name (Khatedar)</th>
                          <th className="py-2 px-2">Interest Type</th>
                          <th className="py-2 px-2">Ownership Share</th>
                          <th className="py-2 px-2">Aadhaar (Masked)</th>
                          <th className="py-2 px-2">Bank Mandate</th>
                          <th className="py-2 px-2">Contact</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {owners.map((owner) => (
                          <tr key={owner.id}>
                            <td className="py-2 px-2 font-semibold text-slate-900 dark:text-slate-100">
                              {owner.ownerName} ({owner.ownerNameHi})
                            </td>
                            <td className="py-2 px-2 text-slate-600 dark:text-slate-400">{owner.interestType}</td>
                            <td className="py-2 px-2 font-mono font-bold text-blue-700 dark:text-blue-300">
                              {(owner.ownershipShare * 100).toFixed(0)}% ({owner.ownershipShare})
                            </td>
                            <td className="py-2 px-2 font-mono text-slate-600 dark:text-slate-400">{owner.governmentIdentifierMasked}</td>
                            <td className="py-2 px-2 font-mono text-emerald-700 dark:text-emerald-400">{owner.bankAccountMasked || 'Verified'}</td>
                            <td className="py-2 px-2 text-slate-600 dark:text-slate-400">{owner.contactNumber}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Sub Tab 3: STATUTORY NOTICES */}
      {activeTab === 'NOTICES' && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 space-y-4">
          <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
            {language === 'en' ? 'Statutory Notices & Service Log' : 'सांविधिक नोटिस एवं तामील पंजी'}
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">
                  <th className="py-3 px-3">Notice Type</th>
                  <th className="py-3 px-3">Issuing Authority</th>
                  <th className="py-3 px-3">Issue Date</th>
                  <th className="py-3 px-3">Publication Mode</th>
                  <th className="py-3 px-3">Response Deadline</th>
                  <th className="py-3 px-3">Service Details</th>
                  <th className="py-3 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {c.notices.map((n) => (
                  <tr key={n.id}>
                    <td className="py-3 px-3 font-bold text-blue-900 dark:text-blue-300">{n.noticeType}</td>
                    <td className="py-3 px-3 text-slate-700 dark:text-slate-300">{n.issuingAuthority}</td>
                    <td className="py-3 px-3">{formatDate(n.issueDate)}</td>
                    <td className="py-3 px-3 text-slate-600 dark:text-slate-400">{n.publicationMode}</td>
                    <td className="py-3 px-3 font-semibold text-amber-700 dark:text-amber-400">{formatDate(n.responseDeadline)}</td>
                    <td className="py-3 px-3 text-slate-600 dark:text-slate-400">
                      {n.serviceDate ? `${formatDate(n.serviceDate)} via ${n.serviceMode}` : 'Pending Proof'}
                    </td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        n.isBreached ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
                      }`}>
                        {n.isBreached ? 'Breached' : 'Active Window'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sub Tab 4: SECTION 15 OBJECTIONS */}
      {activeTab === 'OBJECTIONS' && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {language === 'en' ? 'Section 15 Public Objections & Representation Disposal' : 'धारा 15 लोक आपत्तियां एवं निराकरण'}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {language === 'en' ? 'All objections must be legally disposed of under Section 15(2) before Section 19 Declaration.' : 'धारा 19 घोषणा से पूर्व सभी आपत्तियों का विधिक निस्तारण अनिवार्य है।'}
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {c.objections.map((obj) => (
              <div key={obj.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 space-y-2">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs text-slate-900 dark:text-slate-100">
                        {obj.objectorName}
                      </span>
                      <span className="text-[11px] text-slate-500">({obj.objectorContact})</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                        {obj.groundsCategory}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700 dark:text-slate-300 mt-1 italic">
                      "{obj.substance}"
                    </p>
                  </div>

                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                    obj.disposalState === 'PENDING' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300' :
                    obj.disposalState === 'ACCEPTED' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' :
                    'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                  }`}>
                    {obj.disposalState}
                  </span>
                </div>

                <div className="pt-2 border-t border-slate-200 dark:border-slate-700 flex flex-wrap justify-between items-center gap-2 text-xs">
                  <span className="text-slate-500">Received on: {formatDate(obj.receiptDate)}</span>
                  
                  {obj.disposalState === 'PENDING' ? (
                    <button
                      onClick={() => {
                        setDisposingObjectionId(obj.id);
                        setDisposalReasons('');
                      }}
                      className="px-3 py-1 bg-blue-800 hover:bg-blue-900 text-white rounded-lg font-bold text-xs"
                    >
                      {language === 'en' ? 'Record Section 15 Order' : 'धारा 15 आदेश पारित करें'}
                    </button>
                  ) : (
                    <div className="text-slate-600 dark:text-slate-300 text-[11px]">
                      <strong>Order Reasons:</strong> {obj.disposalReasons} (Decided by: {obj.decidingOfficer})
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sub Tab 5: COMPENSATION AWARDS & DBT PAYOUTS */}
      {activeTab === 'COMPENSATION' && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {language === 'en' ? 'Section 23 Compensation Awards & DBT PFMS Ledger' : 'धारा 23 मुआवजा पंचाट एवं प्रत्यक्ष लाभ अंतरण (DBT)'}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {language === 'en' ? 'Arithmetic verified: Basic Value + 100% Solatium (Sec 30) + 12% Additional Component.' : 'अंकगणितीय सत्यापन: मूल मूल्य + 100% तोषण (संबलन) + 12% अतिरिक्त घटक।'}
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {c.awards.map((award) => (
              <div key={award.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 space-y-3">
                <div className="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-slate-700">
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {award.ownerName}
                    </h4>
                    <p className="text-xs text-slate-500">Determined on {formatDate(award.determinationDate)} by {award.determiningAuthority}</p>
                  </div>
                  <div className="text-right">
                    <div className="font-mono font-black text-base text-blue-900 dark:text-blue-300">
                      {formatCurrencyINR(award.totalAmount)}
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      award.disbursementState === 'FULLY_PAID' ? 'bg-emerald-100 text-emerald-800' :
                      award.disbursementState === 'PART_PAID' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {award.disbursementState}
                    </span>
                  </div>
                </div>

                {/* Itemized Components */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {award.components.map((comp) => (
                    <div key={comp.id} className="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex justify-between">
                      <span className="text-slate-600 dark:text-slate-400">{comp.label}:</span>
                      <span className="font-mono font-bold">{formatCurrencyINR(comp.amount)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sub Tab 6: VALIDATION RULES */}
      {activeTab === 'VALIDATION' && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 space-y-4">
          <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
            {language === 'en' ? 'Automated Rule Execution & Issue Queue' : 'स्वचालित नियम सत्यापन एवं त्रुटि सूची'}
          </h3>

          <div className="space-y-3">
            {c.validationIssues.map((issue) => (
              <div key={issue.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      issue.severity === 'BLOCKING' ? 'bg-red-600 text-white' :
                      issue.severity === 'MAJOR' ? 'bg-amber-500 text-white' : 'bg-blue-600 text-white'
                    }`}>
                      {issue.severity}
                    </span>
                    <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">{issue.ruleTitle}</h4>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">{issue.description}</p>
                  <p className="text-[11px] font-mono text-slate-500 mt-0.5">Observed: {issue.observedValues}</p>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {issue.resolutionState === 'OPEN' ? (
                    <>
                      <button
                        onClick={() => resolveValidationIssue(c.id, issue.id, 'Corrected manually by officer')}
                        className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold"
                      >
                        {language === 'en' ? 'Resolve (Corrected)' : 'हल करें'}
                      </button>
                      <button
                        onClick={() => {
                          setWaivingIssueId(issue.id);
                          setWaiverReason('');
                        }}
                        className="px-3 py-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold"
                      >
                        {language === 'en' ? 'Waive (Collector)' : 'माफ करें'}
                      </button>
                    </>
                  ) : (
                    <span className="px-2.5 py-1 rounded text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                      {issue.resolutionState}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sub Tab 7: AI DELAY EXPLAINABILITY */}
      {activeTab === 'AI_EXPLANATION' && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-6 space-y-6">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-amber-500" />
                {language === 'en' ? 'Top Delay Explanation Factors (SHAP Feature Contributions)' : 'शीर्ष विलंब व्याख्या कारक (SHAP विश्लेषण)'}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {language === 'en' ? 'Calibrated delay probability: ' : 'कैलिब्रेटेड विलंब संभावना: '}
                <strong className="text-red-600 font-mono text-sm">{Math.round(c.riskProbability * 100)}% ({c.riskBand})</strong>
              </p>
            </div>
            <span className="text-xs font-mono text-slate-500">Model: {c.modelVersion}</span>
          </div>

          <div className="space-y-4">
            {c.explanationFactors.map((factor) => {
              const isDelayIncrease = factor.direction === 'INCREASES_DELAY';
              const widthPct = Math.abs(factor.magnitude) * 150;

              return (
                <div key={factor.featureName} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-slate-900 dark:text-slate-100">
                      {language === 'en' ? factor.label : factor.labelHi}
                    </span>
                    <span className={`font-mono font-bold ${isDelayIncrease ? 'text-red-600' : 'text-emerald-600'}`}>
                      {isDelayIncrease ? `+${(factor.magnitude * 100).toFixed(0)}% Risk Impact` : `${(factor.magnitude * 100).toFixed(0)}% Mitigation`}
                    </span>
                  </div>

                  {/* Impact bar */}
                  <div className="h-2 w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${isDelayIncrease ? 'bg-red-500' : 'bg-emerald-500'}`}
                      style={{ width: `${Math.min(widthPct, 100)}%` }}
                    />
                  </div>

                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    {factor.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Sub Tab 8: RERA PROJECT STATUS & STATUTORY MILESTONE CROSS-REFERENCE */}
      {activeTab === 'RERA_INTEGRATION' && (
        <ReraIntegrationHub 
          caseRecord={c}
          initialSelectedParcelId={selectedParcelForRera}
          onNavigateToCase={(caseId) => setSelectedCaseId(caseId)}
        />
      )}

      {/* Advance Stage Modal */}
      {transitionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              {language === 'en' ? 'Advance Statutory Stage' : 'सांविधिक चरण आगे बढ़ाएं'}
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Transitioning from <strong className="text-blue-700">{c.stage.replace(/_/g, ' ')}</strong> to <strong className="text-emerald-700">{selectedNextStage.replace(/_/g, ' ')}</strong>.
            </p>

            {openBlockingIssues.length > 0 && (
              <div className="p-3 bg-red-50 dark:bg-red-950/60 border border-red-300 rounded-xl text-xs text-red-800 dark:text-red-200">
                ⚠ Warning: {openBlockingIssues.length} BLOCKING issues are open. Transition will be rejected unless resolved or waived by Collector.
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setTransitionModalOpen(false)}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-bold"
              >
                Cancel
              </button>
              <button
                onClick={handleStageTransition}
                className="px-4 py-2 bg-blue-800 hover:bg-blue-900 text-white rounded-lg text-xs font-bold"
              >
                Confirm Transition
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Objection Disposal Modal */}
      {disposingObjectionId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              {language === 'en' ? 'Record Section 15(2) Objection Order' : 'धारा 15(2) आपत्ति आदेश दर्ज करें'}
            </h3>

            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1 block">
                Disposal Outcome:
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setDisposalOutcome('ACCEPTED')}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold border ${
                    disposalOutcome === 'ACCEPTED' ? 'bg-emerald-700 text-white border-emerald-800' : 'bg-slate-100 dark:bg-slate-800 border-slate-300'
                  }`}
                >
                  Accept Objection (Revise Award)
                </button>
                <button
                  type="button"
                  onClick={() => setDisposalOutcome('REJECTED')}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold border ${
                    disposalOutcome === 'REJECTED' ? 'bg-red-700 text-white border-red-800' : 'bg-slate-100 dark:bg-slate-800 border-slate-300'
                  }`}
                >
                  Reject Objection
                </button>
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1 block">
                Statutory Reasoning / Findings of Fact (Mandatory):
              </label>
              <textarea
                value={disposalReasons}
                onChange={(e) => setDisposalReasons(e.target.value)}
                placeholder="Enter detailed legal reasoning under RFCTLARR Act 2013..."
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 h-24 focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setDisposingObjectionId(null)}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-bold"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDisposal}
                className="px-4 py-2 bg-blue-800 hover:bg-blue-900 text-white rounded-lg text-xs font-bold"
              >
                Record Statutory Order
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Payout Modal */}
      {payoutModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              {language === 'en' ? 'Initiate DBT PFMS Compensation Payout' : 'डीबीटी मुआवजा भुगतान जारी करें'}
            </h3>

            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1 block">
                Disbursement Amount (INR):
              </label>
              <input
                type="number"
                value={payoutAmount}
                onChange={(e) => setPayoutAmount(Number(e.target.value))}
                className="w-full text-xs font-mono font-bold p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-[11px] text-slate-500 mt-1 block font-mono">
                {formatCurrencyINR(payoutAmount)}
              </span>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1 block">
                PFMS Instrument Reference:
              </label>
              <input
                type="text"
                value={payoutRef}
                onChange={(e) => setPayoutRef(e.target.value)}
                placeholder="DBT/PFMS/2026/08/99812402"
                className="w-full text-xs font-mono p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setPayoutModalOpen(false)}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-bold"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmPayout}
                className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold"
              >
                Authorize Payment
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Validation Waiver Modal */}
      {waivingIssueId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              {language === 'en' ? 'Authorize Statutory Issue Waiver' : 'सांविधिक त्रुटि माफ़ी प्राधिकार'}
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Note: Only District Collector can waive BLOCKING issues. Waiver reason is permanently stored in the audit log.
            </p>

            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1 block">
                Recorded Legal Reason for Waiver (Min 8 characters):
              </label>
              <textarea
                value={waiverReason}
                onChange={(e) => setWaiverReason(e.target.value)}
                placeholder="State administrative justification..."
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 h-20 focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setWaivingIssueId(null)}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-bold"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmWaiver}
                className="px-4 py-2 bg-blue-800 hover:bg-blue-900 text-white rounded-lg text-xs font-bold"
              >
                Authorize Waiver
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI Override Modal */}
      {overrideModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              {language === 'en' ? 'Officer Manual Override of AI Delay Risk' : 'एआई जोखिम गणना का मानवीय ओवरराइड'}
            </h3>

            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1 block">
                Select Overridden Risk Band:
              </label>
              <select
                value={newOverrideBand}
                onChange={(e) => setNewOverrideBand(e.target.value as RiskBand)}
                className="w-full text-xs font-bold p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-blue-500"
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1 block">
                Officer Justification:
              </label>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="e.g. Ground settlement reached in mediation..."
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 h-20 focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setOverrideModalOpen(false)}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-bold"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmOverride}
                className="px-4 py-2 bg-blue-800 hover:bg-blue-900 text-white rounded-lg text-xs font-bold"
              >
                Save Override
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
