import React from 'react';
import { useApp } from '../../context/AppContext';
import { 
  LayoutDashboard, 
  FolderKanban, 
  Map, 
  AlertOctagon, 
  FileCheck, 
  ShieldAlert, 
  Activity, 
  UploadCloud, 
  Lock, 
  History,
  Building2
} from 'lucide-react';
import { OfficerTab } from '../../types';

interface OfficerNavigationProps {
  activeTab?: OfficerTab;
  setActiveTab?: (tab: OfficerTab) => void;
}

export const OfficerNavigation: React.FC<OfficerNavigationProps> = ({ 
  activeTab: propActiveTab, 
  setActiveTab: propSetActiveTab 
}) => {
  const { language, cases, officerTab, setOfficerTab } = useApp();
  const activeTab = propActiveTab ?? officerTab;
  const setActiveTab = propSetActiveTab ?? setOfficerTab;

  // Count open blocking issues across jurisdiction
  const totalBlockingIssues = cases.reduce((sum, c) => 
    sum + c.validationIssues.filter(v => v.severity === 'BLOCKING' && v.resolutionState === 'OPEN').length, 0
  );

  const totalCriticalCases = cases.filter(c => c.riskBand === 'CRITICAL').length;
  const totalPendingOcr = cases.reduce((sum, c) => 
    sum + c.documents.reduce((dSum, doc) => 
      dSum + doc.extractedFields.filter(f => f.reviewState === 'PENDING_REVIEW').length, 0
    ), 0
  );

  const navItems = [
    {
      id: 'DASHBOARD' as OfficerTab,
      label: 'Officer Dashboard',
      labelHi: 'डैशबोर्ड',
      icon: LayoutDashboard,
    },
    {
      id: 'CASE_WORKSPACE' as OfficerTab,
      label: 'Case Workspace (360°)',
      labelHi: 'मामला कार्यस्थान',
      icon: FolderKanban,
    },
    {
      id: 'RERA_GATEWAY' as OfficerTab,
      label: 'RERA Project Status & Cross-Ref',
      labelHi: 'रेरा भूखंड गेटवे',
      icon: Building2,
      badge: 'Sec 11(4)',
      badgeColor: 'bg-[#f37021] text-white',
    },
    {
      id: 'GIS_MAP' as OfficerTab,
      label: 'PostGIS Map Viewer',
      labelHi: 'जीआईएस भू-नक्शा',
      icon: Map,
    },
    {
      id: 'INTERVENTION_QUEUE' as OfficerTab,
      label: 'Intervention Queue',
      labelHi: 'हस्तक्षेप कतार',
      icon: AlertOctagon,
      badge: totalCriticalCases > 0 ? `${totalCriticalCases} At Risk` : undefined,
      badgeColor: 'bg-red-700 text-white',
    },
    {
      id: 'OCR_REVIEW' as OfficerTab,
      label: '7/12 & Sale Deed OCR',
      labelHi: 'ओसीआर सत्यापन',
      icon: FileCheck,
      badge: totalPendingOcr > 0 ? `${totalPendingOcr}` : undefined,
      badgeColor: 'bg-amber-600 text-white',
    },
    {
      id: 'VALIDATION_QUEUE' as OfficerTab,
      label: 'Statutory Rules Engine',
      labelHi: 'सत्यापन इंजन',
      icon: ShieldAlert,
      badge: totalBlockingIssues > 0 ? `${totalBlockingIssues} Blocking` : undefined,
      badgeColor: 'bg-red-700 text-white',
    },
    {
      id: 'MODEL_OBSERVABILITY' as OfficerTab,
      label: 'AI Observability',
      labelHi: 'एआई मॉडल आंकड़े',
      icon: Activity,
    },
    {
      id: 'BULK_IMPORT' as OfficerTab,
      label: 'Bulk Data Migration',
      labelHi: 'थोक डेटा आयात',
      icon: UploadCloud,
    },
    {
      id: 'DPDP_RETENTION' as OfficerTab,
      label: 'DPDP Act & DSR Hub',
      labelHi: 'डीपीडीपी गोपनीयता',
      icon: Lock,
    },
    {
      id: 'AUDIT_LOG' as OfficerTab,
      label: 'Immutable Audit Log',
      labelHi: 'ऑडिट लॉग',
      icon: History,
    },
  ];

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs" aria-label="Officer Workspace Modules">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between gap-4 overflow-x-auto scrollbar-none py-1.5">
          <ul className="flex items-center gap-1 min-w-max" role="tablist">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <li key={item.id} role="presentation">
                  <button
                    role="tab"
                    aria-selected={isActive}
                    onClick={() => setActiveTab(item.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
                      isActive
                        ? 'bg-[#002642] text-white shadow-xs'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-amber-400' : 'text-slate-500'}`} />
                    <span>{language === 'en' ? item.label : item.labelHi}</span>
                    {item.badge && (
                      <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded-md ${
                        isActive ? 'bg-white/20 text-white' : item.badgeColor
                      }`}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </nav>
  );
};
