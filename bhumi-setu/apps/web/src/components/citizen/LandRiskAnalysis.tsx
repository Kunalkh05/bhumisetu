import React, { useState } from 'react';
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  HelpCircle, 
  Filter, 
  Info, 
  ChevronRight, 
  ExternalLink,
  Search,
  Sparkles,
  FileCheck
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { PRELIMINARY_RISK_CHECKS, RiskAnalysisCheck } from '../../data/landIntelligenceData';
import { PublicTab } from '../common/GovNavigation';

export const LandRiskAnalysis: React.FC<{
  onNavigateTab: (tab: PublicTab) => void;
}> = ({ onNavigateTab }) => {
  const { language } = useApp();
  const [filterSeverity, setFilterSeverity] = useState<'ALL' | 'MEDIUM' | 'LOW'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredChecks = PRELIMINARY_RISK_CHECKS.filter(chk => {
    if (filterSeverity === 'MEDIUM' && chk.severityLevel !== 'medium') return false;
    if (filterSeverity === 'LOW' && chk.severityLevel !== 'low') return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        chk.title.toLowerCase().includes(q) ||
        chk.issue.toLowerCase().includes(q) ||
        chk.category.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const mediumCount = PRELIMINARY_RISK_CHECKS.filter(c => c.severityLevel === 'medium').length;
  const lowCount = PRELIMINARY_RISK_CHECKS.filter(c => c.severityLevel === 'low').length;

  return (
    <div className="space-y-6 text-left">
      {/* 1. Header with Mandatory Non-Legal Disclaimer */}
      <div className="bg-[#002642] text-white p-5 rounded-xs border-b-3 border-[#f37021] flex flex-wrap justify-between items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold">
              {language === 'en' ? 'Preliminary Land Record Risk Analysis' : 'प्रारंभिक भू-अभिलेख जोखिम विश्लेषण'}
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-400 text-black">
              12 STATUTORY CHECKS
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            {language === 'en'
              ? 'Multi-dimensional discrepancy detection across 12 statutory parameters to uncover variances between registered instruments, digitized revenue extracts, and cadastral maps.'
              : 'पंजीकृत विलेख, डिजिटल खतौनी एवं भू-नक्शे के मध्य १२ वैधानिक मानकों पर आधारित विसंगति विश्लेषण।'}
          </p>
        </div>

        <button
          onClick={() => onNavigateTab('REPORTS')}
          className="px-4 py-2 bg-[#f37021] hover:bg-[#d95a10] text-white font-extrabold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors"
        >
          <FileCheck className="w-3.5 h-3.5" />
          <span>Export Preliminary Report</span>
        </button>
      </div>

      {/* 2. Critical Terminology & Legal Guardrail Banner */}
      <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-xs text-xs text-amber-950 space-y-1">
        <div className="font-extrabold flex items-center gap-1.5 text-amber-900">
          <ShieldAlert className="w-4 h-4 text-amber-700" />
          <span>IMPORTANT STATUTORY NOTICE: PRELIMINARY ANALYSIS ONLY</span>
        </div>
        <p className="leading-relaxed">
          This system performs cross-registry variance scanning. It does <strong>NOT</strong> provide a legal title verdict, title guarantee, or certification of fraud/genuineness.
          Evaluations are categorized as <strong>“Low discrepancy detected”</strong> or <strong>“Verification recommended”</strong>. Citizens are advised to seek official certification from the Sub-Registrar and Taluka Inspector of Land Records (TILR) prior to concluding real estate transactions.
        </p>
      </div>

      {/* 3. Summary Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xs border border-slate-300 shadow-2xs">
          <div className="text-[11px] font-bold text-slate-500 uppercase">Total Parameters Checked</div>
          <div className="text-2xl font-black text-[#002642] mt-1">12 / 12</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Comprehensive multi-registry scanning</div>
        </div>

        <div className="bg-white p-4 rounded-xs border border-amber-300 bg-amber-50/40 shadow-2xs">
          <div className="text-[11px] font-bold text-amber-900 uppercase">Verification Recommended</div>
          <div className="text-2xl font-black text-[#c2410c] mt-1">{mediumCount} Variance Items</div>
          <div className="text-[11px] text-amber-800 mt-0.5">Area delta &amp; pending mutation timeline</div>
        </div>

        <div className="bg-white p-4 rounded-xs border border-emerald-300 bg-emerald-50/40 shadow-2xs">
          <div className="text-[11px] font-bold text-emerald-900 uppercase">Low Discrepancy Detected</div>
          <div className="text-2xl font-black text-emerald-700 mt-1">{lowCount} Parameters Clear</div>
          <div className="text-[11px] text-emerald-800 mt-0.5">ULPIN, Jurisdiction, Liens &amp; Access intact</div>
        </div>
      </div>

      {/* 4. Filter & Search Controls */}
      <div className="bg-white p-3.5 rounded-xs border border-slate-300 flex flex-wrap justify-between items-center gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-bold text-slate-700 text-xs flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" />
            <span>Filter Status:</span>
          </span>
          <button
            onClick={() => setFilterSeverity('ALL')}
            className={`px-3 py-1 rounded-xs font-bold transition-colors ${
              filterSeverity === 'ALL' ? 'bg-[#002642] text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            All (12)
          </button>
          <button
            onClick={() => setFilterSeverity('MEDIUM')}
            className={`px-3 py-1 rounded-xs font-bold transition-colors ${
              filterSeverity === 'MEDIUM' ? 'bg-[#c2410c] text-white' : 'bg-amber-100 hover:bg-amber-200 text-amber-900'
            }`}
          >
            Verification Recommended ({mediumCount})
          </button>
          <button
            onClick={() => setFilterSeverity('LOW')}
            className={`px-3 py-1 rounded-xs font-bold transition-colors ${
              filterSeverity === 'LOW' ? 'bg-[#138808] text-white' : 'bg-emerald-100 hover:bg-emerald-200 text-emerald-900'
            }`}
          >
            Low Discrepancy ({lowCount})
          </button>
        </div>

        <div className="relative w-full sm:w-64">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search checks or evidence..."
            className="w-full pl-8 pr-3 py-1.5 border border-slate-300 rounded-xs text-xs"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
        </div>
      </div>

      {/* 5. The 12 Statutory Checks Cards */}
      <div className="space-y-4">
        {filteredChecks.map((check) => {
          const isMedium = check.severityLevel === 'medium';

          return (
            <div
              key={check.id}
              className={`bg-white border rounded-xs p-4 sm:p-5 shadow-xs text-xs space-y-3 transition-all ${
                isMedium ? 'border-amber-400 bg-amber-50/20' : 'border-slate-300'
              }`}
            >
              {/* Header Strip with Check ID, Category and Standardized Severity Tag */}
              <div className="flex flex-wrap justify-between items-start gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-xs bg-slate-100 px-2 py-0.5 rounded-xs border border-slate-300 text-slate-700">
                    {check.id}
                  </span>
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      {check.category}
                    </span>
                    <h4 className="font-extrabold text-sm text-[#002642]">
                      {language === 'en' ? check.title : check.titleHi}
                    </h4>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-1 rounded-xs text-[10px] font-black uppercase tracking-wider flex items-center gap-1 ${
                    isMedium 
                      ? 'bg-amber-100 text-amber-950 border border-amber-400' 
                      : 'bg-emerald-100 text-emerald-950 border border-emerald-400'
                  }`}>
                    {isMedium ? (
                      <>
                        <AlertTriangle className="w-3 h-3 text-[#c2410c]" />
                        <span>Verification Recommended</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-3 h-3 text-emerald-700" />
                        <span>Low Discrepancy Detected</span>
                      </>
                    )}
                  </span>
                </div>
              </div>

              {/* Detailed Breakdown: Issue, Evidence, Source */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-3 p-3 bg-white border border-slate-200 rounded-xs">
                <div className="md:col-span-5 space-y-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Detected Situation / Issue</span>
                  <p className="text-slate-800 leading-snug font-medium">
                    {check.issue}
                  </p>
                </div>

                <div className="md:col-span-4 space-y-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Cross-Registry Evidence</span>
                  <p className="text-slate-700 text-[11px] leading-snug">
                    {check.evidence}
                  </p>
                </div>

                <div className="md:col-span-3 space-y-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Source Registry</span>
                  <div className="font-semibold text-slate-800 text-[11px]">
                    {check.source}
                  </div>
                </div>
              </div>

              {/* Recommended Next Verification Step */}
              <div className="p-3 bg-slate-50 rounded-xs border-l-3 border-[#002642] flex items-start gap-2">
                <Info className="w-4 h-4 text-[#002642] flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-slate-800 text-[11px]">
                    {language === 'en' ? 'Recommended Next Verification Step:' : 'अनुशंसित अगला सत्यापन कदम:'}
                  </span>
                  <p className="text-slate-600 mt-0.5 text-[11px]">
                    {language === 'en' ? check.recommendedStep : check.recommendedStepHi}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
