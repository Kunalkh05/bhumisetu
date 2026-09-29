import React, { useState } from 'react';
import { 
  Bot, 
  Send, 
  X, 
  Sparkles, 
  ShieldAlert, 
  HelpCircle, 
  FileText, 
  Search, 
  Compass, 
  CheckCircle2,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

interface Message {
  sender: 'user' | 'assistant';
  text: string;
  textHi?: string;
  timestamp: string;
  sourceNote?: string;
}

export const BhuMitraAiModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onNavigateToTab: (tabId: any) => void;
}> = ({ isOpen, onClose, onNavigateToTab }) => {
  const { language } = useApp();
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'assistant',
      text: "Namaste! I am BhuMitra AI, your citizen-friendly assistant for land records and document understanding. How may I assist you today?",
      textHi: "नमस्ते! मैं भूमिमित्र एआई हूँ, भू-अभिलेखों एवं राजस्व दस्तावेजों को समझने में आपका नागरिक सहायक। मैं आज आपकी क्या सहायता कर सकता हूँ?",
      timestamp: 'Just now',
      sourceNote: 'Civic-tech educational AI assistant • Not legal advice'
    }
  ]);

  const quickQuestions = [
    {
      en: "What is ULPIN?",
      hi: "यूएलपीआईएन (Bhu-Aadhaar) क्या है?",
      answerEn: "ULPIN (Unique Land Parcel Identification Number), often called Bhu-Aadhaar, is a 14-digit alphanumeric code assigned to each land parcel in India. It is generated from the longitude and latitude of the parcel's corner coordinates using CORS and Survey of India standards, preventing duplicate claims and ensuring unique spatial identification.",
      answerHi: "यूएलपीआईएन (भू-आधार) भारत में प्रत्येक भूखंड को दिया जाने वाला १४-अंकीय विशिष्ट पहचान क्रमांक है। यह भूखंड के अक्षांश और देशांतर निर्देशांकों (GPS) पर आधारित होता है, जिससे दोहरे दावों की संभावना समाप्त होती है।"
    },
    {
      en: "What is a 7/12 extract?",
      hi: "७/१२ (सात-बारा) उद्धरण क्या होता है?",
      answerEn: "The 7/12 extract (Saat Bara Utara) is an official Record of Rights (RoR) used in states like Maharashtra and Gujarat. Village Form VII details land ownership, survey numbers, and tenancy, while Village Form XII records agricultural details like crops grown, fallow land, and irrigation. Note: It is an evidentiary record of rights maintained by the Revenue Department, but transactions require registered deeds.",
      answerHi: "७/१२ उद्धरण (सात-बारा) महाराष्ट्र एवं गुजरात जैसे राज्यों में राजस्व अधिकार अभिलेख (RoR) है। गांव नमूना ७ में मालिकाना हक व सर्वे नंबर तथा गांव नमूना १२ में फसल व सिंचाई का विवरण होता है।"
    },
    {
      en: "What is mutation?",
      hi: "नामांतरण (Mutation / दाखिल-खारिज) क्या है?",
      answerEn: "Mutation (also known as Dakhil-Kharij, Ferfar, or Intqal) is the official administrative process of updating revenue records when land ownership transfers through sale deed, inheritance, partition, or gift. It transfers the tax-paying liability in the government revenue books.",
      answerHi: "नामांतरण (दाखिल-खारिज/फेरफार/इंतकाल) भूमि विक्रय, विरासत या विभाजन के बाद सरकारी राजस्व अभिलेखों में नया भूस्वामी दर्ज करने की वैधानिक प्रशासनिक प्रक्रिया है।"
    },
    {
      en: "How do I check my land record?",
      hi: "मैं अपना भू-अभिलेख कैसे देखूँ?",
      answerEn: "You can use our 'Land Search' tab to find your property via State, District, Tehsil, and Village, or directly visit your state's official Bhulekh portal (e.g. Mahabhulekh in Maharashtra, UP Bhulekh in UP, Bhoomi in Karnataka) which are listed in our State Portals Directory.",
      answerHi: "आप हमारे 'भू-अभिलेख खोजें' विकल्प से अपना राज्य, जिला, तहसील व गांव चुनकर रिकॉर्ड देख सकते हैं, या हमारे राज्य पोर्टल निर्देशिका से अपने राज्य के आधिकारिक पोर्टल पर जा सकते हैं।"
    },
    {
      en: "What does an area discrepancy mean?",
      hi: "दस्तावेजों में क्षेत्रफल भिन्नता का क्या अर्थ है?",
      answerEn: "An area discrepancy occurs when the area mentioned in a historic registered sale deed differs from the digitized Record of Rights (7/12 or Jamabandi) or modern drone cadastral resurvey (SVAMITVA). For example, a 2.45 Ha deed vs 2.50 Ha drone map. We recommend getting a joint measurement (Mojani) from the Taluka Inspector of Land Records (TILR).",
      answerHi: "क्षेत्रफल भिन्नता का अर्थ है कि पुराने बैनामे और वर्तमान डिजिटल खतौनी या ड्रोन नक्शे में दर्ज क्षेत्रफल में अंतर है। इसके समाधान हेतु तहसील भूमि अभिलेख निरीक्षक (TILR) से संयुक्त सीमांकन (मोजणी) कराने की सलाह दी जाती है।"
    },
    {
      en: "What documents are required for mutation?",
      hi: "नामांतरण के लिए कौन से दस्तावेज आवश्यक हैं?",
      answerEn: "Common documents required for mutation include: 1) Registered Sale / Gift / Partition Deed from the Sub-Registrar, 2) Current Record of Rights (7/12, Khatauni, or RTC), 3) Death certificate and legal heir certificate (in inheritance cases), 4) Encumbrance Certificate (EC), and 5) Prescribed Application Form.",
      answerHi: "नामांतरण हेतु प्रमुख दस्तावेज: १) उप-पंजीयक द्वारा पंजीकृत विलेख (बैनामा), २) वर्तमान खतौनी/७/१२ नकल, ३) वारिसान प्रमाणपत्र (विरासत मामले में), ४) भारमुक्त प्रमाणपत्र (EC), एवं ५) विहित आवेदन पत्र।"
    }
  ];

  if (!isOpen) return null;

  const handleSendMessage = (textToSend?: string) => {
    const query = textToSend || inputValue.trim();
    if (!query) return;

    const userMsg: Message = {
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setInputValue('');

    // Match with knowledge base
    const lowerQuery = query.toLowerCase();
    let replyEn = "Thank you for asking. BHUMISETU aggregates information from land records, cadastral maps, and registration systems to assist your preliminary inquiry. For binding legal verification, please consult your local Revenue Officer or Sub-Registrar.";
    let replyHi = "पूछने के लिए धन्यवाद। भूमिसेतु भू-अभिलेखों, डिजिटल नक्शों और पंजीयन प्रणालियों की प्राथमिक जानकारी प्रदान करता है। आधिकारिक कानूनी प्रमाणीकरण हेतु कृपया अपने राजस्व अधिकारी से संपर्क करें।";

    for (const q of quickQuestions) {
      if (lowerQuery.includes('ulpin') || lowerQuery.includes('bhu-aadhaar') || lowerQuery.includes('14')) {
        replyEn = quickQuestions[0].answerEn;
        replyHi = quickQuestions[0].answerHi;
        break;
      } else if (lowerQuery.includes('7/12') || lowerQuery.includes('saat bara') || lowerQuery.includes('extract')) {
        replyEn = quickQuestions[1].answerEn;
        replyHi = quickQuestions[1].answerHi;
        break;
      } else if (lowerQuery.includes('mutation') || lowerQuery.includes('dakhil') || lowerQuery.includes('ferfar') || lowerQuery.includes('intqal')) {
        replyEn = quickQuestions[2].answerEn;
        replyHi = quickQuestions[2].answerHi;
        break;
      } else if (lowerQuery.includes('check') || lowerQuery.includes('search') || lowerQuery.includes('find')) {
        replyEn = quickQuestions[3].answerEn;
        replyHi = quickQuestions[3].answerHi;
        break;
      } else if (lowerQuery.includes('discrepancy') || lowerQuery.includes('mismatch') || lowerQuery.includes('difference') || lowerQuery.includes('area')) {
        replyEn = quickQuestions[4].answerEn;
        replyHi = quickQuestions[4].answerHi;
        break;
      } else if (lowerQuery.includes('document') || lowerQuery.includes('required') || lowerQuery.includes('papers')) {
        replyEn = quickQuestions[5].answerEn;
        replyHi = quickQuestions[5].answerHi;
        break;
      }
    }

    setTimeout(() => {
      setMessages(prev => [
        ...prev,
        {
          sender: 'assistant',
          text: replyEn,
          textHi: replyHi,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          sourceNote: 'General guidance • Not legal advice'
        }
      ]);
    }, 400);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/60 backdrop-blur-2xs animate-fadeIn" role="dialog">
      <div className="bg-white border border-slate-300 w-full max-w-2xl rounded-xs shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-[#002642] via-[#0b3866] to-[#002b49] text-white p-4 flex items-center justify-between border-b-2 border-[#f37021]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#f37021] flex items-center justify-center text-white shadow-xs">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-extrabold text-sm sm:text-base tracking-wide">
                  BhuMitra AI • भूमिमित्र
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-[#138808] text-white">
                  Civic AI
                </span>
              </div>
              <p className="text-[11px] text-amber-200">
                {language === 'en' 
                  ? 'Unified Land Information Assistant & Document Explainer' 
                  : 'एकीकृत भू-सूचना सहायक एवं दस्तावेज मार्गदर्शक'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 hover:bg-white/10 rounded-xs text-white transition-colors"
            title="Close Assistant"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Legal Disclaimer Pill */}
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center gap-2 text-[10px] text-amber-900">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-700 flex-shrink-0" />
          <span>
            {language === 'en'
              ? 'Prototype Assistant: Provides preliminary guidance. Never constitutes legally binding title verification or legal advice.'
              : 'प्रारूप सहायक: केवल प्राथमिक मार्गदर्शन हेतु। यह कानूनी शीर्षक सत्यापन अथवा विधिक सलाह नहीं है।'}
          </span>
        </div>

        {/* Message Log */}
        <div className="flex-1 p-4 overflow-y-auto space-y-3.5 bg-slate-50 text-xs">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-xs p-3 shadow-xs leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-[#002642] text-white rounded-br-none'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none'
                }`}
              >
                {msg.sender === 'assistant' && (
                  <div className="flex items-center gap-1.5 font-bold text-[#f37021] text-[10px] uppercase mb-1">
                    <Sparkles className="w-3 h-3" />
                    <span>BhuMitra AI</span>
                  </div>
                )}
                <div>
                  {language === 'en' ? msg.text : (msg.textHi || msg.text)}
                </div>
                <div className="mt-1 flex items-center justify-between gap-3 text-[9px] text-slate-400">
                  <span>{msg.timestamp}</span>
                  {msg.sourceNote && (
                    <span className="italic">{msg.sourceNote}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Quick Question Chips */}
        <div className="px-4 py-2.5 bg-white border-t border-slate-200">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <HelpCircle className="w-3 h-3 text-[#f37021]" />
            <span>{language === 'en' ? 'Quick Land Queries:' : 'त्वरित प्रश्न:'}</span>
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            {quickQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(language === 'en' ? q.en : q.hi)}
                className="px-2.5 py-1 text-[11px] bg-slate-100 hover:bg-[#002642] hover:text-white text-slate-700 rounded-xs border border-slate-200 transition-colors text-left"
              >
                {language === 'en' ? q.en : q.hi}
              </button>
            ))}
          </div>
        </div>

        {/* Message Input Box */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 flex items-center gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder={language === 'en' ? 'Ask BhuMitra about land records, mutation, ULPIN...' : 'भू-अभिलेख, नामांतरण, यूएलपीआईएन के बारे में पूछें...'}
            className="flex-1 px-3 py-2 text-xs border border-slate-300 rounded-xs focus:ring-1 focus:ring-[#002642] focus:outline-hidden bg-white"
          />
          <button
            onClick={() => handleSendMessage()}
            className="px-4 py-2 bg-[#f37021] hover:bg-[#d95a10] text-white font-bold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{language === 'en' ? 'Ask' : 'पूछें'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
