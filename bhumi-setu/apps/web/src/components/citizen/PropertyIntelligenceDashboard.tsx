import React, { useState } from 'react';
import { 
  Building2, 
  MapPin, 
  FileText, 
  User, 
  Calendar, 
  CheckCircle2, 
  AlertCircle, 
  ShieldCheck, 
  Clock, 
  Landmark, 
  ExternalLink, 
  Printer, 
  Share2, 
  Layers, 
  Map, 
  ArrowRight, 
  Sparkles,
  Search,
  BadgeAlert,
  ChevronRight,
  FileCheck,
  Info
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { SAMPLE_PROPERTY_DEMO, DemoProperty } from '../../data/landIntelligenceData';
import { PublicTab } from '../common/GovNavigation';

export const PropertyIntelligenceDashboard: React.FC<{
  property?: DemoProperty;
  onNavigateTab: (tab: PublicTab) => void;
}> = ({ property = SAMPLE_PROPERTY_DEMO, onNavigateTab }) => {
  const { language, addToast } = useApp();
  const [activeSubTab, setActiveSubTab] = useState<'ALL' | 'OVERVIEW' | 'OWNERSHIP' | 'REGISTRATION' | 'MUTATION' | 'ULPIN'>('ALL');

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    addToast({
      type: 'info',
      message: 'Property Intelligence link copied to clipboard.',
      messageHi: 'प्रॉपर्टी लिंक कॉपी किया गया।'
    });
  };

  return (
    <div className="space-y-6 text-left">
      {/* 1. USP Top Header & One-Property Banner */}
      <div className="bg-gradient-to-r from-[#002642] via-[#0b3866] to-[#00172d] text-white p-5 rounded-xs border-b-3 border-[#f37021] shadow-md flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black bg-[#f37021] text-white tracking-wider uppercase">
              ONE PROPERTY • ONE INTELLIGENCE VIEW
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-400 text-black">
              SAMPLE DATA
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-700 text-white">
              {property.recordStatus}
            </span>
          </div>

          <h2 className="text-xl sm:text-2xl font-black tracking-tight mt-2 text-white">
            {property.village} • Survey {property.surveyNumber}
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            {language === 'en'
              ? 'Unified intelligence layer synthesizing Land Records (7/12), SRO Registration, Mutation Workflow, GIS Cadastre, and Bhu-Aadhaar ULPIN.'
              : 'भू-अभिलेख (७/१२), उप-पंजीयक विलेख, नामांतरण स्थिति, डिजिटल भू-नक्शा एवं भू-आधार का एकीकृत नागरिक विश्लेषण।'}
          </p>
        </div>

        {/* Quick Utilities */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => onNavigateTab('REPORTS')}
            className="px-3.5 py-2 bg-[#f37021] hover:bg-[#d95a10] text-white font-extrabold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
          >
            <FileCheck className="w-3.5 h-3.5" />
            <span>Generate Report</span>
          </button>

          <button
            onClick={handleShare}
            className="px-3 py-2 bg-white/10 hover:bg-white/20 text-white font-bold text-xs rounded-xs border border-white/20 flex items-center gap-1.5 transition-colors cursor-pointer"
            title="Share Property"
          >
            <Share2 className="w-3.5 h-3.5 text-slate-300" />
            <span className="hidden sm:inline">Share</span>
          </button>
        </div>
      </div>

      {/* Citizen Plain-Language Land Health Check Summary */}
      <div className="bg-white border border-slate-300 rounded-xs shadow-xs overflow-hidden">
        <div className="bg-[#f1f5f9] border-b border-slate-200 px-4 py-2.5 flex flex-wrap justify-between items-center gap-2">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-extrabold text-xs text-[#002642] uppercase tracking-wider">
              {language === 'en' ? 'Citizen Quick Summary • Land Health Check' : 'नागरिक त्वरित सारांश • भूमि स्वास्थ्य रिपोर्ट'}
            </span>
          </div>
          <span className="text-[11px] text-slate-500 font-semibold">
            {language === 'en' ? 'Plain-language legal status at a glance' : 'सरल भाषा में आपकी भूमि की वर्तमान स्थिति'}
          </span>
        </div>

        <div className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Card 1 */}
          <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-emerald-900 uppercase">
                {language === 'en' ? '1. Title & Ownership' : '१. मालिकाना स्वत्व'}
              </span>
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-sm font-black text-emerald-800 mt-1">
              {language === 'en' ? 'Clear & Undisputed' : 'स्पष्ट एवं निर्विवाद'}
            </div>
            <p className="text-[11px] text-slate-600 mt-1">
              {language === 'en' 
                ? 'Recorded in 7/12 RoR with zero injunctions, civil court stays, or active litigation.' 
                : 'सात-बारा में पूर्णतः दर्ज, कोई अदालती रोक या विवाद नहीं।'}
            </p>
          </div>

          {/* Card 2 */}
          <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-amber-900 uppercase">
                {language === 'en' ? '2. Mutation Status' : '२. नामांतरण स्थिति'}
              </span>
              <Clock className="w-4 h-4 text-[#f37021]" />
            </div>
            <div className="text-sm font-black text-amber-800 mt-1">
              {language === 'en' ? 'Ferfar #8912 In Progress' : 'फेरफार #८९१२ प्रक्रियाधीन'}
            </div>
            <p className="text-[11px] text-slate-600 mt-1">
              {language === 'en' 
                ? 'Applied on 14-Jan-2026. Under public notice period at Tahsildar revenue office.' 
                : '१४ जनवरी को प्रस्तुत। तहसील कार्यालय में नोटिस अवधि में विचाराधीन।'}
            </p>
          </div>

          {/* Card 3 */}
          <div className="p-3 bg-blue-50/70 border border-blue-200 rounded-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-blue-900 uppercase">
                {language === 'en' ? '3. Govt. Acquisition' : '३. सरकारी अधिग्रहण'}
              </span>
              <ShieldCheck className="w-4 h-4 text-[#0b3866]" />
            </div>
            <div className="text-sm font-black text-blue-800 mt-1">
              {language === 'en' ? 'Not Under Acquisition' : 'अधिग्रहण से पूर्णतः मुक्त'}
            </div>
            <p className="text-[11px] text-slate-600 mt-1">
              {language === 'en' 
                ? 'No Section 11/19 gazette notices for highway, rail corridor, or industrial zones.' 
                : 'राष्ट्रीय राजमार्ग अथवा रेलवे गलियारे की कोई अधिग्रहण अधिसूचना नहीं।'}
            </p>
          </div>

          {/* Card 4 */}
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-700 uppercase">
                {language === 'en' ? '4. Bank Loan / Lien' : '४. बंधक / ऋण स्थिति'}
              </span>
              <Landmark className="w-4 h-4 text-slate-700" />
            </div>
            <div className="text-sm font-black text-slate-800 mt-1">
              {language === 'en' ? 'KCC ₹2.50 Lakh Active' : 'केसीसी ₹२.५० लाख सक्रिय'}
            </div>
            <p className="text-[11px] text-slate-600 mt-1">
              {language === 'en' 
                ? 'Kisan Credit Card crop loan charge registered with Bank of Maharashtra.' 
                : 'बैंक ऑफ महाराष्ट्र के साथ किसान क्रेडिट कार्ड फसली ऋण दर्ज।'}
            </p>
          </div>
        </div>
      </div>

      {/* 2. Sub-Tab Switcher for quick jumping */}
      <div className="flex flex-wrap gap-1.5 border-b border-slate-200 pb-2">
        {[
          { id: 'ALL', label: 'Complete Unified View', labelHi: 'सम्पूर्ण एकीकृत दृश्य' },
          { id: 'OVERVIEW', label: 'A. Property Overview', labelHi: 'क. संपत्ति विवरण' },
          { id: 'OWNERSHIP', label: 'B. Ownership Info', labelHi: 'ख. स्वामित्व जानकारी' },
          { id: 'REGISTRATION', label: 'C. Registration Info', labelHi: 'ग. पंजीयन जानकारी' },
          { id: 'MUTATION', label: 'D. Mutation Status', labelHi: 'घ. नामांतरण स्थिति' },
          { id: 'ULPIN', label: 'E. ULPIN Verification', labelHi: 'ड. यूएलपीआईएन सत्यापन' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id as any)}
            className={`px-3 py-1.5 text-xs font-bold rounded-xs transition-colors cursor-pointer ${
              activeSubTab === tab.id
                ? 'bg-[#002642] text-white shadow-2xs'
                : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-200'
            }`}
          >
            {language === 'en' ? tab.label : tab.labelHi}
          </button>
        ))}
      </div>

      {/* 3. The 5 Core Requirement Cards (A, B, C, D, E) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* ================= SECTION A: PROPERTY OVERVIEW ================= */}
        {(activeSubTab === 'ALL' || activeSubTab === 'OVERVIEW') && (
          <div className="lg:col-span-12 bg-white border border-slate-300 rounded-xs shadow-xs overflow-hidden">
            <div className="bg-[#f8fafc] border-b border-slate-200 px-4 py-3 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-[#002642] text-white font-bold text-xs flex items-center justify-center">
                  A
                </span>
                <h3 className="font-extrabold text-sm text-[#002642] uppercase tracking-wide">
                  {language === 'en' ? 'Property Overview & Administrative Cadastre' : 'संपत्ति विवरण एवं प्रशासनिक क्षेत्राधिकार'}
                </h3>
              </div>
              <span className="text-[11px] text-slate-500 font-medium">
                Source: {property.sourceDepartment}
              </span>
            </div>

            <div className="p-4 sm:p-5 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 text-xs">
              <div className="border-l-2 border-slate-300 pl-2.5">
                <span className="text-[11px] font-bold text-slate-500 uppercase">
                  {language === 'en' ? 'ULPIN (Bhu-Aadhaar)' : 'भू-आधार (ULPIN)'}
                </span>
                <div className="font-mono font-bold text-sm text-[#002642] mt-0.5">{property.ulpin}</div>
                <div className="text-[11px] text-emerald-700 font-semibold">14-Digit Land Aadhaar</div>
              </div>

              <div className="border-l-2 border-slate-300 pl-2.5">
                <span className="text-[11px] font-bold text-slate-500 uppercase">
                  {language === 'en' ? 'Survey / Gat No.' : 'खसरा / गट क्रमांक'}
                </span>
                <div className="font-mono font-bold text-sm text-[#002642] mt-0.5">{property.surveyNumber}</div>
                <div className="text-[11px] text-slate-500">Subdivision: {property.subdivision}</div>
              </div>

              <div className="border-l-2 border-slate-300 pl-2.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Area (Recorded)</span>
                <div className="font-bold text-sm text-[#002642] mt-0.5">{property.areaHectares} Ha</div>
                <div className="text-[10px] text-slate-500">{property.areaAcres} Acres ({property.areaSqMeters.toLocaleString()} m²)</div>
              </div>

              <div className="border-l-2 border-slate-300 pl-2.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Land Type</span>
                <div className="font-bold text-xs text-[#002642] mt-0.5">{property.landType}</div>
                <div className="text-[10px] text-slate-500">{property.soilClassification}</div>
              </div>

              <div className="border-l-2 border-slate-300 pl-2.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Record Status</span>
                <div className="font-bold text-xs text-emerald-700 mt-0.5 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{property.recordStatus}</span>
                </div>
                <div className="text-[10px] text-slate-500">Last Synced: {property.lastUpdated}</div>
              </div>

              <div className="border-l-2 border-slate-300 pl-2.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Jurisdiction</span>
                <div className="font-bold text-xs text-[#002642] mt-0.5">{property.village}</div>
                <div className="text-[10px] text-slate-500">{property.tehsil}, {property.district}, {property.state}</div>
              </div>
            </div>
          </div>
        )}

        {/* ================= SECTION B: OWNERSHIP INFORMATION ================= */}
        {(activeSubTab === 'ALL' || activeSubTab === 'OWNERSHIP') && (
          <div className="lg:col-span-6 bg-white border border-slate-300 rounded-xs shadow-xs overflow-hidden flex flex-col">
            <div className="bg-[#f8fafc] border-b border-slate-200 px-4 py-3 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-[#002642] text-white font-bold text-xs flex items-center justify-center">
                  B
                </span>
                <h3 className="font-extrabold text-sm text-[#002642] uppercase tracking-wide">
                  {language === 'en' ? 'Ownership Information (Masked Sample)' : 'स्वामित्व विवरण (सुरक्षित नमूना)'}
                </h3>
              </div>
              <span className="px-2 py-0.5 bg-amber-100 text-amber-900 border border-amber-300 rounded-xs text-[10px] font-bold">
                DPDP MASKED
              </span>
            </div>

            <div className="p-4 space-y-3.5 text-xs flex-1">
              <div className="bg-amber-50/70 p-2.5 rounded-xs border border-amber-200 text-[11px] text-amber-900">
                <strong>Privacy Notice:</strong> In adherence to DPDP Act 2023 principles, real landowner names are not displayed publicly. Fictional sample records are shown for academic prototype testing.
              </div>

              <div className="space-y-2.5">
                <div className="flex justify-between items-center text-slate-500 text-[11px] font-bold border-b border-slate-200 pb-1">
                  <span>RECORDED OWNER(S)</span>
                  <span>SHARE RATIO</span>
                </div>

                {property.owners.map((owner, idx) => (
                  <div key={idx} className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs flex justify-between items-start gap-2">
                    <div>
                      <div className="font-bold text-slate-800 text-xs flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-[#002642]" />
                        <span>{owner.name}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Relation: {owner.fatherName} • Type: <span className="font-semibold text-slate-700">{owner.holdingType}</span>
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Entry Date: {owner.entryDate} (Mutation #{owner.mutationNumber})
                      </div>
                    </div>
                    <span className="px-2 py-1 bg-white border border-slate-300 rounded-xs font-mono font-bold text-[#002642]">
                      {owner.shareRatio}
                    </span>
                  </div>
                ))}
              </div>

              <div className="p-2.5 bg-blue-50 border-l-3 border-[#0b3866] text-[11px] text-[#002642]">
                <div className="font-bold flex items-center gap-1">
                  <Info className="w-3.5 h-3.5 text-[#0b3866]" />
                  <span>Ownership Change Indicator</span>
                </div>
                <p className="mt-0.5 text-slate-600">
                  Last partition endorsement certified on 10 June 2023 adding co-sharer Devendra R. Sharma (Mutation Ferfar 1042).
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ================= SECTION C: REGISTRATION INFORMATION ================= */}
        {(activeSubTab === 'ALL' || activeSubTab === 'REGISTRATION') && (
          <div className="lg:col-span-6 bg-white border border-slate-300 rounded-xs shadow-xs overflow-hidden flex flex-col">
            <div className="bg-[#f8fafc] border-b border-slate-200 px-4 py-3 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-[#002642] text-white font-bold text-xs flex items-center justify-center">
                  C
                </span>
                <h3 className="font-extrabold text-sm text-[#002642] uppercase tracking-wide">
                  {language === 'en' ? 'Sub-Registrar Registration & Deeds' : 'उप-पंजीयक विलेख एवं पंजीयन विवरण'}
                </h3>
              </div>
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-900 border border-emerald-300 rounded-xs text-[10px] font-bold">
                INDEX-II VERIFIED
              </span>
            </div>

            <div className="p-4 space-y-3 text-xs flex-1">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Registration No.</span>
                  <div className="font-mono font-bold text-xs text-[#002642] mt-0.5">{property.registration.registrationNumber}</div>
                </div>
                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Registration Date</span>
                  <div className="font-bold text-xs text-[#002642] mt-0.5">{property.registration.registrationDate}</div>
                </div>
              </div>

              <div className="space-y-1.5 p-3 bg-slate-50 border border-slate-200 rounded-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Sub-Registrar Office (SRO):</span>
                  <span className="font-bold text-slate-800">{property.registration.subRegistrarOffice}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Transaction Nature:</span>
                  <span className="font-bold text-[#002642]">{property.registration.transactionType}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Market Valuation (Ready Reckoner):</span>
                  <span className="font-bold text-slate-800">₹{property.registration.marketValueINR.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Stamp Duty &amp; Registration Fee Paid:</span>
                  <span className="font-bold text-emerald-700">₹{property.registration.stampDutyPaidINR.toLocaleString()}</span>
                </div>
                <div className="flex justify-between pt-1 border-t border-slate-200">
                  <span className="text-slate-500">Statutory Status:</span>
                  <span className="font-bold text-[#138808]">{property.registration.status}</span>
                </div>
              </div>

              <div className="p-2.5 bg-amber-50 border-l-3 border-[#f37021] text-[11px] text-amber-900">
                <strong>Cross-Registry Check:</strong> Registered Deed specifies 2.45 Ha; current digitized 7/12 shows 2.50 Ha. Flagged in Section 7 (Discrepancy Analysis).
              </div>
            </div>
          </div>
        )}

        {/* ================= SECTION D: MUTATION STATUS ================= */}
        {(activeSubTab === 'ALL' || activeSubTab === 'MUTATION') && (
          <div className="lg:col-span-6 bg-white border border-slate-300 rounded-xs shadow-xs overflow-hidden flex flex-col">
            <div className="bg-[#f8fafc] border-b border-slate-200 px-4 py-3 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-[#002642] text-white font-bold text-xs flex items-center justify-center">
                  D
                </span>
                <h3 className="font-extrabold text-sm text-[#002642] uppercase tracking-wide">
                  {language === 'en' ? 'Active Mutation (Ferfar) Status' : 'वर्तमान नामांतरण (फेरफार) स्थिति'}
                </h3>
              </div>
              <span className="px-2 py-0.5 bg-orange-100 text-orange-900 border border-orange-300 rounded-xs text-[10px] font-bold">
                {property.activeMutation.currentStatus}
              </span>
            </div>

            <div className="p-4 space-y-3 text-xs flex-1">
              <div className="p-3 bg-orange-50/60 border border-orange-200 rounded-xs space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold text-orange-900 uppercase">Application ID</span>
                  <span className="font-mono font-bold text-xs text-orange-950 bg-white px-2 py-0.5 rounded-xs border border-orange-300">
                    {property.activeMutation.applicationId}
                  </span>
                </div>
                <div className="font-bold text-slate-800 text-xs">
                  {property.activeMutation.currentStage}
                </div>
                <div className="text-[11px] text-slate-600">
                  Applicant: <strong>{property.activeMutation.applicant}</strong> • Purpose: {property.activeMutation.purpose}
                </div>
              </div>

              <div className="space-y-1.5 p-3 bg-slate-50 border border-slate-200 rounded-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Submission Date:</span>
                  <span className="font-bold text-slate-700">{property.activeMutation.applicationDate}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Last Hearing / Field Inspection:</span>
                  <span className="font-bold text-slate-700">{property.activeMutation.lastUpdate}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Revenue Authority:</span>
                  <span className="font-bold text-[#002642]">{property.activeMutation.revenueOfficer}</span>
                </div>
                <div className="pt-1 text-[11px] text-slate-600 border-t border-slate-200">
                  <span className="font-bold text-slate-700">Remarks:</span> {property.activeMutation.remarks}
                </div>
              </div>

              <button
                onClick={() => onNavigateTab('MUTATION')}
                className="w-full py-2 bg-slate-100 hover:bg-[#002642] hover:text-white text-slate-800 font-bold text-xs rounded-xs border border-slate-300 flex items-center justify-center gap-1.5 transition-colors"
              >
                <span>Track Full Mutation Timeline</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* ================= SECTION E: ULPIN (BHU-AADHAAR) ================= */}
        {(activeSubTab === 'ALL' || activeSubTab === 'ULPIN') && (
          <div className="lg:col-span-6 bg-white border border-slate-300 rounded-xs shadow-xs overflow-hidden flex flex-col">
            <div className="bg-[#f8fafc] border-b border-slate-200 px-4 py-3 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-[#002642] text-white font-bold text-xs flex items-center justify-center">
                  E
                </span>
                <h3 className="font-extrabold text-sm text-[#002642] uppercase tracking-wide">
                  {language === 'en' ? '14-Digit ULPIN (Bhu-Aadhaar) Verification' : '१४-अंकीय भू-आधार (ULPIN) सत्यापन'}
                </h3>
              </div>
              <span className="px-2 py-0.5 bg-sky-100 text-sky-900 border border-sky-300 rounded-xs text-[10px] font-bold">
                GEO-REFERENCED
              </span>
            </div>

            <div className="p-4 space-y-3.5 text-xs flex-1">
              <div className="p-3 bg-sky-50 border border-sky-200 rounded-xs">
                <div className="text-[10px] uppercase font-bold text-sky-900">Unique Land Parcel Identification Number</div>
                <div className="text-lg font-mono font-black text-[#002642] tracking-wider mt-1">
                  27 - 712 - 049 - 001234
                </div>
                <div className="text-[10px] text-sky-800 mt-1">
                  Generated under Digital India Land Records Modernization Programme (DILRMP).
                </div>
              </div>

              {/* 14-Digit Anatomy breakdown */}
              <div className="grid grid-cols-4 gap-2 text-center">
                <div className="p-2 bg-slate-100 rounded-xs border border-slate-200">
                  <div className="font-mono font-bold text-xs text-[#002642]">27</div>
                  <div className="text-[9px] text-slate-500 uppercase mt-0.5 font-bold">State (MH)</div>
                </div>
                <div className="p-2 bg-slate-100 rounded-xs border border-slate-200">
                  <div className="font-mono font-bold text-xs text-[#002642]">712</div>
                  <div className="text-[9px] text-slate-500 uppercase mt-0.5 font-bold">District</div>
                </div>
                <div className="p-2 bg-slate-100 rounded-xs border border-slate-200">
                  <div className="font-mono font-bold text-xs text-[#002642]">049</div>
                  <div className="text-[9px] text-slate-500 uppercase mt-0.5 font-bold">Sub-District</div>
                </div>
                <div className="p-2 bg-slate-100 rounded-xs border border-slate-200">
                  <div className="font-mono font-bold text-xs text-[#002642]">001234</div>
                  <div className="text-[9px] text-slate-500 uppercase mt-0.5 font-bold">Parcel/Subdiv</div>
                </div>
              </div>

              {/* Verification Badges */}
              <div className="space-y-1.5 pt-1 text-[11px]">
                <div className="flex items-center gap-2 text-emerald-800">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                  <span>Centroid Latitude/Longitude coordinates mathematically verified: 21.0764° N, 79.0832° E</span>
                </div>
                <div className="flex items-center gap-2 text-emerald-800">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                  <span>Unique polygon demarcation registered with Survey of India CORS Network</span>
                </div>
              </div>

              <button
                onClick={() => onNavigateTab('GIS_MAP')}
                className="w-full py-2 bg-[#002642] hover:bg-[#0b3866] text-white font-bold text-xs rounded-xs flex items-center justify-center gap-1.5 transition-colors"
              >
                <Map className="w-3.5 h-3.5 text-[#f37021]" />
                <span>Inspect ULPIN Polygon on Cadastral Map</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 4. Bottom Gateway: Quick Jump to Timeline, Risk Analysis & Document Verification */}
      <div className="bg-slate-100 border border-slate-300 p-4 rounded-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="font-bold text-xs text-[#002642] flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-[#f37021]" />
            <span>Further Intelligence Modules for MH-NGP-00012345</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Explore the historical timeline, cross-document OCR checks, and 12-factor discrepancy risk analysis.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => onNavigateTab('TIMELINE')}
            className="px-3.5 py-1.5 bg-white hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xs border border-slate-300 flex items-center gap-1"
          >
            <span>Property Timeline (2018–2026)</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => onNavigateTab('RISK_ANALYSIS')}
            className="px-3.5 py-1.5 bg-[#002642] hover:bg-[#0b3866] text-white font-bold text-xs rounded-xs flex items-center gap-1"
          >
            <span>Preliminary Risk Analysis (12 Checks)</span>
            <ChevronRight className="w-3.5 h-3.5 text-[#f37021]" />
          </button>

          <button
            onClick={() => onNavigateTab('DOC_VERIFY')}
            className="px-3.5 py-1.5 bg-[#f37021] hover:bg-[#d95a10] text-white font-bold text-xs rounded-xs flex items-center gap-1"
          >
            <span>AI Document Verification</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
