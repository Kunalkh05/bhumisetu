import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  AlertTriangle, 
  Clock, 
  FileWarning, 
  HelpCircle, 
  CheckCircle2, 
  IndianRupee, 
  TrendingUp, 
  MapPin, 
  Layers, 
  ShieldAlert, 
  ArrowUpRight,
  Filter,
  BarChart3,
  Calendar,
  Building,
  FileText
} from 'lucide-react';
import { formatCurrencyINR, formatDate } from '../../lib/utils';
import { CaseStage, RiskBand } from '../../types';

export const OfficerDashboard: React.FC<{ onNavigateToCase: (caseId: string) => void }> = ({ onNavigateToCase }) => {
  const { cases, currentUser, language, setSelectedCaseId } = useApp();
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string>('ALL');

  // Filter cases by jurisdiction
  const filteredCases = cases.filter(c => {
    if (selectedJurisdiction !== 'ALL' && c.tehsil !== selectedJurisdiction && c.district !== selectedJurisdiction) {
      return false;
    }
    return currentUser.jurisdiction.includes(c.district) || currentUser.jurisdiction.includes(c.tehsil);
  });

  // Calculate Metrics
  const totalCases = filteredCases.length;
  const criticalCases = filteredCases.filter(c => c.riskBand === 'CRITICAL').length;
  const highRiskCases = filteredCases.filter(c => c.riskBand === 'HIGH').length;
  const mediumRiskCases = filteredCases.filter(c => c.riskBand === 'MEDIUM').length;
  const lowRiskCases = filteredCases.filter(c => c.riskBand === 'LOW').length;

  const breachedDeadlines = filteredCases.filter(c => c.isBreached || c.daysRemaining < 0).length;
  const approachingDeadlines = filteredCases.filter(c => !c.isBreached && c.daysRemaining >= 0 && c.daysRemaining <= 15).length;

  const totalOpenBlockingIssues = filteredCases.reduce((sum, c) => 
    sum + c.validationIssues.filter(v => v.severity === 'BLOCKING' && v.resolutionState === 'OPEN').length, 0
  );
  const totalOpenMajorIssues = filteredCases.reduce((sum, c) => 
    sum + c.validationIssues.filter(v => v.severity === 'MAJOR' && v.resolutionState === 'OPEN').length, 0
  );

  const totalUndisposedObjections = filteredCases.reduce((sum, c) => 
    sum + c.objections.filter(o => o.disposalState === 'PENDING').length, 0
  );

  const totalAwarded = filteredCases.reduce((sum, c) => sum + c.totalAwardedAmount, 0);
  const totalDisbursed = filteredCases.reduce((sum, c) => sum + c.totalDisbursedAmount, 0);
  const disbursementRate = totalAwarded > 0 ? Math.round((totalDisbursed / totalAwarded) * 100) : 0;

  // Stages count breakdown
  const stagesList: { stage: CaseStage; label: string; labelHi: string }[] = [
    { stage: 'STAGE_1_SIA', label: 'Section 4 SIA Report', labelHi: 'धारा 4 सामाजिक प्रभाव' },
    { stage: 'STAGE_2_PRELIM_NOTIF', label: 'Section 11 Preliminary Notif', labelHi: 'धारा 11 प्रारंभिक अधिसूचना' },
    { stage: 'STAGE_3_OBJECTIONS', label: 'Section 15 Hearing & Objections', labelHi: 'धारा 15 सुनवाई व आपत्तियां' },
    { stage: 'STAGE_4_DECLARATION', label: 'Section 19 Declaration', labelHi: 'धारा 19 अंतिम घोषणा' },
    { stage: 'STAGE_5_AWARD_COMPENSATION', label: 'Section 23 Award Determination', labelHi: 'धारा 23 पंचाट निर्धारण' },
    { stage: 'STAGE_6_DISBURSEMENT', label: 'Section 38 Payout & Possession', labelHi: 'धारा 38 भुगतान व कब्जा' },
  ];

  return (
    <div className="space-y-4">
      {/* Top Header: Operational Jurisdiction & Quick Scope Switcher */}
      <div className="gov-surface-card p-4 sm:p-5 flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#002642]/5 border border-slate-200 flex items-center justify-center text-[#002642]">
            <Building className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-[#002642] tracking-wider uppercase">
                {currentUser.role.replace('_', ' ')}
              </span>
              <span className="text-slate-300">•</span>
              <span className="text-xs text-slate-500 font-medium">
                {language === 'en' ? 'CALA Competent Authority' : 'सक्षम प्राधिकारी'}
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 mt-0.5">
              {language === 'en' ? 'Land Acquisition Operations Command' : 'भूमि अधिग्रहण संचालन कमान'}
            </h2>
            <p className="text-xs text-slate-500">
              {currentUser.designation} • {language === 'en' ? 'Assigned Jurisdiction:' : 'अधिकार क्षेत्र:'} <strong className="text-slate-700">{currentUser.jurisdiction.join(', ')}</strong>
            </p>
          </div>
        </div>

        {/* Quick Scope Filter */}
        <div className="flex items-center gap-2 bg-slate-50 p-1.5 rounded-lg border border-slate-200">
          <Filter className="w-3.5 h-3.5 text-slate-500 ml-1.5" />
          <label htmlFor="jurisdiction-select" className="text-xs font-semibold text-slate-700">
            {language === 'en' ? 'Jurisdiction:' : 'अधिकार क्षेत्र:'}
          </label>
          <select
            id="jurisdiction-select"
            value={selectedJurisdiction}
            onChange={(e) => setSelectedJurisdiction(e.target.value)}
            className="bg-white text-slate-800 text-xs font-medium py-1 px-2.5 rounded-md border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#002642]/20"
          >
            <option value="ALL">{language === 'en' ? 'All Assigned Tehsils' : 'सभी अधिकार क्षेत्र'}</option>
            {currentUser.jurisdiction.map((j) => (
              <option key={j} value={j}>{j}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Primary Operational Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="gov-surface-card p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {language === 'en' ? 'Active Acquisition Cases' : 'सक्रिय अधिग्रहण प्रकरण'}
              </p>
              <h3 className="text-2xl font-black text-slate-900 mt-1">
                {totalCases}
              </h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-blue-50 text-[#002642] flex items-center justify-center">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="font-bold text-red-700">
              {criticalCases} {language === 'en' ? 'Critical Risk' : 'अति संवेदनशील'}
            </span>
            <span className="text-slate-500">
              {highRiskCases} High • {lowRiskCases} Low
            </span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="gov-surface-card p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {language === 'en' ? 'Statutory Deadlines' : 'सांविधिक समय-सीमा'}
              </p>
              <h3 className="text-2xl font-black text-red-600 mt-1">
                {breachedDeadlines} <span className="text-xs font-semibold text-slate-500">Breached</span>
              </h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-red-50 text-red-600 flex items-center justify-center">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-amber-700 font-semibold">
              {approachingDeadlines} {language === 'en' ? 'Due in ≤15 days' : '15 दिनों में देय'}
            </span>
            <span className="text-slate-400 text-[11px]">RFCTLARR 2013</span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="gov-surface-card p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {language === 'en' ? 'Blocking Issues & Objections' : 'अवरोधक त्रुटियां व आपत्तियां'}
              </p>
              <h3 className="text-2xl font-black text-amber-700 mt-1">
                {totalOpenBlockingIssues} <span className="text-xs font-semibold text-slate-500">Blocking</span>
              </h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-700 font-medium">
              {totalUndisposedObjections} {language === 'en' ? 'Sec 15 Objections' : 'लंबित आपत्तियां'}
            </span>
            <span className="text-amber-700 font-bold">{totalOpenMajorIssues} Major</span>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="gov-surface-card p-4 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {language === 'en' ? 'PFMS Direct Disbursement' : 'संवितरित मुआवजा राशि'}
              </p>
              <h3 className="text-xl font-black text-emerald-700 mt-1">
                {formatCurrencyINR(totalDisbursed)}
              </h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <IndianRupee className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-600">
              {disbursementRate}% of {formatCurrencyINR(totalAwarded)}
            </span>
            <span className="font-semibold text-emerald-700">PFMS Aadhaar-DBT</span>
          </div>
        </div>
      </div>

      {/* Middle Grid: Statutory Stage Throughput & AI Delay Spectrum */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Stage Progress (2 cols) */}
        <div className="lg:col-span-2 gov-surface-card p-5 space-y-4">
          <div className="border-b border-slate-100 pb-3 flex justify-between items-center">
            <div>
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-[#002642]" />
                <span>{language === 'en' ? 'Statutory Milestone Pipeline (RFCTLARR 2013)' : 'सांविधिक चरणवार प्रकरण वितरण'}</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Active case distribution across statutory milestones
              </p>
            </div>
            <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
              {totalCases} Cases
            </span>
          </div>

          <div className="space-y-3 pt-1">
            {stagesList.map((item, idx) => {
              const count = filteredCases.filter(c => c.stage === item.stage).length;
              const percent = totalCases > 0 ? (count / totalCases) * 100 : 0;
              const hasCritical = filteredCases.some(c => c.stage === item.stage && c.riskBand === 'CRITICAL');

              return (
                <div key={item.stage} className="space-y-1.5 text-xs">
                  <div className="flex justify-between font-medium text-slate-800">
                    <span className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-md bg-[#002642] text-white flex items-center justify-center text-[10px] font-bold">
                        {idx + 1}
                      </span>
                      <span className="font-semibold text-slate-800">{language === 'en' ? item.label : item.labelHi}</span>
                    </span>
                    <span className="text-slate-600 flex items-center gap-2">
                      {hasCritical && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-700 font-semibold border border-red-200">
                          Delay Risk
                        </span>
                      )}
                      <strong className="text-slate-900 font-bold">{count}</strong>
                      <span className="text-slate-400">({percent.toFixed(0)}%)</span>
                    </span>
                  </div>

                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden flex">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${hasCritical ? 'bg-red-500' : 'bg-[#002642]'}`}
                      style={{ width: `${Math.max(percent, count > 0 ? 8 : 0)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* AI Delay Risk Spectrum (1 col) */}
        <div className="gov-surface-card p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div className="border-b border-slate-100 pb-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-amber-500" />
                  <span>{language === 'en' ? 'AI Delay Risk Spectrum' : 'एआई विलंब जोखिम'}</span>
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-blue-50 text-blue-800 rounded-md border border-blue-200">
                  Decision Support
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">Calibrated ML Early-Warning (90-day horizon)</p>
            </div>

            <div className="mt-4 space-y-2 text-xs">
              <div className="p-2.5 rounded-lg bg-red-50/70 border border-red-200 flex justify-between items-center">
                <div>
                  <div className="font-bold text-red-800">CRITICAL</div>
                  <div className="text-[10px] text-red-600">p ≥ 0.75 probability</div>
                </div>
                <span className="font-mono text-base font-black text-red-700">{criticalCases}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-amber-50/70 border border-amber-200 flex justify-between items-center">
                <div>
                  <div className="font-bold text-amber-800">HIGH RISK</div>
                  <div className="text-[10px] text-amber-600">0.50 ≤ p &lt; 0.75</div>
                </div>
                <span className="font-mono text-base font-black text-amber-700">{highRiskCases}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
                <div>
                  <div className="font-bold text-slate-700">MEDIUM RISK</div>
                  <div className="text-[10px] text-slate-500">0.25 ≤ p &lt; 0.50</div>
                </div>
                <span className="font-mono text-base font-black text-slate-700">{mediumRiskCases}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-emerald-50/70 border border-emerald-200 flex justify-between items-center">
                <div>
                  <div className="font-bold text-emerald-800">LOW RISK</div>
                  <div className="text-[10px] text-emerald-600">p &lt; 0.25</div>
                </div>
                <span className="font-mono text-base font-black text-emerald-700">{lowRiskCases}</span>
              </div>
            </div>
          </div>

          <div className="pt-3 text-[11px] text-slate-400 border-t border-slate-100 flex justify-between items-center">
            <span>Model: Calibrated XGBoost v2.4</span>
            <span className="font-semibold text-emerald-700">ECE: 0.038</span>
          </div>
        </div>
      </div>

      {/* Priority Case Registry Table */}
      <div className="gov-surface-card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-[#002642]" />
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              {language === 'en' ? 'Priority Land Acquisition Case Registry' : 'प्राथमिकता भू-अधिग्रहण प्रकरण पंजी'}
            </h3>
          </div>
          <span className="text-xs text-slate-400">Click any row to open 360° workspace</span>
        </div>

        <div className="overflow-x-auto">
          <table className="gov-table-2026">
            <thead>
              <tr>
                <th>Case Reference</th>
                <th>Project Name</th>
                <th>Village / Tehsil</th>
                <th>Current Stage</th>
                <th>Statutory Deadline</th>
                <th>AI Risk</th>
                <th>Disbursed / Awarded</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredCases.map((c) => {
                const isOverdue = c.isBreached || c.daysRemaining < 0;
                return (
                  <tr 
                    key={c.id}
                    onClick={() => {
                      setSelectedCaseId(c.id);
                      onNavigateToCase(c.id);
                    }}
                    className="cursor-pointer hover:bg-slate-50/80 transition-colors"
                  >
                    <td className="font-mono font-bold text-[#002642]">
                      {c.caseReference}
                    </td>
                    <td className="font-medium text-slate-900 max-w-[220px] truncate">
                      {language === 'en' ? c.projectName : c.projectNameHi}
                    </td>
                    <td className="text-slate-600 text-xs">
                      {c.village}, {c.tehsil}
                    </td>
                    <td>
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-800 rounded-md font-semibold text-[11px] border border-slate-200">
                        {c.stage.replace('STAGE_', '').replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      <span className={`font-semibold text-xs ${isOverdue ? 'text-red-700' : 'text-slate-800'}`}>
                        {formatDate(c.stageDeadline)}
                      </span>
                      {isOverdue ? (
                        <span className="block text-[10px] text-red-600 font-bold">
                          {Math.abs(c.daysRemaining)}d Breached
                        </span>
                      ) : (
                        <span className="block text-[10px] text-slate-400">
                          ({c.daysRemaining}d left)
                        </span>
                      )}
                    </td>
                    <td>
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                        c.riskBand === 'CRITICAL' ? 'bg-red-50 text-red-700 border border-red-200' :
                        c.riskBand === 'HIGH' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                        c.riskBand === 'MEDIUM' ? 'bg-slate-100 text-slate-700 border border-slate-200' :
                        'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}>
                        {c.riskBand} ({Math.round(c.riskProbability * 100)}%)
                      </span>
                    </td>
                    <td className="font-mono text-xs">
                      <div className="font-bold text-emerald-700">{formatCurrencyINR(c.totalDisbursedAmount)}</div>
                      <div className="text-[10px] text-slate-400">{formatCurrencyINR(c.totalAwardedAmount)} Awarded</div>
                    </td>
                    <td className="text-right">
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedCaseId(c.id);
                          onNavigateToCase(c.id);
                        }}
                        className="px-3 py-1 bg-[#002642] hover:bg-[#0b3866] text-white font-semibold text-xs rounded-md shadow-xs transition-colors cursor-pointer"
                      >
                        {language === 'en' ? 'Open Case' : 'प्रकरण खोलें'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
