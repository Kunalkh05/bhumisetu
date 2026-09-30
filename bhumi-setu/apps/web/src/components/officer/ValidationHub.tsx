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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="gov-surface-card p-5 sm:p-6 flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 bg-[#002642] text-white text-[10px] font-bold uppercase rounded-sm">
              Statutory Quality Engine
            </span>
            <span className="text-[11px] text-slate-500 font-mono">
              RFCTLARR 2013 &amp; PostGIS Geodesic Rules
            </span>
          </div>
          <h2 className="text-lg font-bold text-[#002642] flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-600" />
            <span>{language === 'en' ? 'Statutory Validation Engine & Resolution Ledger' : 'सांविधिक सत्यापन इंजन एवं त्रुटि निवारण पंजी'}</span>
          </h2>
          <p className="text-xs text-slate-600 mt-1 max-w-3xl">
            {language === 'en'
              ? 'Automated rule verification across ownership share consistency (1.00 tolerance), GIS geodesic bounds, and statutory compensation arithmetic.'
              : 'सह-स्वामित्व शेयर, जीआईएस भू-मापन एवं पंचाट अंकगणित का स्वचालित सत्यापन।'}
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-50 px-3 py-1.5 rounded-sm border border-slate-300 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none pr-2 cursor-pointer"
            >
              <option value="ALL">All Severities</option>
              <option value="BLOCKING">BLOCKING (Stage Halting)</option>
              <option value="MAJOR">MAJOR</option>
              <option value="MINOR">MINOR</option>
              <option value="ADVISORY">ADVISORY</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-50 px-3 py-1.5 rounded-sm border border-slate-300 text-xs">
            <select
              value={selectedResolution}
              onChange={(e) => setSelectedResolution(e.target.value)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none pr-2 cursor-pointer"
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
      <div className="gov-surface-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="gov-table-2026">
            <thead>
              <tr>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Rule Title &amp; Description</th>
                <th className="py-3 px-4">Case Ref / Entity</th>
                <th className="py-3 px-4">Observed Defect Values</th>
                <th className="py-3 px-4">Detected At</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredIssues.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 text-xs">
                    No validation issues match current filter criteria.
                  </td>
                </tr>
              ) : (
                filteredIssues.map((issue) => {
                  const isBlocking = issue.severity === 'BLOCKING';
                  const isOpen = issue.resolutionState === 'OPEN';

                  return (
                    <tr key={issue.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-xs text-[10px] font-bold ${
                          issue.severity === 'BLOCKING' ? 'bg-red-100 text-red-800 border border-red-200' :
                          issue.severity === 'MAJOR' ? 'bg-amber-100 text-amber-800 border border-amber-200' :
                          issue.severity === 'MINOR' ? 'bg-blue-100 text-blue-800 border border-blue-200' : 'bg-slate-100 text-slate-800 border border-slate-200'
                        }`}>
                          {issue.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900">{issue.ruleTitle}</div>
                        <div className="text-[11px] text-slate-500">{issue.description}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-mono font-bold text-[#002642]">{issue.caseReference}</div>
                        <div className="text-[10px] text-slate-500">{issue.affectedEntity} ({issue.entityId})</div>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-700 max-w-[220px]">
                        {issue.observedValues}
                      </td>
                      <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                        {formatDate(issue.detectedAt)}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-xs text-[10px] font-bold ${
                          isOpen ? 'bg-red-50 text-red-700 border border-red-200' :
                          issue.resolutionState === 'RESOLVED_BY_CORRECTION' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                          'bg-purple-50 text-purple-700 border border-purple-200'
                        }`}>
                          {issue.resolutionState}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {isOpen ? (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => resolveValidationIssue(issue.caseId, issue.id, 'Corrected by officer')}
                              className="px-2.5 py-1 rounded-sm bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold transition-colors cursor-pointer"
                            >
                              Resolve
                            </button>
                            <button
                              onClick={() => {
                                setWaiveModalIssue(issue);
                                setWaiverReason('');
                              }}
                              className="px-2.5 py-1 rounded-sm bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 text-xs font-bold transition-colors cursor-pointer"
                            >
                              Waive
                            </button>
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-400 font-mono">Archived in Audit</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Waiver Modal */}
      {waiveModalIssue && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs">
          <div className="bg-white rounded-sm max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <h3 className="text-base font-bold text-[#002642]">
              Authorize Issue Waiver
            </h3>
            <p className="text-xs text-slate-600">
              Rule: <strong className="text-[#002642]">{waiveModalIssue.ruleTitle}</strong>
            </p>

            <div>
              <label className="text-xs font-bold text-slate-700 mb-1 block">
                Recorded Legal Reason for Waiver (Min 8 characters):
              </label>
              <textarea
                value={waiverReason}
                onChange={(e) => setWaiverReason(e.target.value)}
                placeholder="State administrative justification..."
                className="w-full text-xs p-2.5 rounded-sm border border-slate-300 bg-white h-20 focus:outline-none focus:ring-1 focus:ring-[#002642]"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setWaiveModalIssue(null)}
                className="px-4 py-2 bg-slate-100 text-slate-700 rounded-sm text-xs font-bold hover:bg-slate-200 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmWaiver}
                disabled={waiverReason.trim().length < 8}
                className="px-4 py-2 bg-[#002642] hover:bg-[#0b3866] text-white rounded-sm text-xs font-bold transition-colors cursor-pointer disabled:opacity-50"
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
