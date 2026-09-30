import React, { useState } from 'react';
import { 
  HelpCircle, 
  Search, 
  FileCheck, 
  Map, 
  Sparkles, 
  ChevronDown, 
  ChevronUp, 
  ShieldAlert, 
  Phone, 
  Mail, 
  Clock, 
  ArrowRight,
  BookOpen
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { PublicTab } from '../common/GovNavigation';

export const HelpHowItWorksView: React.FC<{
  onNavigateTab: (tab: PublicTab) => void;
  onOpenAiChat: () => void;
}> = ({ onNavigateTab, onOpenAiChat }) => {
  const { language } = useApp();
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const steps = [
    {
      step: '01',
      title: 'Search Any Land Parcel',
      titleHi: 'भू-अभिलेख खोजें',
      desc: 'Use hierarchical selection (State → District → Tehsil → Village) or enter a 14-digit ULPIN / Survey Number to locate your land parcel.'
    },
    {
      step: '02',
      title: 'Inspect Unified Intelligence',
      titleHi: 'एकीकृत आसूचना देखें',
      desc: 'View synthesized ownership details, registered sale deeds, active mutation progress, and cadastral GIS boundaries on a single screen.'
    },
    {
      step: '03',
      title: 'Run AI Document Verification',
      titleHi: 'दस्तावेज सत्यापन करें',
      desc: 'Upload 7/12 extracts, sale deeds, or mutation notices to extract key fields and cross-compare against digital government records.'
    },
    {
      step: '04',
      title: 'Review Discrepancies & Guidelines',
      titleHi: 'विसंगति समीक्षा एवं मार्गदर्शन',
      desc: 'Inspect preliminary risk checks for area variances or name spelling mismatches and receive recommended next steps for revenue authority visits.'
    }
  ];

  const faqs = [
    {
      q: 'Does BHUMISETU provide legally binding title verification?',
      qHi: 'क्या भूमिसेतु कानूनी रूप से बाध्यकारी स्वत्व प्रमाण प्रदान करता है?',
      a: 'No. BHUMISETU is a prototype civic-tech platform created for demonstration and preliminary discovery purposes. It does NOT provide legal title certificates or legal advice. Certified title certificates must be obtained directly from the respective State Sub-Registrar and Revenue Department.'
    },
    {
      q: 'What should I do if an Area Discrepancy is detected?',
      qHi: 'यदि क्षेत्रफल में भिन्नता पाई जाती है तो क्या करें?',
      a: 'If our AI highlights a variance (such as 2.45 Ha in a sale deed vs 2.50 Ha in a drone survey), we recommend applying for a joint field measurement (Mojani) through the Taluka Inspector of Land Records (TILR) at your local Tehsil office.'
    },
    {
      q: 'How does ULPIN (Bhu-Aadhaar) help me as a citizen?',
      qHi: 'यूएलपीआईएन (भू-आधार) एक नागरिक के रूप में मेरी कैसे मदद करता है?',
      a: 'ULPIN provides a unique 14-digit identification number derived from the exact latitude and longitude coordinates of your parcel. It prevents fraudulent duplicate sales of the same piece of land and streamlines bank agricultural loans.'
    },
    {
      q: 'Where can I track an active mutation (Ferfar) application?',
      qHi: 'मैं अपने नामांतरण आवेदन की स्थिति कहाँ देख सकता हूँ?',
      a: 'You can navigate to our "Mutation Tracker" tab and enter your Mutation Application Token (e.g. MUT-MH-2026-001245) to see the step-by-step progress from Talathi scrutiny to final Circle Officer approval.'
    }
  ];

  return (
    <div className="space-y-6 text-left">
      {/* 1. Header Banner */}
      <div className="bg-[#002642] text-white p-5 rounded-xs border-b-3 border-[#f37021] flex flex-wrap justify-between items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold">
              {language === 'en' ? 'Help & How It Works' : 'सहायता एवं उपयोग मार्गदर्शिका'}
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-[#138808] text-white">
              CITIZEN GUIDE
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            {language === 'en'
              ? 'Simple step-by-step guidance on searching land records, running preliminary AI document verification, and resolving record discrepancies.'
              : 'भू-अभिलेखों की खोज, दस्तावेज सत्यापन एवं विसंगति समाधान की सरल नागरिक मार्गदर्शिका।'}
          </p>
        </div>

        <button
          onClick={onOpenAiChat}
          className="px-4 py-2 bg-[#f37021] hover:bg-[#d95a10] text-white font-extrabold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Ask BhuMitra AI</span>
        </button>
      </div>

      {/* 2. 4-Step How It Works Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {steps.map((st, idx) => (
          <div key={idx} className="bg-white border border-slate-300 rounded-xs p-5 shadow-xs text-xs space-y-2">
            <span className="font-mono font-black text-xl text-[#f37021]">
              {st.step}
            </span>
            <h3 className="font-extrabold text-sm text-[#002642]">
              {language === 'en' ? st.title : st.titleHi}
            </h3>
            <p className="text-slate-600 leading-relaxed text-[11px]">
              {st.desc}
            </p>
          </div>
        ))}
      </div>

      {/* 3. Frequently Asked Questions (FAQ) Accordion */}
      <div className="bg-white border border-slate-300 rounded-xs p-6 shadow-xs space-y-4">
        <h3 className="font-black text-base text-[#002642] uppercase tracking-wide border-b border-slate-200 pb-2">
          Frequently Asked Questions (FAQs)
        </h3>

        <div className="space-y-3 text-xs">
          {faqs.map((faq, idx) => {
            const isOpen = openFaq === idx;
            return (
              <div key={idx} className="border border-slate-200 rounded-xs overflow-hidden">
                <button
                  onClick={() => setOpenFaq(isOpen ? null : idx)}
                  className="w-full p-3.5 bg-slate-50 hover:bg-slate-100 flex justify-between items-center text-left font-bold text-xs text-[#002642] transition-colors"
                >
                  <span>{language === 'en' ? faq.q : faq.qHi}</span>
                  {isOpen ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
                </button>
                {isOpen && (
                  <div className="p-4 bg-white text-slate-700 text-[11px] leading-relaxed border-t border-slate-200">
                    {faq.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Helpdesk Contact Information */}
      <div className="bg-slate-100 border border-slate-300 rounded-xs p-5 flex flex-wrap justify-between items-center gap-4 text-xs">
        <div className="space-y-1">
          <div className="font-bold text-[#002642] flex items-center gap-1.5">
            <Phone className="w-4 h-4 text-[#f37021]" />
            <span>Need assistance with your land records?</span>
          </div>
          <p className="text-slate-600 text-[11px]">
            National Toll-Free Helpline: <strong>1800-11-2013</strong> (Monday to Friday, 9:00 AM – 6:00 PM IST)
          </p>
        </div>

        <button
          onClick={() => onNavigateTab('SEARCH')}
          className="px-4 py-2 bg-[#002642] hover:bg-[#0b3866] text-white font-bold text-xs rounded-xs flex items-center gap-1.5 transition-colors"
        >
          <span>Start Land Search</span>
          <ArrowRight className="w-3.5 h-3.5 text-[#f37021]" />
        </button>
      </div>
    </div>
  );
};
