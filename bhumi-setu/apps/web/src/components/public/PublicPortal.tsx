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
  Sparkles
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
import { SAMPLE_PROPERTY_DEMO, DemoProperty } from '../../data/landIntelligenceData';

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
      {/* 1. Official S3WaaS News Marquee Ticker */}
      <div className="bg-[#fff9e6] border-b border-[#ffd27f] text-slate-900 py-1.5 px-4 flex items-center gap-3">
        <div className="bg-[#f37021] text-white px-2.5 py-0.5 font-bold text-[11px] uppercase flex-shrink-0 flex items-center gap-1.5 rounded-xs shadow-xs">
          <span className="w-2 h-2 rounded-full bg-white animate-pulse"></span>
          <span>{language === 'en' ? "WHAT'S NEW" : 'नवीनतम'}</span>
        </div>
        <div className="overflow-hidden whitespace-nowrap flex-1 text-[11px] font-medium text-slate-800">
          <span className="animate-gov-marquee">
            📢 [28-Sept-2026] <strong>PM-KISAN</strong>: 17th Installment credited to 11.8 Cr farmers • 
            <strong>SVAMITVA</strong>: 1.65 Cr+ digital property cards issued via drone survey • 
            <strong>Jal Jeevan Mission</strong>: 15.2 Cr rural households connected with tap water • 
            <strong>PM GatiShakti</strong>: Cadastral PostGIS corridor synchronization live • 
            <strong>RFCTLARR 2013</strong>: Statutory 100% Solatium &amp; 12% interest guaranteed on all notified acquisitions • 
            Direct Benefit Transfer (DBT) compensation disbursed to 1,420 Khatedars via PFMS.
          </span>
        </div>
        <button
          onClick={() => setActiveTab('SCHEMES')}
          className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 bg-[#002642] hover:bg-[#0b3866] text-white text-[11px] font-bold rounded-xs flex-shrink-0 transition-colors cursor-pointer"
        >
          <Landmark className="w-3.5 h-3.5 text-amber-300" />
          <span>{language === 'en' ? 'Flagship Schemes' : 'प्रमुख योजनाएं'}</span>
        </button>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-8">
        {/* ============================================================ */}
        {/* VIEW 1: HOME (S3WaaS STANDARD GOVERNMENT PORTAL HOMEPAGE) */}
        {/* ============================================================ */}
        {activeTab === 'HOME' && (
          <div className="space-y-8">
            {/* 1. Central Hero Rotating Background Carousel with PM Modi Cutout & 9 Schemes */}
            <HeroRotatingBanner onNavigate={setActiveTab} />

            {/* 2. Dashboard Statistics Cards (Section 16) */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-left">
              <div className="bg-white p-4 rounded-xs border border-slate-300 shadow-2xs">
                <span className="text-[10px] uppercase font-bold text-slate-400">States &amp; UTs Covered</span>
                <div className="text-xl sm:text-2xl font-black text-[#002642] mt-1">28 States + 8 UTs</div>
                <div className="text-[10px] text-amber-700 font-semibold mt-0.5 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                  <span>Demo State Directory</span>
                </div>
              </div>

              <div className="bg-white p-4 rounded-xs border border-slate-300 shadow-2xs">
                <span className="text-[10px] uppercase font-bold text-slate-400">Land Records Integrated</span>
                <div className="text-xl sm:text-2xl font-black text-[#002642] mt-1">Prototype Layer</div>
                <div className="text-[10px] text-emerald-700 font-semibold mt-0.5 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  <span>RoR + GIS + ULPIN</span>
                </div>
              </div>

              <div className="bg-white p-4 rounded-xs border border-slate-300 shadow-2xs">
                <span className="text-[10px] uppercase font-bold text-slate-400">Digital Services</span>
                <div className="text-xl sm:text-2xl font-black text-[#002642] mt-1">12+ Workflows</div>
                <div className="text-[10px] text-blue-700 font-semibold mt-0.5 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                  <span>Mutation, Search, OCR</span>
                </div>
              </div>

              <div className="bg-white p-4 rounded-xs border border-slate-300 shadow-2xs">
                <span className="text-[10px] uppercase font-bold text-slate-400">Document Types Supported</span>
                <div className="text-xl sm:text-2xl font-black text-[#002642] mt-1">8+ Formats</div>
                <div className="text-[10px] text-purple-700 font-semibold mt-0.5 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
                  <span>7/12, RoR, Deeds, Khasra</span>
                </div>
              </div>
            </div>

            {/* 3. Core Product USP Section: ONE PROPERTY — ONE INTELLIGENCE VIEW (Section 23) */}
            <div className="bg-gradient-to-r from-[#002642] via-[#0b3866] to-[#00172d] text-white p-6 rounded-xs border-l-4 border-l-[#f37021] text-left shadow-md space-y-4">
              <div className="flex flex-wrap justify-between items-center gap-2">
                <div>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-[#f37021] text-white">
                    CENTRAL PLATFORM USP
                  </span>
                  <h3 className="text-lg sm:text-xl font-black tracking-tight text-white mt-1">
                    “ONE PROPERTY — ONE INTELLIGENCE VIEW”
                  </h3>
                </div>
                <button
                  onClick={() => setActiveTab('PROPERTY_INTEL')}
                  className="px-4 py-2 bg-white text-[#002642] hover:bg-slate-100 font-extrabold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors"
                >
                  <span>Open Intelligence Dashboard</span>
                  <ChevronRight className="w-3.5 h-3.5 text-[#f37021]" />
                </button>
              </div>

              <p className="text-xs text-slate-200 max-w-3xl leading-relaxed">
                Instead of forcing a citizen to navigate multiple disconnected portals, BHUMISETU unifies:
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 text-center text-xs">
                {[
                  { title: 'Land Record', sub: '7/12 & RoR' },
                  { title: 'Cadastral Map', sub: 'BhuNaksha' },
                  { title: '14-Digit ULPIN', sub: 'Bhu-Aadhaar' },
                  { title: 'Registration', sub: 'Index-II Deeds' },
                  { title: 'Mutation', sub: 'Ferfar Tracker' },
                  { title: 'AI OCR Docs', sub: 'Vision Extract' },
                  { title: 'Timeline', sub: '2018–2026' },
                  { title: 'Risk Analysis', sub: '12 Checks' }
                ].map((item, idx) => (
                  <div key={idx} className="p-2 bg-white/10 hover:bg-white/20 rounded-xs border border-white/15 transition-colors">
                    <div className="font-extrabold text-white text-[11px]">{item.title}</div>
                    <div className="text-[9px] text-amber-300 mt-0.5">{item.sub}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* 4. 4 Primary Citizen Action Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <button
                onClick={() => setActiveTab('SEARCH')}
                className="p-4 bg-white text-left text-slate-800 rounded-xs shadow-xs hover:shadow-md transition-all border-t-3 border-[#002642] hover:-translate-y-0.5 group"
              >
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 rounded-xs bg-[#e8f1f8] text-[#002642] flex items-center justify-center font-bold">
                    <Search className="w-5 h-5 text-[#002642]" />
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-[#002642] transition-colors" />
                </div>
                <div className="mt-3 font-bold text-sm text-[#002642]">
                  {language === 'en' ? 'Unified Land Search' : 'भू-अभिलेख खोजें'}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  State → District → Village → Survey / ULPIN
                </div>
              </button>

              <button
                onClick={() => setActiveTab('DOC_VERIFY')}
                className="p-4 bg-white text-left text-slate-800 rounded-xs shadow-xs hover:shadow-md transition-all border-t-3 border-[#f37021] hover:-translate-y-0.5 group"
              >
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 rounded-xs bg-amber-50 text-[#f37021] flex items-center justify-center font-bold">
                    <FileCheck className="w-5 h-5 text-[#f37021]" />
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-[#f37021] transition-colors" />
                </div>
                <div className="mt-3 font-bold text-sm text-[#002642]">
                  {language === 'en' ? 'AI Document Verification' : 'दस्तावेज सत्यापन'}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  OCR extraction &amp; cross-comparison
                </div>
              </button>

              <button
                onClick={() => setActiveTab('MUTATION')}
                className="p-4 bg-white text-left text-slate-800 rounded-xs shadow-xs hover:shadow-md transition-all border-t-3 border-[#138808] hover:-translate-y-0.5 group"
              >
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 rounded-xs bg-emerald-50 text-[#138808] flex items-center justify-center font-bold">
                    <Clock className="w-5 h-5 text-[#138808]" />
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-[#138808] transition-colors" />
                </div>
                <div className="mt-3 font-bold text-sm text-[#002642]">
                  {language === 'en' ? 'Track Mutation' : 'दाखिल-खारिज स्थिति'}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  Real-time status for MUT-MH-2026-001245
                </div>
              </button>

              <button
                onClick={() => setActiveTab('GIS_MAP')}
                className="p-4 bg-white text-left text-slate-800 rounded-xs shadow-xs hover:shadow-md transition-all border-t-3 border-sky-600 hover:-translate-y-0.5 group"
              >
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 rounded-xs bg-sky-50 text-sky-600 flex items-center justify-center font-bold">
                    <Map className="w-5 h-5 text-sky-600" />
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-sky-600 transition-colors" />
                </div>
                <div className="mt-3 font-bold text-sm text-[#002642]">
                  {language === 'en' ? 'Cadastral GIS Map' : 'भू-नक्शा GIS'}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  Inspect parcel boundaries &amp; infrastructure
                </div>
              </button>
            </div>

            {/* 5. Security & Privacy Principles Section (Section 17) */}
            <div className="bg-white border border-slate-300 rounded-xs p-5 shadow-xs text-xs text-left space-y-3">
              <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
                <ShieldCheck className="w-4 h-4 text-[#138808]" />
                <h4 className="font-extrabold text-xs uppercase tracking-wide text-[#002642]">
                  Security, Privacy &amp; Data Governance Principles (DPDP Act 2023)
                </h4>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-slate-600 text-[11px]">
                <div className="p-2.5 bg-slate-50 rounded-xs border border-slate-200">
                  <strong className="text-slate-800 block mb-0.5">Masked Personal Identifiers:</strong>
                  Real landowner names and Aadhaar numbers are never displayed publicly. Fictional sample records are utilized.
                </div>
                <div className="p-2.5 bg-slate-50 rounded-xs border border-slate-200">
                  <strong className="text-slate-800 block mb-0.5">Zero Permanent Storage:</strong>
                  Uploaded deeds and 7/12 extracts are processed in-memory for OCR extraction and are immediately discarded.
                </div>
                <div className="p-2.5 bg-slate-50 rounded-xs border border-slate-200">
                  <strong className="text-slate-800 block mb-0.5">Non-Legal Preliminary Status:</strong>
                  All findings are labeled as preliminary variances. They do not constitute official title certification or legal advice.
                </div>
                <div className="p-2.5 bg-slate-50 rounded-xs border border-slate-200">
                  <strong className="text-slate-800 block mb-0.5">Authentic Gateways Only:</strong>
                  We direct citizens exclusively to verified state revenue URLs (Mahabhulekh, AnyRoR, Bhoomi, UP Bhulekh).
                </div>
              </div>
            </div>

            {/* 2026 GIGW 3.0 Accessible Horizontally Scrolling Government Schemes Banner */}
            <GigwSchemeScrollBanner 
              language={language}
              onSelectScheme={(scheme) => setSelectedSchemeDetail(scheme)}
            />

            {/* PM National Land Reforms & Infrastructure Mission Showcase */}
            <div className="bg-white border border-slate-300 rounded-xs shadow-xs overflow-hidden">
              <div className="tiranga-strip"></div>
              <div className="grid grid-cols-1 lg:grid-cols-12 items-center">
                {/* Left: Official Photograph of PM Narendra Modi at Development Dedication */}
                <div className="lg:col-span-5 relative overflow-hidden bg-slate-900 h-64 lg:h-full min-h-[240px]">
                  <img 
                    src="/assets/pm_modi_event.jpg" 
                    alt={language === 'en' ? 'Prime Minister Narendra Modi dedicating national infrastructure projects' : 'प्रधानमंत्री नरेन्द्र मोदी राष्ट्र को विकास परियोजनाएं समर्पित करते हुए'} 
                    className="w-full h-full object-cover object-center"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent flex flex-col justify-end p-4">
                    <span className="px-2 py-0.5 bg-[#f37021] text-white font-extrabold text-[9px] uppercase rounded-xs w-max mb-1">
                      {language === 'en' ? 'National Mission' : 'राष्ट्रीय मिशन'}
                    </span>
                    <h4 className="text-white font-bold text-sm leading-tight">
                      {language === 'en' ? 'Empowering Citizens Through Digitized Land Governance' : 'डिजिटल भू-प्रशासन से नागरिकों का सशक्तिकरण'}
                    </h4>
                    <p className="text-slate-300 text-[10px] mt-0.5">
                      {language === 'en' ? 'PM Narendra Modi dedicating key national corridors & SVAMITVA cards' : 'माननीय प्रधानमंत्री द्वारा राष्ट्रीय गलियारों एवं स्वामित्व संपत्ति पत्रकों का लोकार्पण'}
                    </p>
                  </div>
                </div>

                {/* Right: Key Statutory Pillars & Directives */}
                <div className="lg:col-span-7 p-5 sm:p-6 space-y-4 text-left">
                  <div className="flex items-center gap-2">
                    <img 
                      src="/assets/pm_modi_2023.jpg" 
                      alt="PM Modi Avatar" 
                      className="w-9 h-9 rounded-full object-cover object-top border-2 border-[#f37021] shadow-2xs"
                    />
                    <div>
                      <div className="text-xs font-bold text-[#002642]">
                        {language === 'en' ? 'Prime Minister’s 4-Point Citizen Guarantee' : 'प्रधानमंत्री जी की ४-सूत्रीय नागरिक गारंटी'}
                      </div>
                      <div className="text-[10px] text-slate-500 font-medium">
                        {language === 'en' ? 'RFCTLARR Act 2013 & Digital India Land Reforms' : 'आरएफ़सीटीएलएआरआर अधिनियम २०१३ एवं डिजिटल भारत भू-सुधार'}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-amber-50/70 border-l-3 border-[#f37021] rounded-xs">
                      <div className="font-bold text-[#c2410c] text-[11px] flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[#f37021]" />
                        <span>{language === 'en' ? '100% DBT Compensation' : '१००% प्रत्यक्ष बैंक अंतरण'}</span>
                      </div>
                      <p className="text-[10px] text-slate-600 mt-1">
                        {language === 'en' ? 'Direct crediting to Aadhaar-linked accounts via PFMS, zero intermediaries.' : 'पीएफएमएस के माध्यम से सीधे आधार-संबद्ध बैंक खातों में भुगतान, पूर्ण पारदर्शिता।'}
                      </p>
                    </div>

                    <div className="p-3 bg-blue-50/70 border-l-3 border-[#0b3866] rounded-xs">
                      <div className="font-bold text-[#0b3866] text-[11px] flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[#0b3866]" />
                        <span>{language === 'en' ? 'Statutory Solatium & Interest' : 'सांविधिक तोषण एवं ब्याज'}</span>
                      </div>
                      <p className="text-[10px] text-slate-600 mt-1">
                        {language === 'en' ? 'Mandatory 100% solatium and 12% annual interest on market value guaranteed.' : 'बाजार मूल्य पर अनिवार्य १००% तोषण एवं १२% वार्षिक ब्याज की कानूनी गारंटी।'}
                      </p>
                    </div>

                    <div className="p-3 bg-emerald-50/70 border-l-3 border-[#138808] rounded-xs">
                      <div className="font-bold text-[#138808] text-[11px] flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[#138808]" />
                        <span>{language === 'en' ? 'Drone Cadastral Mapping' : 'ड्रोन आधारित डिजिटल नक्शा'}</span>
                      </div>
                      <p className="text-[10px] text-slate-600 mt-1">
                        {language === 'en' ? 'Sub-centimeter GIS boundary precision under SVAMITVA for boundary dispute elimination.' : 'स्वामित्व योजना अंतर्गत उप-सेंटीमीटर जीआईएस सटीकता से सीमा विवादों का उन्मूलन।'}
                      </p>
                    </div>

                    <div className="p-3 bg-purple-50/70 border-l-3 border-[#6b21a8] rounded-xs">
                      <div className="font-bold text-[#6b21a8] text-[11px] flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[#6b21a8]" />
                        <span>{language === 'en' ? 'Time-Bound Sec 15 Disposal' : 'समयबद्ध आपत्ति निस्तारण'}</span>
                      </div>
                      <p className="text-[10px] text-slate-600 mt-1">
                        {language === 'en' ? '60-day statutory window with mandatory personal hearing by Collector.' : 'कलेक्टर द्वारा व्यक्तिगत सुनवाई के साथ ६० दिनों की वैधानिक समय-सीमा।'}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* S3WaaS National Statistics Strip */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="swaas-card p-4 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xs bg-[#e8f1f8] flex items-center justify-center text-[#0b3866] flex-shrink-0">
                  <FolderKanban className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-2xl font-bold font-mono text-[#002642]">128</div>
                  <div className="text-xs font-semibold text-slate-600">
                    {language === 'en' ? 'Active Projects' : 'सक्रिय परियोजनाएं'}
                  </div>
                  <div className="text-[10px] text-slate-400">Highways, Rail &amp; Energy</div>
                </div>
              </div>

              <div className="swaas-card p-4 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xs bg-amber-50 flex items-center justify-center text-[#f37021] flex-shrink-0">
                  <Layers className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-2xl font-bold font-mono text-[#002642]">42,850 Ha</div>
                  <div className="text-xs font-semibold text-slate-600">
                    {language === 'en' ? 'Land Notified' : 'अधिसूचित कुल भूमि'}
                  </div>
                  <div className="text-[10px] text-slate-400">Section 11 Gazette decrees</div>
                </div>
              </div>

              <div className="swaas-card p-4 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xs bg-emerald-50 flex items-center justify-center text-[#138808] flex-shrink-0">
                  <IndianRupee className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-2xl font-bold font-mono text-[#138808]">₹ 14,820 Cr</div>
                  <div className="text-xs font-semibold text-slate-600">
                    {language === 'en' ? 'Disbursed via PFMS' : 'प्रत्यक्ष बैंक अंतरण'}
                  </div>
                  <div className="text-[10px] text-slate-400">1,84,320 Khatedar Families</div>
                </div>
              </div>

              <div className="swaas-card p-4 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xs bg-blue-50 flex items-center justify-center text-[#0b3866] flex-shrink-0">
                  <FileCheck className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-2xl font-bold font-mono text-[#f37021]">94.8%</div>
                  <div className="text-xs font-semibold text-slate-600">
                    {language === 'en' ? 'Sec 15 Disposal' : 'आपत्ति निराकरण दर'}
                  </div>
                  <div className="text-[10px] text-slate-400">Time-bound Collector orders</div>
                </div>
              </div>
            </div>

            {/* S3WaaS Main Two-Column Body */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column (8 cols): S3WaaS Tabbed Updates Hub & Statutory Lifecycle */}
              <div className="lg:col-span-8 space-y-6">
                {/* S3WaaS Standard Tabbed Updates Hub */}
                <div className="swaas-card overflow-hidden">
                  <div className="border-b border-slate-200 bg-slate-50 flex items-center justify-between px-2 sm:px-4">
                    <div className="flex">
                      <button
                        onClick={() => setHomeNoticeTab('GAZETTE')}
                        className={`swaas-tab-btn ${homeNoticeTab === 'GAZETTE' ? 'active' : ''}`}
                      >
                        {language === 'en' ? 'Gazette Notifications' : 'राजपत्र अधिसूचनाएं'}
                      </button>
                      <button
                        onClick={() => setHomeNoticeTab('HEARINGS')}
                        className={`swaas-tab-btn ${homeNoticeTab === 'HEARINGS' ? 'active' : ''}`}
                      >
                        {language === 'en' ? 'Public Hearings (Sec 15)' : 'सार्वजनिक सुनवाई'}
                      </button>
                      <button
                        onClick={() => setHomeNoticeTab('ORDERS')}
                        className={`swaas-tab-btn ${homeNoticeTab === 'ORDERS' ? 'active' : ''}`}
                      >
                        {language === 'en' ? 'Circulars & Rules' : 'परिपत्र व आदेश'}
                      </button>
                    </div>

                    <button
                      onClick={() => setActiveTab('NOTICES')}
                      className="text-[11px] text-[#0b3866] hover:text-[#f37021] font-bold hidden sm:inline"
                    >
                      {language === 'en' ? 'View Archive →' : 'पुरालेख देखें →'}
                    </button>
                  </div>

                  <div className="p-0">
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
                        {filteredCases.slice(0, 5).map((c) => (
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
                                className="px-2.5 py-1 text-xs font-semibold bg-[#e8f1f8] hover:bg-[#0b3866] text-[#0b3866] hover:text-white rounded-xs transition-colors inline-flex items-center gap-1"
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

                  <div className="p-3 bg-slate-50 border-t border-slate-200 text-center">
                    <button
                      onClick={() => setActiveTab('NOTICES')}
                      className="text-xs font-bold text-[#0b3866] hover:underline"
                    >
                      {language === 'en' ? 'View All Official Gazette Publications (4,892 Records) →' : 'सभी राजपत्र अधिसूचनाएं देखें (४,८९२ अभिलेख) →'}
                    </button>
                  </div>
                </div>

                {/* Statutory Acquisition Lifecycle (RFCTLARR Act 2013) */}
                <div className="swaas-card p-5 space-y-4">
                  <div className="border-b border-slate-200 pb-2">
                    <h3 className="font-bold text-sm text-[#002642] flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-[#138808]" />
                      <span>{language === 'en' ? 'Statutory Land Acquisition Process (RFCTLARR Act, 2013)' : 'सांविधिक भूमि अधिग्रहण प्रक्रिया (अधिनियम २०१३)'}</span>
                    </h3>
                    <p className="text-slate-500 text-xs mt-0.5">
                      Mandatory statutory milestones ensuring transparent, time-bound legal compliance
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 bg-slate-50 border-l-3 border-[#0b3866] rounded-xs space-y-1">
                      <div className="text-[10px] font-bold text-[#0b3866] uppercase">Stage 1</div>
                      <div className="font-bold text-slate-800">Section 11 Notice</div>
                      <p className="text-[11px] text-slate-600">
                        Preliminary notification &amp; Social Impact Assessment (SIA) published in Official Gazette.
                      </p>
                    </div>

                    <div className="p-3 bg-amber-50/60 border-l-3 border-[#f37021] rounded-xs space-y-1">
                      <div className="text-[10px] font-bold text-[#f37021] uppercase">Stage 2 (60 Days)</div>
                      <div className="font-bold text-slate-800">Section 15 Objections</div>
                      <p className="text-[11px] text-slate-600">
                        Statutory 60-day window for landholders to register objections and seek formal hearing.
                      </p>
                    </div>

                    <div className="p-3 bg-slate-50 border-l-3 border-[#0b3866] rounded-xs space-y-1">
                      <div className="text-[10px] font-bold text-[#0b3866] uppercase">Stage 3 (12 Months)</div>
                      <div className="font-bold text-slate-800">Section 19 Declaration</div>
                      <p className="text-[11px] text-slate-600">
                        Final declaration of land required for public purpose after disposal of all objections.
                      </p>
                    </div>

                    <div className="p-3 bg-emerald-50/60 border-l-3 border-[#138808] rounded-xs space-y-1">
                      <div className="text-[10px] font-bold text-[#138808] uppercase">Stage 4</div>
                      <div className="font-bold text-slate-800">Section 23 &amp; DBT Award</div>
                      <p className="text-[11px] text-slate-600">
                        Award determination with 100% statutory solatium &amp; direct bank transfer via PFMS.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column (4 cols): Quick Search, Statutory Protections & Support */}
              <div className="lg:col-span-4 space-y-6">
                {/* S3WaaS Quick Search Card */}
                <div className="swaas-card p-4 space-y-3">
                  <div className="border-b border-slate-200 pb-2">
                    <h3 className="font-bold text-sm text-[#002642] flex items-center gap-1.5">
                      <Search className="w-4 h-4 text-[#f37021]" />
                      <span>{language === 'en' ? 'Quick Record Search' : 'त्वरित अभिलेख खोज'}</span>
                    </h3>
                  </div>

                  <div className="space-y-2.5">
                    <div>
                      <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                        Select District:
                      </label>
                      <select
                        value={searchDistrict}
                        onChange={(e) => setSearchDistrict(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded-xs bg-white text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[#0b3866]"
                      >
                        <option value="ALL">-- All Districts (महाराष्ट्र) --</option>
                        <option value="Pune">Pune (पुणे)</option>
                        <option value="Nashik">Nashik (नासिक)</option>
                        <option value="Solapur">Solapur (सोलापूर)</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                        Survey / Gat Number:
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. 142/A, 201/1"
                        value={searchGatNumber}
                        onChange={(e) => setSearchGatNumber(e.target.value)}
                        className="w-full p-2 border border-slate-300 rounded-xs bg-white text-xs focus:outline-none focus:ring-1 focus:ring-[#0b3866]"
                      />
                    </div>

                    <button
                      onClick={() => setActiveTab('SEARCH')}
                      className="w-full py-2 bg-[#0b3866] hover:bg-[#082c52] text-white font-bold text-xs rounded-xs transition-colors flex items-center justify-center gap-1.5"
                    >
                      <Search className="w-3.5 h-3.5" />
                      <span>{language === 'en' ? 'Search Database' : 'अभिलेख खोजें'}</span>
                    </button>
                  </div>
                </div>

                {/* Government Scheme Sidebar Ad Banner: SVAMITVA Scheme */}
                <GovSchemeSidebarAd schemeCode="SVAMITVA" language={language} />

                {/* Statutory Rights of Landowners Card */}
                <div className="swaas-card p-4 space-y-3 bg-[#fdfdfd]">
                  <div className="border-b border-slate-200 pb-2">
                    <h3 className="font-bold text-sm text-[#002642] flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-[#138808]" />
                      <span>{language === 'en' ? 'Statutory Landowner Rights' : 'भूस्वामी सांविधिक अधिकार'}</span>
                    </h3>
                  </div>

                  <ul className="space-y-2 text-[11px] text-slate-700">
                    <li className="flex items-start gap-2">
                      <Check className="w-4 h-4 text-[#138808] flex-shrink-0 mt-0.5" />
                      <span><strong>100% Solatium:</strong> Mandated 100% equivalent solatium added to basic land value u/s 30.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="w-4 h-4 text-[#138808] flex-shrink-0 mt-0.5" />
                      <span><strong>12% Interest:</strong> Additional 12% per annum from preliminary notification date till award.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="w-4 h-4 text-[#138808] flex-shrink-0 mt-0.5" />
                      <span><strong>60-Day Hearing Right:</strong> Section 15 objection right before District Collector / LAO.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="w-4 h-4 text-[#138808] flex-shrink-0 mt-0.5" />
                      <span><strong>Direct PFMS DBT:</strong> Payout sent directly to Aadhaar-seeded bank account with zero cuts.</span>
                    </li>
                  </ul>
                </div>

                {/* Government Scheme Sidebar Ad Banner: PM-KISAN */}
                <GovSchemeSidebarAd schemeCode="PM-KISAN" language={language} />

                {/* S3WaaS Toll-Free Helpdesk Card */}
                <div className="swaas-card p-4 space-y-2 border-l-4 border-l-[#f37021]">
                  <div className="font-bold text-xs text-[#002642] flex items-center gap-2">
                    <Phone className="w-4 h-4 text-[#f37021]" />
                    <span>{language === 'en' ? 'Landowner Assistance Helpline' : 'भूस्वामी सहायता केंद्र'}</span>
                  </div>
                  <div className="text-xl font-bold font-mono text-[#0b3866]">
                    1800-11-2013
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Monday to Friday, 9:00 AM – 6:00 PM (Toll-Free, Ministry of Rural Development)
                  </p>
                </div>
              </div>
            </div>

            {/* National Flagship Schemes & Citizen Initiatives Ad Grid */}
            <GovSchemeAdGrid language={language} />

            {/* Allied Government Portals Grid (S3WaaS Standard Integration Hub) */}
            <div className="swaas-card p-5 space-y-3">
              <div className="border-b border-slate-200 pb-2 flex justify-between items-center">
                <span className="font-bold text-xs text-[#002642] tracking-wide uppercase flex items-center gap-1.5">
                  <Landmark className="w-4 h-4 text-[#f37021]" />
                  <span>{language === 'en' ? 'ALLIED GOVERNMENT OF INDIA PORTALS' : 'संबद्ध राष्ट्रीय पोर्टल'}</span>
                </span>
                <span className="text-[10px] text-slate-400">National Single Window Integrations</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <a 
                  href="https://bhoomirashi.gov.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200 hover:border-[#0b3866] transition-all text-center rounded-xs block group"
                >
                  <div className="text-[11px] font-bold text-[#0b3866] group-hover:text-[#f37021]">BHOOMI RASHI</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">MoRTH Highways</div>
                </a>

                <a 
                  href="https://gatishakti.gov.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200 hover:border-[#0b3866] transition-all text-center rounded-xs block group"
                >
                  <div className="text-[11px] font-bold text-[#138808] group-hover:text-[#f37021]">PM GATI SHAKTI</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">National Master Plan</div>
                </a>

                <a 
                  href="https://bhunaksha.gov.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200 hover:border-[#0b3866] transition-all text-center rounded-xs block group"
                >
                  <div className="text-[11px] font-bold text-[#0b3866] group-hover:text-[#f37021]">BHUNAKSHA (NIC)</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Cadastral Maps</div>
                </a>

                <a 
                  href="https://mahabhulekh.maharashtra.gov.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200 hover:border-[#0b3866] transition-all text-center rounded-xs block group"
                >
                  <div className="text-[11px] font-bold text-[#0b3866] group-hover:text-[#f37021]">MAHABHULEKH</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">7/12 Land Records</div>
                </a>

                <a 
                  href="https://pfms.nic.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200 hover:border-[#0b3866] transition-all text-center rounded-xs block group"
                >
                  <div className="text-[11px] font-bold text-[#0b3866] group-hover:text-[#f37021]">PFMS DBT</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Public Finance</div>
                </a>

                <a 
                  href="https://dilrmp.gov.in" 
                  target="_blank" 
                  rel="noreferrer"
                  className="p-3 bg-slate-50 hover:bg-white border border-slate-200 hover:border-[#0b3866] transition-all text-center rounded-xs block group"
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
