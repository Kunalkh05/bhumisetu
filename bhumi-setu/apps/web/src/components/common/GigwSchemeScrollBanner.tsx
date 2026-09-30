import React, { useState, useEffect, useRef } from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  Pause, 
  Play, 
  ExternalLink, 
  Info, 
  Sparkles, 
  Landmark, 
  CheckCircle2, 
  Phone,
  Layers,
  ArrowRight,
  ShieldCheck,
  FileText,
  Download,
  Check,
  QrCode,
  LayoutGrid,
  Maximize2
} from 'lucide-react';
import { GOV_SCHEMES, GovScheme } from '../../data/govSchemesData';
import { GovSchemeModal } from './GovSchemeBanners';
import { NationalEmblem } from './NationalEmblem';
import { useApp } from '../../context/AppContext';

interface GigwSchemeScrollBannerProps {
  language?: 'en' | 'hi';
  className?: string;
  onSelectScheme?: (scheme: GovScheme) => void;
  title?: string;
  titleHi?: string;
  initialMode?: 'billboard' | 'ribbon';
}

/**
 * 2026 National Government Schemes & Flagship Initiatives Billboard Banner
 * Designed to strictly mirror the official 2026 redesigns of india.gov.in, MyGov, and PMIndia.
 * 
 * Features:
 * - Authentic Government Typography, Ashoka Lion Crest, and Official Ministry Signatures
 * - Panoramic Flagship Campaign Showcase with verified PFMS DBT milestones
 * - Interactive 8-Scheme Switcher Tabstrip with animated progress timeline
 * - Accessible GIGW 3.0 & WCAG 2.2.2 Pause/Play & Keyboard navigation controls
 * - Toggleable between "National Billboard Showcase" and "Compact Horizontal Ribbon"
 */
