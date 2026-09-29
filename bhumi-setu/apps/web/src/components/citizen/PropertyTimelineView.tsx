import React from 'react';
import { 
  Clock, 
  Calendar, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  Landmark, 
  ShieldCheck, 
  Building2, 
  ChevronRight,
  ExternalLink,
  Sparkles
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { PROPERTY_TIMELINE_SAMPLE, ChronologicalEvent } from '../../data/landIntelligenceData';
import { PublicTab } from '../common/GovNavigation';

export const PropertyTimelineView: React.FC<{
  onNavigateTab: (tab: PublicTab) => void;
}> = ({ onNavigateTab }) => {
  const { language } = useApp();

  return (
    <div className="space-y-6 text-left">
      {/* 1. Header Banner */}
      <div className="bg-[#002642] text-white p-5 rounded-xs border-b-3 border-[#f37021] flex flex-wrap justify-between items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold">
              {language === 'en' ? 'Property Chronological Timeline' : 'संपत्ति कालानुक्रमिक समयरेखा'}
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-400 text-black">
              2018 – 2026 AUDIT TRAIL
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            {language === 'en'
              ? 'Complete chronological history from original registration deed, succession mutations, drone resurvey, to active 2026 notice.'
              : 'मूल पंजीकृत विलेख से लेकर नामांतरण, ड्रोन पुनर्सर्वेक्षण एवं वर्तमान २०२६ सूचना तक का संपूर्ण कालानुक्रमिक इतिहास।'}
          </p>
        </div>

        <button
          onClick={() => onNavigateTab('MUTATION')}
          className="px-3.5 py-1.5 bg-[#f37021] hover:bg-[#d95a10] text-white font-bold text-xs rounded-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Track Active Mutation (2026)</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 2. Visual Chronological Flow */}
      <div className="bg-white border border-slate-300 rounded-xs p-6 shadow-sm">
        <div className="relative border-l-2 border-slate-300 ml-4 sm:ml-8 pl-6 sm:pl-8 space-y-8">
          {PROPERTY_TIMELINE_SAMPLE.map((evt, idx) => {
            const isLatest = idx === PROPERTY_TIMELINE_SAMPLE.length - 1;

            return (
              <div key={idx} className="relative group">
                {/* Node Milestone Dot */}
                <div className={`absolute -left-[35px] sm:-left-[43px] top-1 w-6 h-6 rounded-full border-2 flex items-center justify-center text-[10px] font-bold ${
                  isLatest
                    ? 'bg-[#f37021] border-white text-white shadow-md animate-pulse ring-4 ring-orange-200'
                    : 'bg-[#002642] border-white text-white'
                }`}>
                  {idx + 1}
                </div>

                {/* Event Card */}
                <div className={`p-4 rounded-xs border text-xs transition-all ${
                  isLatest
                    ? 'bg-orange-50/70 border-orange-300 shadow-sm'
                    : 'bg-slate-50 hover:bg-white border-slate-200 shadow-2xs'
                }`}>
                  {/* Top Bar: Year Badge, Category, Date & Status */}
                  <div className="flex flex-wrap justify-between items-center gap-2 border-b border-slate-200 pb-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-0.5 rounded-xs font-mono font-black text-xs ${
                        isLatest ? 'bg-[#f37021] text-white' : 'bg-[#002642] text-white'
                      }`}>
                        {evt.year}
                      </span>
                      <span className="text-slate-500 font-bold text-[11px]">
                        {evt.date}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] uppercase font-bold text-slate-400">
                        {evt.category}
                      </span>
                      <span className={`px-2 py-0.5 rounded-xs text-[10px] font-bold ${
                        evt.status === 'Completed' || evt.status === 'Certified'
                          ? 'bg-emerald-100 text-emerald-900 border border-emerald-300'
                          : 'bg-amber-100 text-amber-900 border border-amber-300'
                      }`}>
                        {evt.status}
                      </span>
                    </div>
                  </div>

                  {/* Title & Description */}
                  <div className="mt-2.5 space-y-1">
                    <h4 className="font-extrabold text-sm text-[#002642]">
                      {language === 'en' ? evt.title : evt.titleHi}
                    </h4>
                    <p className="text-slate-600 leading-relaxed text-xs">
                      {evt.description}
                    </p>
                  </div>

                  {/* Footer Strip: Source Department & Statutory Reference ID */}
                  <div className="mt-3 pt-2 border-t border-slate-200 flex flex-wrap justify-between items-center text-[11px] text-slate-500">
                    <div>
                      Source: <strong className="text-slate-700">{evt.source}</strong>
                    </div>
                    <div className="font-mono text-[10px] text-slate-600 font-semibold">
                      Ref: {evt.referenceId}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Bottom Summary Info */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-xs text-xs text-[#002642] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-[#138808] flex-shrink-0" />
          <span>
            Chain of Title Integrity: Verified 4 historical mutation cycles spanning 2018 through 2026 with no broken links.
          </span>
        </div>

        <button
          onClick={() => onNavigateTab('PROPERTY_INTEL')}
          className="px-3.5 py-1.5 bg-[#002642] hover:bg-[#0b3866] text-white font-bold text-xs rounded-xs transition-colors"
        >
          Back to Property Overview
        </button>
      </div>
    </div>
  );
};
