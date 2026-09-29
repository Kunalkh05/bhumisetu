import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  Globe, 
  Eye, 
  ChevronDown,
  Phone,
  ShieldCheck,
  User,
  Volume2
} from 'lucide-react';
import { DEMO_USERS } from '../../data/mockData';
import { IndianFlag } from './IndianFlag';
import { NationalEmblem } from './NationalEmblem';

interface GovHeaderProps {
  onOpenDemoLogin?: () => void;
  publicTab?: string;
  setPublicTab?: (tab: string) => void;
}

export const GovHeader: React.FC<GovHeaderProps> = ({ 
  onOpenDemoLogin,
}) => {
  const { 
    currentUser, 
    setCurrentUser,
    portalMode, 
    setPortalMode, 
    language, 
    setLanguage, 
    isHighContrast, 
    setIsHighContrast, 
    fontScale, 
    setFontScale,
    backendStatus,
    refreshBackendData,
    addToast
  } = useApp();

  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  const handleSwitchUser = (user: typeof DEMO_USERS[0]) => {
    setCurrentUser(user);
    if (user.isCitizen) {
      setPortalMode('CITIZEN');
    } else {
      setPortalMode('OFFICER');
    }
    setUserDropdownOpen(false);
    addToast({
      type: 'info',
      message: `Signed in as: ${user.name} (${user.designation})`,
      messageHi: `लॉगिन सफल: ${user.nameHi}`,
    });
  };

  return (
    <header className="w-full bg-white select-none border-b border-slate-200" role="banner">
      {/* 1. Official S3WaaS Top Indian Tricolour Stripe Ribbon */}
      <div className="tiranga-strip"></div>

      {/* 2. S3WaaS Accessibility Utility Bar (GIGW 3.0 Standard) */}
      <div className="bg-[#002642] text-slate-200 text-[11px] border-b border-[#0b3866]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-1.5 flex flex-wrap justify-between items-center gap-2">
          {/* Left: Official Government of India & Ministry Identifiers */}
          <div className="flex items-center gap-2.5 text-xs flex-wrap">
            <span className="font-semibold text-white flex items-center gap-2">
              <IndianFlag width={18} showBorder={true} />
              <span>{language === 'en' ? 'GOVERNMENT OF INDIA' : 'भारत सरकार'}</span>
            </span>
            <span className="text-slate-400">|</span>
            <span className="hidden sm:inline text-slate-300">
              {language === 'en' ? 'Ministry of Rural Development' : 'ग्रामीण विकास मंत्रालय'}
            </span>

            {/* Live Backend Connection Indicator */}
            <button 
              onClick={() => refreshBackendData()}
              title={`Backend: ${backendStatus.statusText} - Click to refresh connection`}
              className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold transition-all border ${
                backendStatus.connected
                  ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/50 hover:bg-emerald-900 cursor-pointer'
                  : 'bg-amber-950/80 text-amber-300 border-amber-500/50 hover:bg-amber-900 cursor-pointer'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${backendStatus.connected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
              <span>{backendStatus.connected ? `API Connected (${backendStatus.latencyMs}ms)` : 'Hybrid / Local Store'}</span>
            </button>
          </div>

          {/* Right: Accessibility Controls & Language Toggle */}
          <div className="flex items-center gap-3 sm:gap-4">
            <a 
              href="#main-content" 
              className="text-slate-300 hover:text-white underline underline-offset-2 hidden md:inline text-[11px]"
            >
              {language === 'en' ? 'Skip to main content' : 'मुख्य सामग्री पर जाएं'}
            </a>

            {/* Screen Reader Access link (GIGW mandate) */}
            <span className="hidden lg:flex items-center gap-1 text-[11px] text-slate-300">
              <Volume2 className="w-3 h-3 text-slate-400" />
              <span>{language === 'en' ? 'Screen Reader' : 'स्क्रीन रीडर'}</span>
            </span>

            <span className="text-slate-600 hidden md:inline">|</span>

            {/* Font Sizing Controls (A- / A / A+) */}
            <div className="flex items-center bg-[#0b3866] border border-slate-600 rounded-xs overflow-hidden" role="group" aria-label="Text Size Controls">
              <button
                onClick={() => setFontScale('normal')}
                className={`px-1.5 py-0.5 text-[11px] font-bold transition-colors ${fontScale === 'normal' ? 'bg-[#f37021] text-white' : 'text-slate-300 hover:text-white'}`}
                title="Standard Text Size (A-)"
                aria-pressed={fontScale === 'normal'}
              >
                A-
              </button>
              <button
                onClick={() => setFontScale('large')}
                className={`px-1.5 py-0.5 text-[11px] font-bold border-x border-slate-600 transition-colors ${fontScale === 'large' ? 'bg-[#f37021] text-white' : 'text-slate-300 hover:text-white'}`}
                title="Large Text Size (A)"
                aria-pressed={fontScale === 'large'}
              >
                A
              </button>
              <button
                onClick={() => setFontScale('xlarge')}
                className={`px-1.5 py-0.5 text-[11px] font-bold transition-colors ${fontScale === 'xlarge' ? 'bg-[#f37021] text-white' : 'text-slate-300 hover:text-white'}`}
                title="Extra Large Text Size (A+)"
                aria-pressed={fontScale === 'xlarge'}
              >
                A+
              </button>
            </div>

            {/* High Contrast Toggle */}
            <button
              onClick={() => setIsHighContrast(!isHighContrast)}
              className={`px-2 py-0.5 rounded-xs border text-[11px] font-semibold flex items-center gap-1 transition-colors ${
                isHighContrast 
                  ? 'bg-amber-400 text-black border-amber-400 font-bold' 
                  : 'bg-[#0b3866] border-slate-600 text-slate-200 hover:text-white'
              }`}
              title="Toggle High Contrast"
            >
              <Eye className="w-3 h-3" />
              <span className="hidden sm:inline">{language === 'en' ? 'Contrast' : 'कंट्रास्ट'}</span>
            </button>

            {/* Language Switcher */}
            <button
              onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
              className="px-2.5 py-0.5 bg-[#f37021] text-white font-bold text-[11px] rounded-xs hover:bg-[#d95a10] flex items-center gap-1 shadow-xs transition-colors"
              title="Switch Language"
            >
              <Globe className="w-3 h-3" />
              <span>{language === 'en' ? 'हिन्दी' : 'English'}</span>
            </button>

            {/* Toll Free Helpline */}
            <div className="hidden xl:flex items-center gap-1 text-[11px] text-slate-300 pl-2 border-l border-slate-700">
              <Phone className="w-3 h-3 text-[#f37021]" />
              <span>{language === 'en' ? 'Toll Free:' : 'टोल फ्री:'} <strong className="text-white">1800-11-2013</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. S3WaaS Main Emblem & Branding Banner */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex flex-wrap justify-between items-center gap-4 bg-white">
        {/* Left: Authentic State Emblem of India + Department Details */}
        <div className="flex items-center gap-4">
          <div className="flex-shrink-0">
            <NationalEmblem size={52} color="#002642" showSlogan={true} />
          </div>

          <div className="border-l border-slate-300 pl-4 py-0.5">
            <div className="text-[12px] font-semibold text-[#002642] tracking-wide">
              {language === 'en' 
                ? 'Department of Land Resources • Ministry of Rural Development' 
                : 'भूमि संसाधन विभाग • ग्रामीण विकास मंत्रालय'}
            </div>
            <div className="text-[11px] text-slate-500 font-medium">
              {language === 'en' 
                ? 'Government of India' 
                : 'भारत सरकार'}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-[#0b3866] leading-none">
                BHUMISETU
              </h1>
              <span className="text-base sm:text-lg font-bold text-[#f37021] leading-none">
                | भूमिसेतु
              </span>
            </div>
            <p className="text-[10px] text-slate-600 mt-0.5 hidden sm:block">
              {language === 'en'
                ? 'National Land Acquisition Management & Statutory Compliance Portal (RFCTLARR Act, 2013)'
                : 'राष्ट्रीय भूमि अधिग्रहण प्रबंधन एवं सांविधिक अनुपालन पोर्टल'}
            </p>
          </div>
        </div>

        {/* Right: S3WaaS Digital India Brand, PM Dignitary Badge & Unified Role/Portal Switcher */}
        <div className="flex items-center gap-3.5">
          {/* Official Dignitary: Hon'ble Prime Minister Shri Narendra Modi */}
          <div className="hidden md:flex items-center gap-2.5 border-r border-slate-200 pr-3.5 py-0.5">
            <div className="relative">
              <img 
                src="/assets/pm_modi_thumb.jpg" 
                alt={language === 'en' ? 'Shri Narendra Modi, Hon\'ble Prime Minister of India' : 'श्री नरेन्द्र मोदी, माननीय प्रधानमंत्री'} 
                className="w-12 h-12 rounded-full object-cover object-top border-2 border-[#f37021] shadow-xs"
              />
              <span className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-[#138808] border-2 border-white rounded-full flex items-center justify-center text-[8px] text-white font-bold" title="Prime Minister of India">
                🇮🇳
              </span>
            </div>
            <div className="flex flex-col text-left">
              <span className="text-[12px] font-extrabold text-[#002642] leading-tight">
                {language === 'en' ? 'Shri Narendra Modi' : 'श्री नरेन्द्र मोदी'}
              </span>
              <span className="text-[10px] text-[#f37021] font-bold leading-tight mt-0.5">
                {language === 'en' ? "Hon'ble Prime Minister" : 'माननीय प्रधानमंत्री'}
              </span>
              <span className="text-[9px] text-slate-500 font-medium">
                {language === 'en' ? 'Government of India' : 'भारत सरकार'}
              </span>
            </div>
          </div>

          {/* Official Campaign Representation */}
          <div className="hidden xl:flex items-center gap-3 border-r border-slate-200 pr-3.5">
            <div className="flex flex-col items-center justify-center">
              <span className="text-xs font-black tracking-wider text-[#002642] uppercase">Digital India</span>
              <span className="text-[9px] text-[#138808] font-bold">Power To Empower</span>
            </div>
            <div className="h-6 w-px bg-slate-200"></div>
            <div className="flex flex-col items-center justify-center">
              <span className="text-[11px] font-black tracking-tight text-[#f37021] uppercase">Viksit Bharat</span>
              <span className="text-[9px] text-[#002642] font-mono font-bold">@ 2047</span>
            </div>
          </div>

          {/* S3WaaS Portal Mode Switcher (Citizen Services vs Officer Portal) */}
          <div className="inline-flex rounded-xs border border-slate-300 bg-slate-100 p-0.5 shadow-2xs">
            <button
              onClick={() => setPortalMode('CITIZEN')}
              className={`px-3 py-1.5 text-xs font-bold transition-all rounded-xs ${
                portalMode === 'CITIZEN'
                  ? 'bg-[#0b3866] text-white shadow-xs'
                  : 'text-slate-700 hover:text-[#0b3866] hover:bg-slate-200'
              }`}
            >
              {language === 'en' ? 'Citizen Services' : 'नागरिक सेवा'}
            </button>
            <button
              onClick={() => setPortalMode('OFFICER')}
              className={`px-3 py-1.5 text-xs font-bold transition-all rounded-xs flex items-center gap-1 ${
                portalMode === 'OFFICER'
                  ? 'bg-[#138808] text-white shadow-xs'
                  : 'text-slate-700 hover:text-[#138808] hover:bg-slate-200'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>{language === 'en' ? 'Official Portal' : 'अधिकारी पोर्टल'}</span>
            </button>
          </div>

          {/* User Persona & Role Switcher */}
          <div className="relative">
            <button
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-300 hover:border-[#0b3866] rounded-xs text-xs font-medium text-slate-800 transition-colors shadow-2xs"
              aria-expanded={userDropdownOpen}
              aria-haspopup="true"
            >
              <div className="w-6 h-6 rounded-full bg-slate-100 text-[#0b3866] border border-slate-300 flex items-center justify-center text-xs">
                {currentUser.isCitizen ? <User className="w-3.5 h-3.5 text-slate-700" /> : <ShieldCheck className="w-3.5 h-3.5 text-[#138808]" />}
              </div>
              <div className="text-left hidden sm:block">
                <div className="font-semibold text-slate-900 leading-tight truncate max-w-[120px]">
                  {currentUser.name}
                </div>
                <div className="text-[10px] text-slate-500 truncate max-w-[120px]">
                  {currentUser.role.replace('_', ' ')}
                </div>
              </div>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {/* Dropdown Menu */}
            {userDropdownOpen && (
              <div className="absolute right-0 mt-1 w-80 bg-white border border-slate-300 shadow-xl rounded-xs z-50 text-slate-800 text-xs overflow-hidden">
                <div className="bg-[#002642] text-white px-3 py-2 font-bold text-xs flex justify-between items-center border-b-2 border-[#f37021]">
                  <span>{language === 'en' ? 'Select Role / Persona' : 'उपयोगकर्ता भूमिका चुनें'}</span>
                  <span className="text-[10px] bg-[#f37021] text-white font-bold px-1.5 py-0.5 rounded-xs">RBAC</span>
                </div>

                <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
                  {DEMO_USERS.map((user) => (
                    <button
                      key={user.id}
                      onClick={() => handleSwitchUser(user)}
                      className={`w-full text-left px-3.5 py-2.5 flex items-start gap-2.5 hover:bg-slate-50 transition-colors ${
                        currentUser.id === user.id ? 'bg-amber-50/80 border-l-3 border-[#f37021]' : ''
                      }`}
                    >
                      <div className="mt-0.5 text-slate-600">
                        {user.isCitizen ? <User className="w-4 h-4 text-slate-600" /> : <ShieldCheck className="w-4 h-4 text-[#138808]" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-bold text-[#002642] truncate">
                          {language === 'en' ? user.name : user.nameHi}
                        </div>
                        <div className="text-[11px] text-slate-600 truncate">
                          {language === 'en' ? user.designation : user.designationHi}
                        </div>
                        <div className="text-[10px] text-slate-400 truncate">
                          {user.jurisdiction.join(', ')}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>

                {onOpenDemoLogin && (
                  <div className="p-2.5 bg-slate-50 border-t border-slate-200">
                    <button
                      onClick={() => {
                        setUserDropdownOpen(false);
                        onOpenDemoLogin();
                      }}
                      className="w-full py-1.5 text-center bg-[#0b3866] hover:bg-[#082c52] text-white font-bold text-[11px] rounded-xs transition-colors"
                    >
                      {language === 'en' ? 'View Official Login Directory' : 'सभी आधिकारिक लॉगिन विवरण देखें'}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
