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

interface PublicPortalProps {
  activeTab: PublicTab;
  setActiveTab: (tab: PublicTab) => void;
  onNavigateToOfficerCase?: (caseId: string) => void;
}

export const PublicPortal: React.FC<PublicPortalProps> = ({ 
  activeTab, 
  setActiveTab,
  onNavigateToOfficerCase
}) => {
  const { cases, submitCitizenObjection, language, addToast } = useApp();

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
            {/* S3WaaS Standard Hero Section */}
            <div className="relative overflow-hidden rounded-xs border border-slate-200 bg-gradient-to-r from-[#002642] via-[#0b3866] to-[#134679] text-white shadow-sm">
              <div className="p-6 sm:p-10 relative z-10 space-y-4">
                <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-xs border border-white/20 px-3 py-1 rounded-xs text-[11px] font-semibold text-amber-300">
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-300" />
                  <span>RFCTLARR ACT, 2013 • STATUTORY E-GOVERNANCE SYSTEM</span>
                </div>

                <div className="max-w-3xl space-y-2">
                  <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-tight">
                    {language === 'en'
                      ? 'National Land Acquisition Management & Compensation Tracking Portal'
                      : 'राष्ट्रीय भूमि अधिग्रहण, मुआवजा निर्धारण एवं पुनर्वास प्रबंधन पोर्टल'}
                  </h2>
                  <p className="text-slate-200 text-xs sm:text-sm leading-relaxed max-w-2xl">
                    {language === 'en'
                      ? 'The single-window digital platform of the Government of India for transparent, time-bound land acquisition under the Right to Fair Compensation and Transparency in Land Acquisition, Rehabilitation and Resettlement Act, 2013.'
                      : 'भूमि अधिग्रहण में उचित मुआवजा एवं पारदर्शिता का अधिकार अधिनियम, २०१३ के अंतर्गत भूमि अधिग्रहण अधिसूचनाओं, धारा १५ आपत्तियों एवं प्रत्यक्ष बैंक अंतरण का आधिकारिक राष्ट्रीय पोर्टल।'}
                  </p>
                </div>

                {/* S3WaaS 4 Primary Action Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4">
                  <button
                    onClick={() => setActiveTab('SEARCH')}
                    className="p-4 bg-white text-left text-slate-800 rounded-xs shadow-sm hover:shadow-md transition-all border-t-3 border-[#0b3866] hover:-translate-y-0.5 group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="w-9 h-9 rounded-xs bg-[#e8f1f8] text-[#0b3866] flex items-center justify-center font-bold">
                        <Search className="w-5 h-5 text-[#0b3866]" />
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-[#0b3866] transition-colors" />
                    </div>
                    <div className="mt-3 font-bold text-sm text-[#002642]">
                      {language === 'en' ? 'Search Land Records' : 'भू-अभिलेख खोजें'}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {language === 'en' ? 'Check Gat/Survey numbers & notices' : 'सर्वे क्रमांक एवं अधिसूचना देखें'}
                    </div>
                  </button>

                  <button
                    onClick={() => setActiveTab('NOTICES')}
                    className="p-4 bg-white text-left text-slate-800 rounded-xs shadow-sm hover:shadow-md transition-all border-t-3 border-[#f37021] hover:-translate-y-0.5 group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="w-9 h-9 rounded-xs bg-amber-50 text-[#f37021] flex items-center justify-center font-bold">
                        <FileText className="w-5 h-5 text-[#f37021]" />
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-[#f37021] transition-colors" />
                    </div>
                    <div className="mt-3 font-bold text-sm text-[#002642]">
                      {language === 'en' ? 'Gazette Notifications' : 'राजपत्र अधिसूचनाएं'}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {language === 'en' ? 'Sec 11, Sec 19 & Award decrees' : 'धारा ११, धारा १९ एवं अधिनिर्णय'}
                    </div>
                  </button>

                  <button
                    onClick={() => setActiveTab('GRIEVANCE')}
                    className="p-4 bg-white text-left text-slate-800 rounded-xs shadow-sm hover:shadow-md transition-all border-t-3 border-[#138808] hover:-translate-y-0.5 group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="w-9 h-9 rounded-xs bg-emerald-50 text-[#138808] flex items-center justify-center font-bold">
                        <AlertCircle className="w-5 h-5 text-[#138808]" />
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-[#138808] transition-colors" />
                    </div>
                    <div className="mt-3 font-bold text-sm text-[#002642]">
                      {language === 'en' ? 'Section 15 Objections' : 'धारा १५ आपत्ति'}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {language === 'en' ? 'File hearing claims within 60 days' : '६० दिवस में आपत्ति दर्ज करें'}
                    </div>
                  </button>

                  <button
                    onClick={() => setActiveTab('GIS_MAP')}
                    className="p-4 bg-white text-left text-slate-800 rounded-xs shadow-sm hover:shadow-md transition-all border-t-3 border-[#0b3866] hover:-translate-y-0.5 group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="w-9 h-9 rounded-xs bg-[#e8f1f8] text-[#0b3866] flex items-center justify-center font-bold">
                        <Map className="w-5 h-5 text-[#0b3866]" />
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-[#0b3866] transition-colors" />
                    </div>
                    <div className="mt-3 font-bold text-sm text-[#002642]">
                      {language === 'en' ? 'Cadastral GIS Map' : 'भू-नक्शा / GIS'}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {language === 'en' ? 'Inspect parcel spatial polygons' : 'भूखंड सीमाओं का डिजिटल सत्यापन'}
                    </div>
                  </button>
                </div>
              </div>
            </div>

            {/* 2026 GIGW 3.0 Accessible Horizontally Scrolling Government Schemes Banner */}
            <GigwSchemeScrollBanner 
              language={language}
              onSelectScheme={(scheme) => setSelectedSchemeDetail(scheme)}
            />

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
        {/* VIEW: GOVERNMENT FLAGSHIP SCHEMES & CITIZEN AD CAMPAIGNS */}
        {/* ============================================================ */}
        {activeTab === 'SCHEMES' && (
          <div className="space-y-8">
            {/* S3WaaS Official Schemes Master Header Banner */}
            <div className="relative overflow-hidden rounded-xs border border-slate-300 shadow-sm bg-white">
              <div className="h-1.5 w-full flex">
                <div className="w-1/3 bg-[#FF9933]"></div>
                <div className="w-1/3 bg-[#FFFFFF]"></div>
                <div className="w-1/3 bg-[#138808]"></div>
              </div>

              <div className="p-6 sm:p-8 bg-gradient-to-r from-[#00172d] via-[#002642] to-[#0b3866] text-white">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                  <div className="flex items-start gap-4">
                    <div className="p-2 bg-white rounded-xs flex-shrink-0 shadow-sm">
                      <NationalEmblem size={44} color="#002b49" showSlogan={true} />
                    </div>
                    <div className="space-y-1">
                      <div className="inline-flex items-center gap-2 bg-amber-400/20 border border-amber-300/40 px-2.5 py-0.5 rounded-xs text-[10px] font-bold text-amber-300">
                        <Sparkles className="w-3 h-3 text-amber-300" />
                        <span>GOVERNMENT OF INDIA FLAGSHIP SCHEMES &amp; CITIZEN CAMPAIGNS</span>
                      </div>
                      <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                        {language === 'en'
                          ? 'National Welfare Schemes, Direct Benefit Transfers & Land Rights'
                          : 'प्रमुख राष्ट्रीय योजनाएं, प्रत्यक्ष लाभ अंतरण एवं नागरिक भू-अधिकार'}
                      </h2>
                      <p className="text-xs text-slate-200 max-w-3xl leading-relaxed">
                        {language === 'en'
                          ? 'Central Government flagship welfare initiatives empowering farmers, rural landowners, and project-affected families through zero-leakage PFMS DBT payouts, high-accuracy drone cadastral surveys, and statutory rights.'
                          : 'किसानों, ग्रामीण भूस्वामियों एवं विस्थापित परिवारों को पारदर्शी प्रत्यक्ष बैंक अंतरण (DBT), आधुनिक ड्रोन सर्वेक्षण एवं १००% सांविधिक सोलेशियम प्रदान करने वाली भारत सरकार की केंद्रीय योजनाएं।'}
                      </p>
                    </div>
                  </div>

                  {/* Right Header Stats Strip */}
                  <div className="flex items-center gap-3 bg-white/10 backdrop-blur-xs p-3 rounded-xs border border-white/15 flex-shrink-0">
                    <div className="text-center px-3 border-r border-white/20">
                      <div className="text-lg font-black font-mono text-amber-300">₹3.24L Cr</div>
                      <div className="text-[10px] text-slate-300">PM-KISAN DBT</div>
                    </div>
                    <div className="text-center px-3 border-r border-white/20">
                      <div className="text-lg font-black font-mono text-emerald-300">1.65+ Cr</div>
                      <div className="text-[10px] text-slate-300">Property Cards</div>
                    </div>
                    <div className="text-center px-2">
                      <div className="text-lg font-black font-mono text-sky-300">15.2+ Cr</div>
                      <div className="text-[10px] text-slate-300">Har Ghar Jal</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 2026 Official Government Schemes Showcase Billboard Banner */}
            <GigwSchemeScrollBanner 
              language={language}
              onSelectScheme={(scheme) => setSelectedSchemeDetail(scheme)}
            />

            {/* Search & Filter Bar */}
            <div className="swaas-card p-4 space-y-3 bg-white">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
                {/* Category Tabs */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  {[
                    { id: 'ALL' as SchemeCategory, label: 'All Schemes (8)', labelHi: 'सभी योजनाएं (८)' },
                    { id: 'LAND_REVENUE' as SchemeCategory, label: 'Land & Revenue', labelHi: 'भू-राजस्व व स्वामित्व' },
                    { id: 'AGRICULTURE_DBT' as SchemeCategory, label: 'Farmer DBT', labelHi: 'कृषि एवं किसान डीबीटी' },
                    { id: 'HOUSING_WATER' as SchemeCategory, label: 'Housing & Water', labelHi: 'आवास एवं जल जीवन' },
                    { id: 'INFRASTRUCTURE' as SchemeCategory, label: 'Infrastructure', labelHi: 'अवसंरचना महायोजना' },
                    { id: 'DIGITAL_CITIZEN' as SchemeCategory, label: 'Digital Citizen', labelHi: 'डिजिटल नागरिक' },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setSchemeCategoryFilter(tab.id)}
                      className={`px-3 py-1.5 text-xs font-bold rounded-xs transition-colors cursor-pointer ${
                        schemeCategoryFilter === tab.id
                          ? 'bg-[#002642] text-white shadow-xs'
                          : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                      }`}
                    >
                      {language === 'en' ? tab.label : tab.labelHi}
                    </button>
                  ))}
                </div>

                {/* Keyword Search Input */}
                <div className="relative w-full md:w-72">
                  <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    placeholder={language === 'en' ? 'Search by scheme name or ministry...' : 'योजना या मंत्रालय खोजें...'}
                    value={schemeSearchQuery}
                    onChange={(e) => setSchemeSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-xs text-xs focus:ring-1 focus:ring-[#002642] bg-white"
                  />
                  {schemeSearchQuery && (
                    <button
                      onClick={() => setSchemeSearchQuery('')}
                      className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 text-xs"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Scheme Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {GOV_SCHEMES
                .filter(s => {
                  if (schemeCategoryFilter !== 'ALL' && s.category !== schemeCategoryFilter) return false;
                  if (schemeSearchQuery) {
                    const q = schemeSearchQuery.toLowerCase();
                    return s.name.toLowerCase().includes(q) ||
                           s.nameHi.includes(q) ||
                           s.shortName.toLowerCase().includes(q) ||
                           s.ministry.toLowerCase().includes(q) ||
                           s.slogan.toLowerCase().includes(q) ||
                           s.sloganHi.includes(q);
                  }
                  return true;
                })
                .map((scheme) => {
                  const theme = getThemeClasses(scheme.theme);

                  return (
                    <div 
                      key={scheme.id}
                      className={`swaas-card overflow-hidden border-2 border-slate-200 transition-all hover:shadow-lg flex flex-col justify-between ${theme.borderAccent}`}
                    >
                      {/* Tricolour Ribbon */}
                      <div className="h-1 w-full flex">
                        <div className="w-1/3 bg-[#FF9933]"></div>
                        <div className="w-1/3 bg-[#FFFFFF]"></div>
                        <div className="w-1/3 bg-[#138808]"></div>
                      </div>

                      {/* Card Header */}
                      <div className={`${theme.bg} text-white p-4 space-y-2`}>
                        <div className="flex items-center justify-between">
                          <span className={`px-2 py-0.5 rounded-xs text-[9px] font-black uppercase tracking-wider border ${theme.badgeBg}`}>
                            {scheme.badge}
                          </span>
                          <span className="text-[10px] text-amber-200 font-serif font-bold">
                            Government of India • भारत सरकार
                          </span>
                        </div>

                        <div>
                          <h3 className="font-black text-base sm:text-lg text-white leading-tight">
                            {language === 'en' ? scheme.name : scheme.nameHi}
                          </h3>
                          <p className="text-[11px] text-slate-200/90 mt-0.5">
                            {language === 'en' ? scheme.ministry : scheme.ministryHi}
                          </p>
                        </div>

                        <div className="p-2 bg-black/25 backdrop-blur-2xs rounded-xs border border-white/15 text-amber-300 font-bold italic text-xs">
                          &ldquo;{language === 'en' ? scheme.slogan : scheme.sloganHi}&rdquo;
                        </div>
                      </div>

                      {/* Card Content */}
                      <div className="p-5 bg-white space-y-4 text-xs flex-1 flex flex-col justify-between">
                        <div className="space-y-3">
                          {/* Metrics Strip */}
                          <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xs">
                            <div>
                              <div className="text-[10px] text-slate-500 uppercase font-semibold">National Milestone:</div>
                              <div className="text-base font-black font-mono text-[#002642]">{scheme.impactMetric}</div>
                              <div className="text-[10px] text-slate-600 leading-tight">{scheme.impactLabel}</div>
                            </div>
                            <div>
                              <div className="text-[10px] text-slate-500 uppercase font-semibold">National Reach:</div>
                              <div className="text-base font-black font-mono text-[#138808]">{scheme.secondaryMetric}</div>
                              <div className="text-[10px] text-slate-600 leading-tight">{scheme.secondaryLabel}</div>
                            </div>
                          </div>

                          {/* Description */}
                          <p className="text-slate-700 leading-relaxed">
                            {language === 'en' ? scheme.description : scheme.descriptionHi}
                          </p>

                          {/* Key Statutory Benefits */}
                          <div className="space-y-1.5">
                            <span className="font-bold text-[#002642] block text-[11px] uppercase tracking-wide">
                              {language === 'en' ? 'Key Citizen & Statutory Benefits:' : 'प्रमुख नागरिक व वैधानिक लाभ:'}
                            </span>
                            <ul className="space-y-1 text-[11px] text-slate-600">
                              {(language === 'en' ? scheme.keyBenefits.slice(0, 3) : scheme.keyBenefitsHi.slice(0, 3)).map((b, i) => (
                                <li key={i} className="flex items-start gap-1.5">
                                  <Check className="w-3.5 h-3.5 text-[#138808] flex-shrink-0 mt-0.5" />
                                  <span>{b}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          {/* Eligibility Note */}
                          <div className="p-2.5 bg-blue-50/70 border border-blue-200 rounded-xs text-[11px] text-slate-700">
                            <strong>{language === 'en' ? 'Eligible Beneficiaries: ' : 'पात्र हितग्राही: '}</strong>
                            {language === 'en' ? scheme.eligibility : scheme.eligibilityHi}
                          </div>
                        </div>

                        {/* Card Action Buttons */}
                        <div className="pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2">
                          <button
                            onClick={() => setSelectedSchemeDetail(scheme)}
                            className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 font-bold text-xs rounded-xs flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer"
                          >
                            <FileText className="w-3.5 h-3.5 text-[#0b3866]" />
                            <span>{language === 'en' ? 'Full Guidelines' : 'संपूर्ण विवरण'}</span>
                          </button>

                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-slate-500 font-mono hidden sm:inline">
                              {scheme.helpline.split(' ')[0]}
                            </span>
                            <a
                              href={scheme.portalUrl}
                              target="_blank"
                              rel="noreferrer"
                              className={`px-3.5 py-1.5 font-bold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors ${theme.btn}`}
                            >
                              <span>{scheme.bannerCtaText || (language === 'en' ? 'Official Portal' : 'आधिकारिक पोर्टल')}</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>

            {/* Interactive Citizen Scheme Entitlement Advisor */}
            <div className="swaas-card p-6 bg-gradient-to-br from-slate-50 via-white to-amber-50/40 border-2 border-slate-300 space-y-5">
              <div className="border-b border-slate-200 pb-3 flex justify-between items-center flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <span className="p-1.5 bg-[#f37021] text-white rounded-xs">
                    <ShieldCheck className="w-5 h-5" />
                  </span>
                  <div>
                    <h3 className="font-black text-base text-[#002642]">
                      {language === 'en'
                        ? 'Citizen Entitlement & Welfare Scheme Eligibility Advisor'
                        : 'नागरिक पात्रता एवं शासकीय योजना लाभ परामर्शदाता'}
                    </h3>
                    <p className="text-xs text-slate-500">
                      Select your citizen profile to calculate matched statutory benefits, DBT payouts, and legal protections
                    </p>
                  </div>
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-xs border border-emerald-300">
                  Instant Verification
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    Select Your Citizen Profile:
                  </label>
                  <select
                    value={advisorProfile}
                    onChange={(e) => setAdvisorProfile(e.target.value as any)}
                    className="w-full p-2 border border-slate-300 rounded-xs text-xs font-medium bg-white focus:ring-1 focus:ring-[#002642]"
                  >
                    <option value="FARMER">Small / Marginal Farmer (कृषक परिवार)</option>
                    <option value="ABADI">Rural Village Abadi Resident (ग्रामीण आबादी)</option>
                    <option value="ACQUIRED">Notified Land Acquisition Affected (भूसंपादित भूस्वामी)</option>
                    <option value="HOUSELESS">Rural Houseless / Kutcha House (ग्रामीण आवासहीन)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    State / Jurisdiction:
                  </label>
                  <select
                    value={advisorState}
                    onChange={(e) => setAdvisorState(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded-xs text-xs font-medium bg-white focus:ring-1 focus:ring-[#002642]"
                  >
                    <option value="Maharashtra">Maharashtra (महाराष्ट्र)</option>
                    <option value="Gujarat">Gujarat (गुजरात)</option>
                    <option value="Karnataka">Karnataka (कर्नाटक)</option>
                    <option value="Madhya Pradesh">Madhya Pradesh (मध्य प्रदेश)</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={() => setAdvisorResultOpen(true)}
                    className="w-full py-2 bg-[#002642] hover:bg-[#0b3866] text-white font-bold text-xs rounded-xs transition-colors flex items-center justify-center gap-2 shadow-xs cursor-pointer"
                  >
                    <Sparkles className="w-4 h-4 text-amber-300" />
                    <span>Calculate Eligible Benefits</span>
                  </button>
                </div>
              </div>

              {/* Calculated Entitlements Card */}
              {advisorResultOpen && (
                <div className="p-4 bg-emerald-50/80 border border-emerald-300 rounded-xs space-y-3 animate-in fade-in">
                  <div className="flex items-center justify-between">
                    <div className="font-extrabold text-sm text-emerald-950 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>
                        {advisorProfile === 'FARMER' && 'Identified Benefits: PM-KISAN + Bhu-Aadhaar + Soil Health'}
                        {advisorProfile === 'ABADI' && 'Identified Benefits: SVAMITVA Property Card + Bank Credit Entitlement'}
                        {advisorProfile === 'ACQUIRED' && 'Identified Benefits: 100% Solatium + 12% Interest + First Schedule R&R + PMAY Priority'}
                        {advisorProfile === 'HOUSELESS' && 'Identified Benefits: PMAY-G ₹1,20,000 + MGNREGA 90-Day Labor + Jal Jeevan'}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-emerald-800 font-bold bg-emerald-200/60 px-2 py-0.5 rounded-xs">
                      PFMS Aadhaar Seeded
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div className="p-3 bg-white border border-emerald-200 rounded-xs space-y-1">
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Direct Financial Benefit:</div>
                      <div className="font-extrabold text-[#002642] text-sm">
                        {advisorProfile === 'FARMER' && '₹6,000 / Year (3 Installments)'}
                        {advisorProfile === 'ABADI' && 'Collateral-free credit up to ₹5 Lakhs'}
                        {advisorProfile === 'ACQUIRED' && '100% Statutory Equivalent Solatium'}
                        {advisorProfile === 'HOUSELESS' && '₹1,20,000 Direct Grant + ₹25,000 Labor'}
                      </div>
                      <p className="text-[11px] text-slate-600">Directly transferred via PFMS without middlemen.</p>
                    </div>

                    <div className="p-3 bg-white border border-emerald-200 rounded-xs space-y-1">
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Statutory Documents Required:</div>
                      <div className="font-semibold text-slate-800 text-[11px]">
                        Aadhaar Card, 7/12 Land Record / Khatauni, Bank Passbook (NPCI linked), Mobile No.
                      </div>
                      <p className="text-[11px] text-slate-600">Verification completed via DigiLocker &amp; Revenue Records.</p>
                    </div>

                    <div className="p-3 bg-white border border-emerald-200 rounded-xs flex flex-col justify-between">
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Next Official Step:</div>
                      <p className="text-[11px] text-slate-700 font-medium">
                        {advisorProfile === 'FARMER' && 'Verify e-KYC on pmkisan.gov.in portal.'}
                        {advisorProfile === 'ABADI' && 'Collect Sampatti Card from Gram Panchayat or svamitva.nic.in.'}
                        {advisorProfile === 'ACQUIRED' && 'Verify Section 11 notice in Gazette or file Section 15 objection.'}
                        {advisorProfile === 'HOUSELESS' && 'Confirm your name in Gram Sabha Awaas+ priority list.'}
                      </p>
                      <div className="pt-2 flex gap-2">
                        <button
                          onClick={() => {
                            addToast({
                              type: 'success',
                              message: 'Application checklist downloaded to your device.',
                            });
                          }}
                          className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-[11px] rounded-xs flex items-center gap-1 cursor-pointer"
                        >
                          <Download className="w-3 h-3" />
                          <span>Checklist PDF</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Official Circulars & Gazette Orders Repository */}
            <div className="swaas-card p-6 space-y-4">
              <div className="border-b border-slate-200 pb-3 flex justify-between items-center flex-wrap gap-2">
                <div>
                  <h3 className="font-bold text-sm text-[#002642]">
                    Official Guidelines, Notifications &amp; Statutory Circulars
                  </h3>
                  <p className="text-slate-500 text-xs mt-0.5">
                    Central Government Gazette decrees and administrative guidelines issued for public schemes
                  </p>
                </div>
                <span className="text-[11px] text-slate-500 font-mono">
                  Updated: 28-Sept-2026
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="gov-table">
                  <thead>
                    <tr>
                      <th>Notification / Circular No</th>
                      <th>Ministry / Department</th>
                      <th>Subject / Scheme</th>
                      <th>Publication Date</th>
                      <th>Status</th>
                      <th className="text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      {
                        ref: 'MoPR/SVAMITVA/2026/CIR-14',
                        ministry: 'Ministry of Panchayati Raj',
                        scheme: 'SVAMITVA Drone Survey & Property Card Demarcation Standards',
                        date: '12-Sept-2026',
                        size: '1.8 MB'
                      },
                      {
                        ref: 'MoA&FW/PM-KISAN/2026/NOTIF-18',
                        ministry: 'Ministry of Agriculture & Farmers Welfare',
                        scheme: '17th Installment DBT Disbursement & Mandatory e-KYC Guidelines',
                        date: '02-Sept-2026',
                        size: '1.2 MB'
                      },
                      {
                        ref: 'DoLR/DILRMP/ULPIN/2026-09',
                        ministry: 'Department of Land Resources (DoLR)',
                        scheme: 'Bhu-Aadhaar 14-Digit Geo-Coded Unique Land Parcel Identification',
                        date: '18-Aug-2026',
                        size: '2.4 MB'
                      },
                      {
                        ref: 'MoRD/PMAY-G/2026/GUIDE-08',
                        ministry: 'Ministry of Rural Development',
                        scheme: 'PMAY-G Housing for All Revised Construction Standards & R&R Integration',
                        date: '10-Aug-2026',
                        size: '3.1 MB'
                      },
                      {
                        ref: 'MoJS/JJM/WATER/2026/CIRC-22',
                        ministry: 'Ministry of Jal Shakti',
                        scheme: 'Har Ghar Jal Water Quality Standards (BIS 10500) & IoT Monitoring',
                        date: '24-July-2026',
                        size: '1.9 MB'
                      }
                    ].map((doc, idx) => (
                      <tr key={idx}>
                        <td className="font-mono font-bold text-[#0b3866]">{doc.ref}</td>
                        <td className="font-medium text-slate-700">{doc.ministry}</td>
                        <td className="font-semibold text-slate-900">{doc.scheme}</td>
                        <td className="text-slate-600 whitespace-nowrap">{doc.date}</td>
                        <td>
                          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-bold text-[10px] rounded-xs">
                            Active Gazette
                          </span>
                        </td>
                        <td className="text-right whitespace-nowrap">
                          <button
                            onClick={() => {
                              addToast({
                                type: 'info',
                                message: `Downloading ${doc.ref} official gazette document (${doc.size})`,
                              });
                            }}
                            className="px-3 py-1 bg-white border border-[#0b3866] text-[#0b3866] hover:bg-[#e8f1f8] font-bold text-xs rounded-xs inline-flex items-center gap-1.5 cursor-pointer"
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>PDF ({doc.size})</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* National Toll-Free Helplines Directory */}
            <div className="swaas-card p-6 space-y-4">
              <div className="border-b border-slate-200 pb-2">
                <h3 className="font-bold text-sm text-[#002642] flex items-center gap-2">
                  <Phone className="w-4 h-4 text-[#f37021]" />
                  <span>National Citizen Scheme Helplines (Toll-Free)</span>
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                  <div className="font-bold text-[#002642] text-xs">SVAMITVA Helpdesk</div>
                  <div className="text-lg font-black font-mono text-[#f37021]">1800-11-7788</div>
                  <p className="text-[10px] text-slate-500">Panchayati Raj &amp; Survey of India</p>
                </div>

                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                  <div className="font-bold text-[#002642] text-xs">PM-KISAN Helpline</div>
                  <div className="text-lg font-black font-mono text-[#138808]">155261</div>
                  <p className="text-[10px] text-slate-500">Ministry of Agriculture DBT</p>
                </div>

                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                  <div className="font-bold text-[#002642] text-xs">PMAY-G Rural Housing</div>
                  <div className="text-lg font-black font-mono text-[#0b3866]">1800-11-6446</div>
                  <p className="text-[10px] text-slate-500">Ministry of Rural Development</p>
                </div>

                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xs space-y-1">
                  <div className="font-bold text-[#002642] text-xs">Har Ghar Jal Helpline</div>
                  <div className="text-lg font-black font-mono text-[#0284c7]">1800-180-1551</div>
                  <p className="text-[10px] text-slate-500">Department of Drinking Water</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 2: SEARCH ACQUISITION RECORDS */}
        {/* ============================================================ */}
        {activeTab === 'SEARCH' && (
          <div className="space-y-6">
            {/* Government Scheme Awareness Banner */}
            <div className="bg-gradient-to-r from-[#7c2d12] via-[#9a3412] to-[#c2410c] text-white p-3.5 rounded-xs shadow-xs flex flex-wrap items-center justify-between gap-3 border border-amber-700">
              <div className="flex items-center gap-3">
                <div className="p-1 bg-white rounded-xs">
                  <NationalEmblem size={20} color="#002b49" showSlogan={false} />
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold tracking-wider text-amber-200">
                    {language === 'en' ? 'BHU-AADHAAR (ULPIN) & SVAMITVA ADVISORY' : 'भू-आधार (ULPIN) एवं स्वामित्व योजना सूचना'}
                  </div>
                  <div className="font-bold text-xs text-white">
                    {language === 'en' 
                      ? 'Link your 14-digit Bhu-Aadhaar ULPIN with your 7/12 Land Record for Fast-Track PFMS DBT Compensation' 
                      : 'त्वरित बैंक अंतरण (DBT) हेतु अपने ७/१२ भू-अभिलेख को १४-अंकीय भू-आधार से लिंक करें'}
                  </div>
                </div>
              </div>
              <a
                href="https://dilrmp.gov.in"
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1 bg-white text-orange-950 font-bold text-xs rounded-xs hover:bg-amber-100 flex items-center gap-1 shadow-xs transition-colors"
              >
                <span>{language === 'en' ? 'Bhu-Aadhaar Portal' : 'भू-आधार पोर्टल'}</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="swaas-card p-6 space-y-4">
              <div className="border-b border-slate-200 pb-3">
                <h2 className="text-lg font-bold text-[#002642]">
                  {language === 'en' ? 'Search Land Acquisition & Compensation Records' : 'भूमि अधिग्रहण एवं मुआवजा अभिलेख खोजें'}
                </h2>
                <p className="text-slate-500 text-xs mt-0.5">
                  Query gazette notifications, survey numbers (Gat No), Khatedars and PFMS direct payout status
                </p>
              </div>

              {/* S3WaaS Structured Search Bar */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 bg-slate-50 p-4 border border-slate-200 rounded-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">District / जिला:</label>
                  <select
                    value={searchDistrict}
                    onChange={(e) => setSearchDistrict(e.target.value)}
                    className="w-full p-2 border border-slate-300 bg-white font-medium text-xs rounded-xs"
                  >
                    <option value="ALL">-- All Districts --</option>
                    <option value="Pune">Pune (पुणे)</option>
                    <option value="Nashik">Nashik (नासिक)</option>
                    <option value="Solapur">Solapur (सोलापूर)</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Tehsil / तहसील:</label>
                  <select
                    value={searchTehsil}
                    onChange={(e) => setSearchTehsil(e.target.value)}
                    className="w-full p-2 border border-slate-300 bg-white font-medium text-xs rounded-xs"
                  >
                    <option value="ALL">-- All Tehsils --</option>
                    <option value="Haveli">Haveli (हवेली)</option>
                    <option value="Niphad">Niphad (निफाड)</option>
                    <option value="Daund">Daund (दौंड)</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Survey / Gat No:</label>
                  <input
                    type="text"
                    placeholder="e.g. 142/A"
                    value={searchGatNumber}
                    onChange={(e) => setSearchGatNumber(e.target.value)}
                    className="w-full p-2 border border-slate-300 bg-white font-medium text-xs rounded-xs"
                  />
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Case Reference ID:</label>
                  <input
                    type="text"
                    placeholder="e.g. MH-PUN-2026-LA-001"
                    value={searchCaseRef}
                    onChange={(e) => setSearchCaseRef(e.target.value)}
                    className="w-full p-2 border border-slate-300 bg-white font-medium text-xs rounded-xs"
                  />
                </div>
              </div>

              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500 font-medium">
                  Showing <strong>{filteredCases.length}</strong> matching statutory records
                </span>
                <button
                  type="button"
                  onClick={handleResetSearch}
                  className="px-3 py-1.5 text-slate-700 hover:text-black border border-slate-300 bg-white hover:bg-slate-50 font-semibold text-xs rounded-xs flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Reset Filters</span>
                </button>
              </div>

              {/* Data Table */}
              <div className="overflow-x-auto">
                <table className="gov-table">
                  <thead>
                    <tr>
                      <th>Case Reference</th>
                      <th>Project Name</th>
                      <th>Village / Tehsil</th>
                      <th>Parcels &amp; Extent</th>
                      <th>Statutory Stage</th>
                      <th>Deadline</th>
                      <th>Award Total</th>
                      <th>PFMS Disbursed</th>
                      <th className="text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCases.map(c => (
                      <tr key={c.id}>
                        <td className="font-mono font-bold text-[#0b3866]">{c.caseReference}</td>
                        <td className="font-semibold text-slate-900">{c.projectName}</td>
                        <td>{c.village}, {c.tehsil}</td>
                        <td className="font-mono">{c.totalParcelsCount} parcels ({c.totalExtentHa} Ha)</td>
                        <td>
                          <span className="px-2 py-0.5 bg-[#e8f1f8] text-[#0b3866] font-semibold text-[10px] rounded-xs">
                            {c.stage.replace('STAGE_', '').replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td>{formatDate(c.stageDeadline)}</td>
                        <td className="font-mono">{formatCurrencyINR(c.totalAwardedAmount)}</td>
                        <td className="font-mono font-bold text-[#138808]">{formatCurrencyINR(c.totalDisbursedAmount)}</td>
                        <td className="text-right whitespace-nowrap">
                          <button
                            onClick={() => setSelectedCaseDetailId(c.id)}
                            className="px-3 py-1 bg-[#0b3866] text-white hover:bg-[#082c52] font-semibold text-xs rounded-xs mr-1.5"
                          >
                            View Record
                          </button>
                          <button
                            onClick={() => {
                              setSelectedCaseForObjection(c.id);
                              setActiveTab('GRIEVANCE');
                            }}
                            className="px-3 py-1 bg-[#f37021] text-white hover:bg-[#e05e10] font-semibold text-xs rounded-xs"
                          >
                            File Objection
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
        {/* VIEW 5: CADASTRAL GIS MAP */}
        {/* ============================================================ */}
        {activeTab === 'GIS_MAP' && (
          <div className="swaas-card p-6 space-y-4">
            <div className="border-b border-slate-200 pb-3 flex justify-between items-center">
              <div>
                <h2 className="text-lg font-bold text-[#002642]">
                  PostGIS Cadastral Parcel Viewer &amp; BhuNaksha GIS
                </h2>
                <p className="text-slate-500 text-xs mt-0.5">
                  Verify geodetic boundaries, parcel coordinates, road alignments and overlap warnings
                </p>
              </div>
            </div>

            <GisMapViewer
              onSelectCase={(caseId) => {
                setSelectedCaseDetailId(caseId);
              }}
            />
          </div>
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
