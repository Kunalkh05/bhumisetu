import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  Search, 
  MapPin, 
  Map,
  Calendar, 
  FileText, 
  IndianRupee, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  Send, 
  Upload, 
  ShieldCheck, 
  Download, 
  User, 
  Phone, 
  ExternalLink,
  ChevronRight,
  Info,
  Layers,
  Filter,
  RefreshCw,
  FolderKanban,
  Building,
  Check,
  HelpCircle,
  BookOpen,
  Landmark,
  Eye,
  FileCheck,
  Share2,
  Printer,
  Sparkles,
  Pause,
  Play,
  ChevronLeft,
  ArrowRight,
  ShieldAlert,
  Globe,
  Activity,
  Award,
  Zap,
  ArrowUpRight
} from 'lucide-react';
import { formatCurrencyINR, formatDate } from '../../lib/utils';
import { GisMapViewer } from '../officer/GisMapViewer';
import { PublicTab } from '../common/GovNavigation';
import { MOCK_PROJECTS } from '../../data/mockData';
import { 
  GovSchemeHeroCarousel, 
  GovSchemeAdGrid, 
  GovSchemeLeaderboardBanner, 
  GovSchemeSidebarAd, 
  GovSchemeModal,
  getThemeClasses 
} from '../common/GovSchemeBanners';
import { GigwSchemeScrollBanner } from '../common/GigwSchemeScrollBanner';
import { GOV_SCHEMES, GovScheme, SchemeCategory } from '../../data/govSchemesData';
import { NationalEmblem } from '../common/NationalEmblem';
import { HeroRotatingBanner } from './HeroRotatingBanner';
import { UnifiedLandSearch } from '../citizen/UnifiedLandSearch';
import { PropertyIntelligenceDashboard } from '../citizen/PropertyIntelligenceDashboard';
import { AiDocumentVerification } from '../citizen/AiDocumentVerification';
import { LandRiskAnalysis } from '../citizen/LandRiskAnalysis';
import { PropertyMapIntelligence } from '../citizen/PropertyMapIntelligence';
import { PropertyTimelineView } from '../citizen/PropertyTimelineView';
import { MutationTrackerView } from '../citizen/MutationTrackerView';
import { StatePortalDirectory } from '../citizen/StatePortalDirectory';
import { GovSchemesView } from '../citizen/GovSchemesView';
import { ReportGeneratorView } from '../citizen/ReportGeneratorView';
import { HelpHowItWorksView } from '../citizen/HelpHowItWorksView';
import { AboutPlatformView } from '../citizen/AboutPlatformView';
import { SAMPLE_PROPERTY_DEMO, DemoProperty, STATE_LAND_DIRECTORY } from '../../data/landIntelligenceData';

interface PublicPortalProps {
  activeTab: PublicTab;
  setActiveTab: (tab: PublicTab) => void;
  onNavigateToOfficerCase?: (caseId: string) => void;
  onOpenAiChat?: () => void;
}

