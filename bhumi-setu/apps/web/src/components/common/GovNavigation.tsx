import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  Home, 
  Search, 
  FileText, 
  Map, 
  AlertCircle, 
  FolderKanban, 
  BookOpen, 
  PhoneCall,
  Menu,
  X,
  ShieldCheck,
  Landmark,
  Building2,
  FileCheck,
  Clock,
  CheckCircle2,
  Sparkles,
  HelpCircle,
  Info,
  Layers,
  Bot
} from 'lucide-react';

export type PublicTab = 
  | 'HOME'
  | 'SEARCH'
  | 'PROPERTY_INTEL'
  | 'DOC_VERIFY'
  | 'GIS_MAP'
  | 'TIMELINE'
  | 'MUTATION'
  | 'RISK_ANALYSIS'
  | 'SCHEMES'
  | 'STATE_PORTALS'
  | 'REPORTS'
  | 'HELP'
  | 'ABOUT'
  | 'NOTICES'
  | 'GRIEVANCE'
  | 'PROJECTS'
  | 'ACTS_RULES'
  | 'CONTACT';

interface GovNavigationProps {
  activeTab: PublicTab;
  setActiveTab: (tab: PublicTab) => void;
  onOpenAiChat?: () => void;
}

export const GovNavigation: React.FC<GovNavigationProps> = ({ 
  activeTab, 
  setActiveTab,
  onOpenAiChat
}) => {
  const { language, portalMode, setPortalMode } = useApp();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Core 11 Primary Nav Items as requested in Section 19
  const primaryNavItems = [
    { id: 'HOME' as PublicTab, label: 'Home', labelHi: 'होम', icon: Home },
    { id: 'SEARCH' as PublicTab, label: 'Land Search', labelHi: 'भू-खोज', icon: Search },
    { id: 'PROPERTY_INTEL' as PublicTab, label: 'Property Intelligence', labelHi: 'प्रॉपर्टी व्यू', icon: Building2, badge: 'ONE-VIEW' },
    { id: 'DOC_VERIFY' as PublicTab, label: 'Document Verification', labelHi: 'दस्तावेज सत्यापन', icon: FileCheck, badge: 'AI' },
    { id: 'GIS_MAP' as PublicTab, label: 'Map', labelHi: 'भू-नक्शा', icon: Map },
    { id: 'MUTATION' as PublicTab, label: 'Mutation', labelHi: 'दाखिल-खारिज', icon: Clock },
    { id: 'RISK_ANALYSIS' as PublicTab, label: 'Risk Analysis', labelHi: 'जोखिम विश्लेषण', icon: AlertCircle },
    { id: 'TIMELINE' as PublicTab, label: 'Timeline', labelHi: 'समयरेखा', icon: Layers },
    { id: 'SCHEMES' as PublicTab, label: 'Schemes', labelHi: 'योजनाएं', icon: Landmark },
    { id: 'STATE_PORTALS' as PublicTab, label: 'State Portals', labelHi: 'राज्य पोर्टल', icon: BookOpen },
    { id: 'REPORTS' as PublicTab, label: 'Reports', labelHi: 'रिपोर्ट्स', icon: FileText },
  ];

  // Secondary/Support Nav items for Mobile / Overflow
  const secondaryNavItems = [
    { id: 'HELP' as PublicTab, label: 'Help / How It Works', labelHi: 'सहायता एवं उपयोग', icon: HelpCircle },
    { id: 'ABOUT' as PublicTab, label: 'About Platform', labelHi: 'मंच के बारे में', icon: Info },
    { id: 'NOTICES' as PublicTab, label: 'Gazette Notifications', labelHi: 'राजपत्र अधिसूचनाएं', icon: FileText },
    { id: 'GRIEVANCE' as PublicTab, label: 'Section 15 Objections', labelHi: 'धारा १५ आपत्ति', icon: AlertCircle },
  ];

  const handleNavClick = (tabId: PublicTab) => {
    setPortalMode('CITIZEN');
    setActiveTab(tabId);
    setMobileMenuOpen(false);
  };

  return (
    <nav className="bg-[#0b3866] text-white sticky top-0 z-40 shadow-sm border-t border-[#134679]" aria-label="Main Navigation">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-11">
          
          {/* Desktop Left: Main Navigation Items (Horizontal Scrollable) */}
          <div className="hidden lg:flex items-center h-full space-x-0.5 overflow-x-auto no-scrollbar">
            {primaryNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = portalMode === 'CITIZEN' && activeTab === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`h-full px-2.5 xl:px-3 flex items-center gap-1.5 text-xs font-semibold whitespace-nowrap transition-colors relative border-r border-[#134679]/40 ${
                    isActive
                      ? 'bg-[#002642] text-white'
                      : 'text-slate-100 hover:bg-[#134679] hover:text-white'
                  }`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#f37021]' : 'text-slate-300'}`} />
                  <span>{language === 'en' ? item.label : item.labelHi}</span>
                  {item.badge && (
                    <span className="px-1 py-0.2 rounded-xs text-[8px] font-black bg-[#f37021] text-white">
                      {item.badge}
                    </span>
                  )}
                  {isActive && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#f37021]"></span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Desktop Right Side: BhuMitra AI, Help, Primary CTA 'Search Land' & Officer Portal */}
          <div className="hidden lg:flex items-center h-full space-x-1.5">
            {/* BhuMitra AI Assistant Button */}
            {onOpenAiChat && (
              <button
                onClick={onOpenAiChat}
                className="h-8 px-2.5 bg-gradient-to-r from-[#f37021] to-[#e65100] hover:from-[#e65100] hover:to-[#c2410c] text-white font-extrabold text-[11px] rounded-xs shadow-xs flex items-center gap-1.5 transition-all transform hover:scale-102"
                title="Open BhuMitra AI Assistant"
              >
                <Bot className="w-3.5 h-3.5 animate-bounce" />
                <span>BhuMitra AI</span>
              </button>
            )}

            {/* Help Link */}
            <button
              onClick={() => handleNavClick('HELP')}
              className={`h-full px-2.5 flex items-center gap-1 text-[11px] font-medium transition-colors ${
                activeTab === 'HELP' ? 'text-amber-300 font-bold' : 'text-slate-200 hover:text-white'
              }`}
            >
              <HelpCircle className="w-3.5 h-3.5 text-slate-300" />
              <span>{language === 'en' ? 'Help' : 'सहायता'}</span>
            </button>

            {/* Primary CTA: Search Land */}
            <button
              onClick={() => handleNavClick('SEARCH')}
              className="h-8 px-3 bg-white text-[#002642] hover:bg-slate-100 font-extrabold text-xs rounded-xs flex items-center gap-1 shadow-xs transition-colors"
            >
              <Search className="w-3 h-3 text-[#f37021]" />
              <span>Search Land</span>
            </button>

            {/* Compact Officer Portal Access */}
            <button
              onClick={() => setPortalMode('OFFICER')}
              className="h-8 px-2.5 bg-[#001f35] hover:bg-[#001728] text-slate-300 hover:text-white font-bold text-[11px] rounded-xs border border-white/20 flex items-center gap-1 transition-colors"
              title="Official Administration Portal"
            >
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              <span className="hidden xl:inline">{language === 'en' ? 'Officer' : 'अधिकारी'}</span>
            </button>
          </div>

          {/* Mobile Bar Header */}
          <div className="flex items-center lg:hidden w-full justify-between py-1.5">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 rounded-xs text-white hover:bg-[#134679] flex items-center gap-2 text-xs font-semibold"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              <span>{language === 'en' ? 'Menu' : 'मेनू'}</span>
            </button>

            <div className="flex items-center gap-2">
              {onOpenAiChat && (
                <button
                  onClick={onOpenAiChat}
                  className="px-2.5 py-1 bg-[#f37021] text-white text-[11px] font-bold rounded-xs flex items-center gap-1"
                >
                  <Bot className="w-3.5 h-3.5" />
                  <span>BhuMitra</span>
                </button>
              )}

              <button
                onClick={() => handleNavClick('SEARCH')}
                className="px-2.5 py-1 bg-white text-[#002642] text-[11px] font-bold rounded-xs"
              >
                Search
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Dropdown Menu with Complete Section Links */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-[#134679] py-2 bg-[#002642] divide-y divide-[#134679]/40 max-h-[80vh] overflow-y-auto">
            <div className="px-4 py-1.5 text-[10px] font-black text-amber-300 uppercase tracking-wider">
              Primary Land Intelligence Modules
            </div>

            {primaryNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = portalMode === 'CITIZEN' && activeTab === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`w-full text-left px-4 py-2.5 flex items-center justify-between text-xs font-medium ${
                    isActive
                      ? 'bg-[#f37021] text-white font-bold'
                      : 'text-slate-200 hover:bg-[#134679]'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-4 h-4" />
                    <span>{language === 'en' ? item.label : item.labelHi}</span>
                  </div>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 rounded-xs text-[8px] font-black bg-white/20 text-white">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}

            <div className="px-4 py-1.5 text-[10px] font-black text-amber-300 uppercase tracking-wider pt-2">
              Support &amp; Directory
            </div>

            {secondaryNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = portalMode === 'CITIZEN' && activeTab === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`w-full text-left px-4 py-2.5 flex items-center gap-2.5 text-xs font-medium ${
                    isActive
                      ? 'bg-[#f37021] text-white font-bold'
                      : 'text-slate-200 hover:bg-[#134679]'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{language === 'en' ? item.label : item.labelHi}</span>
                </button>
              );
            })}

            <div className="p-3">
              <button
                onClick={() => {
                  setPortalMode('OFFICER');
                  setMobileMenuOpen(false);
                }}
                className="w-full py-2 bg-[#138808] hover:bg-[#0e6306] text-white font-bold text-xs rounded-xs flex items-center justify-center gap-1.5"
              >
                <ShieldCheck className="w-4 h-4 text-amber-300" />
                <span>Switch to Officer Administration Portal</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};
