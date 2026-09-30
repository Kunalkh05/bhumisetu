import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  AlertOctagon, 
  Clock, 
  TrendingUp, 
  ArrowUpRight, 
  Check, 
  X, 
  Pause, 
  ShieldAlert, 
  IndianRupee, 
  Filter,
  CheckCircle2,
  Calendar
} from 'lucide-react';
import { formatCurrencyINR, formatDate } from '../../lib/utils';
import { RecommendedAction, AcquisitionCase } from '../../types';

export const InterventionQueue: React.FC<{ onNavigateToCase: (caseId: string) => void }> = ({ onNavigateToCase }) => {
  const { cases, actOnRecommendedAction, setSelectedCaseId, language } = useApp();
  const [filterUrgency, setFilterUrgency] = useState<'ALL' | 'HIGH' | 'MEDIUM'>('ALL');

  // Order cases by Priority Score descending (Req 21.7)
  const rankedCases = [...cases].sort((a, b) => b.priorityScore - a.priorityScore);

  return (
    <div className="max-w-7xl mx-auto space-y-5 animate-in fade-in">
      {/* Header Banner */}
      <div className="gov-surface-card p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
              <AlertOctagon className="w-5 h-5 text-red-600" />
              <span>{language === 'en' ? 'Statutory Priority Intervention Queue' : 'सांविधिक प्राथमिकता हस्तक्षेप कतार'}</span>
            </h2>
            <span className="text-[10px] font-bold px-2 py-0.5 bg-blue-50 text-blue-800 rounded-md border border-blue-200">
              AI Decision Support
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {language === 'en'
              ? 'Multi-factor priority ranking: Priority_Score = f(Calibrated Delay Risk, Stage Deadline Pressure, Financial Exposure). Prescribed actions require officer administrative sanction.'
              : 'एआई विलंब जोखिम, समय-सीमा दबाव एवं वित्तीय दायित्व पर आधारित प्राथमिकता रैंकिंग।'}
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-50 p-1.5 rounded-lg border border-slate-200">
          <Filter className="w-3.5 h-3.5 text-slate-500 ml-1.5" />
          <span className="text-xs font-semibold text-slate-700">Urgency:</span>
          <select
            value={filterUrgency}
            onChange={(e) => setFilterUrgency(e.target.value as any)}
            className="text-xs font-medium rounded-md border border-slate-200 bg-white px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#002642]/20 cursor-pointer"
          >
            <option value="ALL">All Urgencies</option>
            <option value="HIGH">High Urgency Only</option>
            <option value="MEDIUM">Medium Urgency</option>
          </select>
        </div>
      </div>

      {/* Priority Ranked Case Cards */}
      <div className="space-y-4">
        {rankedCases.map((c, index) => {
          const isCritical = c.riskBand === 'CRITICAL';

          return (
            <div
              key={c.id}
              className={`gov-surface-card p-5 sm:p-6 transition-all ${
                isCritical 
                  ? 'border-red-200 ring-1 ring-red-500/10' 
                  : 'border-slate-200'
              }`}
            >
              {/* Card Header */}
              <div className="flex flex-wrap justify-between items-start gap-4 pb-4 border-b border-slate-100">
                <div className="flex items-start gap-3.5">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center font-black text-xs ${
                    index === 0 ? 'bg-red-600 text-white shadow-xs' :
                    index === 1 ? 'bg-amber-600 text-white' : 'bg-[#002642] text-white'
                  }`}>
                    #{index + 1}
                  </div>

                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-bold text-xs text-[#002642]">
                        {c.caseReference}
                      </span>
                      <span className="text-xs text-slate-500">
                        ({c.village}, {c.tehsil})
                      </span>
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                        c.riskBand === 'CRITICAL' ? 'bg-red-50 text-red-700 border border-red-200' :
                        c.riskBand === 'HIGH' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                        'bg-blue-50 text-blue-700 border border-blue-200'
                      }`}>
                        {c.riskBand} ({Math.round(c.riskProbability * 100)}%)
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-slate-900 mt-1">
                      {language === 'en' ? c.projectName : c.projectNameHi}
                    </h3>
                  </div>
                </div>

                {/* Priority Score Gauge Badge */}
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Priority Score</span>
                    <span className="text-2xl font-black font-mono text-red-600">{c.priorityScore}<span className="text-xs text-slate-400">/100</span></span>
                  </div>

                  <button
                    onClick={() => {
                      setSelectedCaseId(c.id);
                      onNavigateToCase(c.id);
                    }}
                    className="px-3 py-1.5 bg-slate-100 text-[#002642] hover:bg-[#002642] hover:text-white rounded-lg font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer border border-slate-200"
                  >
                    <span>Inspect</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Deadline and Value Factors */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 py-3 text-xs border-b border-slate-100">
                <div className="flex items-center gap-2 text-slate-700">
                  <Clock className="w-4 h-4 text-slate-400" />
                  <span><strong>Stage Deadline:</strong> {formatDate(c.stageDeadline)} ({c.daysRemaining}d left)</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700">
                  <IndianRupee className="w-4 h-4 text-emerald-600" />
                  <span><strong>Total Award:</strong> {formatCurrencyINR(c.totalAwardedAmount)}</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700">
                  <ShieldAlert className="w-4 h-4 text-amber-500" />
                  <span><strong>Open Issues:</strong> {c.validationIssues.filter(v => v.resolutionState === 'OPEN').length} issues</span>
                </div>
              </div>

              {/* Recommended Statutory Actions List */}
              <div className="mt-4 space-y-2.5">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                  {language === 'en' ? 'Prescribed Officer Interventions:' : 'अनुशंसित हस्तक्षेप कार्य:'}
                </span>

                {c.recommendedActions.map((act) => (
                  <div 
                    key={act.id} 
                    className="p-3.5 rounded-lg bg-slate-50/70 border border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-50 text-red-700 border border-red-200">
                          {act.urgency}
                        </span>
                        <strong className="text-slate-900">
                          {language === 'en' ? act.title : act.titleHi}
                        </strong>
                      </div>
                      <p className="text-slate-600 mt-1">
                        {act.reason}
                      </p>
                    </div>

                    {/* Disposition Buttons (Req 21.9) */}
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {act.disposition ? (
                        <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          {act.disposition}
                        </span>
                      ) : (
                        <>
                          <button
                            onClick={() => actOnRecommendedAction(c.id, act.id, 'ACCEPTED', 'Officer accepted and scheduled step')}
                            className="px-2.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-md font-semibold flex items-center gap-1 cursor-pointer shadow-xs transition-colors"
                            title="Accept Intervention"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Accept</span>
                          </button>
                          <button
                            onClick={() => actOnRecommendedAction(c.id, act.id, 'DEFERRED', 'Deferred to next district review meeting')}
                            className="px-2.5 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded-md font-semibold flex items-center gap-1 cursor-pointer shadow-xs transition-colors"
                            title="Defer Intervention"
                          >
                            <Pause className="w-3.5 h-3.5" />
                            <span>Defer</span>
                          </button>
                          <button
                            onClick={() => actOnRecommendedAction(c.id, act.id, 'REJECTED', 'Ground settlement achieved without legal hearing')}
                            className="px-2.5 py-1.5 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-md font-semibold flex items-center gap-1 cursor-pointer transition-colors"
                            title="Reject"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
