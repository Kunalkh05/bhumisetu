import React, { useState, useEffect, useRef } from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  Pause, 
  Play, 
  ExternalLink, 
  Info, 
  ShieldCheck, 
  Sparkles, 
  ArrowRight, 
  X, 
  Phone, 
  Landmark, 
  FileText, 
  CheckCircle2, 
  Layers, 
  Compass, 
  Award,
  Download,
  Check,
  Megaphone,
  HelpCircle,
  Clock,
  Send,
  Eye,
  Filter
} from 'lucide-react';
import { GOV_SCHEMES, GovScheme, CAMPAIGN_TICKER_ITEMS, SchemeCategory } from '../../data/govSchemesData';
import { NationalEmblem } from './NationalEmblem';
import { IndianFlag } from './IndianFlag';

interface GovSchemeBannersProps {
  language?: 'en' | 'hi';
  onSelectScheme?: (scheme: GovScheme) => void;
  filterCategory?: SchemeCategory;
}

/**
 * Helper to return themed CSS classes for Indian Government official ad banners
 */
export const getThemeClasses = (theme: GovScheme['theme']) => {
  switch (theme) {
    case 'saffron':
      return {
        bg: 'bg-gradient-to-r from-[#002642] via-[#7c2d12] to-[#c2410c]',
        cardBg: 'bg-orange-50/70 border-orange-200',
        pill: 'bg-amber-100 text-amber-950 border-amber-300',
        accent: 'text-amber-300',
        btn: 'bg-[#f37021] hover:bg-[#d95a10] text-white',
        badgeBg: 'bg-orange-500/20 text-orange-100 border-orange-400/40',
        borderAccent: 'border-t-[#f37021]',
        highlightText: 'text-[#c2410c]',
        gradientBanner: 'from-[#002642] via-[#7c2d12] to-[#c2410c]'
      };
    case 'navy':
      return {
        bg: 'bg-gradient-to-r from-[#00172d] via-[#002642] to-[#0b3866]',
        cardBg: 'bg-blue-50/70 border-blue-200',
        pill: 'bg-blue-100 text-blue-950 border-blue-300',
        accent: 'text-sky-300',
        btn: 'bg-[#002642] hover:bg-[#0b3866] text-white',
        badgeBg: 'bg-blue-500/20 text-blue-100 border-blue-400/40',
        borderAccent: 'border-t-[#002642]',
        highlightText: 'text-[#002642]',
        gradientBanner: 'from-[#00172d] via-[#002642] to-[#0b3866]'
      };
    case 'emerald':
      return {
        bg: 'bg-gradient-to-r from-[#002642] via-[#064e3b] to-[#047857]',
        cardBg: 'bg-emerald-50/70 border-emerald-200',
        pill: 'bg-emerald-100 text-emerald-950 border-emerald-300',
        accent: 'text-emerald-300',
        btn: 'bg-[#138808] hover:bg-[#0f6806] text-white',
        badgeBg: 'bg-emerald-500/20 text-emerald-100 border-emerald-400/40',
        borderAccent: 'border-t-[#138808]',
        highlightText: 'text-[#047857]',
        gradientBanner: 'from-[#002642] via-[#064e3b] to-[#047857]'
      };
    case 'green':
      return {
        bg: 'bg-gradient-to-r from-[#002642] via-[#14532d] to-[#15803d]',
        cardBg: 'bg-green-50/70 border-green-200',
        pill: 'bg-green-100 text-green-950 border-green-300',
        accent: 'text-emerald-300',
        btn: 'bg-[#15803d] hover:bg-[#166534] text-white',
        badgeBg: 'bg-green-500/20 text-green-100 border-green-400/40',
        borderAccent: 'border-t-[#15803d]',
        highlightText: 'text-[#15803d]',
        gradientBanner: 'from-[#002642] via-[#14532d] to-[#15803d]'
      };
    case 'amber':
      return {
        bg: 'bg-gradient-to-r from-[#002642] via-[#78350f] to-[#b45309]',
        cardBg: 'bg-amber-50/70 border-amber-200',
        pill: 'bg-amber-100 text-amber-950 border-amber-300',
        accent: 'text-amber-300',
        btn: 'bg-[#b45309] hover:bg-[#92400e] text-white',
        badgeBg: 'bg-amber-500/20 text-amber-100 border-amber-400/40',
        borderAccent: 'border-t-[#b45309]',
        highlightText: 'text-[#b45309]',
        gradientBanner: 'from-[#002642] via-[#78350f] to-[#b45309]'
      };
    case 'blue':
      return {
        bg: 'bg-gradient-to-r from-[#002642] via-[#0369a1] to-[#0284c7]',
        cardBg: 'bg-sky-50/70 border-sky-200',
        pill: 'bg-sky-100 text-sky-950 border-sky-300',
        accent: 'text-sky-300',
        btn: 'bg-[#0284c7] hover:bg-[#0369a1] text-white',
        badgeBg: 'bg-sky-500/20 text-sky-100 border-sky-400/40',
        borderAccent: 'border-t-[#0284c7]',
        highlightText: 'text-[#0284c7]',
        gradientBanner: 'from-[#002642] via-[#0369a1] to-[#0284c7]'
      };
    case 'purple':
    default:
      return {
        bg: 'bg-gradient-to-r from-[#002642] via-[#3b0764] to-[#6b21a8]',
        cardBg: 'bg-purple-50/70 border-purple-200',
        pill: 'bg-purple-100 text-purple-950 border-purple-300',
        accent: 'text-purple-300',
        btn: 'bg-[#6b21a8] hover:bg-[#581c87] text-white',
        badgeBg: 'bg-purple-500/20 text-purple-100 border-purple-400/40',
        borderAccent: 'border-t-[#6b21a8]',
        highlightText: 'text-[#6b21a8]',
        gradientBanner: 'from-[#002642] via-[#3b0764] to-[#6b21a8]'
      };
  }
};

