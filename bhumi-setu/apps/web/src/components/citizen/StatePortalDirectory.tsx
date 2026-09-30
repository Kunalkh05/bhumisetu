import React, { useState } from 'react';
import { 
  Search, 
  MapPin, 
  ExternalLink, 
  Landmark, 
  Phone, 
  ShieldCheck, 
  CheckCircle2, 
  FileText, 
  Map, 
  Filter,
  Sparkles,
  Layers
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { STATE_LAND_DIRECTORY, StatePortalInfo } from '../../data/landIntelligenceData';

export const StatePortalDirectory: React.FC = () => {
  const { language } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'ALL' | 'State' | 'Union Territory'>('ALL');

  const filteredStates = STATE_LAND_DIRECTORY.filter(item => {
    if (categoryFilter !== 'ALL' && item.category !== categoryFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        item.stateName.toLowerCase().includes(q) ||
        item.landRecordsPortal.toLowerCase().includes(q) ||
        item.rorName.toLowerCase().includes(q) ||
        item.stateCode.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6 text-left">
      {/* 1. Header Banner */}
      <div className="bg-[#002642] text-white p-5 rounded-xs border-b-3 border-[#f37021] flex flex-wrap justify-between items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold">
              {language === 'en' ? 'State Land Information Directory' : 'राज्य भू-अभिलेख एवं सेवा निर्देशिका'}
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-[#138808] text-white">
              VERIFIED PORTALS
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            {language === 'en'
              ? 'Comprehensive national directory indexing official Land Records (Bhulekh), RoR (7/12, Khatauni, RTC), Cadastral Maps (BhuNaksha), and Property Registration systems across all Indian States & Union Territories.'
              : 'सभी भारतीय राज्यों एवं केंद्र शासित प्रदेशों के आधिकारिक भू-अभिलेख (भूलेख), खतौनी, भू-नक्शा एवं विलेख पंजीयन पोर्टलों की सत्यापित राष्ट्रीय निर्देशिका।'}
          </p>
        </div>

        <div className="text-right text-xs text-slate-300">
          <div className="font-bold text-amber-300">{STATE_LAND_DIRECTORY.length} Jurisdictions Configured</div>
          <div className="text-[10px] text-slate-400">Authentic state government gateways</div>
        </div>
      </div>

      {/* 2. Filter & Search Controls */}
      <div className="bg-white p-4 rounded-xs border border-slate-300 shadow-2xs flex flex-wrap justify-between items-center gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-bold text-slate-700 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5 text-[#002642]" />
            <span>Category:</span>
          </span>
          <button
            onClick={() => setCategoryFilter('ALL')}
            className={`px-3 py-1 rounded-xs font-bold transition-colors ${
              categoryFilter === 'ALL' ? 'bg-[#002642] text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            All States &amp; UTs
          </button>
          <button
            onClick={() => setCategoryFilter('State')}
            className={`px-3 py-1 rounded-xs font-bold transition-colors ${
              categoryFilter === 'State' ? 'bg-[#002642] text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            States
          </button>
          <button
            onClick={() => setCategoryFilter('Union Territory')}
            className={`px-3 py-1 rounded-xs font-bold transition-colors ${
              categoryFilter === 'Union Territory' ? 'bg-[#002642] text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            Union Territories
          </button>
        </div>

        <div className="relative w-full sm:w-72">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search state, portal name, 7/12, RTC..."
            className="w-full pl-8 pr-3 py-1.5 border border-slate-300 rounded-xs text-xs"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
        </div>
      </div>

      {/* 3. States Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredStates.map((state) => (
          <div
            key={state.stateCode}
            className="bg-white border border-slate-300 rounded-xs p-5 shadow-xs text-xs space-y-3 hover:border-[#0b3866] transition-colors"
          >
            {/* Top State Header */}
            <div className="flex justify-between items-start border-b border-slate-200 pb-2.5">
              <div>
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-xs bg-[#002642] text-white font-mono font-bold text-xs flex items-center justify-center">
                    {state.stateCode}
                  </span>
                  <h3 className="font-extrabold text-base text-[#002642]">
                    {state.stateName}
                  </h3>
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  Capital: {state.capital} • Category: {state.category}
                </div>
              </div>

              <span className="px-2 py-0.5 rounded-xs text-[9px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
                {state.digitizationStatus}
              </span>
            </div>

            {/* Department Name */}
            <div className="text-[11px] text-slate-600">
              Department: <strong className="text-slate-800">{state.departmentName}</strong>
            </div>

            {/* Service Gateways Grid */}
            <div className="space-y-2 bg-slate-50 p-3 rounded-xs border border-slate-200">
              {/* Land Records / RoR */}
              <div className="flex justify-between items-center">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Land Records &amp; RoR</span>
                  <div className="font-bold text-slate-800">{state.landRecordsPortal} ({state.rorName})</div>
                </div>
                {state.landRecordsUrl ? (
                  <a
                    href={state.landRecordsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 hover:bg-slate-200 rounded-xs text-[#002642] transition-colors flex items-center gap-1 font-bold text-[11px]"
                    title="Open Official Portal"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-[#f37021]" />
                    <span>Open</span>
                  </a>
                ) : (
                  <span className="text-[10px] text-slate-400 italic">Official link not configured</span>
                )}
              </div>

              {/* Cadastral Map */}
              <div className="flex justify-between items-center pt-1 border-t border-slate-200">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Cadastral GIS (BhuNaksha)</span>
                  <div className="font-semibold text-slate-700">{state.cadastralMapPortal}</div>
                </div>
                {state.cadastralMapUrl ? (
                  <a
                    href={state.cadastralMapUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 hover:bg-slate-200 rounded-xs text-[#002642] transition-colors flex items-center gap-1 font-bold text-[11px]"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-[#f37021]" />
                    <span>Map</span>
                  </a>
                ) : (
                  <span className="text-[10px] text-slate-400 italic">Official link not configured</span>
                )}
              </div>

              {/* Registration */}
              <div className="flex justify-between items-center pt-1 border-t border-slate-200">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Deed Registration (IGR / SRO)</span>
                  <div className="font-semibold text-slate-700">{state.registrationPortal}</div>
                </div>
                {state.registrationUrl ? (
                  <a
                    href={state.registrationUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 hover:bg-slate-200 rounded-xs text-[#002642] transition-colors flex items-center gap-1 font-bold text-[11px]"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-[#f37021]" />
                    <span>Portal</span>
                  </a>
                ) : (
                  <span className="text-[10px] text-slate-400 italic">Official link not configured</span>
                )}
              </div>

              {/* Mutation */}
              <div className="pt-1 border-t border-slate-200">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Mutation Services (Intqal / Ferfar)</span>
                <div className="text-slate-800 font-medium">{state.mutationPortal}</div>
              </div>
            </div>

            {/* Helpline Footer */}
            <div className="flex justify-between items-center text-[10px] text-slate-500 pt-1">
              <span className="flex items-center gap-1">
                <Phone className="w-3 h-3 text-[#f37021]" />
                <span>Helpline: {state.tollFree}</span>
              </span>
              <span className="text-emerald-700 font-semibold">NIC / State Govt Hosted</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
