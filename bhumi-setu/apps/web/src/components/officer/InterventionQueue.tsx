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
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-in fade-in">
      {/* Header Banner */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <AlertOctagon className="w-5 h-5 text-red-600 dark:text-red-400" />
            {language === 'en' ? 'Statutory Priority Intervention Queue' : 'सांविधिक प्राथमिकता हस्तक्षेप कतार'}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {language === 'en'
              ? 'Multi-factor priority ranking: Priority_Score = f(Calibrated Delay Risk, Stage Deadline Pressure, Financial Exposure).'
              : 'एआई विलंब जोखिम, समय-सीमा दबाव एवं वित्तीय दायित्व पर आधारित प्राथमिकता रैंकिंग।'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-xs font-semibold text-slate-500">Urgency:</span>
          <select
            value={filterUrgency}
            onChange={(e) => setFilterUrgency(e.target.value as any)}
            className="text-xs font-bold rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2.5 py-1.5 text-slate-800 dark:text-slate-200"
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
              className={`p-6 rounded-2xl border transition-all bg-white dark:bg-slate-900 shadow-sm ${
                isCritical 
                  ? 'border-red-300 dark:border-red-900/60 ring-1 ring-red-500/20' 
                  : 'border-slate-200 dark:border-slate-800'
              }`}
            >
              {/* Card Header */}
              <div className="flex flex-wrap justify-between items-start gap-4 pb-4 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-black text-sm ${
                    index === 0 ? 'bg-red-600 text-white shadow-md' :
                    index === 1 ? 'bg-amber-500 text-white' : 'bg-blue-800 text-white'
                  }`}>
                    #{index + 1}
                  </div>

                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-bold text-sm text-blue-900 dark:text-blue-300">
                        {c.caseReference}
                      </span>
                      <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                        ({c.village}, {c.tehsil})
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        c.riskBand === 'CRITICAL' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300' :
                        c.riskBand === 'HIGH' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {c.riskBand} ({Math.round(c.riskProbability * 100)}%)
                      </span>
                    </div>

                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-1">
                      {language === 'en' ? c.projectName : c.projectNameHi}
                    </h3>
                  </div>
                </div>

                {/* Priority Score Gauge Badge */}
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Priority Score</span>
                    <span className="text-2xl font-black font-mono text-red-600 dark:text-red-400">{c.priorityScore}/100</span>
                  </div>

                  <button
                    onClick={() => {
                      setSelectedCaseId(c.id);
                      onNavigateToCase(c.id);
                    }}
                    className="p-2 bg-blue-50 text-blue-700 hover:bg-blue-800 hover:text-white dark:bg-slate-800 dark:text-blue-300 rounded-xl font-bold text-xs flex items-center gap-1 transition-colors"
                  >
                    <span>Inspect</span>
                    <ArrowUpRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Deadline and Value Factors */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 py-3 text-xs border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <Clock className="w-4 h-4 text-slate-500" />
                  <span><strong>Stage Deadline:</strong> {formatDate(c.stageDeadline)} ({c.daysRemaining}d left)</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <IndianRupee className="w-4 h-4 text-emerald-600" />
                  <span><strong>Total Award:</strong> {formatCurrencyINR(c.totalAwardedAmount)}</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
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
                    className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">
                          {act.urgency}
                        </span>
                        <strong className="text-slate-900 dark:text-slate-100">
                          {language === 'en' ? act.title : act.titleHi}
                        </strong>
                      </div>
                      <p className="text-slate-600 dark:text-slate-400 mt-1">
                        {act.reason}
                      </p>
                    </div>

                    {/* Disposition Buttons (Req 21.9) */}
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {act.disposition ? (
                        <span className="px-2.5 py-1 rounded text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          {act.disposition}
                        </span>
                      ) : (
                        <>
                          <button
                            onClick={() => actOnRecommendedAction(c.id, act.id, 'ACCEPTED', 'Officer accepted and scheduled step')}
                            className="px-2.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold flex items-center gap-1"
                            title="Accept Intervention"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Accept</span>
                          </button>
                          <button
                            onClick={() => actOnRecommendedAction(c.id, act.id, 'DEFERRED', 'Deferred to next district review meeting')}
                            className="px-2.5 py-1.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-lg font-bold flex items-center gap-1"
                            title="Defer Intervention"
                          >
                            <Pause className="w-3.5 h-3.5" />
                            <span>Defer</span>
                          </button>
                          <button
                            onClick={() => actOnRecommendedAction(c.id, act.id, 'REJECTED', 'Ground settlement achieved without legal hearing')}
                            className="px-2.5 py-1.5 bg-red-100 hover:bg-red-200 text-red-800 dark:bg-red-950 dark:text-red-300 rounded-lg font-bold flex items-center gap-1"
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
