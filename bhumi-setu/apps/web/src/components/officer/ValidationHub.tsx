import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  Filter, 
  FileCheck, 
  FileText, 
  HelpCircle,
  XCircle,
  Clock,
  ShieldCheck
} from 'lucide-react';
import { formatDate } from '../../lib/utils';
import { ValidationSeverity, ValidationIssue } from '../../types';

export const ValidationHub: React.FC = () => {
  const { cases, currentUser, resolveValidationIssue, waiveValidationIssue, language } = useApp();
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [selectedResolution, setSelectedResolution] = useState<string>('OPEN');

  // Collect all validation issues across all cases
  const allIssues = cases.flatMap(c => 
    c.validationIssues.map(v => ({
      ...v,
      caseReference: c.caseReference,
      caseId: c.id,
      village: c.village,
    }))
  );

  const filteredIssues = allIssues.filter(i => {
    if (selectedSeverity !== 'ALL' && i.severity !== selectedSeverity) return false;
    if (selectedResolution !== 'ALL' && i.resolutionState !== selectedResolution) return false;
    return true;
  });

  const [waiveModalIssue, setWaiveModalIssue] = useState<any>(null);
  const [waiverReason, setWaiverReason] = useState('');

  const handleConfirmWaiver = () => {
    if (!waiveModalIssue) return;
    waiveValidationIssue(waiveModalIssue.caseId, waiveModalIssue.id, waiverReason);
    setWaiveModalIssue(null);
    setWaiverReason('');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-600 dark:text-red-400" />
            {language === 'en' ? 'Statutory Validation Engine & Resolution Ledger' : 'सांविधिक सत्यापन इंजन एवं त्रुटि निवारण पंजी'}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {language === 'en'
              ? 'Automated rule verification across ownership share consistency (1.00 tolerance), GIS geodesic bounds, and award arithmetic.'
              : 'सह-स्वामित्व शेयर, जीआईएस भू-मापन एवं पंचाट अंकगणित का स्वचालित सत्यापन।'}
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-50 dark:bg-slate-800 p-1 rounded-xl border border-slate-300 dark:border-slate-700 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400 ml-1" />
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="bg-transparent font-bold text-slate-800 dark:text-slate-200 focus:outline-none pr-2"
            >
              <option value="ALL">All Severities</option>
              <option value="BLOCKING">BLOCKING (Stage Halting)</option>
              <option value="MAJOR">MAJOR</option>
              <option value="MINOR">MINOR</option>
              <option value="ADVISORY">ADVISORY</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-50 dark:bg-slate-800 p-1 rounded-xl border border-slate-300 dark:border-slate-700 text-xs">
            <select
              value={selectedResolution}
              onChange={(e) => setSelectedResolution(e.target.value)}
              className="bg-transparent font-bold text-slate-800 dark:text-slate-200 focus:outline-none pr-2"
            >
              <option value="ALL">All States</option>
              <option value="OPEN">OPEN Only</option>
              <option value="RESOLVED_BY_CORRECTION">Resolved</option>
              <option value="WAIVED">Waived</option>
            </select>
          </div>
        </div>
      </div>

      {/* Issues Queue Table */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/70 text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 font-semibold">
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Rule Title</th>
                <th className="py-3 px-4">Case Ref / Entity</th>
                <th className="py-3 px-4">Observed Defect Values</th>
                <th className="py-3 px-4">Detected At</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filteredIssues.map((issue) => {
                const isBlocking = issue.severity === 'BLOCKING';
                const isOpen = issue.resolutionState === 'OPEN';

                return (
                  <tr key={issue.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        issue.severity === 'BLOCKING' ? 'bg-red-600 text-white' :
                        issue.severity === 'MAJOR' ? 'bg-amber-500 text-white' :
                        issue.severity === 'MINOR' ? 'bg-blue-600 text-white' : 'bg-slate-500 text-white'
                      }`}>
                        {issue.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900 dark:text-slate-100">{issue.ruleTitle}</div>
                      <div className="text-[11px] text-slate-500">{issue.description}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-mono font-bold text-blue-700 dark:text-blue-300">{issue.caseReference}</div>
                      <div className="text-[10px] text-slate-500">{issue.affectedEntity} ({issue.entityId})</div>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-700 dark:text-slate-300 max-w-[220px]">
                      {issue.observedValues}
                    </td>
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                      {formatDate(issue.detectedAt)}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isOpen ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300' :
                        issue.resolutionState === 'RESOLVED_BY_CORRECTION' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' :
                        'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300'
                      }`}>
                        {issue.resolutionState}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      {isOpen ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => resolveValidationIssue(issue.caseId, issue.id, 'Corrected by officer')}
                            className="px-2.5 py-1 rounded bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold"
                          >
                            Resolve
                          </button>
                          <button
                            onClick={() => {
                              setWaiveModalIssue(issue);
                              setWaiverReason('');
                            }}
                            className="px-2.5 py-1 rounded bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 text-slate-800 dark:text-slate-200 text-xs font-bold"
                          >
                            Waive
                          </button>
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-400">Archived in Audit</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Waiver Modal */}
      {waiveModalIssue && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Authorize Issue Waiver
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Rule: <strong className="text-blue-700">{waiveModalIssue.ruleTitle}</strong>
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
                onClick={() => setWaiveModalIssue(null)}
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
    </div>
  );
};
