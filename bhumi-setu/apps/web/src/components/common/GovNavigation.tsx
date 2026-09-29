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
  Landmark
} from 'lucide-react';

export type PublicTab = 
  | 'HOME'
  | 'SEARCH'
  | 'SCHEMES'
  | 'NOTICES'
  | 'GRIEVANCE'
  | 'GIS_MAP'
  | 'PROJECTS'
  | 'ACTS_RULES'
  | 'CONTACT';

interface GovNavigationProps {
  activeTab: PublicTab;
  setActiveTab: (tab: PublicTab) => void;
}

export const GovNavigation: React.FC<GovNavigationProps> = ({ activeTab, setActiveTab }) => {
  const { language, portalMode, setPortalMode } = useApp();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: 'HOME' as PublicTab, label: 'Home', labelHi: 'मुख्य पृष्ठ', icon: Home },
    { id: 'SEARCH' as PublicTab, label: 'Search Records', labelHi: 'अभिलेख खोजें', icon: Search },
    { id: 'SCHEMES' as PublicTab, label: 'Govt Schemes', labelHi: 'सरकारी योजनाएं', icon: Landmark, badge: 'NEW' },
    { id: 'NOTICES' as PublicTab, label: 'Gazette Notifications', labelHi: 'राजपत्र अधिसूचनाएं', icon: FileText },
    { id: 'GRIEVANCE' as PublicTab, label: 'Section 15 Objections', labelHi: 'धारा १५ आपत्ति', icon: AlertCircle },
    { id: 'GIS_MAP' as PublicTab, label: 'Cadastral GIS Map', labelHi: 'भू-नक्शा GIS', icon: Map },
    { id: 'PROJECTS' as PublicTab, label: 'Acquisition Projects', labelHi: 'परियोजनाएं', icon: FolderKanban },
    { id: 'ACTS_RULES' as PublicTab, label: 'Acts & Rules', labelHi: 'अधिनियम व नियम', icon: BookOpen },
    { id: 'CONTACT' as PublicTab, label: 'Helpline & FAQs', labelHi: 'हेल्पलाइन व संपर्क', icon: PhoneCall },
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
          {/* Desktop Navigation Links */}
          <div className="hidden md:flex items-center h-full space-x-0.5 overflow-x-auto">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = portalMode === 'CITIZEN' && activeTab === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`h-full px-3.5 flex items-center gap-1.5 text-xs font-semibold whitespace-nowrap transition-colors relative border-r border-[#134679]/40 ${
                    isActive
                      ? 'bg-[#002642] text-white'
                      : 'text-slate-100 hover:bg-[#134679] hover:text-white'
                  }`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#f37021]' : 'text-slate-300'}`} />
                  <span>{language === 'en' ? item.label : item.labelHi}</span>
                  {item.badge && (
                    <span className="px-1.5 py-0.2 rounded-xs text-[9px] font-black bg-[#f37021] text-white animate-pulse">
                      {item.badge}
                    </span>
                  )}
                  {isActive && (
                    <span className="absolute bottom-0 left-0 right-0 h-1 bg-[#f37021]"></span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Direct Officer Portal Link (Desktop Right) */}
          <div className="hidden md:flex items-center h-full">
            <button
              onClick={() => setPortalMode('OFFICER')}
              className={`h-full px-4 flex items-center gap-1.5 text-xs font-bold transition-colors ${
                portalMode === 'OFFICER'
                  ? 'bg-[#138808] text-white shadow-inner'
                  : 'bg-[#134679] text-white hover:bg-[#002642]'
              }`}
              title="Official Administration Portal"
            >
              <ShieldCheck className="w-4 h-4 text-amber-300" />
              <span>{language === 'en' ? 'Officer Portal' : 'अधिकारी लॉगिन'}</span>
            </button>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex items-center md:hidden w-full justify-between py-1.5">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 rounded-xs text-white hover:bg-[#134679] focus:outline-none flex items-center gap-2 text-xs font-semibold"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              <span>{language === 'en' ? 'Menu' : 'मेनू'}</span>
            </button>

            <button
              onClick={() => setPortalMode('OFFICER')}
              className={`px-3 py-1 text-xs font-bold rounded-xs flex items-center gap-1 ${
                portalMode === 'OFFICER' ? 'bg-[#138808] text-white' : 'bg-[#134679] text-white'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-amber-300" />
              <span>{language === 'en' ? 'Officer Portal' : 'विभागीय लॉगिन'}</span>
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-[#134679] py-2 bg-[#002642] divide-y divide-[#134679]/40">
            {navItems.map((item) => {
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
          </div>
        )}
      </div>
    </nav>
  );
};
