import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  Search, 
  MapPin, 
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
  ArrowRight
} from 'lucide-react';
import { formatCurrencyINR, formatDate } from '../../lib/utils';
import { CaseStage } from '../../types';

type ObjectionGroundType = 'Valuation & Compensation' | 'Measurement / Boundary Dispute' | 'Ownership / Title Claim' | 'Environmental / Religious Structure';

export const CitizenPortal: React.FC = () => {
  const { cases, submitCitizenObjection, language, addToast } = useApp();

  const [activeCitizenTab, setActiveCitizenTab] = useState<'TRACKER' | 'OBJECTION' | 'COMPENSATION' | 'NOTICES' | 'PRIVACY_DSR'>('TRACKER');
  
  // Search parameters
  const [searchQuery, setSearchQuery] = useState('MH-PUN-2026-LA-001');
  const [activeCase, setActiveCase] = useState(cases[0]);

  // Section 15 Objection Form States
  const [objectorName, setObjectorName] = useState('Tukaram Bapu Jadhav');
  const [objectorContact, setObjectorContact] = useState('+91 98231 44521');
  const [objectorAadhaar, setObjectorAadhaar] = useState('XXXX-XXXX-4819');
  const [surveyGat, setSurveyGat] = useState('142/A');
  const [groundsCategory, setGroundsCategory] = useState<ObjectionGroundType>('Valuation & Compensation');
  const [objectionSubstance, setObjectionSubstance] = useState('');
  const [attachedFile, setAttachedFile] = useState<string | null>('sale_deed_comparable_2025.pdf');
  const [submittedTrackingId, setSubmittedTrackingId] = useState<string | null>(null);

  // DSR Form States
  const [dsrType, setDsrType] = useState<'ACCESS' | 'CORRECTION' | 'ERASURE'>('ACCESS');
  const [dsrDetails, setDsrDetails] = useState('');

  const handleSearchCase = (e: React.FormEvent) => {
    e.preventDefault();
    const found = cases.find(c => 
      c.caseReference.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.village.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.parcels.some(p => p.surveyNumber.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    if (found) {
      setActiveCase(found);
      addToast({
        type: 'success',
        message: `Located land acquisition case record: ${found.caseReference}`,
        messageHi: `भू-अधिग्रहण प्रकरण प्राप्त: ${found.caseReference}`,
      });
    } else {
      addToast({
        type: 'warning',
        message: 'No case matched that reference number or survey gat.',
        messageHi: 'दिए गए संदर्भ क्रमांक से कोई प्रकरण नहीं मिला।',
      });
    }
  };

  const handleSubmitObjection = (e: React.FormEvent) => {
    e.preventDefault();
    if (!objectionSubstance.trim()) {
      addToast({
        type: 'warning',
        message: 'Please provide detailed grounds and substance for the objection.',
      });
      return;
    }

    const trackingId = submitCitizenObjection(activeCase.id, {
      objectorName,
      objectorContact,
      surveyNumber: surveyGat,
      groundsCategory,
      substance: objectionSubstance,
    });

    setSubmittedTrackingId(trackingId);
    setObjectionSubstance('');
  };

  const handleSubmitDsr = (e: React.FormEvent) => {
    e.preventDefault();
    if (!dsrDetails.trim()) return;

    addToast({
      type: 'success',
      message: `DPDP Data Subject Request (${dsrType}) submitted successfully. Reference ID: DSR-2026-${Math.floor(1000 + Math.random() * 9000)}`,
      messageHi: 'डीपीडीपी डेटा अधिकार अनुरोध सफलतापूर्वक दर्ज हुआ।',
    });
    setDsrDetails('');
  };

  const stageDescriptions: Record<CaseStage, { title: string; titleHi: string; desc: string; descHi: string }> = {
    STAGE_1_SIA: {
      title: '1. Social Impact Assessment (Section 4)',
      titleHi: '१. सामाजिक समाघात निर्धारण (धारा ४)',
      desc: 'SIA team evaluates affected families, public purpose, and rehabilitation needs.',
      descHi: 'एसआईए टीम द्वारा प्रभावित परिवारों एवं पुनर्वास आवश्यकताओं का अध्ययन किया जा रहा है।',
    },
    STAGE_2_PRELIM_NOTIF: {
      title: '2. Preliminary Notification (Section 11)',
      titleHi: '२. प्रारंभिक अधिसूचना (धारा ११)',
      desc: 'Government notifies public intention to acquire designated land parcels.',
      descHi: 'शासन द्वारा भूमि अधिग्रहण की प्राथमिक अधिसूचना राजपत्र में प्रकाशित की गई है।',
    },
    STAGE_3_OBJECTIONS: {
      title: '3. Public Hearing & Objections (Section 15)',
      titleHi: '३. जनसुनवाई एवं आपत्तियां (धारा १५)',
      desc: '60-day window for land owners to submit objections on valuation or title.',
      descHi: 'भू-स्वामियों द्वारा आपत्तियां दर्ज कराने हेतु ६० दिनों की विधिक समयावधि।',
    },
    STAGE_4_DECLARATION: {
      title: '4. Statutory Declaration (Section 19)',
      titleHi: '४. अंतिम घोषणा (धारा १९)',
      desc: 'Final declaration published after Collector approves rehabilitation and objection reports.',
      descHi: 'आपत्तियों के निस्तारण उपरांत अधिग्रहण की अंतिम कानूनी घोषणा।',
    },
    STAGE_5_AWARD_COMPENSATION: {
      title: '5. Determination of Award (Section 23)',
      titleHi: '५. मुआवजा पंचाट निर्धारण (धारा २३)',
      desc: 'Collector computes land market value + 100% Solatium + 12% additional component.',
      descHi: 'कलेक्टर द्वारा बाजार मूल्य, १००% तोषण एवं १२% अतिरिक्त ब्याज का निर्धारण।',
    },
    STAGE_6_DISBURSEMENT: {
      title: '6. Direct Benefit Transfer Payout (Section 38)',
      titleHi: '६. बैंक खाते में मुआवजा अंतरण (धारा ३८)',
      desc: 'Compensation deposited directly into validated Aadhaar-linked bank accounts via PFMS.',
      descHi: 'पीएफ़एमएस प्रणाली द्वारा मुआवजा राशि का सीधे बैंक खाते में प्रत्यक्ष अंतरण।',
    },
    STAGE_7_COMPLETED: {
      title: '7. Possession & Land Handover',
      titleHi: '७. कब्जा एवं भूमि हस्तांतरण',
      desc: 'Land possession handed over to Requiring Agency for infrastructure execution.',
      descHi: 'परियोजना कार्य हेतु भूमि का विधिवत हस्तांतरण पूर्ण।',
    },
  };

  const stageOrder: CaseStage[] = [
    'STAGE_1_SIA',
    'STAGE_2_PRELIM_NOTIF',
    'STAGE_3_OBJECTIONS',
    'STAGE_4_DECLARATION',
    'STAGE_5_AWARD_COMPENSATION',
    'STAGE_6_DISBURSEMENT',
    'STAGE_7_COMPLETED'
  ];

  const currentStageIdx = stageOrder.indexOf(activeCase.stage);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8 animate-in fade-in">
      {/* Citizen Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-950 to-blue-900 text-white rounded-3xl p-8 shadow-xl relative overflow-hidden">
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-xs font-semibold text-blue-200">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>{language === 'en' ? 'RFCTLARR Act 2013 Citizen Self-Service Portal' : 'भूमि अधिग्रहण नागरिक सेवा पोर्टल'}</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-black tracking-tight">
            {language === 'en' 
              ? 'Track Land Acquisition, File Objections & Check Compensation' 
              : 'भू-अधिग्रहण स्थिति जांचें, आपत्ति दर्ज करें एवं मुआवजा देखें'}
          </h1>

          <p className="text-sm text-blue-100/90 leading-relaxed">
            {language === 'en'
              ? 'Transparent, real-time statutory milestone tracking for affected khatedars, co-sharers, and citizens. Verified by the District Revenue Authority.'
              : 'प्रभावित खातेदारों एवं सह-स्वामियों हेतु पारदर्शी, वास्तविक समय सांविधिक प्रगति एवं मुआवजा विवरण।'}
          </p>

          {/* Quick Search Bar */}
          <form onSubmit={handleSearchCase} className="pt-3 flex flex-col sm:flex-row gap-2 max-w-xl">
            <div className="relative flex-1">
              <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={language === 'en' ? 'Enter Case Ref (e.g. MH-PUN-2026-LA-001) or Survey Gat...' : 'प्रकरण क्रमांक या सर्वे नंबर दर्ज करें...'}
                className="w-full pl-12 pr-4 py-3 text-sm rounded-2xl bg-white text-slate-900 placeholder:text-slate-400 shadow-md focus:outline-none focus:ring-2 focus:ring-blue-400 font-medium"
              />
            </div>
            <button
              type="submit"
              className="px-6 py-3 bg-amber-500 hover:bg-amber-600 text-slate-950 font-black text-sm rounded-2xl shadow-md transition-all flex items-center justify-center gap-2 flex-shrink-0"
            >
              <span>{language === 'en' ? 'Search Record' : 'खोजें'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>

        {/* Decorative Watermark */}
        <div className="absolute right-[-40px] bottom-[-40px] opacity-10 pointer-events-none">
          <ShieldCheck className="w-96 h-96 text-white" />
        </div>
      </div>

      {/* Citizen Portal Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 overflow-x-auto">
        {[
          { id: 'TRACKER', label: '1. Statutory Case Timeline & Stage' },
          { id: 'OBJECTION', label: '2. File Section 15 Objection' },
          { id: 'COMPENSATION', label: '3. Award Calculator & DBT Payout' },
          { id: 'NOTICES', label: '4. Public Gazettes & Notices' },
          { id: 'PRIVACY_DSR', label: '5. Privacy & DPDP Data Rights' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveCitizenTab(tab.id as any)}
            className={`px-5 py-3.5 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
              activeCitizenTab === tab.id
                ? 'border-blue-700 text-blue-900 dark:text-blue-300 dark:border-blue-400 bg-blue-50/40 dark:bg-blue-950/20'
                : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: STATUTORY CASE TIMELINE */}
      {activeCitizenTab === 'TRACKER' && (
        <div className="space-y-6">
          {/* Active Case Summary Box */}
          <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
            <div className="flex flex-wrap justify-between items-start gap-4 pb-5 border-b border-slate-100 dark:border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-sm text-blue-800 dark:text-blue-300 bg-blue-50 dark:bg-blue-950 px-2.5 py-1 rounded-lg">
                    Case Ref: {activeCase.caseReference}
                  </span>
                  <span className="text-xs font-semibold text-slate-500">
                    (Village: {activeCase.village}, Tehsil: {activeCase.tehsil})
                  </span>
                </div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                  {language === 'en' ? activeCase.projectName : activeCase.projectNameHi}
                </h2>
              </div>

              <div className="text-right">
                <span className="text-xs text-slate-500 block">Competent Authority:</span>
                <strong className="text-xs text-slate-800 dark:text-slate-200 block">
                  {activeCase.landAcquisitionOfficer} (LAO / Sub-Divisional Officer)
                </strong>
                <span className="text-[11px] text-blue-600 dark:text-blue-400">Helpline: +91 20 2612 8490</span>
              </div>
            </div>

            {/* Statutory Stage Flowchart */}
            <div className="py-6 space-y-6">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                {language === 'en' ? 'Statutory Progression Steps (RFCTLARR Act 2013):' : 'सांविधिक चरण प्रगति विवरण:'}
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {stageOrder.slice(0, 4).map((stg, index) => {
                  const isCompleted = index < currentStageIdx;
                  const isCurrent = index === currentStageIdx;
                  const info = stageDescriptions[stg];

                  return (
                    <div
                      key={stg}
                      className={`p-4 rounded-2xl border transition-all ${
                        isCurrent
                          ? 'border-blue-600 bg-blue-50/70 dark:bg-blue-950/60 ring-2 ring-blue-500 shadow-md'
                          : isCompleted
                          ? 'border-emerald-200 dark:border-emerald-900 bg-emerald-50/30 dark:bg-emerald-950/20'
                          : 'border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 opacity-70'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-black font-mono">STEP {index + 1}</span>
                        {isCompleted ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            Completed ✓
                          </span>
                        ) : isCurrent ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-600 text-white animate-pulse">
                            In Progress
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-400">Upcoming</span>
                        )}
                      </div>

                      <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                        {language === 'en' ? info.title : info.titleHi}
                      </h4>
                      <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-1">
                        {language === 'en' ? info.desc : info.descHi}
                      </p>
                    </div>
                  );
                })}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {stageOrder.slice(4, 7).map((stg, index) => {
                  const actualIdx = index + 4;
                  const isCompleted = actualIdx < currentStageIdx;
                  const isCurrent = actualIdx === currentStageIdx;
                  const info = stageDescriptions[stg];

                  return (
                    <div
                      key={stg}
                      className={`p-4 rounded-2xl border transition-all ${
                        isCurrent
                          ? 'border-blue-600 bg-blue-50/70 dark:bg-blue-950/60 ring-2 ring-blue-500 shadow-md'
                          : isCompleted
                          ? 'border-emerald-200 dark:border-emerald-900 bg-emerald-50/30 dark:bg-emerald-950/20'
                          : 'border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 opacity-70'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-black font-mono">STEP {actualIdx + 1}</span>
                        {isCompleted ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            Completed ✓
                          </span>
                        ) : isCurrent ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-600 text-white animate-pulse">
                            In Progress
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-400">Upcoming</span>
                        )}
                      </div>

                      <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                        {language === 'en' ? info.title : info.titleHi}
                      </h4>
                      <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-1">
                        {language === 'en' ? info.desc : info.descHi}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Next Action for Citizen */}
            <div className="p-4 bg-amber-50 dark:bg-amber-950/40 rounded-2xl border border-amber-200 dark:border-amber-800 flex items-start gap-3">
              <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-amber-900 dark:text-amber-200 space-y-1">
                <span className="font-bold block">Current Milestone Notice:</span>
                <p>
                  {language === 'en' ? activeCase.nextExpectedStep : activeCase.nextExpectedStepHi}
                </p>
                <p className="text-[11px] text-amber-700 dark:text-amber-400">
                  Statutory hearing deadline: <strong>{formatDate(activeCase.stageDeadline)}</strong> ({activeCase.daysRemaining} days remaining).
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: FILE SECTION 15 OBJECTION */}
      {activeCitizenTab === 'OBJECTION' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Form */}
          <div className="lg:col-span-8 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div>
              <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-700" />
                <span>{language === 'en' ? 'Section 15 Statutory Objection & Representation Form' : 'धारा १५ सांविधिक आपत्ति एवं प्रतिवेदन पत्र'}</span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {language === 'en'
                  ? 'Land owners & interested persons may record objections regarding valuation, title, area measurement, or public purpose within 60 days of preliminary notification.'
                  : 'अधिसूचना के ६० दिनों के भीतर मूल्यांकन, स्वामित्व, अथवा क्षेत्रफल के संबंध में आपत्ति दर्ज करें।'}
              </p>
            </div>

            {submittedTrackingId ? (
              <div className="p-6 bg-emerald-50 dark:bg-emerald-950/60 rounded-2xl border-2 border-emerald-500 text-center space-y-4">
                <CheckCircle2 className="w-12 h-12 text-emerald-600 mx-auto" />
                <h3 className="text-base font-black text-emerald-900 dark:text-emerald-100">
                  {language === 'en' ? 'Statutory Objection Successfully Registered' : 'आपत्ति सफलतापूर्वक दर्ज की गई'}
                </h3>
                <div className="inline-block p-3 bg-white dark:bg-slate-900 rounded-xl border border-emerald-300 font-mono font-bold text-lg text-emerald-800 dark:text-emerald-300">
                  Ack Tracking No: {submittedTrackingId}
                </div>
                <p className="text-xs text-emerald-800 dark:text-emerald-300 max-w-md mx-auto">
                  A formal SMS confirmation with hearing date has been sent to {objectorContact}. A digital stamped receipt has been generated.
                </p>
                <div className="pt-2 flex justify-center gap-3">
                  <button
                    onClick={() => {
                      addToast({
                        type: 'info',
                        message: `Downloaded formal Section 15 acknowledgment receipt: ${submittedTrackingId}.pdf`,
                      });
                    }}
                    className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl font-bold text-xs flex items-center gap-1.5 shadow-sm"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Stamped Receipt PDF</span>
                  </button>
                  <button
                    onClick={() => setSubmittedTrackingId(null)}
                    className="px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-xl font-bold text-xs"
                  >
                    Submit Another Representation
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmitObjection} className="space-y-4 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                      Full Name of Objector / Khatedar:
                    </label>
                    <input
                      type="text"
                      required
                      value={objectorName}
                      onChange={(e) => setObjectorName(e.target.value)}
                      className="w-full p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-blue-500 font-medium"
                    />
                  </div>

                  <div>
                    <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                      Mobile Number (for SMS Tracking):
                    </label>
                    <input
                      type="text"
                      required
                      value={objectorContact}
                      onChange={(e) => setObjectorContact(e.target.value)}
                      className="w-full p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-blue-500 font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                      Survey Gat Number:
                    </label>
                    <input
                      type="text"
                      required
                      value={surveyGat}
                      onChange={(e) => setSurveyGat(e.target.value)}
                      className="w-full p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 font-mono"
                    />
                  </div>

                  <div>
                    <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                      Aadhaar Number (Masked):
                    </label>
                    <input
                      type="text"
                      value={objectorAadhaar}
                      onChange={(e) => setObjectorAadhaar(e.target.value)}
                      className="w-full p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 font-mono"
                    />
                  </div>

                  <div>
                    <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                      Grounds of Objection:
                    </label>
                    <select
                      value={groundsCategory}
                      onChange={(e) => setGroundsCategory(e.target.value as ObjectionGroundType)}
                      className="w-full p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 font-bold text-slate-800 dark:text-slate-200"
                    >
                      <option value="Valuation & Compensation">Valuation &amp; Compensation</option>
                      <option value="Measurement / Boundary Dispute">Measurement / Boundary Dispute</option>
                      <option value="Ownership / Title Claim">Ownership / Title Claim</option>
                      <option value="Environmental / Religious Structure">Environmental / Religious Structure</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Detailed Legal Substance &amp; Claim (Section 15):
                  </label>
                  <textarea
                    required
                    rows={4}
                    value={objectionSubstance}
                    onChange={(e) => setObjectionSubstance(e.target.value)}
                    placeholder="Provide specific details, registered sale instances, crop details, or boundary disputes..."
                    className="w-full p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-blue-500 font-medium"
                  />
                </div>

                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Upload Supporting Evidence (7/12, Sale Deed, Valuation Report, max 25MB):
                  </label>
                  <div className="p-4 border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-2xl text-center space-y-2 bg-slate-50/50 dark:bg-slate-800/40">
                    <Upload className="w-6 h-6 text-slate-400 mx-auto" />
                    <p className="text-slate-600 dark:text-slate-400">
                      {attachedFile ? `Attached: ${attachedFile}` : 'Drag & drop PDF / JPG or click to select file'}
                    </p>
                    <button
                      type="button"
                      onClick={() => setAttachedFile('registered_sale_deed_2025.pdf')}
                      className="px-3 py-1.5 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 text-slate-800 dark:text-slate-200 rounded-lg text-xs font-bold"
                    >
                      Attach Sample Deed
                    </button>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="submit"
                    className="px-6 py-3 bg-blue-800 hover:bg-blue-900 text-white font-black text-xs rounded-xl shadow-md flex items-center gap-2 transition-colors"
                  >
                    <Send className="w-4 h-4" />
                    <span>{language === 'en' ? 'Submit Section 15 Objection' : 'आपत्ति पत्र प्रेषित करें'}</span>
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* Legal Guidance Card */}
          <div className="lg:col-span-4 space-y-6">
            <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Statutory Rights under Section 15</span>
              </h3>
              <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-400">
                <li className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span>Every person interested has the right to a personal hearing before the Collector.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span>Collector must pass a reasoned written order within 60 days of hearing.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span>No land acquisition declaration (Sec 19) can be issued until all Sec 15 objections are legally disposed.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: COMPENSATION CALCULATOR & DBT PAYOUT TRACKER */}
      {activeCitizenTab === 'COMPENSATION' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div>
              <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <IndianRupee className="w-5 h-5 text-emerald-600" />
                <span>{language === 'en' ? 'Section 23 Compensation Award & PFMS DBT Ledger' : 'धारा २३ मुआवजा पंचाट एवं प्रत्यक्ष अंतरण विवरण'}</span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {language === 'en'
                  ? 'Statutory breakdown of compensation calculated under First Schedule of RFCTLARR Act 2013 with 100% Solatium (Sec 30).'
                  : 'प्रथम अनुसूची एवं धारा ३० के अंतर्गत निर्धारित मुआवजा एवं बैंक अंतरण स्थिति।'}
              </p>
            </div>

            {/* Itemized Compensation Formula Card */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">1. Basic Land Value (Market Rate)</span>
                <div className="text-xl font-black font-mono text-slate-900 dark:text-slate-100 mt-1">
                  ₹ 1,50,00,000
                </div>
                <span className="text-[11px] text-slate-500 mt-1 block">Based on Ready Reckoner x 1.5 Rural Factor</span>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">2. Solatium (100% under Sec 30)</span>
                <div className="text-xl font-black font-mono text-blue-700 dark:text-blue-300 mt-1">
                  ₹ 1,50,00,000
                </div>
                <span className="text-[11px] text-slate-500 mt-1 block">Mandatory 100% statutory solatium</span>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">3. Additional Interest (12% Sec 30(3))</span>
                <div className="text-xl font-black font-mono text-amber-600 dark:text-amber-400 mt-1">
                  ₹ 18,00,000
                </div>
                <span className="text-[11px] text-slate-500 mt-1 block">12% per annum from Sec 4 to Award</span>
              </div>

              <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-300 dark:border-emerald-800">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-300">Total Statutory Award</span>
                <div className="text-2xl font-black font-mono text-emerald-800 dark:text-emerald-300 mt-1">
                  ₹ 3,45,00,000
                </div>
                <span className="text-[11px] text-emerald-700 dark:text-emerald-400 font-semibold mt-1 block">Includes Tree &amp; Structure Valuation</span>
              </div>
            </div>

            {/* DBT Direct Payout Records for Khatedars */}
            <div className="space-y-3 pt-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                {language === 'en' ? 'Direct Benefit Transfer (PFMS) Disbursement Status:' : 'प्रत्यक्ष लाभ अंतरण (पीएफ़एमएस) भुगतान स्थिति:'}
              </h3>

              {activeCase.awards.map((award) => (
                <div key={award.id} className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 flex flex-wrap justify-between items-center gap-4 text-xs">
                  <div>
                    <div className="flex items-center gap-2">
                      <strong className="text-sm font-bold text-slate-900 dark:text-slate-100">{award.ownerName}</strong>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                        {award.disbursementState}
                      </span>
                    </div>
                    <p className="text-slate-500 mt-0.5">
                      Determined on {formatDate(award.determinationDate)} by {award.determiningAuthority}
                    </p>
                  </div>

                  <div className="text-right">
                    <span className="font-mono font-black text-lg text-blue-900 dark:text-blue-300">
                      {formatCurrencyINR(award.totalAmount)}
                    </span>
                    <span className="block text-[11px] font-mono text-slate-500 mt-0.5">
                      PFMS UTR: DBT/2026/08/99812402
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: PUBLIC GAZETTES & NOTICES */}
      {activeCitizenTab === 'NOTICES' && (
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-4">
          <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-700" />
            <span>{language === 'en' ? 'Official Gazette Publications & Public Notices' : 'राजकीय राजपत्र एवं सार्वजनिक सूचनाएं'}</span>
          </h2>

          <div className="space-y-3">
            {activeCase.notices.map((n) => (
              <div key={n.id} className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 flex flex-wrap justify-between items-center gap-4 text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-blue-900 dark:text-blue-300">{n.noticeType}</span>
                    <span className="text-slate-500">({n.publicationMode})</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-400 mt-0.5">
                    Issued by: {n.issuingAuthority} on {formatDate(n.issueDate)}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-amber-700 dark:text-amber-400 font-semibold">
                    Response Window: {formatDate(n.responseDeadline)}
                  </span>
                  <button
                    onClick={() => {
                      addToast({
                        type: 'info',
                        message: `Downloading certified gazette copy for ${n.noticeType}...`,
                      });
                    }}
                    className="px-3 py-1.5 bg-blue-800 hover:bg-blue-900 text-white rounded-xl font-bold text-xs flex items-center gap-1 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Gazette PDF</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 5: PRIVACY & DPDP DATA RIGHTS (Req 32.7) */}
      {activeCitizenTab === 'PRIVACY_DSR' && (
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-6">
          <div>
            <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-purple-700" />
              <span>{language === 'en' ? 'Citizen Data Rights Self-Service (DPDP Act 2023)' : 'नागरिक डेटा अधिकार स्व-सेवा (डीपीडीपी अधिनियम २०२३)'}</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {language === 'en'
                ? 'Under the Digital Personal Data Protection Act 2023, you have statutory rights to access your processed identity records, request correction of inaccurate data, or file grievance.'
                : 'डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम २०२३ के अंतर्गत अपने व्यक्तिगत डेटा तक पहुंच एवं सुधार का अधिकार।'}
            </p>
          </div>

          <form onSubmit={handleSubmitDsr} className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 space-y-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Request Type under DPDP Act:
                </label>
                <select
                  value={dsrType}
                  onChange={(e) => setDsrType(e.target.value as any)}
                  className="w-full p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 font-bold"
                >
                  <option value="ACCESS">Right to Summary of Personal Data &amp; Sharing Log</option>
                  <option value="CORRECTION">Right to Correction of Inaccurate Name / Bank PII</option>
                  <option value="ERASURE">Right to Erasure of Retained PII (Post Statutory Window)</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Your Identifier (Aadhaar / Mobile Number):
                </label>
                <input
                  type="text"
                  required
                  placeholder="+91 98231 44521 or XXXX-XXXX-4819"
                  className="w-full p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 font-mono"
                />
              </div>
            </div>

            <div>
              <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                Details of Request or Specific Discrepancy:
              </label>
              <textarea
                required
                rows={3}
                value={dsrDetails}
                onChange={(e) => setDsrDetails(e.target.value)}
                placeholder="Describe your data access or correction inquiry..."
                className="w-full p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                className="px-5 py-2.5 bg-purple-700 hover:bg-purple-800 text-white rounded-xl font-bold text-xs flex items-center gap-1.5 shadow-sm transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Submit DPDP Data Subject Request</span>
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
