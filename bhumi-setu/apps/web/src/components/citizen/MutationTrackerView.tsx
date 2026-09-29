import React, { useState } from 'react';
import { 
  Search, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  UserCheck, 
  FileText, 
  Landmark, 
  ShieldCheck, 
  RefreshCw,
  Sparkles,
  ChevronRight,
  Info
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { MUTATION_TRACKING_SAMPLE } from '../../data/landIntelligenceData';
import { PublicTab } from '../common/GovNavigation';

export const MutationTrackerView: React.FC<{
  onNavigateTab: (tab: PublicTab) => void;
}> = ({ onNavigateTab }) => {
  const { language, addToast } = useApp();
  const [appIdInput, setAppIdInput] = useState('MUT-MH-2026-001245');
  const [isSearching, setIsSearching] = useState(false);
  const [activeMutation, setActiveMutation] = useState(MUTATION_TRACKING_SAMPLE);

  const handleTrack = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsSearching(true);
    setTimeout(() => {
      setIsSearching(false);
      setActiveMutation(MUTATION_TRACKING_SAMPLE);
      addToast({
        type: 'info',
        message: `Mutation status retrieved for ${appIdInput}`,
        messageHi: `नामांतरण स्थिति प्राप्त: ${appIdInput}`
      });
    }, 300);
  };

  return (
    <div className="space-y-6 text-left">
      {/* 1. Top Header Banner */}
      <div className="bg-[#002642] text-white p-5 rounded-xs border-b-3 border-[#f37021] flex flex-wrap justify-between items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold">
              {language === 'en' ? 'Track Mutation Application' : 'नामांतरण आवेदन की स्थिति जांचें'}
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-400 text-black">
              DEMONSTRATION DATA
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            {language === 'en'
              ? 'Real-time lifecycle tracking of land revenue mutation (Ferfar / Dakhil-Kharij / Intqal) from application submission to final 7/12 RoR endorsement.'
              : 'आवेदन प्रस्तुति, तलाठी जांच, राजस्व अधिकारी समीक्षा से लेकर अंतिम खतौनी निर्गमन तक की चरणबद्ध ट्रैकिंग।'}
          </p>
        </div>

        <button
          onClick={() => onNavigateTab('PROPERTY_INTEL')}
          className="px-3.5 py-1.5 bg-[#f37021] hover:bg-[#d95a10] text-white font-bold text-xs rounded-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Property Intelligence View</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 2. Search Application Box */}
      <div className="bg-white border border-slate-300 rounded-xs p-5 shadow-xs text-xs">
        <form onSubmit={handleTrack} className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[260px]">
            <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
              {language === 'en' ? 'Mutation Application ID / Acknowledgement Token' : 'नामांतरण आवेदन क्रमांक'} <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={appIdInput}
              onChange={(e) => setAppIdInput(e.target.value)}
              placeholder="e.g. MUT-MH-2026-001245"
              className="w-full p-2.5 border border-slate-300 rounded-xs font-mono font-bold text-sm text-[#002642]"
            />
          </div>

          <button
            type="submit"
            disabled={isSearching}
            className="px-6 py-2.5 bg-[#002642] hover:bg-[#0b3866] text-white font-bold text-xs rounded-xs flex items-center gap-2 shadow-xs transition-colors"
          >
            {isSearching ? <RefreshCw className="w-4 h-4 animate-spin text-amber-300" /> : <Search className="w-4 h-4 text-[#f37021]" />}
            <span>{language === 'en' ? 'Track Status' : 'स्थिति देखें'}</span>
          </button>

          <button
            type="button"
            onClick={() => setAppIdInput('MUT-MH-2026-001245')}
            className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xs border border-slate-200 transition-colors"
          >
            Load Sample Token
          </button>
        </form>
      </div>

      {/* 3. Mutation Application Detail Header */}
      <div className="bg-white border border-slate-300 rounded-xs p-5 shadow-xs text-xs space-y-4">
        <div className="flex flex-wrap justify-between items-center gap-3 border-b border-slate-200 pb-3">
          <div>
            <span className="text-[10px] font-bold text-slate-400 uppercase">Tracked Application</span>
            <div className="font-mono font-black text-base text-[#002642] mt-0.5">
              {activeMutation.applicationId}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Property ID: <span className="font-mono font-semibold">{activeMutation.propertyId}</span> • ULPIN: <span className="font-mono">{activeMutation.ulpin}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-amber-100 text-amber-950 border border-amber-300 rounded-xs font-bold text-xs flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
              <span>Stage 04: Revenue Officer Review (In Progress)</span>
            </span>
          </div>
        </div>

        {/* 4. Sequential 5-Stage Mutation Flow */}
        <div className="space-y-4 pt-2">
          {activeMutation.steps.map((step) => {
            const isCompleted = step.status === 'Completed';
            const isInProgress = step.status === 'In Progress';
            const isPending = step.status === 'Pending';
            const isActionRequired = step.status === 'Action Required';

            return (
              <div
                key={step.stepNumber}
                className={`p-4 rounded-xs border transition-all ${
                  isInProgress
                    ? 'border-amber-400 bg-amber-50/50 shadow-xs'
                    : isCompleted
                    ? 'border-slate-200 bg-white'
                    : 'border-slate-200 bg-slate-50 opacity-80'
                }`}
              >
                <div className="flex flex-wrap justify-between items-center gap-2">
                  <div className="flex items-center gap-3">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs ${
                      isCompleted 
                        ? 'bg-[#138808] text-white' 
                        : isInProgress 
                        ? 'bg-[#f37021] text-white animate-pulse' 
                        : 'bg-slate-200 text-slate-600'
                    }`}>
                      {isCompleted ? '✓' : `0${step.stepNumber}`}
                    </div>

                    <div>
                      <h4 className="font-bold text-xs sm:text-sm text-[#002642]">
                        {language === 'en' ? step.title : step.titleHi}
                      </h4>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        Officer / Authority: <strong className="text-slate-700">{step.responsibleOfficer}</strong>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-500 font-mono">
                      {step.date}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-xs text-[10px] font-black uppercase tracking-wider ${
                      isCompleted
                        ? 'bg-emerald-100 text-emerald-950 border border-emerald-300'
                        : isInProgress
                        ? 'bg-amber-100 text-amber-950 border border-amber-400'
                        : isActionRequired
                        ? 'bg-rose-100 text-rose-950 border border-rose-400'
                        : 'bg-slate-100 text-slate-600'
                    }`}>
                      {step.status}
                    </span>
                  </div>
                </div>

                <p className="mt-2 text-slate-600 text-[11px] pl-10 leading-relaxed">
                  {step.details}
                </p>
              </div>
            );
          })}
        </div>

        {/* Notice Info Box */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs text-[11px] text-slate-600 flex items-start gap-2">
          <Info className="w-4 h-4 text-[#002642] flex-shrink-0 mt-0.5" />
          <div>
            <strong>Citizen Charter Timeline:</strong> Standard processing timeline for undisputed inheritance/partition mutations under MLRC Section 149 is 30 to 45 statutory working days.
          </div>
        </div>
      </div>
    </div>
  );
};