export const PublicPortal: React.FC<PublicPortalProps> = ({ 
  activeTab, 
  setActiveTab,
  onNavigateToOfficerCase,
  onOpenAiChat
}) => {
  const { cases, submitCitizenObjection, language, addToast } = useApp();
  const [selectedProperty, setSelectedProperty] = useState<DemoProperty>(SAMPLE_PROPERTY_DEMO);
  const [liveNewsIndex, setLiveNewsIndex] = useState(0);
  const [isLiveNewsPaused, setIsLiveNewsPaused] = useState(false);
  const [activePreviewTab, setActivePreviewTab] = useState<'ROR' | 'MAP' | 'MUTATION' | 'RISK'>('ROR');
  const [ecosystemTab, setEcosystemTab] = useState<'SCHEMES' | 'STATES' | 'NOTICES' | 'RIGHTS'>('SCHEMES');

  const LIVE_ANNOUNCEMENTS = [
    {
      id: '1',
      tag: 'PM-KISAN DBT',
      text: '17th Installment of ₹20,000+ Cr credited directly to 11.8 Cr registered farmers via PFMS Aadhaar bridge.',
      textHi: '११.८ करोड़ पंजीकृत किसानों के बैंक खातों में १७वीं किस्त के ₹२०,०००+ करोड़ सीधे पीएफएमएस द्वारा अंतरित।',
      linkTab: 'SCHEMES' as PublicTab
    },
    {
      id: '2',
      tag: 'SVAMITVA CADASTRE',
      text: 'Sub-centimeter drone mapping completed across 3.15 Lakh+ villages; 1.65 Cr+ digital property cards generated.',
      textHi: '३.१५ लाख+ गाँवों में उप-सेंटीमीटर ड्रोन सर्वेक्षण पूर्ण; १.६५ करोड़+ डिजिटल संपत्ति पत्रक जारी।',
      linkTab: 'SCHEMES' as PublicTab
    },
    {
      id: '3',
      tag: 'RFCTLARR ACT 2013',
      text: 'Statutory 100% Solatium & 12% additional interest per annum mandated on all Section 11 gazette acquisitions.',
      textHi: 'धारा ११ राजपत्र अधिसूचनाओं पर अनिवार्य १००% तोषण एवं १२% वार्षिक ब्याज की कानूनी गारंटी।',
      linkTab: 'NOTICES' as PublicTab
    },
    {
      id: '4',
      tag: 'PM GATISHAKTI NMP',
      text: 'National Cadastral Layer integrated across 28 States & 8 UTs for real-time highway & rail corridor alignment.',
      textHi: '२८ राज्यों व ८ केंद्रशासित प्रदेशों में राष्ट्रीय भू-मानचित्र गलियारा समन्वय लाइव।',
      linkTab: 'GIS_MAP' as PublicTab
    }
  ];

  React.useEffect(() => {
    if (isLiveNewsPaused) return;
    const interval = setInterval(() => {
      setLiveNewsIndex(prev => (prev + 1) % LIVE_ANNOUNCEMENTS.length);
    }, 5500);
    return () => clearInterval(interval);
  }, [isLiveNewsPaused, LIVE_ANNOUNCEMENTS.length]);

  // Search State
  const [searchState, setSearchState] = useState('Maharashtra');
  const [searchDistrict, setSearchDistrict] = useState('ALL');
  const [searchTehsil, setSearchTehsil] = useState('ALL');
  const [searchVillage, setSearchVillage] = useState('ALL');
  const [searchProject, setSearchProject] = useState('ALL');
  const [searchGatNumber, setSearchGatNumber] = useState('');
  const [searchCaseRef, setSearchCaseRef] = useState('');
  const [selectedCaseDetailId, setSelectedCaseDetailId] = useState<string | null>(null);

  // Tabbed Widget State for S3WaaS Homepage
  const [homeNoticeTab, setHomeNoticeTab] = useState<'GAZETTE' | 'HEARINGS' | 'ORDERS'>('GAZETTE');

  // Section 15 Objection Form State
  const [objectorName, setObjectorName] = useState('Tukaram Bapu Jadhav');
  const [objectorContact, setObjectorContact] = useState('+91 98231 44521');
  const [objectorAadhaar, setObjectorAadhaar] = useState('XXXX-XXXX-4819');
  const [surveyGat, setSurveyGat] = useState('142/A');
  const [selectedCaseForObjection, setSelectedCaseForObjection] = useState(cases[0].id);
  const [groundsCategory, setGroundsCategory] = useState<'Valuation & Compensation' | 'Measurement / Boundary Dispute' | 'Ownership / Title Claim' | 'Environmental / Religious Structure'>('Valuation & Compensation');
  const [objectionSubstance, setObjectionSubstance] = useState('');
  const [attachedFile, setAttachedFile] = useState<string | null>('comparable_registered_sale_instance_2025.pdf');
  const [submittedTrackingId, setSubmittedTrackingId] = useState<string | null>(null);

  // Objection Tracker State
  const [trackAckNumber, setTrackAckNumber] = useState('OBJ-2026-8812');
  const [trackResult, setTrackResult] = useState<{
    id: string;
    objector: string;
    caseRef: string;
    hearingDate: string;
    officer: string;
    status: string;
    remarks: string;
  } | null>(null);

  // FAQ Accordion State
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  // Schemes Tab & Citizen Entitlement Advisor State
  const [schemeCategoryFilter, setSchemeCategoryFilter] = useState<SchemeCategory>('ALL');
  const [schemeSearchQuery, setSchemeSearchQuery] = useState('');
  const [selectedSchemeDetail, setSelectedSchemeDetail] = useState<GovScheme | null>(null);
  const [advisorProfile, setAdvisorProfile] = useState<'FARMER' | 'ABADI' | 'ACQUIRED' | 'HOUSELESS'>('FARMER');
  const [advisorState, setAdvisorState] = useState('Maharashtra');
  const [advisorResultOpen, setAdvisorResultOpen] = useState(false);

  // Filtered cases based on search criteria
  const filteredCases = cases.filter(c => {
    if (searchDistrict !== 'ALL' && c.district !== searchDistrict) return false;
    if (searchTehsil !== 'ALL' && c.tehsil !== searchTehsil) return false;
    if (searchVillage !== 'ALL' && c.village !== searchVillage) return false;
    if (searchProject !== 'ALL' && c.projectId !== searchProject) return false;
    if (searchCaseRef && !c.caseReference.toLowerCase().includes(searchCaseRef.toLowerCase())) return false;
    if (searchGatNumber && !c.parcels.some(p => p.surveyNumber.toLowerCase().includes(searchGatNumber.toLowerCase()))) return false;
    return true;
  });

  const handleResetSearch = () => {
    setSearchDistrict('ALL');
    setSearchTehsil('ALL');
    setSearchVillage('ALL');
    setSearchProject('ALL');
    setSearchGatNumber('');
    setSearchCaseRef('');
  };

  const handleSubmitObjection = (e: React.FormEvent) => {
    e.preventDefault();
    if (!objectionSubstance.trim()) {
      addToast({
        type: 'warning',
        message: 'Please provide grounds and substance for the objection under Section 15.',
      });
      return;
    }

    const trackingId = submitCitizenObjection(selectedCaseForObjection, {
      objectorName,
      objectorContact,
      surveyNumber: surveyGat,
      groundsCategory,
      substance: objectionSubstance,
    });

    setSubmittedTrackingId(trackingId);
    setObjectionSubstance('');
    addToast({
      type: 'success',
      message: `Section 15 Objection registered successfully. Ack ID: ${trackingId}`,
      messageHi: `आपत्ति सफलतापूर्वक दर्ज की गई। पावती क्रमांक: ${trackingId}`,
    });
  };

  const handleTrackObjection = (e: React.FormEvent) => {
    e.preventDefault();
    if (!trackAckNumber.trim()) return;

    setTrackResult({
      id: trackAckNumber.toUpperCase(),
      objector: 'Tukaram Bapu Jadhav (Survey Gat No. 142/A)',
      caseRef: 'MH-PUN-2026-LA-001 (Pune-Bengaluru Expressway)',
      hearingDate: '15-Sept-2026 at 11:00 AM',
      officer: 'Shri R. K. Shinde, Sub-Divisional Officer / LAO Haveli',
      status: 'HEARING_SCHEDULED',
      remarks: 'Notice served under Section 15(2). Valuation report requisitioned from District Town Planner.',
    });
  };

  const selectedCaseForModal = cases.find(c => c.id === selectedCaseDetailId);

  return (
    <div id="main-content" className="w-full bg-[#f8fafc] text-slate-800 text-xs min-h-screen">
      {/* 1. Sovereign 2026 DPI Live Stream (Clean, High-Tech, Accessible - No 90s Marquee) */}
      <div className="bg-[#00172d] border-b border-slate-800 text-slate-200 py-2.5 px-4 sm:px-6 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 flex-1 min-w-[280px]">
            {/* Live Indicator Badge */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gradient-to-r from-[#f37021] to-[#e65100] text-white text-[10px] font-black uppercase tracking-wider shadow-xs flex-shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping"></span>
              <span>{language === 'en' ? 'LIVE DPI STREAM' : 'लाइव अपडेट'}</span>
            </div>

            {/* Current Announcement Chip */}
            <div className="flex items-center gap-2 overflow-hidden flex-1">
              <span className="px-2 py-0.5 rounded-md bg-white/10 text-amber-300 font-mono text-[10px] font-bold uppercase tracking-wider flex-shrink-0 hidden md:inline">
                {LIVE_ANNOUNCEMENTS[liveNewsIndex].tag}
              </span>
              <p className="text-[11px] text-slate-200 truncate font-medium">
                {language === 'en' ? LIVE_ANNOUNCEMENTS[liveNewsIndex].text : LIVE_ANNOUNCEMENTS[liveNewsIndex].textHi}
              </p>
            </div>

            {/* Carousel Controls */}
            <div className="flex items-center gap-1 flex-shrink-0 pl-1">
              <button
                type="button"
                onClick={() => setLiveNewsIndex((prev) => (prev - 1 + LIVE_ANNOUNCEMENTS.length) % LIVE_ANNOUNCEMENTS.length)}
                className="p-1 rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                title="Previous Update"
                aria-label="Previous Update"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setIsLiveNewsPaused(!isLiveNewsPaused)}
                className="p-1 rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                title={isLiveNewsPaused ? "Play Stream" : "Pause Stream"}
                aria-label={isLiveNewsPaused ? "Play Stream" : "Pause Stream"}
              >
                {isLiveNewsPaused ? <Play className="w-3.5 h-3.5 text-amber-300" /> : <Pause className="w-3.5 h-3.5" />}
              </button>
              <button
                type="button"
                onClick={() => setLiveNewsIndex((prev) => (prev + 1) % LIVE_ANNOUNCEMENTS.length)}
                className="p-1 rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                title="Next Update"
                aria-label="Next Update"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Quick Direct Link Chips */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => setActiveTab('SCHEMES')}
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/10 hover:bg-white/20 border border-white/20 text-white text-[11px] font-bold rounded-full transition-all cursor-pointer shadow-xs"
            >
              <Landmark className="w-3.5 h-3.5 text-amber-300" />
              <span>{language === 'en' ? 'Flagship Schemes (9)' : 'प्रमुख योजनाएं'}</span>
            </button>
            <button
              onClick={() => setActiveTab('NOTICES')}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 bg-white/10 hover:bg-white/20 border border-white/20 text-white text-[11px] font-bold rounded-full transition-all cursor-pointer shadow-xs"
            >
              <FileText className="w-3.5 h-3.5 text-emerald-300" />
              <span>{language === 'en' ? 'Gazette Decrees' : 'राजपत्र सूचना'}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-8">
        {/* ============================================================ */}
        {/* VIEW 1: HOME (2026 DIGITAL PUBLIC INFRASTRUCTURE HOMEPAGE) */}
        {/* ============================================================ */}
        {activeTab === 'HOME' && (
          <div className="space-y-8">
            {/* 1. Central Hero Rotating Background Carousel with Search Console & Leadership Card */}
            <HeroRotatingBanner onNavigate={setActiveTab} />

            {/* 2. National DPI Metrics Bar (Single, High-Impact 2026 Standard) */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-left">
              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-blue-50/80 to-transparent rounded-bl-full pointer-events-none transition-transform group-hover:scale-110"></div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">National Cadastre</span>
                  <div className="w-8 h-8 rounded-lg bg-blue-50 text-[#0b3866] flex items-center justify-center">
                    <Globe className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl font-black text-[#002642] mt-2">28 States &amp; 8 UTs</div>
                <div className="text-[11px] text-blue-700 font-semibold mt-1 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
                  <span>100% Interoperable Layer</span>
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-amber-50/80 to-transparent rounded-bl-full pointer-events-none transition-transform group-hover:scale-110"></div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Drone Mapping</span>
                  <div className="w-8 h-8 rounded-lg bg-amber-50 text-[#f37021] flex items-center justify-center">
                    <Layers className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl font-black text-[#002642] mt-2">3.15 Lakh+</div>
                <div className="text-[11px] text-amber-700 font-semibold mt-1 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#f37021]"></span>
                  <span>SVAMITVA Inhabited Villages</span>
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-emerald-50/80 to-transparent rounded-bl-full pointer-events-none transition-transform group-hover:scale-110"></div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">PFMS Direct Payout</span>
                  <div className="w-8 h-8 rounded-lg bg-emerald-50 text-[#138808] flex items-center justify-center">
                    <IndianRupee className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl font-black text-[#138808] mt-2">₹14,820 Cr</div>
                <div className="text-[11px] text-emerald-700 font-semibold mt-1 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#138808]"></span>
                  <span>1.84 Lakh Khatedar Families</span>
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-purple-50/80 to-transparent rounded-bl-full pointer-events-none transition-transform group-hover:scale-110"></div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Sec 15 Objections</span>
                  <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-700 flex items-center justify-center">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl font-black text-[#002642] mt-2">94.8% Fixed</div>
                <div className="text-[11px] text-purple-700 font-semibold mt-1 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-600"></span>
                  <span>Time-Bound Collector Disposal</span>
                </div>
              </div>
            </div>

            {/* 3. 4 Primary Citizen Gateway Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <button
                onClick={() => setActiveTab('SEARCH')}
                className="p-5 bg-white text-left text-slate-800 rounded-2xl shadow-sm hover:shadow-xl transition-all border border-slate-200/90 hover:border-[#002642]/40 hover:-translate-y-1 group cursor-pointer relative overflow-hidden"
              >
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#002642] to-[#0b3866]"></div>
                <div className="flex items-center justify-between">
                  <div className="w-11 h-11 rounded-xl bg-blue-50 text-[#002642] flex items-center justify-center font-bold shadow-xs group-hover:scale-105 transition-transform">
                    <Search className="w-5 h-5 text-[#002642]" />
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-blue-100 text-blue-800">
                    Fast Search
                  </span>
                </div>
                <div className="mt-3.5 font-bold text-sm text-[#002642] group-hover:text-[#0b3866]">
                  {language === 'en' ? 'Unified Land Search' : 'भू-अभिलेख खोजें'}
                </div>
                <div className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                  State → District → Village → Survey No. or 14-digit ULPIN lookup
                </div>
                <div className="mt-3 flex items-center gap-1 text-[11px] font-bold text-[#0b3866] group-hover:translate-x-1 transition-transform">
                  <span>Launch Search</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </button>

              <button
                onClick={() => setActiveTab('DOC_VERIFY')}
                className="p-5 bg-white text-left text-slate-800 rounded-2xl shadow-sm hover:shadow-xl transition-all border border-slate-200/90 hover:border-[#f37021]/40 hover:-translate-y-1 group cursor-pointer relative overflow-hidden"
              >
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#f37021] to-[#d95a10]"></div>
                <div className="flex items-center justify-between">
                  <div className="w-11 h-11 rounded-xl bg-amber-50 text-[#f37021] flex items-center justify-center font-bold shadow-xs group-hover:scale-105 transition-transform">
                    <FileCheck className="w-5 h-5 text-[#f37021]" />
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-amber-100 text-amber-800">
                    AI OCR
                  </span>
                </div>
                <div className="mt-3.5 font-bold text-sm text-[#002642] group-hover:text-[#f37021]">
                  {language === 'en' ? 'AI Document Verification' : 'दस्तावेज सत्यापन'}
                </div>
                <div className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                  Instant deed OCR extraction &amp; cross-comparison against live RoR
                </div>
                <div className="mt-3 flex items-center gap-1 text-[11px] font-bold text-[#f37021] group-hover:translate-x-1 transition-transform">
                  <span>Upload &amp; Verify</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </button>

              <button
                onClick={() => setActiveTab('MUTATION')}
                className="p-5 bg-white text-left text-slate-800 rounded-2xl shadow-sm hover:shadow-xl transition-all border border-slate-200/90 hover:border-[#138808]/40 hover:-translate-y-1 group cursor-pointer relative overflow-hidden"
              >
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#138808] to-[#0e6706]"></div>
                <div className="flex items-center justify-between">
                  <div className="w-11 h-11 rounded-xl bg-emerald-50 text-[#138808] flex items-center justify-center font-bold shadow-xs group-hover:scale-105 transition-transform">
                    <Clock className="w-5 h-5 text-[#138808]" />
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-800">
                    Lifecycle
                  </span>
                </div>
                <div className="mt-3.5 font-bold text-sm text-[#002642] group-hover:text-[#138808]">
                  {language === 'en' ? 'Track Mutation (Ferfar)' : 'दाखिल-खारिज स्थिति'}
                </div>
                <div className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                  Track 15-day notice, Talathi site report, and Circle Officer orders
                </div>
                <div className="mt-3 flex items-center gap-1 text-[11px] font-bold text-[#138808] group-hover:translate-x-1 transition-transform">
                  <span>Track Application</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </button>

              <button
                onClick={() => setActiveTab('GIS_MAP')}
                className="p-5 bg-white text-left text-slate-800 rounded-2xl shadow-sm hover:shadow-xl transition-all border border-slate-200/90 hover:border-sky-500/40 hover:-translate-y-1 group cursor-pointer relative overflow-hidden"
              >
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-sky-500 to-blue-600"></div>
                <div className="flex items-center justify-between">
                  <div className="w-11 h-11 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center font-bold shadow-xs group-hover:scale-105 transition-transform">
                    <Map className="w-5 h-5 text-sky-600" />
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-sky-100 text-sky-800">
                    BhuNaksha
                  </span>
                </div>
                <div className="mt-3.5 font-bold text-sm text-[#002642] group-hover:text-sky-700">
                  {language === 'en' ? 'Cadastral GIS Map' : 'भू-नक्शा GIS'}
                </div>
                <div className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                  Inspect sub-centimeter parcel boundaries &amp; infrastructure corridors
                </div>
                <div className="mt-3 flex items-center gap-1 text-[11px] font-bold text-sky-700 group-hover:translate-x-1 transition-transform">
                  <span>View Cadastre</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </button>
            </div>

            {/* 4. THE SHOWSTOPPER: INTERACTIVE "ONE PROPERTY — ONE VIEW" LIVE CONSOLE */}
            <div className="bg-gradient-to-br from-[#001c38] via-[#002642] to-[#0b3866] text-white p-6 sm:p-8 rounded-3xl border border-blue-900/60 shadow-2xl relative overflow-hidden text-left">
              {/* Subtle background glow */}
              <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>
              <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none"></div>

              {/* Header with Title and Dashboard CTA */}
              <div className="relative z-10 flex flex-wrap justify-between items-center gap-4 border-b border-white/10 pb-5">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-[#f37021] text-white shadow-xs">
                      CENTRAL PLATFORM USP • LIVE CONSOLE
                    </span>
                    <span className="text-[11px] font-mono text-amber-300 hidden sm:inline">
                      ULPIN: 27712049001234
                    </span>
                  </div>
                  <h3 className="text-xl sm:text-2xl font-black tracking-tight text-white mt-2">
                    “ONE PROPERTY — ONE INTELLIGENCE VIEW”
                  </h3>
                  <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
                    Interactive unified console combining Record of Rights (RoR), Cadastral GIS (BhuNaksha), Mutation Ferfar, and AI Title Risk analysis into a single view.
                  </p>
                </div>

                <button
                  onClick={() => setActiveTab('PROPERTY_INTEL')}
                  className="px-5 py-2.5 bg-white text-[#002642] hover:bg-slate-100 font-extrabold text-xs rounded-xl flex items-center gap-2 shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-0.5 cursor-pointer flex-shrink-0"
                >
                  <Sparkles className="w-4 h-4 text-[#f37021]" />
                  <span>Open Full Intelligence Dashboard (12 Checks)</span>
                  <ChevronRight className="w-4 h-4 text-[#f37021]" />
                </button>
              </div>

              {/* Interactive Segmented Tab Controls */}
              <div className="relative z-10 mt-6 flex flex-wrap gap-2">
                <button
                  onClick={() => setActivePreviewTab('ROR')}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                    activePreviewTab === 'ROR'
                      ? 'bg-white text-[#002642] shadow-md scale-102'
                      : 'bg-white/10 hover:bg-white/20 text-slate-300 border border-white/15'
                  }`}
                >
                  <FileText className={`w-3.5 h-3.5 ${activePreviewTab === 'ROR' ? 'text-[#002642]' : 'text-amber-300'}`} />
                  <span>1. 7/12 &amp; RoR Record</span>
                </button>

                <button
                  onClick={() => setActivePreviewTab('MAP')}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                    activePreviewTab === 'MAP'
                      ? 'bg-white text-[#002642] shadow-md scale-102'
                      : 'bg-white/10 hover:bg-white/20 text-slate-300 border border-white/15'
                  }`}
                >
                  <Map className={`w-3.5 h-3.5 ${activePreviewTab === 'MAP' ? 'text-[#002642]' : 'text-sky-300'}`} />
                  <span>2. Cadastral Map (BhuNaksha)</span>
                </button>

                <button
                  onClick={() => setActivePreviewTab('MUTATION')}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                    activePreviewTab === 'MUTATION'
                      ? 'bg-white text-[#002642] shadow-md scale-102'
                      : 'bg-white/10 hover:bg-white/20 text-slate-300 border border-white/15'
                  }`}
                >
                  <Clock className={`w-3.5 h-3.5 ${activePreviewTab === 'MUTATION' ? 'text-[#002642]' : 'text-emerald-300'}`} />
                  <span>3. Mutation Lifecycle (Ferfar)</span>
                </button>

                <button
                  onClick={() => setActivePreviewTab('RISK')}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                    activePreviewTab === 'RISK'
                      ? 'bg-white text-[#002642] shadow-md scale-102'
                      : 'bg-white/10 hover:bg-white/20 text-slate-300 border border-white/15'
                  }`}
                >
                  <ShieldCheck className={`w-3.5 h-3.5 ${activePreviewTab === 'RISK' ? 'text-[#002642]' : 'text-purple-300'}`} />
                  <span>4. AI Title Risk Analysis</span>
                </button>
              </div>

              {/* Dynamic Interactive Preview Canvas */}
              <div className="relative z-10 mt-4 bg-slate-900/60 backdrop-blur-md border border-white/15 rounded-2xl p-5 sm:p-6 transition-all">
                {/* 1. ROR PREVIEW */}
                {activePreviewTab === 'ROR' && (
                  <div className="space-y-4">
                    <div className="flex flex-wrap justify-between items-center gap-2 border-b border-white/10 pb-3">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                        <span className="font-bold text-sm text-white">e-Mahabhulekh Record of Rights (Village Form VII-XII)</span>
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          Digitally Signed
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Survey Gat: <strong className="text-amber-300">142/A</strong> • Mouza: Besa • Dist: Nagpur
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold">Khatedar (Owner)</span>
                        <div className="font-bold text-white mt-1">Tukaram Bapu Jadhav &amp; Others</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">Aadhaar: XXXX-XXXX-4819 (Masked)</div>
                      </div>
                      <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Area</span>
                        <div className="font-bold text-white mt-1">1.4500 Hectares (3.58 Acres)</div>
                        <div className="text-[10px] text-emerald-400 mt-0.5">Pot-Kharaba: 0.0500 Ha</div>
                      </div>
                      <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold">Tenancy / Rights Class</span>
                        <div className="font-bold text-white mt-1">Class-1 (Bhumiswami)</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">Direct Occupant • Non-Tenanted</div>
                      </div>
                      <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold">Encumbrance / Charges</span>
                        <div className="font-bold text-emerald-400 mt-1 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Clear / No Mortgage</span>
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">Annual Revenue: ₹12.50</div>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-[11px] text-slate-300">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        <span>Authenticated via National DILRMP Data Bridge • IT Act 2000 Section 4 Compliance</span>
                      </div>
                      <button
                        onClick={() => setActiveTab('PROPERTY_INTEL')}
                        className="text-amber-300 hover:text-white font-bold inline-flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        <span>View complete 18-field digital abstract →</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* 2. MAP PREVIEW */}
                {activePreviewTab === 'MAP' && (
                  <div className="space-y-4">
                    <div className="flex flex-wrap justify-between items-center gap-2 border-b border-white/10 pb-3">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
                        <span className="font-bold text-sm text-white">BhuNaksha Cadastral GIS Vector Geometry</span>
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30">
                          Sub-Centimeter Drone Cadastre
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Centroid: 18.5204° N, 73.8567° E (EPSG:4326)
                      </div>
                    </div>

                    {/* Cadastral Polygon Simulation */}
                    <div className="bg-slate-950 rounded-xl p-4 border border-white/10 relative overflow-hidden">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                        <div className="md:col-span-2 relative h-40 bg-gradient-to-br from-slate-900 to-slate-950 rounded-lg border border-slate-800 flex items-center justify-center p-3">
                          {/* Simulated SVG Cadastral Polygons */}
                          <svg className="w-full h-full" viewBox="0 0 400 150">
                            {/* Neighbor Gat 141 */}
                            <polygon points="20,15 150,15 140,55 30,55" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                            <text x="75" y="38" fill="#94a3b8" fontSize="10" textAnchor="middle">Gat 141 (0.92 Ha)</text>

                            {/* Active Gat 142/A (Selected) */}
                            <polygon points="150,15 310,25 295,120 135,110" fill="rgba(19, 136, 8, 0.25)" stroke="#22c55e" strokeWidth="2.5" strokeDasharray="none" />
                            <text x="220" y="65" fill="#ffffff" fontWeight="bold" fontSize="12" textAnchor="middle">GAT 142/A (1.45 Ha)</text>
                            <text x="220" y="80" fill="#86efac" fontSize="9" textAnchor="middle">★ Selected Target Parcel</text>

                            {/* Neighbor Gat 142/B */}
                            <polygon points="310,25 385,30 375,125 295,120" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                            <text x="345" y="75" fill="#94a3b8" fontSize="9" textAnchor="middle">142/B</text>

                            {/* Neighbor Gat 143 */}
                            <polygon points="135,110 295,120 280,145 120,145" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
                            <text x="200" y="135" fill="#94a3b8" fontSize="9" textAnchor="middle">Gat 143</text>

                            {/* 12m PWD Road Marker */}
                            <line x1="20" y1="12" x2="385" y2="12" stroke="#f37021" strokeWidth="2" strokeDasharray="4 2" />
                            <text x="200" y="9" fill="#f37021" fontSize="8" fontWeight="bold" textAnchor="middle">12M PWD ROAD (NORTH BOUNDARY)</text>
                          </svg>
                        </div>

                        <div className="space-y-2 text-[11px] text-slate-300">
                          <div className="p-2.5 bg-white/5 rounded-lg border border-white/10">
                            <span className="text-slate-400 block text-[10px]">Perimeter Accuracy</span>
                            <span className="font-bold text-white">±2.0 cm (CORS RTK Survey)</span>
                          </div>
                          <div className="p-2.5 bg-white/5 rounded-lg border border-white/10">
                            <span className="text-slate-400 block text-[10px]">Infrastructure Proximity</span>
                            <span className="font-bold text-amber-300">45m to NH-53 Corridor</span>
                          </div>
                          <button
                            onClick={() => setActiveTab('GIS_MAP')}
                            className="w-full py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-xs"
                          >
                            <Map className="w-3.5 h-3.5" />
                            <span>Launch Full GIS Viewer</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. MUTATION PREVIEW */}
                {activePreviewTab === 'MUTATION' && (
                  <div className="space-y-4">
                    <div className="flex flex-wrap justify-between items-center gap-2 border-b border-white/10 pb-3">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                        <span className="font-bold text-sm text-white">Ferfar (Mutation) Application Status</span>
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          Approved &amp; Certified
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Ref: <strong className="text-emerald-300">MUT-MH-2026-001245</strong> • Type: Varas (Succession)
                      </div>
                    </div>

                    {/* Step Timeline */}
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                      <div className="p-3 bg-white/5 rounded-xl border border-emerald-500/30">
                        <div className="flex items-center justify-between">
                          <span className="text-[9px] uppercase font-bold text-emerald-400">Step 1</span>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        </div>
                        <div className="font-bold text-white mt-1">Application Filed</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">12-Jan-2026 via e-Mutation</div>
                      </div>

                      <div className="p-3 bg-white/5 rounded-xl border border-emerald-500/30">
                        <div className="flex items-center justify-between">
                          <span className="text-[9px] uppercase font-bold text-emerald-400">Step 2</span>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        </div>
                        <div className="font-bold text-white mt-1">15-Day Public Notice</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">Zero Objections Registered</div>
                      </div>

                      <div className="p-3 bg-white/5 rounded-xl border border-emerald-500/30">
                        <div className="flex items-center justify-between">
                          <span className="text-[9px] uppercase font-bold text-emerald-400">Step 3</span>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        </div>
                        <div className="font-bold text-white mt-1">Talathi Panchnama</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">Site Verification Affirmative</div>
                      </div>

                      <div className="p-3 bg-emerald-950/40 rounded-xl border border-emerald-400">
                        <div className="flex items-center justify-between">
                          <span className="text-[9px] uppercase font-bold text-emerald-300">Step 4</span>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        </div>
                        <div className="font-bold text-emerald-300 mt-1">Circle Officer Order</div>
                        <div className="text-[10px] text-emerald-200 mt-0.5">Approved &amp; Updated in 7/12</div>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-[11px] text-slate-300">
                      <span>Assigned Revenue Officer: <strong>Shri S. V. Kulkarni (Circle Officer, Besa)</strong></span>
                      <button
                        onClick={() => setActiveTab('MUTATION')}
                        className="text-emerald-400 hover:text-white font-bold inline-flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        <span>Open Mutation Tracker &amp; Acknowledgement →</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* 4. RISK PREVIEW */}
                {activePreviewTab === 'RISK' && (
                  <div className="space-y-4">
                    <div className="flex flex-wrap justify-between items-center gap-2 border-b border-white/10 pb-3">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                        <span className="font-bold text-sm text-white">AI Cross-Layer Title Risk Assessment</span>
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black bg-emerald-500 text-white">
                          SCORE: 94 / 100 (LOW RISK)
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Automated AI Triangulation: RoR vs Cadastre vs e-Courts
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                      <div className="p-3 bg-white/5 rounded-xl border border-emerald-500/30">
                        <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Litigation Check</span>
                        </div>
                        <p className="text-[10px] text-slate-300 mt-1">
                          No pending civil court suits or lis pendens injunctions in District &amp; Taluka Courts.
                        </p>
                      </div>

                      <div className="p-3 bg-white/5 rounded-xl border border-emerald-500/30">
                        <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Bank Mortgage Lien</span>
                        </div>
                        <p className="text-[10px] text-slate-300 mt-1">
                          CERSAI registry confirms unencumbered title with zero financial hypothecation.
                        </p>
                      </div>

                      <div className="p-3 bg-white/5 rounded-xl border border-amber-500/40">
                        <div className="flex items-center gap-1.5 text-amber-400 font-bold text-[11px]">
                          <ShieldAlert className="w-3.5 h-3.5" />
                          <span>Corridor Advisory</span>
                        </div>
                        <p className="text-[10px] text-slate-300 mt-1">
                          45m from NH-53 project line. Statutory 100% solatium guaranteed if notified.
                        </p>
                      </div>

                      <div className="p-3 bg-white/5 rounded-xl border border-emerald-500/30">
                        <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Tribal / Forest Land</span>
                        </div>
                        <p className="text-[10px] text-slate-300 mt-1">
                          Non-Scheduled V area. Valid freehold private tenure (Class-1 Bhumiswami).
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-[11px] text-slate-300">
                      <span>12 automated regulatory checks validated across 4 government repositories</span>
                      <button
                        onClick={() => setActiveTab('PROPERTY_INTEL')}
                        className="text-purple-300 hover:text-white font-bold inline-flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        <span>Download Complete PDF Intelligence Report →</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 5. UNIFIED ECOSYSTEM HUB: Tabbed Flagship Schemes vs State Portals vs Gazette Notices vs Statutory Rights */}
            <div className="bg-white border border-slate-200/90 rounded-3xl p-6 sm:p-7 shadow-sm text-left space-y-6">
              <div className="flex flex-wrap justify-between items-center gap-3 border-b border-slate-200 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#f37021]"></span>
                    <h3 className="font-black text-base sm:text-lg text-[#002642]">
                      {language === 'en' ? 'National Land Governance Ecosystem' : 'राष्ट्रीय भू-प्रशासन पारिस्थितिकी तंत्र'}
                    </h3>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Unified access to Flagship Initiatives, State Portals, Gazette Decrees, and Landowner Protections
                  </p>
                </div>

                {/* Segmented Ecosystem Tab Switcher */}
                <div className="flex flex-wrap items-center p-1 bg-slate-100 rounded-xl border border-slate-200 text-xs font-bold">
                  <button
                    onClick={() => setEcosystemTab('SCHEMES')}
                    className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                      ecosystemTab === 'SCHEMES'
                        ? 'bg-[#002642] text-white shadow-xs'
                        : 'text-slate-600 hover:text-[#002642]'
                    }`}
                  >
                    {language === 'en' ? 'Flagship Schemes' : 'प्रमुख योजनाएं'}
                  </button>

                  <button
                    onClick={() => setEcosystemTab('STATES')}
                    className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                      ecosystemTab === 'STATES'
                        ? 'bg-[#002642] text-white shadow-xs'
                        : 'text-slate-600 hover:text-[#002642]'
                    }`}
                  >
                    {language === 'en' ? 'State Portals (28)' : 'राज्य पोर्टल'}
                  </button>

                  <button
                    onClick={() => setEcosystemTab('NOTICES')}
                    className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                      ecosystemTab === 'NOTICES'
                        ? 'bg-[#002642] text-white shadow-xs'
                        : 'text-slate-600 hover:text-[#002642]'
                    }`}
                  >
                    {language === 'en' ? 'Gazette Decrees' : 'राजपत्र सूचना'}
                  </button>

                  <button
                    onClick={() => setEcosystemTab('RIGHTS')}
                    className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                      ecosystemTab === 'RIGHTS'
                        ? 'bg-[#002642] text-white shadow-xs'
                        : 'text-slate-600 hover:text-[#002642]'
                    }`}
                  >
                    {language === 'en' ? 'Statutory Rights' : 'नागरिक अधिकार'}
                  </button>
                </div>
              </div>

              {/* ECOSYSTEM TAB 1: SCHEMES */}
              {ecosystemTab === 'SCHEMES' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {GOV_SCHEMES.slice(0, 6).map((scheme) => (
                      <div
                        key={scheme.id}
                        className="p-5 bg-slate-50/70 hover:bg-white rounded-2xl border border-slate-200/80 hover:border-[#f37021]/50 shadow-xs hover:shadow-lg transition-all text-left flex flex-col justify-between group"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-orange-100 text-[#c2410c]">
                              {scheme.badge}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono font-bold">
                              {scheme.code}
                            </span>
                          </div>

                          <h4 className="font-bold text-sm text-[#002642] group-hover:text-[#f37021] transition-colors leading-tight">
                            {language === 'en' ? scheme.name : scheme.nameHi}
                          </h4>

                          <p className="text-[11px] text-slate-600 mt-2 line-clamp-2 leading-relaxed">
                            {language === 'en' ? scheme.tagline : scheme.taglineHi}
                          </p>
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-200/80 flex items-center justify-between">
                          <div>
                            <span className="text-xs font-black text-[#0b3866]">{scheme.impactMetric}</span>
                            <span className="text-[9px] text-slate-500 block">{scheme.impactLabel}</span>
                          </div>

                          <button
                            onClick={() => setSelectedSchemeDetail(scheme)}
                            className="px-3 py-1.5 bg-[#0b3866] hover:bg-[#002642] text-white text-[11px] font-bold rounded-xl transition-all shadow-xs cursor-pointer"
                          >
                            Details
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="pt-2 text-center">
                    <button
                      onClick={() => setActiveTab('SCHEMES')}
                      className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-[#002642] font-bold text-xs rounded-xl inline-flex items-center gap-1.5 transition-all cursor-pointer"
                    >
                      <Landmark className="w-3.5 h-3.5 text-[#f37021]" />
                      <span>{language === 'en' ? 'Explore All 9 National Schemes with Citizen Advisor →' : 'सभी ९ योजनाएं व नागरिक सलाहकार देखें →'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* ECOSYSTEM TAB 2: STATE PORTALS */}
              {ecosystemTab === 'STATES' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {STATE_LAND_DIRECTORY.slice(0, 6).map((item) => (
                      <div
                        key={item.stateCode}
                        className="p-5 bg-slate-50/70 hover:bg-white rounded-2xl border border-slate-200/80 hover:border-[#0b3866]/50 shadow-xs hover:shadow-lg transition-all text-left flex flex-col justify-between group"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-blue-100 text-[#0b3866]">
                              {item.stateCode}
                            </span>
                            <span className="text-[10px] text-slate-400 font-medium">
                              {item.category}
                            </span>
                          </div>

                          <h4 className="font-bold text-sm text-[#002642] group-hover:text-[#0b3866] transition-colors">
                            {item.stateName}
                          </h4>
                          <div className="text-[10px] text-slate-500 font-medium mt-0.5">
                            {item.departmentName}
                          </div>

                          <div className="mt-3 space-y-1 text-[11px] text-slate-600">
                            <div><strong>Portal:</strong> {item.landRecordsPortal}</div>
                            <div><strong>RoR Document:</strong> {item.rorName}</div>
                            <div><strong>Cadastral Map:</strong> {item.cadastralMapPortal}</div>
                          </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-200/80 flex items-center justify-between">
                          <span className="text-[10px] text-emerald-700 font-bold flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>100% Interoperable</span>
                          </span>

                          <a
                            href={item.landRecordsUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="px-3 py-1.5 bg-[#0b3866] hover:bg-[#002642] text-white text-[11px] font-bold rounded-xl transition-all shadow-xs inline-flex items-center gap-1 cursor-pointer"
                          >
                            <span>Launch</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="pt-2 text-center">
                    <button
                      onClick={() => setActiveTab('STATE_PORTALS')}
                      className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-[#002642] font-bold text-xs rounded-xl inline-flex items-center gap-1.5 transition-all cursor-pointer"
                    >
                      <Globe className="w-3.5 h-3.5 text-[#0b3866]" />
                      <span>{language === 'en' ? 'Open Full 28 States & UTs Directory →' : 'संपूर्ण २८ राज्य निर्देशिका देखें →'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* ECOSYSTEM TAB 3: GAZETTE NOTICES */}
              {ecosystemTab === 'NOTICES' && (
                <div className="space-y-4">
                  <div className="overflow-x-auto">
                    <table className="gov-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Gazette / Notification Ref</th>
                          <th>Project / Description</th>
                          <th>District</th>
                          <th className="text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredCases.slice(0, 4).map((c) => (
                          <tr key={c.id}>
                            <td className="whitespace-nowrap font-medium text-slate-600">
                              {formatDate(c.stageDeadline)}
                            </td>
                            <td>
                              <span className="font-mono font-bold text-[#0b3866] block">
                                {c.caseReference}
                              </span>
                              <span className="text-[10px] text-slate-500">
                                {c.stage.replace('STAGE_', '').replace(/_/g, ' ')}
                              </span>
                            </td>
                            <td className="font-medium text-slate-800">
                              {c.projectName} ({c.village})
                            </td>
                            <td className="text-slate-600">
                              {c.district}
                            </td>
                            <td className="text-right whitespace-nowrap">
                              <button
                                onClick={() => setSelectedCaseDetailId(c.id)}
                                className="px-3 py-1 text-xs font-semibold bg-[#e8f1f8] hover:bg-[#0b3866] text-[#0b3866] hover:text-white rounded-lg transition-all inline-flex items-center gap-1.5 shadow-xs cursor-pointer"
                              >
                                <Eye className="w-3 h-3" />
                                <span>{language === 'en' ? 'View' : 'देखें'}</span>
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="pt-2 text-center">
                    <button
                      onClick={() => setActiveTab('NOTICES')}
                      className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-[#002642] font-bold text-xs rounded-xl inline-flex items-center gap-1.5 transition-all cursor-pointer"
                    >
                      <FileText className="w-3.5 h-3.5 text-[#0b3866]" />
                      <span>{language === 'en' ? 'View All Official Gazette Publications (4,892 Records) →' : 'सभी राजपत्र अधिसूचनाएं देखें (४,८९२ अभिलेख) →'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* ECOSYSTEM TAB 4: STATUTORY RIGHTS */}
              {ecosystemTab === 'RIGHTS' && (
                <div className="space-y-6">
                  {/* 4 Guarantees */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="p-4 bg-amber-50/70 border-l-4 border-[#f37021] rounded-2xl shadow-xs">
                      <div className="font-bold text-[#c2410c] text-xs flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-[#f37021]" />
                        <span>100% Solatium Guaranteed</span>
                      </div>
                      <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                        Mandated 100% equivalent solatium added to basic land value under Section 30 of RFCTLARR Act 2013.
                      </p>
                    </div>

                    <div className="p-4 bg-blue-50/70 border-l-4 border-[#0b3866] rounded-2xl shadow-xs">
                      <div className="font-bold text-[#0b3866] text-xs flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-[#0b3866]" />
                        <span>12% Annual Interest</span>
                      </div>
                      <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                        Statutory 12% additional interest calculated from preliminary notification date till award determination.
                      </p>
                    </div>

                    <div className="p-4 bg-purple-50/70 border-l-4 border-purple-700 rounded-2xl shadow-xs">
                      <div className="font-bold text-purple-700 text-xs flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-purple-700" />
                        <span>60-Day Section 15 Hearing</span>
                      </div>
                      <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                        Statutory right to submit objections and be personally heard by the District Collector / LAO.
                      </p>
                    </div>

                    <div className="p-4 bg-emerald-50/70 border-l-4 border-[#138808] rounded-2xl shadow-xs">
                      <div className="font-bold text-[#138808] text-xs flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-[#138808]" />
                        <span>Direct PFMS Bank Transfer</span>
                      </div>
                      <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                        Direct compensation credited into Aadhaar-linked accounts with zero intermediaries or deductions.
                      </p>
                    </div>
                  </div>

                  {/* 4-Stage Statutory Lifecycle */}
                  <div className="p-5 bg-slate-50 rounded-2xl border border-slate-200">
                    <div className="text-xs font-bold text-[#002642] mb-3">
                      Mandatory Acquisition Lifecycle (RFCTLARR Act, 2013)
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                      <div className="p-3 bg-white rounded-xl border border-slate-200/80">
                        <div className="text-[9px] font-bold text-[#0b3866] uppercase">Stage 1</div>
                        <div className="font-bold text-slate-800 mt-0.5">Section 11 Notice</div>
                        <p className="text-[10px] text-slate-500 mt-1">Preliminary notification &amp; Social Impact Assessment (SIA).</p>
                      </div>

                      <div className="p-3 bg-white rounded-xl border border-amber-300">
                        <div className="text-[9px] font-bold text-[#f37021] uppercase">Stage 2 (60 Days)</div>
                        <div className="font-bold text-slate-800 mt-0.5">Section 15 Objections</div>
                        <p className="text-[10px] text-slate-500 mt-1">60-day objection window with formal Collector hearing.</p>
                      </div>

                      <div className="p-3 bg-white rounded-xl border border-slate-200/80">
                        <div className="text-[9px] font-bold text-[#0b3866] uppercase">Stage 3 (12 Months)</div>
                        <div className="font-bold text-slate-800 mt-0.5">Section 19 Declaration</div>
                        <p className="text-[10px] text-slate-500 mt-1">Final declaration of public purpose land requirement.</p>
                      </div>

                      <div className="p-3 bg-white rounded-xl border border-emerald-300">
                        <div className="text-[9px] font-bold text-[#138808] uppercase">Stage 4</div>
                        <div className="font-bold text-slate-800 mt-0.5">Section 23 &amp; DBT Award</div>
                        <p className="text-[10px] text-slate-500 mt-1">100% solatium compensation disbursed via PFMS.</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* 6. Security, Privacy & Data Governance Principles (DPDP Act 2023) */}
            <div className="bg-white border border-slate-200/90 rounded-3xl p-6 shadow-sm text-xs text-left space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
                <ShieldCheck className="w-4 h-4 text-[#138808]" />
                <h4 className="font-extrabold text-xs uppercase tracking-wide text-[#002642]">
                  Security, Privacy &amp; Data Governance Principles (DPDP Act 2023)
                </h4>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-slate-600 text-[11px]">
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80">
                  <strong className="text-slate-800 block mb-1">Masked Personal Identifiers:</strong>
                  Real landowner names and Aadhaar numbers are never displayed publicly. Fictional sample records are utilized.
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80">
                  <strong className="text-slate-800 block mb-1">Zero Permanent Storage:</strong>
                  Uploaded deeds and 7/12 extracts are processed in-memory for OCR extraction and are immediately discarded.
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80">
                  <strong className="text-slate-800 block mb-1">Non-Legal Preliminary Status:</strong>
                  All findings are labeled as preliminary variances. They do not constitute official title certification or legal advice.
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80">
                  <strong className="text-slate-800 block mb-1">Authentic Gateways Only:</strong>
                  We direct citizens exclusively to verified state revenue URLs (Mahabhulekh, AnyRoR, Bhoomi, UP Bhulekh).
                </div>
              </div>
            </div>

            {/* 7. Allied Government Portals Grid (Single Window Integrations) */}
            <div className="bg-white border border-slate-200/90 rounded-3xl p-5 shadow-sm space-y-3 text-left">
              <div className="flex justify-between items-center border-b border-slate-200 pb-2.5">
                <span className="font-bold text-xs text-[#002642] tracking-wide uppercase flex items-center gap-2">
                  <Landmark className="w-4 h-4 text-[#f37021]" />
                  <span>{language === 'en' ? 'ALLIED GOVERNMENT OF INDIA PORTALS' : 'संबद्ध राष्ट्रीय पोर्टल'}</span>
                </span>
                <span className="text-[10px] text-slate-400 font-medium">National Single Window Integrations</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <a 
                  href="https://bhoomirashi.gov.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200/90 hover:border-[#0b3866] transition-all text-center rounded-xl block group shadow-xs hover:shadow-md hover:-translate-y-0.5"
                >
                  <div className="text-[11px] font-bold text-[#0b3866] group-hover:text-[#f37021]">BHOOMI RASHI</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">MoRTH Highways</div>
                </a>

                <a 
                  href="https://gatishakti.gov.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200/90 hover:border-[#0b3866] transition-all text-center rounded-xl block group shadow-xs hover:shadow-md hover:-translate-y-0.5"
                >
                  <div className="text-[11px] font-bold text-[#138808] group-hover:text-[#f37021]">PM GATI SHAKTI</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">National Master Plan</div>
                </a>

                <a 
                  href="https://bhunaksha.gov.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200/90 hover:border-[#0b3866] transition-all text-center rounded-xl block group shadow-xs hover:shadow-md hover:-translate-y-0.5"
                >
                  <div className="text-[11px] font-bold text-[#0b3866] group-hover:text-[#f37021]">BHUNAKSHA (NIC)</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Cadastral Maps</div>
                </a>

                <a 
                  href="https://mahabhulekh.maharashtra.gov.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200/90 hover:border-[#0b3866] transition-all text-center rounded-xl block group shadow-xs hover:shadow-md hover:-translate-y-0.5"
                >
                  <div className="text-[11px] font-bold text-[#0b3866] group-hover:text-[#f37021]">MAHABHULEKH</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">7/12 Land Records</div>
                </a>

                <a 
                  href="https://pfms.nic.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200/90 hover:border-[#0b3866] transition-all text-center rounded-xl block group shadow-xs hover:shadow-md hover:-translate-y-0.5"
                >
                  <div className="text-[11px] font-bold text-[#0b3866] group-hover:text-[#f37021]">PFMS DBT</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Public Finance</div>
                </a>

                <a 
                  href="https://dilrmp.gov.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200/90 hover:border-[#0b3866] transition-all text-center rounded-xl block group shadow-xs hover:shadow-md hover:-translate-y-0.5"
                >
                  <div className="text-[11px] font-bold text-[#0b3866] group-hover:text-[#f37021]">DILRMP</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Land Modernisation</div>
                </a>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 2: UNIFIED LAND SEARCH */}
        {/* ============================================================ */}
        {activeTab === 'SEARCH' && (
          <UnifiedLandSearch 
            onSelectProperty={(prop) => {
              setSelectedProperty(prop);
              setActiveTab('PROPERTY_INTEL');
            }}
            onNavigateTab={setActiveTab}
          />
        )}

        {/* ============================================================ */}
        {/* VIEW 3: PROPERTY INTELLIGENCE DASHBOARD (ONE PROPERTY - ONE VIEW) */}
        {/* ============================================================ */}
        {activeTab === 'PROPERTY_INTEL' && (
          <PropertyIntelligenceDashboard 
            property={selectedProperty}
            onNavigateTab={setActiveTab}
          />
        )}

        {/* ============================================================ */}
        {/* VIEW 4: AI DOCUMENT VERIFICATION */}
        {/* ============================================================ */}
        {activeTab === 'DOC_VERIFY' && (
          <AiDocumentVerification onNavigateTab={setActiveTab} />
        )}

        {/* ============================================================ */}
        {/* VIEW 5: PRELIMINARY LAND RECORD RISK ANALYSIS */}
        {/* ============================================================ */}
        {activeTab === 'RISK_ANALYSIS' && (
          <LandRiskAnalysis onNavigateTab={setActiveTab} />
        )}

        {/* ============================================================ */}
        {/* VIEW 6: PROPERTY TIMELINE */}
        {/* ============================================================ */}
        {activeTab === 'TIMELINE' && (
          <PropertyTimelineView onNavigateTab={setActiveTab} />
        )}

        {/* ============================================================ */}
        {/* VIEW 7: MUTATION TRACKER */}
        {/* ============================================================ */}
        {activeTab === 'MUTATION' && (
          <MutationTrackerView onNavigateTab={setActiveTab} />
        )}

        {/* ============================================================ */}
        {/* VIEW 8: GOVERNMENT SCHEMES & WELFARE DIRECTORY */}
        {/* ============================================================ */}
        {activeTab === 'SCHEMES' && (
          <GovSchemesView />
        )}

        {/* ============================================================ */}
        {/* VIEW 9: STATE LAND INFORMATION DIRECTORY */}
        {/* ============================================================ */}
        {activeTab === 'STATE_PORTALS' && (
          <StatePortalDirectory />
        )}

        {/* ============================================================ */}
        {/* VIEW 10: PRELIMINARY PROPERTY REPORT */}
        {/* ============================================================ */}
        {activeTab === 'REPORTS' && (
          <ReportGeneratorView onNavigateTab={setActiveTab} />
        )}

        {/* ============================================================ */}
        {/* VIEW 11: HELP & HOW IT WORKS */}
        {/* ============================================================ */}
        {activeTab === 'HELP' && (
          <HelpHowItWorksView 
            onNavigateTab={setActiveTab} 
            onOpenAiChat={() => onOpenAiChat?.()} 
          />
        )}

        {/* ============================================================ */}
        {/* VIEW 12: ABOUT BHUMISETU */}
        {/* ============================================================ */}
        {activeTab === 'ABOUT' && (
          <AboutPlatformView onNavigateTab={setActiveTab} />
        )}

        {/* ============================================================ */}
        {/* VIEW 3: GAZETTE NOTIFICATIONS */}
        {/* ============================================================ */}
        {activeTab === 'NOTICES' && (
          <div className="space-y-6">
            {/* Government Scheme Awareness Banner */}
            <div className="bg-gradient-to-r from-[#002642] via-[#0b3866] to-[#1e3a8a] text-white p-3.5 rounded-xs shadow-xs flex flex-wrap items-center justify-between gap-3 border border-blue-900">
              <div className="flex items-center gap-3">
                <div className="p-1 bg-white rounded-xs">
                  <NationalEmblem size={20} color="#002b49" showSlogan={false} />
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold tracking-wider text-sky-200">
                    {language === 'en' ? 'STATUTORY COMPLIANCE • MINISTRY OF RURAL DEVELOPMENT' : 'सांविधिक अनुपालन • ग्रामीण विकास मंत्रालय'}
                  </div>
                  <div className="font-bold text-xs text-white">
                    {language === 'en' 
                      ? 'RFCTLARR 2013 Statutory Guarantee: 100% Solatium plus 12% annual interest on all Gazette notified parcels' 
                      : 'भूसंपादन अधिनियम २०१३: सभी राजपत्र अधिसूचित भूखंडों पर १००% अनिवार्य सोलेशियम एवं १२% वार्षिक ब्याज'}
                  </div>
                </div>
              </div>
              <a
                href="https://bhoomirashi.gov.in"
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1 bg-[#f37021] hover:bg-[#d95d13] text-white font-bold text-xs rounded-xs flex items-center gap-1 shadow-xs transition-colors"
              >
                <span>{language === 'en' ? 'Bhoomi Rashi Portal' : 'भूमि राशि पोर्टल'}</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="swaas-card p-6 space-y-4">
              <div className="border-b border-slate-200 pb-3 flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold text-[#002642]">
                    Official Gazette Notifications Repository
                  </h2>
                  <p className="text-slate-500 text-xs mt-0.5">
                    Published under Sections 4, 11, 15, 19 and 23 of RFCTLARR Act 2013
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="gov-table">
                  <thead>
                    <tr>
                      <th>Notification No</th>
                      <th>Publication Date</th>
                      <th>Section / Subject</th>
                      <th>Corridor / Project</th>
                      <th>District</th>
                      <th>Statutory Window</th>
                      <th className="text-right">Official Document</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCases.map((c) => (
                      <tr key={c.id}>
                        <td className="font-mono font-bold text-[#0b3866]">
                          GAZ-GOI-2026-{(parseInt(c.id.replace(/\D/g, '')) * 382 + 104)}
                        </td>
                        <td className="font-medium text-slate-600">
                          {formatDate(c.stageDeadline)}
                        </td>
                        <td>
                          <span className="font-bold text-slate-800 block">
                            {c.stage.replace('STAGE_', '').replace(/_/g, ' ')}
                          </span>
                          <span className="text-[10px] text-slate-500">
                            Public notification for survey and acquisition
                          </span>
                        </td>
                        <td className="font-semibold text-[#002642]">
                          {c.projectName}
                        </td>
                        <td>{c.district}</td>
                        <td className="text-amber-800 font-semibold text-xs">
                          {c.daysRemaining} days remaining
                        </td>
                        <td className="text-right whitespace-nowrap">
                          <button
                            onClick={() => {
                              addToast({
                                type: 'info',
                                message: `Opening certified Gazette Notification for ${c.caseReference}`,
                              });
                            }}
                            className="px-3 py-1 bg-white border border-[#0b3866] text-[#0b3866] hover:bg-[#e8f1f8] font-semibold text-xs rounded-xs inline-flex items-center gap-1.5"
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>Gazette PDF (1.4 MB)</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 4: SECTION 15 OBJECTIONS & TRACKING */}
        {/* ============================================================ */}
        {activeTab === 'GRIEVANCE' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Form (8 cols) */}
              <div className="lg:col-span-8 swaas-card p-6 space-y-4">
                <div className="border-b border-slate-200 pb-3">
                  <h2 className="text-lg font-bold text-[#002642]">
                    File Public Objection under Section 15 of RFCTLARR Act, 2013
                  </h2>
                  <p className="text-slate-500 text-xs mt-0.5">
                    Any person interested in any land which has been notified under Section 11 may object within sixty days
                  </p>
                </div>

                {submittedTrackingId && (
                  <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-xs space-y-2">
                    <div className="font-bold text-emerald-800 flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                      <span>Objection Registered Successfully!</span>
                    </div>
                    <p className="text-xs text-emerald-700">
                      Acknowledgement Tracking Number: <strong className="font-mono">{submittedTrackingId}</strong>
                    </p>
                    <p className="text-[11px] text-slate-600">
                      Formal notice of hearing under Section 15(2) will be issued to your registered contact number.
                    </p>
                  </div>
                )}

                <form onSubmit={handleSubmitObjection} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">
                        Objector Full Name (खातेदाराचे नाव): *
                      </label>
                      <input
                        type="text"
                        required
                        value={objectorName}
                        onChange={(e) => setObjectorName(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded-xs text-xs font-medium focus:ring-1 focus:ring-[#0b3866]"
                      />
                    </div>

                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">
                        Mobile Contact Number: *
                      </label>
                      <input
                        type="text"
                        required
                        value={objectorContact}
                        onChange={(e) => setObjectorContact(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded-xs text-xs font-medium focus:ring-1 focus:ring-[#0b3866]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">
                        Select Project / Case: *
                      </label>
                      <select
                        value={selectedCaseForObjection}
                        onChange={(e) => setSelectedCaseForObjection(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded-xs text-xs font-medium bg-white"
                      >
                        {cases.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.caseReference} - {c.projectName}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">
                        Survey / Gat Number: *
                      </label>
                      <input
                        type="text"
                        required
                        value={surveyGat}
                        onChange={(e) => setSurveyGat(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded-xs text-xs font-medium"
                      />
                    </div>

                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">
                        Grounds of Objection: *
                      </label>
                      <select
                        value={groundsCategory}
                        onChange={(e) => setGroundsCategory(e.target.value as any)}
                        className="w-full p-2 border border-slate-300 rounded-xs text-xs font-medium bg-white"
                      >
                        <option value="Valuation & Compensation">Valuation &amp; Compensation Inadequacy</option>
                        <option value="Measurement / Boundary Dispute">Measurement / Cadastral Boundary Error</option>
                        <option value="Ownership / Title Claim">Ownership / Khatedar Title Claim</option>
                        <option value="Environmental / Religious Structure">Religious / Environmental Structure</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">
                      Detailed Substance of Objection &amp; Grounds (विस्तृत कारणे): *
                    </label>
                    <textarea
                      rows={4}
                      required
                      placeholder="Specify why the notified acquisition or market valuation is disputed under Section 15..."
                      value={objectionSubstance}
                      onChange={(e) => setObjectionSubstance(e.target.value)}
                      className="w-full p-2.5 border border-slate-300 rounded-xs text-xs focus:ring-1 focus:ring-[#0b3866]"
                    />
                  </div>

                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-[#0b3866]" />
                      <span className="text-xs font-semibold text-slate-700">
                        {attachedFile || 'No evidentiary file attached'}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setAttachedFile('registered_7_12_extract_survey142.pdf');
                        addToast({ type: 'info', message: 'Evidentiary proof document attached.' });
                      }}
                      className="px-3 py-1 bg-white border border-slate-300 hover:bg-slate-100 font-semibold text-xs rounded-xs"
                    >
                      Attach 7/12 or Deed
                    </button>
                  </div>

                  <button
                    type="submit"
                    className="px-6 py-2.5 bg-[#f37021] hover:bg-[#e05e10] text-white font-bold text-xs rounded-xs transition-colors flex items-center gap-2"
                  >
                    <Send className="w-4 h-4" />
                    <span>Submit Section 15 Objection</span>
                  </button>
                </form>
              </div>

              {/* Objection Status Tracker (4 cols) */}
              <div className="lg:col-span-4 space-y-6">
                <div className="swaas-card p-6 space-y-4">
                  <div className="border-b border-slate-200 pb-3">
                    <h3 className="font-bold text-sm text-[#002642]">
                      Track Status of Registered Objection
                    </h3>
                  </div>

                  <form onSubmit={handleTrackObjection} className="space-y-3">
                    <div>
                      <label className="font-semibold text-slate-700 block mb-1">
                        Acknowledgement / Case Reference:
                      </label>
                      <input
                        type="text"
                        required
                        value={trackAckNumber}
                        onChange={(e) => setTrackAckNumber(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded-xs text-xs font-mono font-bold"
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full py-2 bg-[#0b3866] hover:bg-[#082c52] text-white font-bold text-xs rounded-xs transition-colors"
                    >
                      Check Hearing Status
                    </button>
                  </form>

                  {trackResult && (
                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-xs space-y-2.5 text-xs">
                      <div className="font-bold text-[#002642] flex justify-between items-center">
                        <span>{trackResult.id}</span>
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-800 font-bold text-[10px] rounded-xs">
                          {trackResult.status}
                        </span>
                      </div>
                      <div className="text-slate-700">
                        <strong>Objector:</strong> {trackResult.objector}
                      </div>
                      <div className="text-slate-700">
                        <strong>Hearing Date:</strong> {trackResult.hearingDate}
                      </div>
                      <div className="text-slate-700">
                        <strong>Presiding Officer:</strong> {trackResult.officer}
                      </div>
                      <div className="text-[11px] text-slate-600 bg-white p-2 border border-slate-200 rounded-xs">
                        <strong>Officer Remarks:</strong> {trackResult.remarks}
                      </div>
                    </div>
                  )}
                </div>

                <div className="swaas-card p-4 space-y-2 border-l-4 border-l-[#138808]">
                  <h4 className="font-bold text-xs text-[#002642]">Section 15 Legal Safeguards:</h4>
                  <p className="text-[11px] text-slate-600">
                    The District Collector or Land Acquisition Officer (LAO) is statutorily mandated to give the objector an opportunity of being heard in person or by any person authorised by him before making any recommendation.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW: PROPERTY MAP INTELLIGENCE */}
        {/* ============================================================ */}
        {activeTab === 'GIS_MAP' && (
          <PropertyMapIntelligence onNavigateTab={setActiveTab} />
        )}

        {/* ============================================================ */}
        {/* VIEW 6: PROJECTS DIRECTORY */}
        {/* ============================================================ */}
        {activeTab === 'PROJECTS' && (
          <div className="space-y-6">
            <div className="swaas-card p-6 space-y-4">
              <div className="border-b border-slate-200 pb-3">
                <h2 className="text-lg font-bold text-[#002642]">
                  National Infrastructure Land Acquisition Corridors
                </h2>
                <p className="text-slate-500 text-xs mt-0.5">
                  Strategic highway, high-speed rail and industrial corridor projects under execution
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {MOCK_PROJECTS.map((p) => (
                  <div key={p.id} className="swaas-service-card space-y-3">
                    <div className="flex justify-between items-start">
                      <span className="text-[10px] font-bold text-[#0b3866] bg-[#e8f1f8] px-2 py-0.5 rounded-xs">
                        {p.id}
                      </span>
                      <span className="font-mono text-xs font-bold text-[#138808]">
                        {formatCurrencyINR(p.totalBudgetINR)}
                      </span>
                    </div>

                    <h3 className="font-bold text-sm text-[#002642]">{p.name}</h3>
                    <p className="text-xs text-slate-600">
                      {p.implementingAuthority} • {p.purposeCategory}
                    </p>

                    <div className="pt-2 border-t border-slate-100 flex justify-between text-[11px] text-slate-600">
                      <span>Sanctioned: <strong>{p.sanctionedExtentHa} Ha</strong></span>
                      <span>Cases: <strong>{p.activeCases} active / {p.totalCases} total</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 7: ACTS & RULES */}
        {/* ============================================================ */}
        {activeTab === 'ACTS_RULES' && (
          <div className="space-y-6">
            <div className="swaas-card p-6 space-y-4">
              <div className="border-b border-slate-200 pb-3">
                <h2 className="text-lg font-bold text-[#002642]">
                  Statutory Provisions &amp; RFCTLARR Act 2013 Reference
                </h2>
                <p className="text-slate-500 text-xs mt-0.5">
                  Key legal milestones governing compulsory land acquisition in India
                </p>
              </div>

              <div className="space-y-4 text-xs">
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                  <div className="font-bold text-sm text-[#0b3866]">Section 11: Preliminary Notification</div>
                  <p className="text-slate-700 leading-relaxed">
                    Whenever it appears to the appropriate Government that land in any area is required or likely to be required for any public purpose, a notification to that effect along with details of the land shall be published in the Official Gazette, in two daily newspapers, and in the local Panchayat / Municipality.
                  </p>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                  <div className="font-bold text-sm text-[#0b3866]">Section 15: Hearing of Objections</div>
                  <p className="text-slate-700 leading-relaxed">
                    Any person interested in any land which has been notified under Section 11 may, within sixty days from the date of publication, object to the area and suitability of the land proposed to be acquired, or the findings of the Social Impact Assessment report.
                  </p>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                  <div className="font-bold text-sm text-[#0b3866]">Section 19: Declaration of Acquisition</div>
                  <p className="text-slate-700 leading-relaxed">
                    When the appropriate Government is satisfied after considering the report made under Section 15 that any particular land is needed for a public purpose, a declaration shall be made to that effect within twelve months from the date of publication of the preliminary notification under Section 11.
                  </p>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                  <div className="font-bold text-sm text-[#0b3866]">Section 30: Statutory Solatium (100%)</div>
                  <p className="text-slate-700 leading-relaxed">
                    The Collector shall in every case award a solatium amount equivalent to one hundred per cent over and above the market value determined under Section 26, in consideration of the compulsory nature of the acquisition.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 8: CONTACT & FAQS */}
        {/* ============================================================ */}
        {activeTab === 'CONTACT' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-7 swaas-card p-6 space-y-4">
                <div className="border-b border-slate-200 pb-3">
                  <h2 className="text-lg font-bold text-[#002642]">Frequently Asked Questions (FAQs)</h2>
                </div>

                <div className="space-y-2">
                  {[
                    {
                      q: "What is the time limit for filing an objection under Section 15?",
                      a: "Under Section 15(1) of the RFCTLARR Act 2013, any interested landowner has exactly 60 days from the date of publication of the preliminary notification under Section 11 to submit an objection in writing."
                    },
                    {
                      q: "How is compensation calculated for rural versus urban lands?",
                      a: "Compensation begins with base market value. For rural areas, a statutory multiplier factor between 1.0 and 2.0 is applied based on distance from urban limits, followed by mandatory 100% Solatium and 12% annual interest."
                    },
                    {
                      q: "How does the DBT compensation payment reach my bank account?",
                      a: "Once the Collector signs the award under Section 23/30, payment orders are uploaded to the Public Financial Management System (PFMS) and routed directly to the verified Aadhaar-linked bank account of each Khatedar."
                    },
                    {
                      q: "What if my parcel boundary in BhuNaksha GIS differs from ground measurement?",
                      a: "Landowners can raise a measurement dispute u/s 15. The Sub-Divisional Officer / Survey Superintendent conducts a Joint Measurement Survey (JMS) with physical boundary stones (DGPS survey)."
                    }
                  ].map((faq, idx) => (
                    <div key={idx} className="border border-slate-200 rounded-xs overflow-hidden">
                      <button
                        onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                        className="w-full text-left p-3 bg-slate-50 hover:bg-slate-100 font-semibold text-xs text-[#002642] flex justify-between items-center transition-colors"
                      >
                        <span>{faq.q}</span>
                        <ChevronRight className={`w-4 h-4 transition-transform ${openFaq === idx ? 'rotate-90' : ''}`} />
                      </button>
                      {openFaq === idx && (
                        <div className="p-3 bg-white text-xs text-slate-700 leading-relaxed border-t border-slate-200">
                          {faq.a}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="lg:col-span-5 swaas-card p-6 space-y-4">
                <div className="border-b border-slate-200 pb-3">
                  <h3 className="font-bold text-sm text-[#002642]">Official Contact Directory</h3>
                </div>

                <div className="space-y-3 text-xs text-slate-700">
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                    <div className="font-bold text-[#002642]">Department of Land Resources (DoLR)</div>
                    <p className="text-slate-600">NBO Building, Nirman Bhawan, New Delhi - 110011</p>
                    <p className="text-slate-600">Email: support-bhumisetu@gov.in</p>
                  </div>

                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                    <div className="font-bold text-[#002642]">Competent Authority Land Acquisition (CALA) Pune</div>
                    <p className="text-slate-600">Collector Office, Bund Garden Road, Pune - 411001</p>
                    <p className="text-slate-600">Phone: 020-26123456</p>
                  </div>

                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                    <div className="font-bold text-[#002642]">National Informatics Centre (NIC) Helpdesk</div>
                    <p className="text-slate-600">Toll-Free Helpline: 1800-11-2013</p>
                    <p className="text-slate-600">Technical Support: nic-support@bhumisetu.gov.in</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Case Details Modal */}
      {selectedCaseForModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-2xs" role="dialog">
          <div className="bg-white border border-slate-300 max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-xl rounded-xs">
            <div className="bg-[#002642] text-white p-4 flex justify-between items-center border-b-2 border-[#f37021]">
              <div>
                <span className="font-mono text-xs text-amber-300 font-bold block">{selectedCaseForModal.caseReference}</span>
                <h3 className="font-bold text-sm text-white">{selectedCaseForModal.projectName}</h3>
              </div>
              <button
                onClick={() => setSelectedCaseDetailId(null)}
                className="px-2.5 py-1 bg-white/10 hover:bg-white/20 text-white font-bold text-xs rounded-xs"
              >
                ✕ Close
              </button>
            </div>

            <div className="p-6 space-y-5 text-xs">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xs">
                <div>
                  <div className="text-[10px] text-slate-500 font-semibold uppercase">Location</div>
                  <div className="font-bold text-slate-800">{selectedCaseForModal.village}, {selectedCaseForModal.tehsil}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 font-semibold uppercase">Total Extent</div>
                  <div className="font-bold text-slate-800">{selectedCaseForModal.totalExtentHa} Hectares</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 font-semibold uppercase">Total Award</div>
                  <div className="font-bold text-[#0b3866]">{formatCurrencyINR(selectedCaseForModal.totalAwardedAmount)}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 font-semibold uppercase">PFMS Disbursed</div>
                  <div className="font-bold text-[#138808]">{formatCurrencyINR(selectedCaseForModal.totalDisbursedAmount)}</div>
                </div>
              </div>

              <div>
                <h4 className="font-bold text-sm text-[#002642] mb-2">Notified Cadastral Parcels:</h4>
                <div className="overflow-x-auto">
                  <table className="gov-table">
                    <thead>
                      <tr>
                        <th>Gat / Survey</th>
                        <th>Khatedar Name</th>
                        <th>Classification</th>
                        <th>Area (Ha)</th>
                        <th>Base Value</th>
                        <th>100% Solatium</th>
                        <th>Total Compensation</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedCaseForModal.parcels.map(p => (
                        <tr key={p.id}>
                          <td className="font-mono font-bold text-[#0b3866]">{p.surveyNumber}</td>
                          <td className="font-semibold text-slate-800">{p.landownerName}</td>
                          <td>{p.classification}</td>
                          <td className="font-mono">{p.areaHectares}</td>
                          <td className="font-mono">{formatCurrencyINR(p.marketValuePerSqm * p.areaHectares * 10000)}</td>
                          <td className="font-mono text-amber-700">100% Mandated</td>
                          <td className="font-mono font-bold text-[#138808]">{formatCurrencyINR(p.compensationCalculated)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  onClick={() => {
                    setSelectedCaseForObjection(selectedCaseForModal.id);
                    setSelectedCaseDetailId(null);
                    setActiveTab('GRIEVANCE');
                  }}
                  className="px-4 py-2 bg-[#f37021] hover:bg-[#e05e10] text-white font-bold text-xs rounded-xs"
                >
                  File Section 15 Objection
                </button>
                <button
                  onClick={() => setSelectedCaseDetailId(null)}
                  className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold text-xs rounded-xs"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Official Government Scheme Details Modal */}
      {selectedSchemeDetail && (
        <GovSchemeModal
          scheme={selectedSchemeDetail}
          language={language}
          onClose={() => setSelectedSchemeDetail(null)}
        />
      )}
    </div>
  );
};
