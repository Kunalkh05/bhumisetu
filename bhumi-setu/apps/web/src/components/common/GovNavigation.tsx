import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  Home, 
  Search, 
  FileText, 
  Map, 
  AlertCircle, 
  BookOpen, 
  Menu, 
  X, 
  ShieldCheck, 
  Landmark, 
  Building2, 
  FileCheck, 
  Clock, 
  HelpCircle, 
  Info, 
  Layers, 
  Bot,
  ChevronDown,
  Sparkles
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

interface NavGroupItem {
  id: PublicTab;
  label: string;
  labelHi: string;
  desc: string;
  descHi: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface NavGroup {
  id: string;
  label: string;
  labelHi: string;
  icon: React.ComponentType<{ className?: string }>;
  items: NavGroupItem[];
}

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
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const navRef = useRef<HTMLDivElement>(null);

  // Grouped Navigation Architecture (eliminates horizontal overflow)
  const navGroups: NavGroup[] = [
    {
      id: 'LAND_SERVICES',
      label: 'Land Records & Map',
      labelHi: 'भू-अभिलेख एवं नक्शा',
      icon: Building2,
      items: [
        {
          id: 'SEARCH',
          label: 'Unified Land Search',
          labelHi: 'एकीकृत भू-खोज',
          desc: 'Search by State, District, Survey / Gat or ULPIN',
          descHi: 'राज्य, ज़िला, सर्वे/गट या १४-अंकीय भू-आधार द्वारा खोजें',
          icon: Search,
        },
        {
          id: 'PROPERTY_INTEL',
          label: 'One Property — One View',
          labelHi: 'एकल संपत्ति विश्लेषण',
          desc: 'Unified 7/12 RoR, SRO Deeds, Mutation & Cadastre',
          descHi: 'सात-बारा, पंजीयन, नामांतरण एवं नक्शा का समग्र दृश्य',
          icon: Building2,
          badge: 'ONE-VIEW'
        },
        {
          id: 'GIS_MAP',
          label: 'Cadastral GIS Map',
          labelHi: 'भू-नक्शा GIS',
          desc: 'PostGIS spatial parcel boundaries & corridors',
          descHi: 'डिजिटल सीमा रेखा एवं सरकारी गलियारा ओवरलैप',
          icon: Map,
        },
        {
          id: 'MUTATION',
          label: 'Mutation Tracker',
          labelHi: 'दाखिल-खारिज स्थिति',
          desc: 'Real-time Ferfar mutation lifecycle tracking',
          descHi: 'नामांतरण आवेदन एवं आपत्ति की वास्तविक स्थिति',
          icon: Clock,
        }
      ]
    },
    {
      id: 'VERIFICATION',
      label: 'AI Verification & Risk',
      labelHi: 'एआई सत्यापन एवं जोखिम',
      icon: ShieldCheck,
      items: [
        {
          id: 'DOC_VERIFY',
          label: 'AI Document Verification',
          labelHi: 'दस्तावेज सत्यापन',
          desc: 'Vision OCR extraction & deed cross-verification',
          descHi: 'विलेख एवं ७/१२ का स्वतः मिलान व विसंगति जांच',
          icon: FileCheck,
          badge: 'AI'
        },
        {
          id: 'RISK_ANALYSIS',
          label: '12-Point Risk Analysis',
          labelHi: '१२-सूत्रीय जोखिम विश्लेषण',
          desc: 'Title encumbrances, litigation & tribal land checks',
          descHi: 'कानूनी विवाद, शासकीय निर्बंधन एवं स्वत्व सुरक्षा जांच',
          icon: AlertCircle,
        },
        {
          id: 'TIMELINE',
          label: 'Historical Ownership Timeline',
          labelHi: 'ऐतिहासिक समयरेखा',
          desc: 'Chain of title from 2018 to present year',
          descHi: 'वर्ष २०१८ से वर्तमान तक क्रमिक हस्तांतरण का इतिहास',
          icon: Layers,
        }
      ]
    },
    {
      id: 'SCHEMES_PORTALS',
      label: 'Schemes & Portals',
      labelHi: 'योजनाएं एवं राज्य पोर्टल',
      icon: Landmark,
      items: [
        {
          id: 'SCHEMES',
          label: 'Flagship Central Schemes',
          labelHi: 'प्रमुख केंद्रीय योजनाएं',
          desc: 'SVAMITVA, PM-KISAN, PMAY-G & Bhoomi Rashi',
          descHi: 'स्वामित्व, पीएम-किसान, आवास एवं भू-अधिग्रहण योजनाएं',
          icon: Landmark,
        },
        {
          id: 'STATE_PORTALS',
          label: '28 States & UTs Directory',
          labelHi: 'राज्य पोर्टल निर्देशिका',
          desc: 'Official Mahabhulekh, AnyRoR, UP Bhulekh portals',
          descHi: 'राज्यों के अधिकृत भू-अभिलेख एवं पंजीयन पोर्टल',
          icon: BookOpen,
        }
      ]
    },
    {
      id: 'CITIZEN_SERVICES',
      label: 'Reports & Objections',
      labelHi: 'रिपोर्ट एवं आपत्तियां',
      icon: FileText,
      items: [
        {
          id: 'REPORTS',
          label: 'Statutory Report Generator',
          labelHi: 'विधिक रिपोर्ट जनरेटर',
          desc: 'Download consolidated Property Intelligence PDF',
          descHi: 'संपूर्ण संपत्ति सारांश पीडीएफ डाउनलोड करें',
          icon: FileText,
        },
        {
          id: 'GRIEVANCE',
          label: 'Section 15 Objections',
          labelHi: 'धारा १५ आपत्ति दर्ज करें',
          desc: 'File statutory objection & track hearing notice',
          descHi: 'अधिग्रहण आपत्ति दर्ज करें एवं सुनवाई स्थिति देखें',
          icon: AlertCircle,
        },
        {
          id: 'NOTICES',
          label: 'Gazette Notifications',
          labelHi: 'राजपत्र अधिसूचनाएं',
          desc: 'Sec 11 preliminary decrees & Sec 19 declarations',
          descHi: 'विधिक अधिसूचनाएं, गजट आदेश एवं जन-सुनवाई',
          icon: FileText,
        },
        {
          id: 'HELP',
          label: 'How It Works / User Guide',
          labelHi: 'उपयोग मार्गदर्शिका',
          desc: 'Citizen guide, videos & frequently asked questions',
          descHi: 'नागरिक उपयोग निर्देश एवं प्रायः पूछे जाने वाले प्रश्न',
          icon: HelpCircle,
        },
        {
          id: 'ABOUT',
          label: 'About Platform',
          labelHi: 'मंच के बारे में',
          desc: 'Mission, architecture, and DPDP compliance',
          descHi: 'उद्देश्य, तकनीकी ढाँचा एवं डेटा सुरक्षा सिद्धांत',
          icon: Info,
        }
      ]
    }
  ];

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setOpenDropdown(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleNavClick = (tabId: PublicTab) => {
    setPortalMode('CITIZEN');
    setActiveTab(tabId);
    setOpenDropdown(null);
    setMobileMenuOpen(false);
  };

  const isGroupActive = (group: NavGroup) => {
    return portalMode === 'CITIZEN' && group.items.some(item => item.id === activeTab);
  };

  return (
    <nav 
      ref={navRef}
      className="bg-[#0b3866] text-white sticky top-0 z-40 shadow-sm border-t border-[#134679]" 
      aria-label="Main Navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-11">
          
          {/* Desktop Left: Clean Grouped Navigation */}
          <div className="hidden lg:flex items-center h-full space-x-1">
            {/* 1. Home Direct Button */}
            <button
              onClick={() => handleNavClick('HOME')}
              className={`h-full px-3 flex items-center gap-1.5 text-xs font-semibold whitespace-nowrap transition-colors relative ${
                portalMode === 'CITIZEN' && activeTab === 'HOME'
                  ? 'bg-[#002642] text-white'
                  : 'text-slate-100 hover:bg-[#134679] hover:text-white'
              }`}
              aria-current={portalMode === 'CITIZEN' && activeTab === 'HOME' ? 'page' : undefined}
            >
              <Home className={`w-3.5 h-3.5 ${portalMode === 'CITIZEN' && activeTab === 'HOME' ? 'text-[#f37021]' : 'text-slate-300'}`} />
              <span>{language === 'en' ? 'Home' : 'होम'}</span>
              {portalMode === 'CITIZEN' && activeTab === 'HOME' && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#f37021]" />
              )}
            </button>

            {/* 2. Nav Groups Dropdowns */}
            {navGroups.map((group) => {
              const active = isGroupActive(group);
              const isOpen = openDropdown === group.id;
              const GroupIcon = group.icon;

              return (
                <div key={group.id} className="relative h-full flex items-center">
                  <button
                    onClick={() => setOpenDropdown(isOpen ? null : group.id)}
                    onMouseEnter={() => setOpenDropdown(group.id)}
                    className={`h-full px-3 flex items-center gap-1.5 text-xs font-semibold whitespace-nowrap transition-colors relative cursor-pointer ${
                      active || isOpen
                        ? 'bg-[#002642] text-white'
                        : 'text-slate-100 hover:bg-[#134679] hover:text-white'
                    }`}
                    aria-expanded={isOpen}
                    aria-haspopup="true"
                  >
                    <GroupIcon className={`w-3.5 h-3.5 ${active ? 'text-[#f37021]' : 'text-slate-300'}`} />
                    <span>{language === 'en' ? group.label : group.labelHi}</span>
                    <ChevronDown className={`w-3 h-3 text-slate-300 transition-transform ${isOpen ? 'rotate-180 text-amber-300' : ''}`} />
                    {active && (
                      <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#f37021]" />
                    )}
                  </button>

                  {/* Dropdown Menu */}
                  {isOpen && (
                    <div 
                      onMouseLeave={() => setOpenDropdown(null)}
                      className="absolute top-full left-0 w-80 bg-white text-slate-900 border border-slate-200/90 shadow-2xl rounded-2xl z-50 overflow-hidden divide-y divide-slate-100 animate-in fade-in slide-in-from-top-1 duration-150"
                    >
                      <div className="bg-[#002642] text-white px-4 py-2.5 text-[11px] font-bold flex items-center justify-between border-b-2 border-[#f37021]">
                        <span>{language === 'en' ? group.label : group.labelHi}</span>
                        <span className="text-[10px] text-amber-300 font-semibold bg-white/10 px-2 py-0.5 rounded-full">{group.items.length} Modules</span>
                      </div>

                      <div className="p-1.5 space-y-1">
                        {group.items.map((item) => {
                          const ItemIcon = item.icon;
                          const isItemActive = portalMode === 'CITIZEN' && activeTab === item.id;

                          return (
                            <button
                              key={item.id}
                              onClick={() => handleNavClick(item.id)}
                              className={`w-full text-left p-2.5 rounded-xl flex items-start gap-2.5 transition-all cursor-pointer ${
                                isItemActive
                                  ? 'bg-amber-50 text-[#002642] border-l-4 border-[#f37021]'
                                  : 'hover:bg-slate-50 text-slate-800'
                              }`}
                            >
                              <div className={`p-2 rounded-lg flex-shrink-0 mt-0.5 ${
                                isItemActive ? 'bg-[#002642] text-white shadow-xs' : 'bg-slate-100 text-[#002642]'
                              }`}>
                                <ItemIcon className="w-4 h-4" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <span className="font-bold text-xs">
                                    {language === 'en' ? item.label : item.labelHi}
                                  </span>
                                  {item.badge && (
                                    <span className="px-2 py-0.5 rounded-full text-[8px] font-black bg-[#f37021] text-white uppercase shadow-xs">
                                      {item.badge}
                                    </span>
                                  )}
                                </div>
                                <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-1 font-normal">
                                  {language === 'en' ? item.desc : item.descHi}
                                </p>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Desktop Right Side: BhuMitra AI, Direct Search CTA & Officer Portal */}
          <div className="hidden lg:flex items-center h-full space-x-2.5">
            {/* BhuMitra AI Assistant Button */}
            {onOpenAiChat && (
              <button
                onClick={onOpenAiChat}
                className="h-8 px-3.5 bg-gradient-to-r from-[#f37021] to-[#e65100] hover:from-[#e65100] hover:to-[#c2410c] text-white font-extrabold text-[11px] rounded-full shadow-xs hover:shadow-md flex items-center gap-1.5 transition-all transform hover:-translate-y-0.5 cursor-pointer"
                title="Open BhuMitra AI Assistant"
              >
                <Bot className="w-3.5 h-3.5" />
                <span>BhuMitra AI</span>
              </button>
            )}

            {/* Primary Direct CTA: Search Land */}
            <button
              onClick={() => handleNavClick('SEARCH')}
              className="h-8 px-4 bg-white text-[#002642] hover:bg-slate-100 font-extrabold text-xs rounded-full flex items-center gap-1.5 shadow-xs hover:shadow-sm transition-all transform hover:-translate-y-0.5 cursor-pointer"
            >
              <Search className="w-3.5 h-3.5 text-[#f37021]" />
              <span>{language === 'en' ? 'Search Land' : 'भू-खोज'}</span>
            </button>

            {/* Officer Portal Switcher */}
            <button
              onClick={() => setPortalMode('OFFICER')}
              className="h-8 px-3 bg-[#001f35] hover:bg-[#001728] text-slate-200 hover:text-white font-bold text-[11px] rounded-full border border-white/20 flex items-center gap-1.5 transition-all shadow-xs cursor-pointer"
              title="Official Administration Portal"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>{language === 'en' ? 'Officer Portal' : 'अधिकारी'}</span>
            </button>
          </div>

          {/* Mobile Bar Header */}
          <div className="flex items-center lg:hidden w-full justify-between py-1.5">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 rounded-lg text-white hover:bg-[#134679] flex items-center gap-2 text-xs font-semibold cursor-pointer"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              <span>{language === 'en' ? 'Menu' : 'मेनू'}</span>
            </button>

            <div className="flex items-center gap-2">
              {onOpenAiChat && (
                <button
                  onClick={onOpenAiChat}
                  className="px-3 py-1 bg-[#f37021] text-white text-[11px] font-bold rounded-full flex items-center gap-1 cursor-pointer shadow-xs"
                >
                  <Bot className="w-3.5 h-3.5" />
                  <span>BhuMitra</span>
                </button>
              )}

              <button
                onClick={() => handleNavClick('SEARCH')}
                className="px-3 py-1 bg-white text-[#002642] text-[11px] font-bold rounded-full cursor-pointer shadow-xs"
              >
                Search
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Accordion Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-[#134679] py-2 bg-[#002642] divide-y divide-[#134679]/40 max-h-[80vh] overflow-y-auto">
            {/* Home Link */}
            <button
              onClick={() => handleNavClick('HOME')}
              className={`w-full text-left px-4 py-2.5 flex items-center gap-2.5 text-xs font-medium cursor-pointer ${
                portalMode === 'CITIZEN' && activeTab === 'HOME'
                  ? 'bg-[#f37021] text-white font-bold'
                  : 'text-slate-200 hover:bg-[#134679]'
              }`}
            >
              <Home className="w-4 h-4" />
              <span>{language === 'en' ? 'Home' : 'होम'}</span>
            </button>

            {/* Groups */}
            {navGroups.map((group) => (
              <div key={group.id} className="py-2">
                <div className="px-4 py-1 text-[10px] font-black text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                  <group.icon className="w-3 h-3 text-[#f37021]" />
                  <span>{language === 'en' ? group.label : group.labelHi}</span>
                </div>

                <div className="mt-1 space-y-0.5">
                  {group.items.map((item) => {
                    const ItemIcon = item.icon;
                    const isActive = portalMode === 'CITIZEN' && activeTab === item.id;

                    return (
                      <button
                        key={item.id}
                        onClick={() => handleNavClick(item.id)}
                        className={`w-full text-left px-4 py-2 flex items-center justify-between text-xs font-medium cursor-pointer ${
                          isActive
                            ? 'bg-[#f37021] text-white font-bold'
                            : 'text-slate-200 hover:bg-[#134679]'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <ItemIcon className="w-3.5 h-3.5 text-slate-300" />
                          <span>{language === 'en' ? item.label : item.labelHi}</span>
                        </div>
                        {item.badge && (
                          <span className="px-2 py-0.5 rounded-full text-[8px] font-black bg-white/20 text-white">
                            {item.badge}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}

            <div className="p-3">
              <button
                onClick={() => {
                  setPortalMode('OFFICER');
                  setMobileMenuOpen(false);
                }}
                className="w-full py-2.5 bg-[#138808] hover:bg-[#0e6306] text-white font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 cursor-pointer shadow-md"
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
