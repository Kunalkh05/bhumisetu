import React from 'react';
import { 
  Building2, 
  Layers, 
  Map, 
  ShieldCheck, 
  Sparkles, 
  CheckCircle2, 
  ExternalLink,
  ChevronRight,
  Info,
  BookOpen
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { PublicTab } from '../common/GovNavigation';

export const AboutPlatformView: React.FC<{
  onNavigateTab: (tab: PublicTab) => void;
}> = ({ onNavigateTab }) => {
  const { language } = useApp();

  const challengesSolved = [
    {
      title: 'State-Wise Portal Fragmentation',
      desc: 'India has 36 States & UTs with distinct land portals (Mahabhulekh, AnyRoR, Bhoomi, Bhulekh UP). BHUMISETU unifies discovery under one interface.'
    },
    {
      title: 'Separation of Textual Records & GIS Maps',
      desc: 'Textual Records of Rights (7/12, Jamabandi) and Cadastral maps (BhuNaksha) operate on isolated servers. We bridge text with spatial polygons.'
    },
    {
      title: 'Registration & Mutation Silos',
      desc: 'Deed registration at Sub-Registrar Offices (IGR) often fails to sync automatically with Talathi revenue mutations, causing lengthy delays.'
    },
    {
      title: 'Document Comprehension & Discrepancies',
      desc: 'Citizens struggle to read complex revenue terminology or detect area mismatches between historical deeds and modern drone maps.'
    },
    {
      title: 'Lack of Single Property View',
      desc: 'Our USP: “ONE PROPERTY — ONE INTELLIGENCE VIEW” brings RoR, Map, ULPIN, Deeds, Mutation, and Timeline into a single citizen card.'
    },
    {
      title: 'Navigating Central Flagship Schemes',
      desc: 'Aggregates SVAMITVA, PM-KISAN, GatiShakti, and Bhoomi Rashi so landowners can verify their statutory rights and entitlements.'
    }
  ];

  return (
    <div className="space-y-6 text-left">
      {/* 1. Header Banner */}
      <div className="bg-[#002642] text-white p-5 rounded-xs border-b-3 border-[#f37021] flex flex-wrap justify-between items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold">
              {language === 'en' ? 'About BHUMISETU Platform' : 'भूमिसेतु मंच के बारे में'}
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-400 text-black">
              SIH / ACADEMIC CIVIC-TECH PROTOTYPE
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            {language === 'en'
              ? 'A demonstration civic-tech initiative creating an AI-powered intelligence layer over India’s diverse land information systems.'
              : 'भारत की विविध भू-सूचना प्रणालियों के ऊपर एक एकीकृत एआई आसूचना मंच स्थापित करने वाली शैक्षणिक नागरिक-तकनीक पहल।'}
          </p>
        </div>

        <button
          onClick={() => onNavigateTab('PROPERTY_INTEL')}
          className="px-4 py-2 bg-[#f37021] hover:bg-[#d95a10] text-white font-extrabold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors"
        >
          <span>Explore Unified View</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 2. Core Purpose Card */}
      <div className="bg-white border border-slate-300 rounded-xs p-6 shadow-xs text-xs space-y-3">
        <h3 className="font-black text-sm sm:text-base text-[#002642] uppercase tracking-wide border-b border-slate-200 pb-2">
          Core Purpose &amp; Academic Mission
        </h3>
        <p className="text-slate-700 leading-relaxed">
          The goal of BHUMISETU is <strong>NOT</strong> to replace existing state government portals. Rather, our goal is to empower citizens with one transparent, accessible interface to discover, understand, compare, and preliminarily verify land-related information that originates from disconnected government databases.
        </p>
        <p className="text-slate-700 leading-relaxed">
          Built as an SIH-style innovation prototype, BHUMISETU adheres strictly to data governance principles: masking private citizen details, generating non-legal discrepancy evaluations, and celebrating India’s transformative Digital India Land Records Modernization Programme (DILRMP).
        </p>
      </div>

      {/* 3. The 6 Key Challenges Addressed */}
      <div className="space-y-3">
        <h3 className="font-extrabold text-sm text-[#002642] uppercase tracking-wide">
          Key Challenges Addressed by BHUMISETU
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          {challengesSolved.map((item, idx) => (
            <div key={idx} className="bg-white border border-slate-300 p-4 rounded-xs shadow-2xs space-y-1.5">
              <div className="font-bold text-[#002642] text-xs flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#138808] flex-shrink-0" />
                <span>{item.title}</span>
              </div>
              <p className="text-slate-600 text-[11px] leading-relaxed">
                {item.desc}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Product USP Banner */}
      <div className="bg-gradient-to-r from-[#002642] via-[#0b3866] to-[#00172d] text-white p-6 rounded-xs border-l-4 border-l-[#f37021] space-y-2">
        <div className="text-[10px] font-black uppercase tracking-wider text-amber-300">
          Core Architectural USP
        </div>
        <h3 className="text-base sm:text-lg font-black tracking-tight text-white">
          “ONE PROPERTY — ONE INTELLIGENCE VIEW”
        </h3>
        <p className="text-xs text-slate-200 max-w-2xl leading-relaxed">
          Instead of forcing a citizen to navigate multiple disconnected services, BHUMISETU synthesizes:
          Land Record + Cadastral Map + 14-Digit ULPIN + SRO Registration + Mutation Workflow + AI Document OCR + Property Timeline + Discrepancy Risk Analysis in one cohesive citizen view.
        </p>
      </div>
    </div>
  );
};