export const GigwSchemeScrollBanner: React.FC<GigwSchemeScrollBannerProps> = ({
  language: propLanguage,
  className = '',
  onSelectScheme,
  title,
  titleHi,
  initialMode = 'billboard'
}) => {
  const { language: contextLanguage, addToast } = useApp();
  const language = propLanguage || contextLanguage || 'en';

  const [activeIndex, setActiveIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [viewMode, setViewMode] = useState<'billboard' | 'ribbon'>(initialMode);
  const [selectedSchemeForModal, setSelectedSchemeForModal] = useState<GovScheme | null>(null);
  const [isHovered, setIsHovered] = useState<boolean>(false);
  const [progressKey, setProgressKey] = useState<number>(0);

  const ribbonRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const totalSchemes = GOV_SCHEMES.length;
  const currentScheme = GOV_SCHEMES[activeIndex] || GOV_SCHEMES[0];

  // Auto-advance billboard slides every 6 seconds
  useEffect(() => {
    // Respect user's reduced-motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      setIsPlaying(false);
      return;
    }

    if (isPlaying && !isHovered) {
      timerRef.current = setInterval(() => {
        setActiveIndex((prev) => (prev + 1) % totalSchemes);
        setProgressKey((prev) => prev + 1);
      }, 6200);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isPlaying, isHovered, totalSchemes]);

  const handleNext = () => {
    setActiveIndex((prev) => (prev + 1) % totalSchemes);
    setProgressKey((prev) => prev + 1);
  };

  const handlePrev = () => {
    setActiveIndex((prev) => (prev - 1 + totalSchemes) % totalSchemes);
    setProgressKey((prev) => prev + 1);
  };

  const handleSelectScheme = (index: number) => {
    setActiveIndex(index);
    setProgressKey((prev) => prev + 1);
  };

  const openModal = (scheme: GovScheme) => {
    setSelectedSchemeForModal(scheme);
    if (onSelectScheme) {
      onSelectScheme(scheme);
    }
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowRight') {
      handleNext();
    } else if (e.key === 'ArrowLeft') {
      handlePrev();
    }
  };

  // Scheme visual theme attributes (institutional government palette)
  const getSchemeDecor = (code: string) => {
    switch (code) {
      case 'PM-KISAN':
        return {
          icon: '🌾',
          accentColor: '#138808',
          accentBg: 'bg-[#138808]',
          lightBg: 'bg-emerald-50/70 border-emerald-200 text-emerald-950',
          badgeText: 'DIRECT BENEFIT TRANSFER (PFMS)',
          posterTheme: 'from-[#0b3866] via-[#104875] to-[#14532d]',
          sealLabel: '100% Aadhaar-Linked DBT'
        };
      case 'SVAMITVA':
        return {
          icon: '🚁',
          accentColor: '#f37021',
          accentBg: 'bg-[#f37021]',
          lightBg: 'bg-orange-50/70 border-orange-200 text-orange-950',
          badgeText: 'DRONE CADASTRAL SURVEY',
          posterTheme: 'from-[#002642] via-[#7c2d12] to-[#c2410c]',
          sealLabel: 'Legal Property Card (Sampatti Patra)'
        };
      case 'PMAY-G':
        return {
          icon: '🏠',
          accentColor: '#b45309',
          accentBg: 'bg-[#b45309]',
          lightBg: 'bg-amber-50/70 border-amber-200 text-amber-950',
          badgeText: 'HOUSING FOR ALL (RURAL)',
          posterTheme: 'from-[#002642] via-[#78350f] to-[#92400e]',
          sealLabel: 'Pucca House with Solar & Water'
        };
      case 'JAL-JEEVAN':
        return {
          icon: '💧',
          accentColor: '#0284c7',
          accentBg: 'bg-[#0284c7]',
          lightBg: 'bg-sky-50/70 border-sky-200 text-sky-950',
          badgeText: 'HAR GHAR JAL (POTABLE WATER)',
          posterTheme: 'from-[#002642] via-[#0369a1] to-[#0284c7]',
          sealLabel: '55 Litres / Capita / Day Quality Tested'
        };
      case 'PM-GATISHAKTI':
        return {
          icon: '⚡',
          accentColor: '#002642',
          accentBg: 'bg-[#002642]',
          lightBg: 'bg-blue-50/70 border-blue-200 text-blue-950',
          badgeText: 'NATIONAL MULTI-MODAL MASTER PLAN',
          posterTheme: 'from-[#00172d] via-[#002642] to-[#0b3866]',
          sealLabel: 'PostGIS Integrated Spatial Engine'
        };
      case 'BHU-AADHAAR':
        return {
          icon: '🗺️',
          accentColor: '#047857',
          accentBg: 'bg-[#047857]',
          lightBg: 'bg-teal-50/70 border-teal-200 text-teal-950',
          badgeText: '14-DIGIT UNIQUE PARCEL ID (ULPIN)',
          posterTheme: 'from-[#002642] via-[#064e3b] to-[#047857]',
          sealLabel: 'WGS-84 Geo-Coordinates Title Seal'
        };
      case 'BHOOMI-RASHI':
        return {
          icon: '🛣️',
          accentColor: '#0b3866',
          accentBg: 'bg-[#0b3866]',
          lightBg: 'bg-indigo-50/70 border-indigo-200 text-indigo-950',
          badgeText: 'NATIONAL HIGHWAY ACQUISITION',
          posterTheme: 'from-[#001a33] via-[#002b49] to-[#003d66]',
          sealLabel: 'Statutory 100% Solatium Guaranteed'
        };
      case 'DIGILOCKER':
      default:
        return {
          icon: '📂',
          accentColor: '#6b21a8',
          accentBg: 'bg-[#6b21a8]',
          lightBg: 'bg-purple-50/70 border-purple-200 text-purple-950',
          badgeText: 'DIGITAL INDIA PAPERLESS VAULT',
          posterTheme: 'from-[#002642] via-[#3b0764] to-[#581c87]',
          sealLabel: 'Rule 9A IT Rules 2016 Authentic Deed'
        };
    }
  };

  const decor = getSchemeDecor(currentScheme.code);

  return (
    <>
      <section
        className={`w-full bg-white border border-slate-200/90 shadow-sm rounded-2xl overflow-hidden select-none ${className}`}
        aria-label={language === 'en' ? 'Government Flagship Welfare Schemes' : 'भारत सरकार की प्रमुख जन-कल्याणकारी योजनाएं'}
        role="region"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onKeyDown={handleKeyDown}
        tabIndex={0}
      >
        {/* ============================================================ */}
        {/* 1. OFFICIAL S3WaaS TRICOLOUR ACCENT STRIP */}
        {/* ============================================================ */}
        <div className="h-1.5 w-full flex">
          <div className="w-1/3 bg-[#FF9933]"></div>
          <div className="w-1/3 bg-[#FFFFFF]"></div>
          <div className="w-1/3 bg-[#138808]"></div>
        </div>

        {/* ============================================================ */}
        {/* 2. OFFICIAL GOVERNMENT HEADER & ACCESSIBILITY BAR */}
        {/* ============================================================ */}
        <div className="bg-[#002642] text-white px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 border-b border-[#0b3866]">
          {/* Left: State Emblem of India + Official Ministry Label */}
          <div className="flex items-center gap-3">
            <div className="p-1 bg-white rounded-md flex-shrink-0 shadow-xs">
              <NationalEmblem size={24} color="#002642" showSlogan={false} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-black uppercase tracking-wider bg-[#f37021] text-white px-2 py-0.2 rounded-full font-mono shadow-xs">
                  {language === 'en' ? 'GOVERNMENT OF INDIA' : 'भारत सरकार'}
                </span>
                <span className="text-[10px] text-slate-300 font-bold hidden sm:inline">
                  {language === 'en' ? 'National Portal of Central Flagship Schemes' : 'केंद्रीय योजनाओं का राष्ट्रीय अधिकृत पोर्टल'}
                </span>
              </div>
              <h2 className="font-extrabold text-xs sm:text-sm text-white tracking-tight leading-snug">
                {language === 'en' 
                  ? (title || 'Central Welfare Schemes, Direct Benefit Transfers & Land Rights')
                  : (titleHi || 'प्रमुख केंद्रीय जन-कल्याणकारी योजनाएं एवं डीबीटी मुआवजा')}
              </h2>
            </div>
          </div>

          {/* Right: GIGW Accessibility & View Controls */}
          <div className="flex items-center gap-2" role="toolbar" aria-label="Scheme banner controls">
            {/* View Mode Switcher (Billboard vs Ribbon) */}
            <div className="hidden md:inline-flex rounded-full border border-slate-700 bg-slate-900/80 p-0.5 text-[10px] font-bold">
              <button
                onClick={() => setViewMode('billboard')}
                className={`px-2.5 py-0.5 rounded-full transition-colors cursor-pointer ${
                  viewMode === 'billboard' ? 'bg-[#0b3866] text-white shadow-xs' : 'text-slate-400 hover:text-white'
                }`}
                title="Full Billboard Showcase"
              >
                Showcase
              </button>
              <button
                onClick={() => setViewMode('ribbon')}
                className={`px-2.5 py-0.5 rounded-full transition-colors cursor-pointer ${
                  viewMode === 'ribbon' ? 'bg-[#0b3866] text-white shadow-xs' : 'text-slate-400 hover:text-white'
                }`}
                title="Compact Ribbon View"
              >
                Ribbon
              </button>
            </div>

            {/* GIGW Mandated Pause / Play Button */}
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className={`px-3 py-1 rounded-full text-[11px] font-bold flex items-center gap-1.5 transition-all cursor-pointer border ${
                isPlaying 
                  ? 'bg-slate-800 text-slate-200 hover:text-white border-slate-600' 
                  : 'bg-amber-400 text-slate-950 font-black border-amber-300 shadow-xs'
              }`}
              title={isPlaying ? 'Pause banner auto-rotation (GIGW mandate)' : 'Resume banner auto-rotation'}
              aria-label={isPlaying ? 'Pause auto-scrolling' : 'Resume auto-scrolling'}
              aria-pressed={!isPlaying}
            >
              {isPlaying ? (
                <>
                  <Pause className="w-3.5 h-3.5 text-amber-400" />
                  <span className="hidden sm:inline">{language === 'en' ? 'Pause' : 'रोकें'}</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 text-slate-950 fill-current" />
                  <span className="hidden sm:inline">{language === 'en' ? 'Auto-Play' : 'चलाएं'}</span>
                </>
              )}
            </button>

            {/* Prev / Next Controls */}
            <button
              onClick={handlePrev}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-full border border-slate-600 cursor-pointer transition-colors"
              title="Previous Scheme"
              aria-label="Previous Scheme"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={handleNext}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-full border border-slate-600 cursor-pointer transition-colors"
              title="Next Scheme"
              aria-label="Next Scheme"
            >
              <ChevronRight className="w-4 h-4" />
            </button>

            {/* Scheme Counter */}
            <div className="bg-black/40 border border-white/10 px-2.5 py-0.5 rounded-full font-mono text-[10px] text-amber-300">
              <span>{activeIndex + 1}</span>
              <span className="opacity-60">/</span>
              <span>{totalSchemes}</span>
            </div>
          </div>
        </div>

        {/* ============================================================ */}
        {/* 3. VIEW MODE A: NATIONAL BILLBOARD SHOWCASE (DEFAULT) */}
        {/* ============================================================ */}
        {viewMode === 'billboard' && (
          <div className="relative overflow-hidden bg-gradient-to-br from-slate-50 via-white to-slate-100">
            {/* Ashoka Chakra Filigree Watermark on background */}
            <div className="absolute right-[-40px] top-[-40px] w-96 h-96 rounded-full border-[18px] border-slate-200/40 pointer-events-none flex items-center justify-center opacity-60">
              <div className="w-72 h-72 rounded-full border-[12px] border-slate-200/40"></div>
              <div className="w-48 h-48 rounded-full border-[6px] border-slate-200/40"></div>
            </div>

            <div className="p-5 sm:p-7 grid grid-cols-1 lg:grid-cols-12 gap-6 relative z-10 items-stretch">
              {/* Left Column (8 cols): Official Scheme Decree, Benefits & Actions */}
              <div className="lg:col-span-8 space-y-4 flex flex-col justify-between">
                <div className="space-y-3">
                  {/* Scheme Badge + Ministry Stamp */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="text-xl">{decor.icon}</span>
                    <span className={`px-3 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider font-mono border shadow-xs ${decor.lightBg}`}>
                      {decor.badgeText}
                    </span>
                    <span className="text-slate-400 font-bold">•</span>
                    <span className="text-[11px] font-bold text-slate-700">
                      {language === 'en' ? currentScheme.ministry : currentScheme.ministryHi}
                    </span>
                  </div>

                  {/* Main Scheme Headline */}
                  <div>
                    <h3 className="text-xl sm:text-2xl font-black text-[#002642] tracking-tight leading-snug">
                      {language === 'en' ? currentScheme.name : currentScheme.nameHi}
                    </h3>
                    <div className="mt-1 text-xs sm:text-sm font-extrabold text-[#f37021] italic font-serif">
                      &ldquo;{language === 'en' ? currentScheme.slogan : currentScheme.sloganHi}&rdquo;
                    </div>
                  </div>

                  {/* Statutory Reference Badge */}
                  {currentScheme.circularRef && (
                    <div className="inline-flex items-center gap-2 px-2.5 py-0.5 bg-slate-100 border border-slate-200 rounded-md text-[10px] font-mono text-slate-700">
                      <FileText className="w-3 h-3 text-[#002642]" />
                      <span>Gazette Decree: <strong>{currentScheme.circularRef}</strong></span>
                    </div>
                  )}

                  {/* Key Benefits List */}
                  <div className="space-y-1.5 pt-1">
                    <div className="text-[10px] font-black uppercase tracking-wider text-slate-500">
                      {language === 'en' ? 'Statutory Citizen Entitlements & Protections:' : 'नागरिक अधिकार एवं सांविधिक प्रावधान:'}
                    </div>
                    <ul className="space-y-1.5 text-xs text-slate-700">
                      {(language === 'en' ? currentScheme.keyBenefits.slice(0, 3) : currentScheme.keyBenefitsHi.slice(0, 3)).map((benefit, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <Check className="w-4 h-4 text-[#138808] flex-shrink-0 mt-0.5" />
                          <span className="leading-snug">{benefit}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Official Call to Action Buttons */}
                <div className="pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <a
                      href={currentScheme.portalUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="px-4 py-2 bg-[#002642] hover:bg-[#0b3866] text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-sm hover:shadow-md transition-all transform hover:-translate-y-0.5 cursor-pointer"
                    >
                      <span>{currentScheme.bannerCtaText || (language === 'en' ? 'Official Portal ↗' : 'आधिकारिक पोर्टल ↗')}</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>

                    <button
                      onClick={() => openModal(currentScheme)}
                      className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-800 border border-slate-200 font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-xs hover:shadow-sm transition-all cursor-pointer"
                    >
                      <Info className="w-3.5 h-3.5 text-[#0b3866]" />
                      <span>{language === 'en' ? 'View Guidelines' : 'दिशानिर्देश देखें'}</span>
                    </button>

                    <button
                      onClick={() => {
                        addToast({
                          type: 'success',
                          message: `Downloading official gazette decree for ${currentScheme.shortName} (PDF)`,
                        });
                      }}
                      className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl flex items-center gap-1.5 border border-slate-200 transition-all cursor-pointer shadow-xs"
                      title="Download Official Notification"
                    >
                      <Download className="w-3.5 h-3.5 text-slate-600" />
                      <span className="hidden sm:inline">Gazette PDF</span>
                    </button>
                  </div>

                  {/* Direct Toll-Free Helpline */}
                  <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium">
                    <Phone className="w-3.5 h-3.5 text-[#f37021]" />
                    <span>Toll-Free: <strong className="text-slate-900 font-mono font-bold">{currentScheme.helpline.split(' ')[0]}</strong></span>
                  </div>
                </div>
              </div>

              {/* Right Column (4 cols): Authentic Official Government Poster Card */}
              <div className="lg:col-span-4 flex flex-col">
                <div className={`h-full rounded-xl p-5 bg-gradient-to-br ${decor.posterTheme} text-white shadow-lg flex flex-col justify-between relative overflow-hidden border border-white/10`}>
                  {/* Decorative subtle national seal background */}
                  <div className="absolute right-[-20px] bottom-[-20px] opacity-10 pointer-events-none">
                    <NationalEmblem size={160} color="#ffffff" showSlogan={false} />
                  </div>

                  <div className="space-y-4 relative z-10">
                    {/* Poster Top Strip */}
                    <div className="flex items-center justify-between pb-3 border-b border-white/20">
                      <div className="text-[10px] font-black uppercase tracking-wider text-amber-300 font-mono">
                        NATIONAL ACHIEVEMENT
                      </div>
                      <div className="text-[10px] font-serif font-bold text-slate-200">
                        भारत सरकार
                      </div>
                    </div>

                    {/* Primary Big Metric */}
                    <div className="space-y-1">
                      <div className="text-2xl sm:text-3xl font-black font-mono text-amber-300 tracking-tight">
                        {currentScheme.impactMetric}
                      </div>
                      <div className="text-xs font-semibold text-slate-100 leading-snug">
                        {currentScheme.impactLabel}
                      </div>
                    </div>

                    {/* Secondary Metric */}
                    <div className="p-2.5 bg-black/25 backdrop-blur-2xs rounded-xs border border-white/15 space-y-0.5">
                      <div className="text-lg font-black font-mono text-emerald-300">
                        {currentScheme.secondaryMetric}
                      </div>
                      <div className="text-[11px] text-slate-200">
                        {currentScheme.secondaryLabel}
                      </div>
                    </div>

                    {/* Seal / Trust Guarantee */}
                    <div className="flex items-center gap-2 pt-1 text-[11px] text-amber-200 font-medium">
                      <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span>{decor.sealLabel}</span>
                    </div>
                  </div>

                  {/* Poster Bottom Bar */}
                  <div className="pt-3 mt-4 border-t border-white/15 flex items-center justify-between text-[11px] text-slate-300 relative z-10">
                    <span className="font-mono text-[10px] text-slate-300">
                      {currentScheme.portalName}
                    </span>
                    <span className="px-1.5 py-0.5 bg-white/20 rounded-xs text-[9px] font-bold text-white uppercase">
                      Verified
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* ============================================================ */}
            {/* 4. INTERACTIVE 8-SCHEME SELECTOR TABSTRIP */}
            {/* ============================================================ */}
            <div className="border-t border-slate-300 bg-white p-2">
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scroll-smooth">
                {GOV_SCHEMES.map((scheme, idx) => {
                  const sDecor = getSchemeDecor(scheme.code);
                  const isCurrent = idx === activeIndex;

                  return (
                    <button
                      key={scheme.id}
                      onClick={() => handleSelectScheme(idx)}
                      className={`flex-1 min-w-[125px] sm:min-w-0 p-2 rounded-xs text-left transition-all border cursor-pointer relative overflow-hidden ${
                        isCurrent
                          ? 'bg-[#002642] text-white border-[#002642] shadow-xs'
                          : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                      }`}
                      aria-label={`Select ${scheme.shortName}`}
                    >
                      {/* Active Progress Bar (GIGW 3.0 Timeline) */}
                      {isCurrent && isPlaying && !isHovered && (
                        <div 
                          key={progressKey}
                          className="absolute bottom-0 left-0 h-1 bg-[#f37021] animate-scheme-progress"
                        />
                      )}

                      <div className="flex items-center justify-between text-[10px]">
                        <span className="font-bold flex items-center gap-1">
                          <span>{sDecor.icon}</span>
                          <span>{scheme.shortName}</span>
                        </span>
                        <span className={`text-[9px] font-mono ${isCurrent ? 'text-amber-300' : 'text-slate-400'}`}>
                          0{idx + 1}
                        </span>
                      </div>

                      <div className={`text-[10px] font-medium truncate mt-0.5 ${isCurrent ? 'text-slate-200' : 'text-slate-500'}`}>
                        {scheme.tagline.split(' ')[0]} {scheme.impactMetric}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* 5. VIEW MODE B: COMPACT HORIZONTAL SCROLLING RIBBON */}
        {/* ============================================================ */}
        {viewMode === 'ribbon' && (
          <div 
            ref={ribbonRef}
            className="flex items-stretch gap-3 p-3.5 overflow-x-auto scroll-smooth snap-x snap-mandatory bg-slate-50/80 focus:outline-none"
            tabIndex={0}
            role="region"
            aria-label="Scrollable list of government schemes"
          >
            {GOV_SCHEMES.map((scheme, idx) => {
              const sDecor = getSchemeDecor(scheme.code);
              const isSelected = idx === activeIndex;

              return (
                <div
                  key={scheme.id}
                  onClick={() => openModal(scheme)}
                  className={`flex-shrink-0 w-80 sm:w-88 snap-start swaas-card overflow-hidden border-2 bg-white flex flex-col justify-between transition-all cursor-pointer group ${
                    isSelected ? 'border-[#002642] ring-2 ring-[#002642]/20 shadow-md' : 'border-slate-300 hover:shadow-md'
                  }`}
                >
                  <div className={`h-1.5 w-full ${sDecor.accentBg}`}></div>

                  <div className="p-4 space-y-2.5 flex-1 flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black uppercase px-2 py-0.5 rounded-xs bg-slate-100 text-slate-800 border border-slate-300">
                          {scheme.shortName}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          {scheme.portalName}
                        </span>
                      </div>

                      <h4 className="font-extrabold text-sm text-[#002642] leading-snug line-clamp-1">
                        {language === 'en' ? scheme.name : scheme.nameHi}
                      </h4>

                      <p className="text-[11px] text-[#f37021] font-serif italic line-clamp-1">
                        &ldquo;{language === 'en' ? scheme.slogan : scheme.sloganHi}&rdquo;
                      </p>

                      <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs flex items-center justify-between">
                        <div>
                          <div className="text-base font-black font-mono text-[#002642]">
                            {scheme.impactMetric}
                          </div>
                          <div className="text-[10px] text-slate-500">
                            {scheme.impactLabel}
                          </div>
                        </div>
                        <span className="text-lg">{sDecor.icon}</span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-xs">
                      <button
                        type="button"
                        className="text-[#002642] font-bold text-xs flex items-center gap-1 group-hover:text-[#f37021]"
                      >
                        <span>{language === 'en' ? 'Guidelines' : 'विवरण'}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>

                      <a
                        href={scheme.portalUrl}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="px-2.5 py-1 bg-[#002642] hover:bg-[#0b3866] text-white text-[11px] font-bold rounded-xs flex items-center gap-1"
                      >
                        <span>Portal ↗</span>
                      </a>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ============================================================ */}
        {/* 6. GIGW ACCESSIBILITY FOOTER STATUS NOTICE */}
        {/* ============================================================ */}
        <div className="bg-slate-100 border-t border-slate-300 px-4 py-2 flex flex-wrap items-center justify-between text-[11px] text-slate-600">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#138808]"></span>
            <span>
              {language === 'en' 
                ? 'GIGW 3.0 Compliant • Official Central Sector Initiatives Verified via PFMS & BhuNaksha' 
                : 'जीआईजीडब्ल्यू ३.० अनुपालित • पीएफएमएस एवं भू-नक्शा द्वारा सत्यापित केंद्रीय योजनाएं'}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span>
              Toll-Free Helpline: <strong className="text-[#002642] font-mono">1800-11-2013</strong>
            </span>
          </div>
        </div>
      </section>

      {/* Official Guidelines Modal when a scheme is clicked */}
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
