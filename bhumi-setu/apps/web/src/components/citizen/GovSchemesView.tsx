import React, { useState } from 'react';
import { 
  Landmark, 
  ExternalLink, 
  ShieldCheck, 
  HelpCircle, 
  Sparkles, 
  CheckCircle2, 
  Phone, 
  Search, 
  Filter, 
  Info,
  ChevronRight,
  ArrowRight,
  BookOpen
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { GOV_SCHEMES, GovScheme, SchemeCategory } from '../../data/govSchemesData';

export const GovSchemesView: React.FC = () => {
  const { language } = useApp();
  const [categoryFilter, setCategoryFilter] = useState<SchemeCategory>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedScheme, setSelectedScheme] = useState<GovScheme | null>(null);

  const filteredSchemes = GOV_SCHEMES.filter(scheme => {
    if (categoryFilter !== 'ALL' && scheme.category !== categoryFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        scheme.name.toLowerCase().includes(q) ||
        scheme.shortName.toLowerCase().includes(q) ||
        scheme.ministry.toLowerCase().includes(q) ||
        scheme.description.toLowerCase().includes(q)
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
              {language === 'en' ? 'Land & Rural Development Schemes' : 'भूमि एवं ग्रामीण विकास की प्रमुख योजनाएं'}
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-[#f37021] text-white">
              CENTRAL FLAGSHIP SCHEMES
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            {language === 'en'
              ? 'Authoritative directory of central flagship initiatives empowering rural landowners, agricultural credit, housing entitlements, and digital land modernization.'
              : 'ग्रामीण भूस्वामियों, कृषि वित्तीय संबल, पक्के आवास एवं डिजिटल भू-आधुनिकीकरण को समर्पित प्रमुख केंद्रीय योजनाओं की अधिकृत निर्देशिका।'}
          </p>
        </div>

        <div className="text-right text-xs text-slate-300">
          <div className="font-bold text-amber-300">{GOV_SCHEMES.length} Flagship Schemes</div>
          <div className="text-[10px] text-slate-400">Authentic guidelines &amp; citizen benefits</div>
        </div>
      </div>

      {/* 2. Official vs Guidance Transparency Notice */}
      <div className="bg-blue-50 border-l-4 border-[#0b3866] p-4 rounded-xs text-xs text-[#002642] space-y-1">
        <div className="font-bold flex items-center gap-1.5">
          <Info className="w-4 h-4 text-[#0b3866]" />
          <span>STATUTORY GUIDANCE TRANSPARENCY NOTICE</span>
        </div>
        <p className="leading-relaxed text-slate-700">
          Every scheme in this directory distinguishes <strong>“Official Government Information”</strong> (sourced directly from respective Ministry circulars and gazettes) from <strong>“BHUMISETU Platform Guidance”</strong> (suggested practical citizen navigation steps). We do not modify official eligibility criteria or benefit allocations.
        </p>
      </div>

      {/* 3. Filter & Search Controls */}
      <div className="bg-white p-4 rounded-xs border border-slate-300 shadow-2xs flex flex-wrap justify-between items-center gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-bold text-slate-700 mr-1 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5 text-[#002642]" />
            <span>Category:</span>
          </span>

          {[
            { id: 'ALL' as SchemeCategory, label: 'All Schemes' },
            { id: 'LAND_REVENUE' as SchemeCategory, label: 'Land & Property (SVAMITVA, ULPIN)' },
            { id: 'AGRICULTURE_DBT' as SchemeCategory, label: 'Farmer DBT (PM-KISAN)' },
            { id: 'INFRASTRUCTURE' as SchemeCategory, label: 'Infrastructure (GatiShakti, Bhoomi Rashi)' },
            { id: 'HOUSING_WATER' as SchemeCategory, label: 'Housing & Water (PMAY-G, JJM)' },
            { id: 'DIGITAL_CITIZEN' as SchemeCategory, label: 'Digital Credentials (DigiLocker)' },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setCategoryFilter(cat.id)}
              className={`px-2.5 py-1 rounded-xs font-semibold transition-colors ${
                categoryFilter === cat.id
                  ? 'bg-[#002642] text-white shadow-2xs'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search schemes by name or ministry..."
            className="w-full pl-8 pr-3 py-1.5 border border-slate-300 rounded-xs text-xs"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
        </div>
      </div>

      {/* 4. Schemes Grid Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredSchemes.map((scheme) => (
          <div
            key={scheme.id}
            className="bg-white border border-slate-300 rounded-xs shadow-xs overflow-hidden flex flex-col hover:border-[#0b3866] transition-colors"
          >
            {/* Top Scheme Ribbon */}
            <div className="bg-[#002642] text-white p-3.5 flex justify-between items-start">
              <div>
                <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-[#f37021] text-white">
                  {scheme.badge}
                </span>
                <h3 className="font-extrabold text-sm text-white mt-1.5 leading-snug">
                  {language === 'en' ? scheme.shortName : scheme.nameHi}
                </h3>
              </div>

              <div className="text-right">
                <span className="text-[10px] text-amber-300 font-mono font-bold block">{scheme.impactMetric}</span>
                <span className="text-[8px] text-slate-300 block">{scheme.impactLabel}</span>
              </div>
            </div>

            {/* Ministry & Tagline */}
            <div className="p-4 space-y-3 flex-1 text-xs">
              <div className="text-[11px] text-slate-500 font-medium">
                {scheme.ministry}
              </div>

              <p className="text-slate-700 leading-relaxed text-xs">
                {language === 'en' ? scheme.description : scheme.descriptionHi}
              </p>

              {/* Key Benefits (Official Information) */}
              <div className="p-3 bg-slate-50 rounded-xs border border-slate-200 space-y-1.5">
                <div className="text-[10px] font-bold text-slate-500 uppercase flex items-center justify-between">
                  <span>Official Citizen Benefits:</span>
                  <span className="text-[9px] text-emerald-700 font-bold">GOI VERIFIED</span>
                </div>
                <ul className="space-y-1">
                  {(language === 'en' ? scheme.keyBenefits : scheme.keyBenefitsHi).slice(0, 3).map((benefit, bIdx) => (
                    <li key={bIdx} className="flex items-start gap-1.5 text-[11px] text-slate-700">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#138808] flex-shrink-0 mt-0.5" />
                      <span>{benefit}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Eligibility & How to Access */}
              <div className="space-y-1.5 text-[11px]">
                <div>
                  <span className="font-bold text-slate-700">Eligibility: </span>
                  <span className="text-slate-600">{language === 'en' ? scheme.eligibility : scheme.eligibilityHi}</span>
                </div>
                <div>
                  <span className="font-bold text-[#002642]">How to Access: </span>
                  <span className="text-slate-600">Apply via CSC Center, State Revenue Portal, or direct scheme portal ({scheme.portalName}).</span>
                </div>
              </div>
            </div>

            {/* Bottom Actions Bar */}
            <div className="p-3 bg-slate-100 border-t border-slate-200 flex justify-between items-center text-xs">
              <span className="text-[10px] text-slate-500 flex items-center gap-1">
                <Phone className="w-3 h-3 text-[#f37021]" />
                <span>{scheme.helpline}</span>
              </span>

              <a
                href={scheme.portalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1 bg-[#002642] hover:bg-[#0b3866] text-white font-bold text-xs rounded-xs flex items-center gap-1 transition-colors"
              >
                <span>Visit Official Portal</span>
                <ExternalLink className="w-3 h-3 text-[#f37021]" />
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
