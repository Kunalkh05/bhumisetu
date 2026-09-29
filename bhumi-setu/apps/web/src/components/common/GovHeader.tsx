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

      {/* 2. Compact Accessibility & Prototype Utility Bar (GIGW 3.0 Standard) */}
      <div className="bg-[#002642] text-slate-200 text-[11px] border-b border-[#0b3866]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-1.5 flex flex-wrap justify-between items-center gap-2">
          {/* Left: Official Government of India & Academic Prototype Identifier */}
          <div className="flex items-center gap-2.5 text-xs flex-wrap">
            <span className="font-semibold text-white flex items-center gap-2">
              <IndianFlag width={18} showBorder={true} />
              <span>{language === 'en' ? 'GOVERNMENT OF INDIA' : 'भारत सरकार'}</span>
            </span>
            <span className="text-slate-500">|</span>
            <span className="hidden sm:inline text-slate-300">
              {language === 'en' ? 'Ministry of Rural Development' : 'ग्रामीण विकास मंत्रालय'}
            </span>
            <span className="text-slate-500 hidden sm:inline">|</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-400/20 text-amber-300 border border-amber-400/30">
              {language === 'en' ? 'Academic / SIH Prototype' : 'शैक्षणिक / एसआईएच प्रोटोटाइप'}
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
          <div className="flex items-center gap-2.5 sm:gap-3">
            <a 
              href="#main-content" 
              className="text-slate-300 hover:text-white underline underline-offset-2 hidden md:inline text-[11px]"
            >
              {language === 'en' ? 'Skip to content' : 'सामग्री पर जाएं'}
            </a>

            {/* Font Sizing Controls (A- / A / A+) */}
            <div className="flex items-center bg-[#0b3866]/80 border border-slate-600/70 rounded-md overflow-hidden" role="group" aria-label="Text Size Controls">
              <button
                onClick={() => setFontScale('normal')}
                className={`px-2 py-0.5 text-[11px] font-bold transition-all ${fontScale === 'normal' ? 'bg-[#f37021] text-white' : 'text-slate-300 hover:text-white'}`}
                title="Standard Text Size (A-)"
                aria-pressed={fontScale === 'normal'}
              >
                A-
              </button>
              <button
                onClick={() => setFontScale('large')}
                className={`px-2 py-0.5 text-[11px] font-bold border-x border-slate-600/70 transition-all ${fontScale === 'large' ? 'bg-[#f37021] text-white' : 'text-slate-300 hover:text-white'}`}
                title="Large Text Size (A)"
                aria-pressed={fontScale === 'large'}
              >
                A
              </button>
              <button
                onClick={() => setFontScale('xlarge')}
                className={`px-2 py-0.5 text-[11px] font-bold transition-all ${fontScale === 'xlarge' ? 'bg-[#f37021] text-white' : 'text-slate-300 hover:text-white'}`}
                title="Extra Large Text Size (A+)"
                aria-pressed={fontScale === 'xlarge'}
              >
                A+
              </button>
            </div>

            {/* High Contrast Toggle */}
            <button
              onClick={() => setIsHighContrast(!isHighContrast)}
              className={`px-2 py-0.5 rounded-md border text-[11px] font-medium flex items-center gap-1 transition-all ${
                isHighContrast 
                  ? 'bg-amber-400 text-black border-amber-400 font-bold ring-2 ring-amber-300/40' 
                  : 'bg-[#0b3866]/80 border-slate-600/70 text-slate-200 hover:text-white'
              }`}
              title="Toggle High Contrast"
            >
              <Eye className="w-3 h-3" />
              <span className="hidden sm:inline">{language === 'en' ? 'Contrast' : 'कंट्रास्ट'}</span>
            </button>

            {/* Language Switcher */}
            <button
              onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
              className="px-2.5 py-0.5 bg-[#f37021] hover:bg-[#d95a10] text-white font-semibold text-[11px] rounded-md flex items-center gap-1 transition-all shadow-xs"
              title="Switch Language"
            >
              <Globe className="w-3 h-3" />
              <span>{language === 'en' ? 'हिन्दी' : 'English'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 3. Modern Sovereign Main Header */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap justify-between items-center gap-3 bg-white">
        {/* Left: State Emblem + Brand Identity */}
        <div className="flex items-center gap-3.5">
          <div className="flex-shrink-0">
            <NationalEmblem size={44} color="#002642" showSlogan={false} />
          </div>

          <div className="border-l border-slate-200 pl-3.5 py-0.5">
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-black tracking-tight text-[#002642] leading-none">
                BHUMISETU
              </h1>
              <span className="text-base sm:text-lg font-bold text-[#f37021] leading-none">
                | भूमिसेतु
              </span>
            </div>
            <p className="text-xs text-slate-600 font-medium mt-0.5">
              {language === 'en' 
                ? 'AI-Powered Land Acquisition Intelligence, Monitoring & Verification' 
                : 'एआई-संचालित भूमि अधिग्रहण आसूचना, निगरानी एवं सत्यापन'}
            </p>
          </div>
        </div>

        {/* Right: Modern Mode Switcher & Demo Persona Selector */}
        <div className="flex items-center gap-3">
          {/* 2026 Segmented Mode Switcher */}
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5 shadow-xs">
            <button
              onClick={() => setPortalMode('CITIZEN')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
                portalMode === 'CITIZEN'
                  ? 'bg-white text-[#002642] shadow-xs font-bold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <User className="w-3.5 h-3.5 text-slate-500" />
              <span>{language === 'en' ? 'Citizen Portal' : 'नागरिक पोर्टल'}</span>
            </button>
            <button
              onClick={() => setPortalMode('OFFICER')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
                portalMode === 'OFFICER'
                  ? 'bg-[#002642] text-white shadow-xs font-bold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
              <span>{language === 'en' ? 'Officer Workspace' : 'अधिकारी कार्यक्षेत्र'}</span>
            </button>
          </div>

          {/* User Persona & Role Switcher */}
          <div className="relative">
            <button
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 hover:border-slate-300 rounded-lg text-xs font-medium text-slate-800 transition-all shadow-xs cursor-pointer"
              aria-expanded={userDropdownOpen}
              aria-haspopup="true"
            >
              <div className="w-6 h-6 rounded-full bg-slate-100 text-[#002642] border border-slate-200 flex items-center justify-center text-xs font-bold">
                {currentUser.isCitizen ? <User className="w-3.5 h-3.5 text-slate-600" /> : <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />}
              </div>
              <div className="text-left hidden sm:block">
                <div className="font-semibold text-slate-900 leading-tight truncate max-w-[130px]">
                  {currentUser.name}
                </div>
                <div className="text-[10px] text-slate-500 truncate max-w-[130px]">
                  {currentUser.role.replace('_', ' ')}
                </div>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {/* Dropdown Menu */}
            {userDropdownOpen && (
              <div className="absolute right-0 mt-1.5 w-80 bg-white border border-slate-200 shadow-xl rounded-xl z-50 text-slate-800 text-xs overflow-hidden">
                <div className="bg-[#002642] text-white px-4 py-2.5 font-bold text-xs flex justify-between items-center border-b border-slate-700">
                  <span>{language === 'en' ? 'Switch Demo Persona' : 'डेमो उपयोगकर्ता बदलें'}</span>
                  <span className="text-[10px] bg-amber-400/20 text-amber-300 font-bold px-2 py-0.5 rounded-full border border-amber-400/30">SIH DEMO</span>
                </div>

                <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
                  {DEMO_USERS.map((user) => (
                    <button
                      key={user.id}
                      onClick={() => handleSwitchUser(user)}
                      className={`w-full text-left px-4 py-2.5 flex items-start gap-3 hover:bg-slate-50 transition-colors cursor-pointer ${
                        currentUser.id === user.id ? 'bg-amber-50/80 border-l-4 border-[#f37021]' : ''
                      }`}
                    >
                      <div className="mt-0.5 text-slate-500">
                        {user.isCitizen ? <User className="w-4 h-4 text-slate-500" /> : <ShieldCheck className="w-4 h-4 text-emerald-600" />}
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
                      className="w-full py-1.5 text-center bg-[#002642] hover:bg-[#0b3866] text-white font-semibold text-[11px] rounded-lg transition-colors cursor-pointer shadow-xs"
                    >
                      {language === 'en' ? 'View Demo Login Directory' : 'सभी डेमो लॉगिन देखें'}
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