/**
 * 1. Hero Auto-Sliding Government Flagship Scheme Ad Banner Carousel
 * Modeled after the official campaign carousels on india.gov.in, digitalindia.gov.in, and rural.nic.in
 */
export const GovSchemeHeroCarousel: React.FC<GovSchemeBannersProps> = ({ 
  language = 'en' 
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [selectedSchemeForModal, setSelectedSchemeForModal] = useState<GovScheme | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const totalSlides = GOV_SCHEMES.length;

  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % totalSlides);
      }, 5500);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, totalSlides]);

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev - 1 + totalSlides) % totalSlides);
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev + 1) % totalSlides);
  };

  const currentScheme = GOV_SCHEMES[currentIndex];
  const themeStyle = getThemeClasses(currentScheme.theme);

  return (
    <>
      <div 
        className="relative overflow-hidden rounded-xs border border-slate-300 shadow-md group transition-all"
        onMouseEnter={() => setIsPlaying(false)}
        onMouseLeave={() => setIsPlaying(true)}
        aria-label="Government Schemes and Flagship Campaigns Banner"
      >
        {/* Top Tricolour Ribbon (Saffron, White, Green) */}
        <div className="h-1.5 w-full flex">
          <div className="w-1/3 bg-[#FF9933]"></div>
          <div className="w-1/3 bg-[#FFFFFF]"></div>
          <div className="w-1/3 bg-[#138808]"></div>
        </div>

        {/* Main Banner Slide Container */}
        <div className={`${themeStyle.bg} text-white p-5 sm:p-7 relative transition-all duration-500`}>
          {/* Subtle Ashoka Chakra / Geometric Background Watermark */}
          <div className="absolute right-[-40px] top-[-40px] w-80 h-80 rounded-full border-[18px] border-white/5 pointer-events-none flex items-center justify-center">
            <div className="w-60 h-60 rounded-full border-[10px] border-white/5"></div>
          </div>

          <div className="relative z-10 space-y-3.5">
            {/* Top Bar: Ministry Stamp + Scheme Badge + Counter */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2">
                <div className="p-1 bg-white rounded-xs shadow-2xs">
                  <NationalEmblem size={24} color="#002b49" showSlogan={false} />
                </div>
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-amber-200 font-serif">
                    {language === 'en' ? 'GOVERNMENT OF INDIA FLAGSHIP SCHEME' : 'भारत सरकार की प्रमुख राष्ट्रीय योजना'}
                  </div>
                  <div className="text-[11px] font-semibold text-white/90">
                    {language === 'en' ? currentScheme.ministry : currentScheme.ministryHi}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className={`px-2.5 py-0.5 rounded-xs text-[10px] font-extrabold uppercase tracking-wide border ${themeStyle.badgeBg}`}>
                  {currentScheme.badge}
                </span>

                <div className="flex items-center gap-1 bg-black/30 backdrop-blur-xs px-2 py-0.5 rounded-xs text-[11px] font-mono text-slate-200 border border-white/10">
                  <span>{currentIndex + 1}</span>
                  <span className="opacity-60">/</span>
                  <span>{totalSlides}</span>
                </div>
              </div>
            </div>

            {/* Scheme Headline & Slogan */}
            <div className="space-y-1.5 max-w-4xl">
              <h3 className="text-xl sm:text-2xl font-black text-white tracking-tight leading-snug">
                {language === 'en' ? currentScheme.name : currentScheme.nameHi}
              </h3>
              
              <div className="flex items-center gap-2">
                <span className="text-xs sm:text-sm font-bold text-amber-300 italic">
                  &ldquo;{language === 'en' ? currentScheme.slogan : currentScheme.sloganHi}&rdquo;
                </span>
              </div>

              <p className="text-xs sm:text-sm text-slate-100/90 leading-relaxed max-w-3xl line-clamp-2">
                {language === 'en' ? currentScheme.description : currentScheme.descriptionHi}
              </p>
            </div>

            {/* Key Metrics Strip & CTA Buttons */}
            <div className="pt-2 flex flex-wrap items-center justify-between gap-4 border-t border-white/15">
              {/* Impact Metric Chips */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="bg-black/30 backdrop-blur-xs border border-white/15 px-3 py-1.5 rounded-xs">
                  <div className="text-base sm:text-lg font-black font-mono text-amber-300">
                    {currentScheme.impactMetric}
                  </div>
                  <div className="text-[10px] text-slate-200">
                    {currentScheme.impactLabel}
                  </div>
                </div>

                <div className="bg-black/30 backdrop-blur-xs border border-white/15 px-3 py-1.5 rounded-xs hidden sm:block">
                  <div className="text-base sm:text-lg font-black font-mono text-emerald-300">
                    {currentScheme.secondaryMetric}
                  </div>
                  <div className="text-[10px] text-slate-200">
                    {currentScheme.secondaryLabel}
                  </div>
                </div>
              </div>

              {/* Call to Action Buttons */}
              <div className="flex items-center gap-2.5">
                <button
                  onClick={() => setSelectedSchemeForModal(currentScheme)}
                  className="px-3.5 py-1.5 bg-white hover:bg-slate-100 text-slate-900 rounded-xs text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all hover:scale-102 cursor-pointer"
                >
                  <Info className="w-3.5 h-3.5 text-[#0b3866]" />
                  <span>{language === 'en' ? 'View Scheme Details' : 'योजना विवरण देखें'}</span>
                </button>

                <a
                  href={currentScheme.portalUrl}
                  target="_blank"
                  rel="noreferrer"
                  className={`px-3.5 py-1.5 rounded-xs text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all hover:scale-102 ${themeStyle.btn}`}
                >
                  <span>{currentScheme.bannerCtaText || (language === 'en' ? 'Official Portal' : 'आधिकारिक पोर्टल')}</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Carousel Bottom Control Strip */}
        <div className="bg-slate-900 text-slate-300 px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs border-t border-slate-800">
          {/* Slide Indicator Dots */}
          <div className="flex items-center gap-1.5">
            {GOV_SCHEMES.map((scheme, idx) => (
              <button
                key={scheme.id}
                onClick={() => setCurrentIndex(idx)}
                className={`transition-all rounded-full cursor-pointer ${
                  idx === currentIndex 
                    ? 'w-7 h-2 bg-[#f37021]' 
                    : 'w-2 h-2 bg-slate-600 hover:bg-slate-400'
                }`}
                title={`Go to slide ${idx + 1}: ${scheme.shortName}`}
                aria-label={`Slide ${idx + 1}`}
              />
            ))}
          </div>

          {/* Quick Scheme Labels */}
          <div className="hidden md:flex items-center gap-3 text-[11px]">
            {GOV_SCHEMES.map((s, idx) => (
              <button
                key={s.id}
                onClick={() => setCurrentIndex(idx)}
                className={`font-semibold transition-colors cursor-pointer ${
                  idx === currentIndex 
                    ? 'text-amber-400 font-bold underline underline-offset-4' 
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {s.shortName}
              </button>
            ))}
          </div>

          {/* Previous / Pause / Next Controls */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={handlePrev}
              className="p-1 rounded-xs bg-slate-800 hover:bg-slate-700 text-white transition-colors cursor-pointer"
              title="Previous Scheme Banner"
              aria-label="Previous"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-1 rounded-xs bg-slate-800 hover:bg-slate-700 text-white transition-colors cursor-pointer"
              title={isPlaying ? 'Pause Auto-Slide' : 'Play Auto-Slide'}
              aria-label={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>

            <button
              onClick={handleNext}
              className="p-1 rounded-xs bg-slate-800 hover:bg-slate-700 text-white transition-colors cursor-pointer"
              title="Next Scheme Banner"
              aria-label="Next"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Scheme Detailed Guidelines Modal */}
      {selectedSchemeForModal && (
        <GovSchemeModal 
          scheme={selectedSchemeForModal} 
          language={language}
          onClose={() => setSelectedSchemeForModal(null)} 
        />
      )}
    </>
  );
};

/**
 * 2. Authentic Government Website Leaderboard Ad Banner
 * Modeled after the official promotional billboards shown on government portals
 * like National Single Window System, PM India, and MyGov.
 */
export const GovSchemeLeaderboardBanner: React.FC<GovSchemeBannersProps> = ({
  language = 'en',
  onSelectScheme
}) => {
  const [activeTabIdx, setActiveTabIdx] = useState(0);
  const [selectedScheme, setSelectedScheme] = useState<GovScheme | null>(null);

  // Focus on top 3 citizen impact schemes
  const featured = [
    GOV_SCHEMES.find(s => s.code === 'PM-KISAN')!,
    GOV_SCHEMES.find(s => s.code === 'SVAMITVA')!,
    GOV_SCHEMES.find(s => s.code === 'PMAY-G')!,
    GOV_SCHEMES.find(s => s.code === 'BHU-AADHAAR')!
  ].filter(Boolean);

  const current = featured[activeTabIdx] || featured[0];
  const theme = getThemeClasses(current.theme);

  return (
    <>
      <div className="bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-emerald-500/10 border border-amber-300/80 rounded-xs p-3 shadow-xs">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          {/* Left: Stamp & Govt Label */}
          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="p-1.5 bg-white border border-amber-300 rounded-xs shadow-2xs flex-shrink-0">
              <NationalEmblem size={28} color="#002642" showSlogan={false} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-black uppercase tracking-wider bg-[#f37021] text-white px-1.5 py-0.2 rounded-xs">
                  {language === 'en' ? 'GOVERNMENT CAMPAIGN' : 'राष्ट्रीय अभियान'}
                </span>
                <span className="text-[10px] text-slate-500 font-bold">
                  {language === 'en' ? 'Ministry of Rural Development & Agriculture' : 'ग्रामीण विकास एवं कृषि मंत्रालय'}
                </span>
              </div>
              <div className="text-xs font-extrabold text-[#002642] mt-0.5">
                {language === 'en' ? current.name : current.nameHi}
              </div>
              <div className="text-[11px] text-[#f37021] font-semibold italic">
                &ldquo;{language === 'en' ? current.slogan : current.sloganHi}&rdquo;
              </div>
            </div>
          </div>

          {/* Center: Scheme switcher pills */}
          <div className="flex items-center gap-1.5 flex-wrap justify-center">
            {featured.map((scheme, idx) => (
              <button
                key={scheme.id}
                onClick={() => setActiveTabIdx(idx)}
                className={`px-2.5 py-1 text-[11px] font-bold rounded-xs transition-all cursor-pointer ${
                  activeTabIdx === idx
                    ? 'bg-[#002642] text-white shadow-xs'
                    : 'bg-white text-slate-700 hover:bg-amber-100 border border-slate-200'
                }`}
              >
                {scheme.shortName}
              </button>
            ))}
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-2 flex-shrink-0 w-full md:w-auto justify-end">
            <button
              onClick={() => setSelectedScheme(current)}
              className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 text-xs font-bold rounded-xs transition-colors cursor-pointer"
            >
              {language === 'en' ? 'Know Details' : 'विस्तार'}
            </button>
            <a
              href={current.portalUrl}
              target="_blank"
              rel="noreferrer"
              className={`px-3 py-1.5 text-xs font-bold rounded-xs shadow-xs transition-colors flex items-center gap-1.5 ${theme.btn}`}
            >
              <span>{current.bannerCtaText || (language === 'en' ? 'Apply / Verify' : 'आवेदन / सत्यापन')}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </div>

      {selectedScheme && (
        <GovSchemeModal
          scheme={selectedScheme}
          language={language}
          onClose={() => setSelectedScheme(null)}
        />
      )}
    </>
  );
};

/**
 * 3. Authentic Government Sidebar Ad Banners (Square / Skyscraper style)
 * Displayed in side panels or widget columns, featuring real scheme announcements.
 */
export const GovSchemeSidebarAd: React.FC<{
  schemeCode: 'PM-KISAN' | 'SVAMITVA' | 'PMAY-G' | 'JAL-JEEVAN' | 'BHU-AADHAAR';
  language?: 'en' | 'hi';
}> = ({ schemeCode, language = 'en' }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const scheme = GOV_SCHEMES.find(s => s.code === schemeCode) || GOV_SCHEMES[0];
  const theme = getThemeClasses(scheme.theme);

  return (
    <>
      <div className={`swaas-card overflow-hidden border-2 border-slate-200 transition-all hover:shadow-md ${theme.borderAccent}`}>
        {/* Tricolour Accent */}
        <div className="h-1 w-full flex">
          <div className="w-1/3 bg-[#FF9933]"></div>
          <div className="w-1/3 bg-[#FFFFFF]"></div>
          <div className="w-1/3 bg-[#138808]"></div>
        </div>

        {/* Ad Header */}
        <div className={`${theme.bg} text-white p-3 space-y-1 relative`}>
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-black uppercase tracking-wider bg-white/20 backdrop-blur-2xs px-1.5 py-0.2 rounded-xs border border-white/20">
              {scheme.badge}
            </span>
            <span className="text-[10px] text-amber-200 font-serif font-bold">Govt. of India</span>
          </div>

          <h4 className="font-extrabold text-sm text-white leading-tight">
            {scheme.shortName}
          </h4>
          <p className="text-[10px] text-amber-200 font-semibold italic">
            &ldquo;{language === 'en' ? scheme.slogan : scheme.sloganHi}&rdquo;
          </p>
        </div>

        {/* Ad Body */}
        <div className="p-3 bg-white space-y-2.5 text-xs">
          <div className="p-2 bg-slate-50 border border-slate-200 rounded-xs">
            <div className="text-base font-black font-mono text-[#002642]">
              {scheme.impactMetric}
            </div>
            <div className="text-[10px] text-slate-500 font-medium">
              {scheme.impactLabel}
            </div>
          </div>

          <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed">
            {language === 'en' ? scheme.description : scheme.descriptionHi}
          </p>

          <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
            <button
              onClick={() => setModalOpen(true)}
              className="text-[#0b3866] hover:text-[#f37021] font-bold text-[11px] flex items-center gap-1 cursor-pointer"
            >
              <span>{language === 'en' ? 'Guidelines' : 'दिशानिर्देश'}</span>
              <Info className="w-3 h-3" />
            </button>

            <a
              href={scheme.portalUrl}
              target="_blank"
              rel="noreferrer"
              className={`px-2.5 py-1 text-[11px] font-bold rounded-xs shadow-2xs flex items-center gap-1 ${theme.btn}`}
            >
              <span>{scheme.bannerCtaText || (language === 'en' ? 'Portal ↗' : 'पोर्टल ↗')}</span>
            </a>
          </div>
        </div>
      </div>

      {modalOpen && (
        <GovSchemeModal
          scheme={scheme}
          language={language}
          onClose={() => setModalOpen(null as any)}
        />
      )}
    </>
  );
};

/**
 * 4. Multi-Banner Promotional Ad Grid (Authentic Govt Advertisement Cards)
 * Displays promotional ad cards for major schemes with badges, slogans, and stats
 */
export const GovSchemeAdGrid: React.FC<GovSchemeBannersProps> = ({ 
  language = 'en',
  filterCategory = 'ALL'
}) => {
  const [selectedScheme, setSelectedScheme] = useState<GovScheme | null>(null);
  const [activeCategory, setActiveCategory] = useState<SchemeCategory>(filterCategory);

  const filteredSchemes = activeCategory === 'ALL'
    ? GOV_SCHEMES
    : GOV_SCHEMES.filter(s => s.category === activeCategory);

  return (
    <>
      <div className="space-y-4">
        {/* Section Header */}
        <div className="flex flex-wrap justify-between items-center border-b border-slate-200 pb-2 gap-2">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-xs bg-[#f37021] text-white">
              <Landmark className="w-3.5 h-3.5" />
            </span>
            <div>
              <h3 className="font-extrabold text-xs text-[#002642] uppercase tracking-wide">
                {language === 'en' 
                  ? 'NATIONAL SCHEMES & CITIZEN INITIATIVES' 
                  : 'प्रमुख राष्ट्रीय योजनाएं एवं जन-कल्याणकारी अभियान'}
              </h3>
              <p className="text-[10px] text-slate-500">
                {language === 'en' ? 'Government of India • Central Flagship Programmes' : 'भारत सरकार • केंद्रीय प्रमुख योजनाएं'}
              </p>
            </div>
          </div>

          {/* Category Filter Pills */}
          <div className="flex items-center gap-1 flex-wrap text-[11px]">
            <button
              onClick={() => setActiveCategory('ALL')}
              className={`px-2 py-0.5 rounded-xs font-semibold cursor-pointer ${
                activeCategory === 'ALL' 
                  ? 'bg-[#002642] text-white' 
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {language === 'en' ? 'All (8)' : 'सभी (८)'}
            </button>
            <button
              onClick={() => setActiveCategory('LAND_REVENUE')}
              className={`px-2 py-0.5 rounded-xs font-semibold cursor-pointer ${
                activeCategory === 'LAND_REVENUE' 
                  ? 'bg-[#002642] text-white' 
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {language === 'en' ? 'Land & Revenue' : 'भू-राजस्व'}
            </button>
            <button
              onClick={() => setActiveCategory('AGRICULTURE_DBT')}
              className={`px-2 py-0.5 rounded-xs font-semibold cursor-pointer ${
                activeCategory === 'AGRICULTURE_DBT' 
                  ? 'bg-[#002642] text-white' 
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {language === 'en' ? 'Agriculture DBT' : 'कृषि डीबीटी'}
            </button>
            <button
              onClick={() => setActiveCategory('HOUSING_WATER')}
              className={`px-2 py-0.5 rounded-xs font-semibold cursor-pointer ${
                activeCategory === 'HOUSING_WATER' 
                  ? 'bg-[#002642] text-white' 
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {language === 'en' ? 'Housing & Water' : 'आवास व जल'}
            </button>
            <button
              onClick={() => setActiveCategory('INFRASTRUCTURE')}
              className={`px-2 py-0.5 rounded-xs font-semibold cursor-pointer ${
                activeCategory === 'INFRASTRUCTURE' 
                  ? 'bg-[#002642] text-white' 
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {language === 'en' ? 'Infrastructure' : 'अवसंरचना'}
            </button>
          </div>
        </div>

        {/* Multi-Column Ad Banner Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {filteredSchemes.map((scheme) => {
            const theme = getThemeClasses(scheme.theme);

            return (
              <div
                key={scheme.id}
                className={`swaas-card p-4 flex flex-col justify-between space-y-3 transition-all hover:shadow-md hover:-translate-y-0.5 border-t-4 ${theme.borderAccent}`}
              >
                <div className="space-y-2">
                  {/* Top Badge & Ministry */}
                  <div className="flex items-center justify-between gap-1">
                    <span className={`px-2 py-0.5 rounded-xs text-[9px] font-black uppercase tracking-wider border ${theme.cardBg} ${theme.highlightText}`}>
                      {scheme.shortName}
                    </span>
                    <span className="text-[10px] text-slate-400 font-bold">Govt. Scheme</span>
                  </div>

                  {/* Scheme Title */}
                  <h4 className="font-bold text-xs text-[#002642] leading-tight line-clamp-2">
                    {language === 'en' ? scheme.name : scheme.nameHi}
                  </h4>

                  {/* Slogan */}
                  <p className={`text-[11px] font-semibold italic ${theme.highlightText}`}>
                    &ldquo;{language === 'en' ? scheme.slogan : scheme.sloganHi}&rdquo;
                  </p>

                  {/* Metric Box */}
                  <div className="p-2 bg-slate-50 rounded-xs border border-slate-200/80">
                    <div className="text-sm font-black font-mono text-[#002642]">
                      {scheme.impactMetric}
                    </div>
                    <div className="text-[10px] text-slate-500 leading-tight">
                      {scheme.impactLabel}
                    </div>
                  </div>
                </div>

                {/* Card Action Links */}
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs font-bold">
                  <button
                    onClick={() => setSelectedScheme(scheme)}
                    className="text-[#0b3866] hover:text-[#f37021] flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <span>{language === 'en' ? 'Guidelines' : 'विवरण'}</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>

                  <a
                    href={scheme.portalUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-slate-600 hover:text-slate-900 flex items-center gap-1 text-[11px] bg-slate-100 hover:bg-slate-200 px-2 py-0.5 rounded-xs"
                    title={`Open ${scheme.portalName}`}
                  >
                    <span>{scheme.portalName}</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Modal View */}
      {selectedScheme && (
        <GovSchemeModal
          scheme={selectedScheme}
          language={language}
          onClose={() => setSelectedScheme(null)}
        />
      )}
    </>
  );
};

/**
 * 5. Government Scheme Details Dialog / Modal
 * Displays full official details, statutory benefits, eligibility, and helpline
 */
interface GovSchemeModalProps {
  scheme: GovScheme;
  language?: 'en' | 'hi';
  onClose: () => void;
}

export const GovSchemeModal: React.FC<GovSchemeModalProps> = ({ 
  scheme, 
  language = 'en', 
  onClose 
}) => {
  return (
    <div className="fixed inset-0 z-[9999] bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in" role="dialog">
      <div className="bg-white rounded-xs max-w-2xl w-full border border-slate-300 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header with Tricolour Top Accent */}
        <div className="h-1.5 w-full flex">
          <div className="w-1/3 bg-[#FF9933]"></div>
          <div className="w-1/3 bg-[#FFFFFF]"></div>
          <div className="w-1/3 bg-[#138808]"></div>
        </div>

        <div className="bg-[#002642] text-white p-4 sm:p-5 flex justify-between items-start gap-4">
          <div className="flex items-start gap-3">
            <div className="p-1.5 bg-white rounded-xs flex-shrink-0 mt-0.5">
              <NationalEmblem size={28} color="#002b49" showSlogan={false} />
            </div>
            <div>
              <span className="px-2 py-0.5 rounded-xs text-[9px] font-black uppercase tracking-wider bg-amber-400 text-slate-950 font-mono">
                {scheme.badge}
              </span>
              <h3 className="font-extrabold text-base sm:text-lg text-white mt-1 leading-snug">
                {language === 'en' ? scheme.name : scheme.nameHi}
              </h3>
              <p className="text-[11px] text-slate-300 mt-0.5">
                {language === 'en' ? scheme.ministry : scheme.ministryHi}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-xs text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            aria-label="Close Modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs leading-relaxed text-slate-800">
          {/* Official Slogan Banner */}
          <div className="p-3 bg-amber-50 border-l-4 border-[#f37021] text-[#7c2d12] rounded-xs font-semibold italic text-xs">
            &ldquo;{language === 'en' ? scheme.slogan : scheme.sloganHi}&rdquo;
          </div>

          {/* Scheme Overview */}
          <div className="space-y-1">
            <h4 className="font-bold text-xs text-[#002642] uppercase tracking-wide flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-[#0b3866]" />
              <span>{language === 'en' ? 'Scheme Overview & Objective' : 'योजना का परिचय एवं उद्देश्य'}</span>
            </h4>
            <p className="text-slate-700 leading-relaxed">
              {language === 'en' ? scheme.description : scheme.descriptionHi}
            </p>
          </div>

          {/* Key Impact Stats */}
          <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xs">
            <div>
              <div className="text-[10px] text-slate-500 uppercase font-semibold">Primary Milestone:</div>
              <div className="text-lg font-black font-mono text-[#002642]">{scheme.impactMetric}</div>
              <div className="text-[11px] text-slate-600">{scheme.impactLabel}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase font-semibold">National Reach:</div>
              <div className="text-lg font-black font-mono text-[#138808]">{scheme.secondaryMetric}</div>
              <div className="text-[11px] text-slate-600">{scheme.secondaryLabel}</div>
            </div>
          </div>

          {/* Key Citizen & Landowner Benefits */}
          <div className="space-y-2">
            <h4 className="font-bold text-xs text-[#002642] uppercase tracking-wide flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-[#138808]" />
              <span>{language === 'en' ? 'Key Statutory & Citizen Benefits' : 'प्रमुख वैधानिक एवं नागरिक लाभ'}</span>
            </h4>
            <ul className="space-y-1.5 text-[11px] text-slate-700">
              {(language === 'en' ? scheme.keyBenefits : scheme.keyBenefitsHi).map((benefit, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#138808] flex-shrink-0 mt-1.5"></span>
                  <span>{benefit}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Eligibility & Integration Note */}
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-xs space-y-1 text-[11px]">
            <span className="font-bold text-[#0b3866] block">
              {language === 'en' ? 'Target Beneficiaries & Eligibility:' : 'पात्रता एवं लक्षित हितग्राही:'}
            </span>
            <p className="text-slate-700">
              {language === 'en' ? scheme.eligibility : scheme.eligibilityHi}
            </p>
          </div>

          {/* Helpline and Portal Info */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-200 text-xs">
            <div className="flex items-center gap-2 text-slate-600">
              <Phone className="w-4 h-4 text-[#f37021]" />
              <span>
                <strong>{language === 'en' ? 'Toll-Free Helpline:' : 'हेल्पलाइन नंबर:'}</strong> {scheme.helpline}
              </span>
            </div>
            <div className="text-slate-500 font-mono text-[11px]">
              Portal: {scheme.portalName}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-3.5 bg-slate-100 border-t border-slate-200 flex justify-between items-center">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-xs text-xs font-bold transition-colors cursor-pointer"
          >
            {language === 'en' ? 'Close Window' : 'बंद करें'}
          </button>

          <a
            href={scheme.portalUrl}
            target="_blank"
            rel="noreferrer"
            className="px-4 py-1.5 bg-[#0b3866] hover:bg-[#002642] text-white rounded-xs text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <span>{language === 'en' ? 'Open Official Portal' : 'आधिकारिक पोर्टल खोलें'}</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
};
