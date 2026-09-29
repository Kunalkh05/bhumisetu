import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  ShieldCheck, 
  Lock, 
  Trash2, 
  Clock, 
  UserX, 
  FileText, 
  CheckCircle2, 
  AlertCircle,
  HelpCircle,
  EyeOff
} from 'lucide-react';
import { formatDate } from '../../lib/utils';
import { MOCK_DSR_REQUESTS } from '../../data/mockData';
import { DataSubjectRequest } from '../../types';

interface DpdpPolicyItem {
  id: string;
  dataCategory: string;
  retentionTrigger: string;
  statutoryPeriodYears: number;
  calculatedErasureDate: string;
  isAutomaticPurge: boolean;
}

const DEFAULT_DPDP_POLICIES: DpdpPolicyItem[] = [
  {
    id: 'POL-01',
    dataCategory: 'OWNER_CONTACT (Phone, Email)',
    retentionTrigger: 'Section 38 Final Compensation Disbursement',
    statutoryPeriodYears: 3,
    calculatedErasureDate: '2029-08-30',
    isAutomaticPurge: true,
  },
  {
    id: 'POL-02',
    dataCategory: 'OWNER_IDENTITY (Aadhaar, Masked Bank PII)',
    retentionTrigger: 'CAG & Statutory Audit Sign-off',
    statutoryPeriodYears: 7,
    calculatedErasureDate: '2033-08-30',
    isAutomaticPurge: false,
  },
  {
    id: 'POL-03',
    dataCategory: 'MODEL_FEATURE (Anonymized Delay Vectors)',
    retentionTrigger: 'Permanent AI Baseline Drift Calibration',
    statutoryPeriodYears: 10,
    calculatedErasureDate: '2036-08-30',
    isAutomaticPurge: true,
  },
];

export const DpdpRetentionHub: React.FC = () => {
  const { language, addToast } = useApp();
  const [policies, setPolicies] = useState<DpdpPolicyItem[]>(DEFAULT_DPDP_POLICIES);
  const [dsrRequests, setDsrRequests] = useState<DataSubjectRequest[]>(MOCK_DSR_REQUESTS);

  const handleResolveDsr = (requestId: string) => {
    setDsrRequests(prev => prev.map(r => r.id === requestId ? { ...r, status: 'SERVED' } : r));
    addToast({
      type: 'success',
      message: `Citizen DSR request fulfilled. Redacted PII export certificate issued.`,
      messageHi: 'नागरिक डेटा अधिकार अनुरोध पूर्ण किया गया।',
    });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-purple-700 dark:text-purple-400" />
              {language === 'en' ? 'DPDP Act 2023 Compliance & Data Retention Lifecycle' : 'डीपीडीपी अधिनियम 2023 अनुपालन एवं डेटा प्रतिधारण'}
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">
              Statutory Privacy Mode: ENFORCED
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {language === 'en'
              ? 'Data category isolation, automated cryptographic erasure scheduling, and Citizen Data Subject Request (DSR) ledger.'
              : 'व्यक्तिगत डेटा पृथक्करण, स्वचालित विलोपन शेड्यूलिंग एवं नागरिक डेटा अधिकार प्रबंधन।'}
          </p>
        </div>
      </div>

      {/* Retention Policies Table */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <Clock className="w-4 h-4 text-purple-700" />
          <span>{language === 'en' ? 'Statutory Retention Schedules by Data Category' : 'डेटा श्रेणी अनुसार प्रतिधारण अनुसूची'}</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">
                <th className="py-2.5 px-3">Data Category</th>
                <th className="py-2.5 px-3">Retention Trigger</th>
                <th className="py-2.5 px-3">Statutory Period</th>
                <th className="py-2.5 px-3">Calculated Erasure Date</th>
                <th className="py-2.5 px-3">Enforcement Mode</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {policies.map((p) => (
                <tr key={p.id}>
                  <td className="py-2.5 px-3 font-mono font-bold text-blue-900 dark:text-blue-300">
                    {p.dataCategory}
                  </td>
                  <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">{p.retentionTrigger}</td>
                  <td className="py-2.5 px-3 font-semibold">{p.statutoryPeriodYears} Years ({p.statutoryPeriodYears * 365} Days)</td>
                  <td className="py-2.5 px-3 font-mono font-bold text-purple-700 dark:text-purple-300">
                    {formatDate(p.calculatedErasureDate)}
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                      {p.isAutomaticPurge ? 'Crypto Shredding' : 'Manual Sign-off'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Incoming Citizen DSR Ledger (Req 32.7) */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <UserX className="w-4 h-4 text-purple-700" />
          <span>{language === 'en' ? 'Citizen Data Subject Rights (DSR) Requests Ledger' : 'नागरिक डेटा अधिकार (डीएसआर) अनुरोध पंजी'}</span>
        </h3>

        <div className="space-y-3">
          {dsrRequests.map((dsr) => (
            <div key={dsr.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-xs">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-blue-700 dark:text-blue-300">{dsr.id}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200">
                    {dsr.requestType}
                  </span>
                  <strong className="text-slate-900 dark:text-slate-100">{dsr.citizenName}</strong>
                </div>
                <p className="text-slate-600 dark:text-slate-400 mt-1">
                  <strong>Case:</strong> {dsr.caseReference} {dsr.targetField && `• Target Field: ${dsr.targetField}`}
                </p>
                {dsr.assertedValue && (
                  <p className="text-[11px] text-emerald-700 dark:text-emerald-400 font-mono mt-0.5">
                    Asserted: {dsr.assertedValue}
                  </p>
                )}
                <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-3">
                  <span>Filed on: {formatDate(dsr.submittedAt)}</span>
                  <span>•</span>
                  <span>Contact: {dsr.mobile}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                {dsr.status === 'SERVED' ? (
                  <span className="px-3 py-1 rounded-lg text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Fulfilled</span>
                  </span>
                ) : (
                  <button
                    onClick={() => handleResolveDsr(dsr.id)}
                    className="px-3 py-1.5 bg-purple-700 hover:bg-purple-800 text-white rounded-lg text-xs font-bold"
                  >
                    Fulfill &amp; Sign Off
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
