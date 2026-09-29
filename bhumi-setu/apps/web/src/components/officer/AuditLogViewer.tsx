import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  ShieldCheck, 
  Search, 
  Filter, 
  Code, 
  Terminal, 
  Clock, 
  User, 
  Lock, 
  FileText,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { formatDate } from '../../lib/utils';
import { AuditEvent } from '../../types';

export const AuditLogViewer: React.FC = () => {
  const { auditLog, language } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const filteredLogs = auditLog.filter(log => {
    const q = searchQuery.toLowerCase();
    const action = (log.actionType || log.eventType || '').toLowerCase();
    const actor = (log.actorName || '').toLowerCase();
    const entity = (log.entityType || '').toLowerCase();
    const entityId = (log.entityId || '').toLowerCase();
    return action.includes(q) || actor.includes(q) || entity.includes(q) || entityId.includes(q);
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              {language === 'en' ? 'Statutory Immutable Audit Trail & Provenance Ledger' : 'सांविधिक अपरिवर्तनीय ऑडिट ट्रेल एवं लॉग'}
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
              Append-Only (WORM Compliant)
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {language === 'en'
              ? 'Every stage progression, OCR human verification, objection disposal, compensation disbursement, and issue waiver is cryptographically signed and permanently logged.'
              : 'प्रत्येक चरण प्रगति, ओसीआर सुधार, आपत्ति निराकरण एवं मुआवजा भुगतान का क्रिप्टोग्राफ़िक हस्ताक्षर युक्त लॉग।'}
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder={language === 'en' ? 'Search event, actor, entity...' : 'लॉग खोजें...'}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 pr-3 py-1.5 text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-blue-500 w-56 sm:w-64"
          />
        </div>
      </div>

      {/* Log Feed */}
      <div className="space-y-3">
        {filteredLogs.map((log) => {
          const isExpanded = expandedLogId === log.id;

          return (
            <div
              key={log.id}
              className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-4 text-xs transition-all hover:border-slate-300"
            >
              <div className="flex flex-wrap justify-between items-start gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono font-bold text-blue-900 dark:text-blue-300 bg-blue-50 dark:bg-blue-950 px-2 py-0.5 rounded">
                      {log.actionType || log.eventType}
                    </span>
                    <span className="text-slate-500">•</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {log.entityType} ({log.entityId})
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-slate-500 text-[11px] pt-1">
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3 text-slate-400" />
                      <strong>Actor:</strong> {log.actorName} ({log.actorRole})
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {log.timestamp ? new Date(log.timestamp).toLocaleString('en-IN') : log.occurrenceTime || 'Recent'}
                    </span>
                    {log.ipAddress && <span className="font-mono text-slate-400">IP: {log.ipAddress}</span>}
                  </div>
                </div>

                <button
                  onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 text-xs font-bold flex items-center gap-1 transition-colors"
                >
                  <Code className="w-3 h-3" />
                  <span>{isExpanded ? 'Hide Payload' : 'Inspect JSON'}</span>
                  {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
              </div>

              {/* JSON Payload Inspection Drawer */}
              {isExpanded && (
                <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                  <pre className="p-3 bg-slate-950 text-emerald-400 rounded-xl font-mono text-[11px] overflow-x-auto">
                    {JSON.stringify(log.payload, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
