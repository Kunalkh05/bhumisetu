import React, { useState, useEffect } from 'react';
import { 
  Search, 
  FileCheck, 
  Landmark, 
  ShieldAlert, 
  ChevronRight, 
  ChevronLeft, 
  Pause, 
  Play,
  Sparkles,
  ArrowRight,
  ExternalLink,
  Layers,
  Mic
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { PublicTab } from '../common/GovNavigation';

interface HeroSlide {
  id: string;
  schemeCode: string;
  title: string;
  titleHi: string;
  tagline: string;
  taglineHi: string;
  badge: string;
  gradientOverlay: string;
  accentColor: string;
  backgroundImageUrl?: string;
  ministry: string;
}

const HERO_SLIDES: HeroSlide[] = [
  {
    id: 'svamitva',
    schemeCode: 'SVAMITVA',
    title: 'SVAMITVA Scheme • Drone Cadastral Mapping',
    titleHi: 'स्वामित्व योजना • हाई-रिज़ॉल्यूशन ड्रोन सर्वेक्षण',
    tagline: 'High-precision drone mapping delivering statutory Property Cards (Sampatti Patra) for rural inhabited lands across 3.15+ lakh villages.',
    taglineHi: '३.१५+ लाख ग्रामों में आधुनिक ड्रोन सर्वेक्षण द्वारा ग्रामीण आबादी भूमि का निर्विवाद कानूनी संपत्ति पत्रक।',
    badge: 'RURAL LAND RIGHTS',
    gradientOverlay: 'from-[#00172d]/90 via-[#002642]/85 to-[#0b3866]/80',
    accentColor: '#f37021',
    ministry: 'Ministry of Panchayati Raj & Survey of India'
  },
  {
    id: 'pmkisan',
    schemeCode: 'PM-KISAN',
    title: 'PM-KISAN • Direct Farmer Land Benefit Transfer',
    titleHi: 'पीएम-किसान • पारदर्शी प्रत्यक्ष बैंक अंतरण',
    tagline: 'Over ₹3.24 Lakh Crore directly transferred into Aadhaar-seeded accounts of 11+ Crore registered landholding farmers nationwide.',
    taglineHi: '११+ करोड़ पंजीकृत किसान परिवारों के बैंक खातों में ₹३.२४+ लाख करोड़ से अधिक का प्रत्यक्ष लाभ अंतरण।',
    badge: 'DIRECT BENEFIT TRANSFER',
    gradientOverlay: 'from-[#001e14]/90 via-[#002b1f]/85 to-[#05402a]/80',
    accentColor: '#22c55e',
    ministry: 'Ministry of Agriculture & Farmers Welfare'
  },
  {
    id: 'gatishakti',
    schemeCode: 'PM GatiShakti',
    title: 'PM GatiShakti • National Master Plan for Infrastructure',
    titleHi: 'पीएम गतिशक्ति • राष्ट्रीय मल्टी-मॉडल कनेक्टिविटी मास्टर प्लान',
    tagline: 'Multi-modal connectivity and GIS corridor synchronization ensuring rapid statutory land clearance for national highways and freight corridors.',
    taglineHi: 'राष्ट्रीय राजमार्गों एवं आर्थिक गलियारों हेतु जीआईएस आधारित त्वरित वैधानिक भूमि अनापत्ति व योजना समन्वय।',
    badge: 'MULTIMODAL INFRASTRUCTURE',
    gradientOverlay: 'from-[#110526]/90 via-[#1e0a3d]/85 to-[#002642]/80',
    accentColor: '#a855f7',
    ministry: 'Department for Promotion of Industry and Internal Trade (DPIIT)'
  },
  {
    id: 'ulpin',
    schemeCode: 'ULPIN / Bhu-Aadhaar',
    title: 'ULPIN (Bhu-Aadhaar) • 14-Digit Land Identity',
    titleHi: 'भू-आधार (यूएलपीआईएन) • १४-अंकीय विशिष्ट भू-पहचान',
    tagline: 'A unique geospatial Bhu-Aadhaar assigned to every land parcel based on longitude and latitude centroid coordinates under DILRMP.',
    taglineHi: 'डिजिटल भारत भू-अभिलेख आधुनिकीकरण कार्यक्रम के तहत अक्षांश-देशांतर निर्देशांकों पर आधारित विशिष्ट १४-अंकीय भू-आधार।',
    badge: 'NATIONAL GEO-STANDARD',
    gradientOverlay: 'from-[#002038]/90 via-[#0b3866]/85 to-[#002b49]/80',
    accentColor: '#38bdf8',
    ministry: 'Department of Land Resources (DoLR)'
  },
  {
    id: 'pmayg',
    schemeCode: 'PMAY-G',
    title: 'PMAY-G • Housing for All with Clear Land Titles',
    titleHi: 'प्रधानमंत्री आवास योजना (ग्रामीण) • पक्का मकान, सुरक्षित अधिकार',
    tagline: 'Enabling over 2.95 Crore pucca homes in rural India backed by authenticated homestead land records and direct geo-tagged DBT.',
    taglineHi: 'ग्रामीण भारत में २.९५ करोड़ से अधिक पक्के मकान, प्रमाणित आवासीय भू-अभिलेखों एवं जियो-टैग्ड वित्तीय सहायता के साथ।',
    badge: 'AFFORDABLE HOUSING',
    gradientOverlay: 'from-[#2b1000]/90 via-[#592300]/85 to-[#002642]/80',
    accentColor: '#f97316',
    ministry: 'Ministry of Rural Development'
  },
  {
    id: 'jjm',
    schemeCode: 'Jal Jeevan Mission',
    title: 'Jal Jeevan Mission • Har Ghar Jal Infrastructure',
    titleHi: 'जल जीवन मिशन • हर घर जल पाइपलाइन एवं भूमि समन्वय',
    tagline: 'Providing tap water connections to 15+ Crore rural households, coordinating village public land rights for water treatment infrastructure.',
    taglineHi: '१५+ करोड़ ग्रामीण परिवारों तक नल से शुद्ध जल, ग्राम पंचायत सार्वजनिक भूमि अधिकार एवं जल शोधन संयंत्र समन्वय।',
    badge: 'RURAL INFRASTRUCTURE',
    gradientOverlay: 'from-[#001c38]/90 via-[#03396c]/85 to-[#005b96]/80',
    accentColor: '#0ea5e9',
    ministry: 'Department of Drinking Water and Sanitation, Ministry of Jal Shakti'
  },
  {
    id: 'digilocker',
    schemeCode: 'DigiLocker',
    title: 'DigiLocker • Authenticated Digital Land Credentials',
    titleHi: 'डिजिलॉकर • सुरक्षित डिजिटल भू-अभिलेख एवं ई-प्रमाणपत्र',
    tagline: 'Legally valid digital repository under IT Act 2000 for storing and fetching digitally signed 7/12 extracts, property cards, and sale deeds.',
    taglineHi: 'सूचना प्रौद्योगिकी अधिनियम २००० के तहत मान्य, डिजिटल हस्ताक्षरित सात-बारा, खतौनी एवं विलेखों का सुरक्षित डिजिटल लॉकर।',
    badge: 'DIGITAL INDIA',
    gradientOverlay: 'from-[#00172e]/90 via-[#003366]/85 to-[#002244]/80',
    accentColor: '#60a5fa',
    ministry: 'Ministry of Electronics and Information Technology (MeitY)'
  },
  {
    id: 'bhoomikrashi',
    schemeCode: 'Bhoomi Rashi',
    title: 'Bhoomi Rashi • Seamless Highway Land Acquisition',
    titleHi: 'भूमि राशि पोर्टल • त्वरित राजमार्ग भूमि अधिग्रहण एवं मुआवजा',
    tagline: 'Accelerating public notifications under Section 3A/3D of NH Act and direct compensation payments to project-affected landowners.',
    taglineHi: 'राष्ट्रीय राजमार्ग अधिनियम की धारा ३ए/३डी के अंतर्गत त्वरित अधिसूचनाएं एवं सीधे भूस्वामियों के खाते में मुआवजा वितरण।',
    badge: 'EXPRESSWAY HIGHWAYS',
    gradientOverlay: 'from-[#2a1300]/90 via-[#4d2503]/85 to-[#002642]/80',
    accentColor: '#fb923c',
    ministry: 'Ministry of Road Transport and Highways (MoRTH)'
  },
  {
    id: 'viksitbharat',
    schemeCode: 'Viksit Bharat',
    title: 'Viksit Bharat @2047 • Next-Gen Land Governance',
    titleHi: 'विकसित भारत @२०४७ • आधुनिक एवं पारदर्शी भू-प्रशासन',
    tagline: 'Building a unified spatial intelligence layer where every citizen can discover, compare, and preliminary verify land records with zero friction.',
    taglineHi: 'एक ऐसी एकीकृत भू-आसूचना प्रणाली का निर्माण जहाँ प्रत्येक नागरिक बिना किसी बाधा के भू-अभिलेखों का प्राथमिक सत्यापन कर सके।',
    badge: 'VISION 2047',
    gradientOverlay: 'from-[#001b33]/90 via-[#002b49]/85 to-[#003e6b]/80',
    accentColor: '#eab308',
    ministry: 'Government of India Civic-Tech Vision'
  }
];

export const HeroRotatingBanner: React.FC<{
  onNavigate: (tab: PublicTab) => void;
  onOpenReport?: () => void;
}> = ({ onNavigate }) => {
  const { language, addToast } = useApp();
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [quickSearch, setQuickSearch] = useState('');
  const [isListening, setIsListening] = useState(false);

  const handleVoiceSearch = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      try {
        const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        const recognition = new SpeechRec();
        recognition.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
        setIsListening(true);
        recognition.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          setQuickSearch(transcript);
          setIsListening(false);
          addToast({
            type: 'info',
            message: `Voice search recognized: "${transcript}"`,
            messageHi: `आवाज पहचानी गई: "${transcript}"`
          });
          onNavigate('SEARCH');
        };
        recognition.onerror = () => {
          setIsListening(false);
        };
        recognition.onend = () => {
          setIsListening(false);
        };
        recognition.start();
      } catch {
        setIsListening(false);
      }
    } else {
      addToast({
        type: 'info',
        message: 'Speech recognition is simulating for your browser.',
        messageHi: 'आवाज इनपुट अनुकरण किया जा रहा है।'
      });
      setQuickSearch('Gat 123 Besa Nagpur');
      setTimeout(() => onNavigate('SEARCH'), 800);
    }
  };

  // Auto-rotate every 4.5 seconds
  useEffect(() => {
    if (isPaused) return;

    const timer = setInterval(() => {
      setCurrentSlideIndex((prev) => (prev + 1) % HERO_SLIDES.length);
    }, 4500);

    return () => clearInterval(timer);
  }, [isPaused]);

  const currentSlide = HERO_SLIDES[currentSlideIndex];

  return (
    <div className="relative overflow-hidden bg-[#00172d] text-white border-b-3 border-[#f37021] min-h-[460px] sm:min-h-[500px] flex items-center shadow-lg">
      {/* 1. Rotating Background Carousel Layers with Smooth Fade */}
      {HERO_SLIDES.map((slide, index) => {
        const isCurrent = index === currentSlideIndex;
        return (
          <div
            key={slide.id}
            className={`absolute inset-0 transition-opacity duration-1000 ease-in-out pointer-events-none ${
              isCurrent ? 'opacity-100 z-0' : 'opacity-0 -z-10'
            }`}
            style={{
              backgroundImage: `url(/assets/pm_modi_event.jpg)`,
              backgroundSize: 'cover',
              backgroundPosition: 'center 35%'
            }}
          >
            {/* Thematic Multi-Stop Gradient Overlay to ensure crystal-clear text readability */}
            <div className={`absolute inset-0 bg-gradient-to-r ${slide.gradientOverlay} backdrop-blur-2xs`} />
            
            {/* Subtle decorative grid lines representing Cadastral GIS Polygons */}
            <div className="absolute inset-0 opacity-15 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:24px_24px]" />
          </div>
        );
      })}

      {/* 2. Foreground Content Container */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left Column: Platform Title, Subtitle, CTAs & Live Slide Badge */}
          <div className="lg:col-span-8 text-left space-y-4">
            {/* Active Scheme Theme Pill */}
            <div className="flex flex-wrap items-center gap-2">
              <span 
                className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider text-slate-900 shadow-xs"
                style={{ backgroundColor: currentSlide.accentColor }}
              >
                {currentSlide.badge}
              </span>
              <span className="text-[11px] font-medium text-slate-300 hidden sm:inline">
                {currentSlide.ministry}
              </span>
            </div>

            {/* Main Hero Headings */}
            <div>
              <h1 className="text-2xl sm:text-4xl lg:text-5xl font-black tracking-tight text-white leading-tight">
                {language === 'en' ? (
                  <>
                    India’s Unified <span className="text-[#f37021]">Land Intelligence</span> Platform
                  </>
                ) : (
                  <>
                    भारत का एकीकृत <span className="text-[#f37021]">भू-आसूचना</span> एवं सत्यापन पोर्टल
                  </>
                )}
              </h1>
              <p className="mt-2.5 text-sm sm:text-base text-slate-200 max-w-2xl font-normal leading-relaxed">
                {language === 'en'
                  ? 'Search, understand and preliminarily verify land information through one citizen-friendly interface.'
                  : 'एकल नागरिक-हितैषी इंटरफ़ेस के माध्यम से विभिन्न राज्यों के भू-अभिलेखों की खोज, समझ एवं प्रारंभिक सत्यापन।'}
              </p>
            </div>

            {/* Scheme Synchronized Dynamic Sub-headline */}
            <div className="p-3 bg-white/10 backdrop-blur-sm border-l-3 border-[#f37021] rounded-xs max-w-2xl">
              <div className="text-xs font-bold text-amber-300">
                {language === 'en' ? currentSlide.title : currentSlide.titleHi}
              </div>
              <p className="text-[11px] text-slate-200 mt-0.5 line-clamp-2">
                {language === 'en' ? currentSlide.tagline : currentSlide.taglineHi}
              </p>
            </div>

            {/* Direct Quick Search Bar with Voice Input */}
            <div className="pt-2 max-w-2xl">
              <form 
                onSubmit={(e) => {
                  e.preventDefault();
                  onNavigate('SEARCH');
                }}
                className="bg-white p-1 sm:p-1.5 rounded-xs shadow-xl flex items-center gap-2 border-2 border-amber-400"
              >
                <div className="pl-2 text-slate-500">
                  <Search className="w-4 h-4 text-[#002642]" />
                </div>
                <input
                  type="text"
                  value={quickSearch}
                  onChange={(e) => setQuickSearch(e.target.value)}
                  placeholder={language === 'en' 
                    ? "Enter Survey / Gat No., 14-digit ULPIN, or Village..." 
                    : "सर्वे / गट क्रमांक, १४-अंकीय भू-आधार (ULPIN) या गाँव दर्ज करें..."}
                  className="flex-1 bg-transparent text-slate-800 text-xs sm:text-sm font-semibold focus:outline-none placeholder:text-slate-400"
                />
                <button
                  type="button"
                  onClick={handleVoiceSearch}
                  className={`p-1.5 rounded-xs transition-colors flex items-center gap-1 text-[11px] font-bold ${
                    isListening 
                      ? 'bg-red-500 text-white animate-pulse' 
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                  title={language === 'en' ? "Search by Voice" : "बोलकर खोजें"}
                  aria-label="Search by Voice"
                >
                  <Mic className={`w-3.5 h-3.5 ${isListening ? 'text-white' : 'text-[#f37021]'}`} />
                  <span className="hidden sm:inline">{language === 'en' ? 'Voice' : 'बोलें'}</span>
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#f37021] hover:bg-[#d95a10] text-white font-extrabold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
                >
                  <span>{language === 'en' ? 'Search' : 'खोजें'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </form>

              {/* Instant sample search chips for zero cognitive load */}
              <div className="flex flex-wrap items-center gap-1.5 mt-2 text-[10px]">
                <span className="text-slate-300 font-semibold">{language === 'en' ? 'Quick samples:' : 'त्वरित नमूने:'}</span>
                {[
                  { label: 'Gat 123/4 Besa', tab: 'SEARCH' },
                  { label: 'ULPIN: 27712049001234', tab: 'SEARCH' },
                  { label: 'One Property View', tab: 'PROPERTY_INTEL' }
                ].map((chip, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setQuickSearch(chip.label);
                      onNavigate(chip.tab as any);
                    }}
                    className="px-2 py-0.5 bg-white/15 hover:bg-white/30 text-amber-200 border border-white/20 rounded-xs transition-colors cursor-pointer"
                  >
                    {chip.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Primary, Secondary & Third Action CTAs */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              {/* Secondary CTA */}
              <button
                onClick={() => onNavigate('DOC_VERIFY')}
                className="px-4 py-2 bg-white text-[#002642] hover:bg-slate-100 font-extrabold text-xs rounded-xs shadow-md flex items-center gap-1.5 transition-all transform hover:-translate-y-0.5"
              >
                <FileCheck className="w-3.5 h-3.5 text-[#002642]" />
                <span>{language === 'en' ? 'AI Document Verification' : 'दस्तावेज सत्यापन'}</span>
              </button>

              {/* Third CTA */}
              <button
                onClick={() => onNavigate('SCHEMES')}
                className="px-4 py-2 bg-white/15 hover:bg-white/25 border border-white/30 text-white font-bold text-xs rounded-xs transition-colors flex items-center gap-1.5"
              >
                <Landmark className="w-3.5 h-3.5 text-amber-300" />
                <span>{language === 'en' ? 'Explore 9 Schemes' : '९ प्रमुख योजनाएं'}</span>
              </button>

              {/* Fourth CTA */}
              <button
                onClick={() => onNavigate('PROPERTY_INTEL')}
                className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-700 hover:to-teal-800 text-white font-extrabold text-xs rounded-xs shadow-md flex items-center gap-1.5 transition-all"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                <span>{language === 'en' ? 'One Property — One View' : 'एकल संपत्ति दृश्य'}</span>
              </button>
            </div>

            {/* Subtle Mandatory Disclaimer */}
            <div className="flex items-center gap-2 pt-2 text-[11px] text-amber-200/90 font-medium">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              <span>
                {language === 'en'
                  ? 'Prototype platform — information shown is for preliminary verification and does not constitute legal title clearance.'
                  : 'प्रारूप मंच — प्रदर्शित जानकारी केवल प्रारंभिक सत्यापन हेतु है और विधिक स्वत्व प्रमाणीकरण नहीं है।'}
              </span>
            </div>
          </div>

          {/* Right Column: Hon'ble Prime Minister Dignitary & Vision Card */}
          <div className="lg:col-span-4">
            <div className="bg-white/10 backdrop-blur-md border border-white/25 rounded-xs p-4 shadow-xl text-left space-y-3">
              <div className="flex items-center gap-3.5">
                {/* Official Cutout Studio Portrait with Clean Framing */}
                <div className="relative flex-shrink-0">
                  <div className="w-20 h-24 sm:w-24 sm:h-28 rounded-xs overflow-hidden border-2 border-[#f37021] bg-white shadow-md flex items-center justify-center">
                    <img 
                      src="/assets/pm_modi_2023.jpg" 
                      alt={language === 'en' ? 'Shri Narendra Modi, Prime Minister of India' : 'श्री नरेन्द्र मोदी, माननीय प्रधानमंत्री'} 
                      className="w-full h-full object-cover object-top"
                    />
                  </div>
                  <div className="absolute -top-1.5 -left-1.5 px-1.5 py-0.5 bg-[#f37021] text-white font-bold text-[9px] rounded-xs shadow-xs uppercase tracking-wider">
                    {language === 'en' ? 'Leadership' : 'नेतृत्व'}
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-xs font-extrabold text-white leading-tight">
                    {language === 'en' ? 'Shri Narendra Modi' : 'श्री नरेन्द्र मोदी'}
                  </div>
                  <div className="text-[11px] text-[#f37021] font-bold">
                    {language === 'en' ? "Hon'ble Prime Minister of India" : 'माननीय प्रधानमंत्री, भारत'}
                  </div>
                  <div className="text-[10px] text-slate-300">
                    {language === 'en' ? 'Government of India' : 'भारत सरकार'}
                  </div>
                </div>
              </div>

              {/* Authentic Vision Quote */}
              <div className="border-t border-white/20 pt-2.5">
                <blockquote className="text-[11px] italic text-amber-200 font-serif leading-relaxed">
                  {language === 'en'
                    ? '"Transparent land records and time-bound compensation empower our farmers and establish the foundation of Viksit Bharat."'
                    : '“पारदर्शी भू-अभिलेख और समयबद्ध मुआवजा हमारे किसानों को सशक्त बनाकर विकसित भारत का आधार स्थापित करते हैं।”'}
                </blockquote>
              </div>

              {/* Quick Jump to One Property One View */}
              <button
                onClick={() => onNavigate('PROPERTY_INTEL')}
                className="w-full mt-1 py-1.5 bg-white/10 hover:bg-white/20 border border-white/30 rounded-xs text-[11px] text-white font-semibold flex items-center justify-between px-3 transition-colors"
              >
                <span>{language === 'en' ? 'View Demo Intelligence Card' : 'डेमो कार्ड देखें'}</span>
                <ChevronRight className="w-3.5 h-3.5 text-amber-300" />
              </button>
            </div>
          </div>
        </div>

        {/* 3. Bottom Carousel Controller Strip */}
        <div className="mt-8 pt-4 border-t border-white/15 flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Slide Indicators */}
          <div className="flex items-center gap-1.5">
            {HERO_SLIDES.map((slide, idx) => (
              <button
                key={slide.id}
                onClick={() => setCurrentSlideIndex(idx)}
                className={`h-1.5 rounded-full transition-all ${
                  idx === currentSlideIndex 
                    ? 'w-8 bg-[#f37021]' 
                    : 'w-2 bg-white/30 hover:bg-white/60'
                }`}
                title={`Go to slide: ${slide.schemeCode}`}
                aria-label={`Slide ${idx + 1}: ${slide.schemeCode}`}
              />
            ))}
          </div>

          {/* Carousel Controls */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-300 font-mono">
              {currentSlideIndex + 1} / {HERO_SLIDES.length}
            </span>

            <button
              onClick={() => setIsPaused(!isPaused)}
              className="p-1.5 rounded-xs bg-white/10 hover:bg-white/20 text-white transition-colors"
              title={isPaused ? "Play Carousel" : "Pause Carousel"}
              aria-label={isPaused ? "Play Carousel" : "Pause Carousel"}
            >
              {isPaused ? <Play className="w-3.5 h-3.5 text-amber-300" /> : <Pause className="w-3.5 h-3.5" />}
            </button>

            <button
              onClick={() => setCurrentSlideIndex((prev) => (prev - 1 + HERO_SLIDES.length) % HERO_SLIDES.length)}
              className="p-1.5 rounded-xs bg-white/10 hover:bg-white/20 text-white transition-colors"
              title="Previous Scheme"
              aria-label="Previous Scheme"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={() => setCurrentSlideIndex((prev) => (prev + 1) % HERO_SLIDES.length)}
              className="p-1.5 rounded-xs bg-white/10 hover:bg-white/20 text-white transition-colors"
              title="Next Scheme"
              aria-label="Next Scheme"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
