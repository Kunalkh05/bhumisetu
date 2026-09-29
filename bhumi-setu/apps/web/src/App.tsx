import React, { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { GovHeader } from './components/common/GovHeader';
import { GovNavigation, PublicTab } from './components/common/GovNavigation';
import { GovFooter } from './components/common/GovFooter';
import { ToastContainer } from './components/common/ToastContainer';
import { PublicPortal } from './components/public/PublicPortal';
import { OfficerNavigation } from './components/officer/OfficerNavigation';
import { OfficerDashboard } from './components/officer/OfficerDashboard';
import { CaseWorkspace } from './components/officer/CaseWorkspace';
import { GisMapViewer } from './components/officer/GisMapViewer';
import { DocumentOcrReviewer } from './components/officer/DocumentOcrReviewer';
import { InterventionQueue } from './components/officer/InterventionQueue';
import { ValidationHub } from './components/officer/ValidationHub';
import { ModelObservabilityHub } from './components/officer/ModelObservabilityHub';
import { BulkImportHub } from './components/officer/BulkImportHub';
import { DpdpRetentionHub } from './components/officer/DpdpRetentionHub';
import { AuditLogViewer } from './components/officer/AuditLogViewer';
import { ReraIntegrationHub } from './components/officer/ReraIntegrationHub';
import { DEMO_USERS } from './data/mockData';

const MainContent: React.FC<{ 
  publicTab: PublicTab; 
  setPublicTab: (tab: PublicTab) => void;
  onOpenDemoLogin: () => void;
}> = ({ publicTab, setPublicTab }) => {
  const { portalMode, setPortalMode, officerTab, setOfficerTab, setSelectedCaseId } = useApp();

  return (
    <main className="flex-1" id="main-content">
      {portalMode === 'CITIZEN' ? (
        <PublicPortal 
          activeTab={publicTab} 
          setActiveTab={setPublicTab}
          onNavigateToOfficerCase={(caseId) => {
            setSelectedCaseId(caseId);
            setPortalMode('OFFICER');
            setOfficerTab('CASE_WORKSPACE');
          }}
        />
      ) : (
        <div className="space-y-0">
          <OfficerNavigation />
          
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
            {officerTab === 'DASHBOARD' && (
              <OfficerDashboard 
                onNavigateToCase={(caseId) => {
                  setSelectedCaseId(caseId);
                  setOfficerTab('CASE_WORKSPACE');
                }} 
              />
            )}

            {officerTab === 'CASE_WORKSPACE' && (
              <CaseWorkspace 
                onNavigateToOcr={() => setOfficerTab('OCR_REVIEW')} 
              />
            )}

            {officerTab === 'RERA_GATEWAY' && (
              <ReraIntegrationHub />
            )}

            {officerTab === 'GIS_MAP' && (
              <div className="swaas-card p-6">
                <div className="border-b border-slate-200 pb-3 mb-4 flex justify-between items-center">
                  <div>
                    <h2 className="text-lg font-bold text-[#002642]">
                      PostGIS Spatial Parcel Viewer &amp; Cadastral GIS Engine
                    </h2>
                    <p className="text-slate-500 text-xs mt-0.5">
                      Live ST_Area, ST_Perimeter, geodesic boundary validation and spatial overlap detection
                    </p>
                  </div>
                </div>
                <GisMapViewer 
                  onSelectCase={(caseId) => {
                    setSelectedCaseId(caseId);
                    setOfficerTab('CASE_WORKSPACE');
                  }} 
                />
              </div>
            )}

            {officerTab === 'OCR_REVIEW' && (
              <DocumentOcrReviewer />
            )}

            {officerTab === 'INTERVENTION_QUEUE' && (
              <InterventionQueue 
                onNavigateToCase={(caseId) => {
                  setSelectedCaseId(caseId);
                  setOfficerTab('CASE_WORKSPACE');
                }} 
              />
            )}

            {officerTab === 'VALIDATION_QUEUE' && (
              <ValidationHub />
            )}

            {officerTab === 'MODEL_OBSERVABILITY' && (
              <ModelObservabilityHub />
            )}

            {officerTab === 'BULK_IMPORT' && (
              <BulkImportHub />
            )}

            {officerTab === 'DPDP_RETENTION' && (
              <DpdpRetentionHub />
            )}

            {officerTab === 'AUDIT_LOG' && (
              <AuditLogViewer />
            )}
          </div>
        </div>
      )}
    </main>
  );
};

export default function App() {
  const [publicTab, setPublicTab] = useState<PublicTab>('HOME');
  const [demoLoginOpen, setDemoLoginOpen] = useState(false);

  return (
    <AppProvider>
      <AppShell 
        publicTab={publicTab} 
        setPublicTab={setPublicTab} 
        demoLoginOpen={demoLoginOpen}
        setDemoLoginOpen={setDemoLoginOpen}
      />
    </AppProvider>
  );
}

const AppShell: React.FC<{
  publicTab: PublicTab;
  setPublicTab: (tab: PublicTab) => void;
  demoLoginOpen: boolean;
  setDemoLoginOpen: (open: boolean) => void;
}> = ({ publicTab, setPublicTab, demoLoginOpen, setDemoLoginOpen }) => {
  const { isHighContrast, fontScale, currentUser, setCurrentUser, setPortalMode, addToast } = useApp();

  const handleSelectUser = (user: typeof DEMO_USERS[0]) => {
    setCurrentUser(user);
    if (user.isCitizen) {
      setPortalMode('CITIZEN');
    } else {
      setPortalMode('OFFICER');
    }
    setDemoLoginOpen(false);
    addToast({
      type: 'info',
      message: `Signed in as: ${user.name} (${user.designation})`,
      messageHi: `लॉगिन सफल: ${user.nameHi}`,
    });
  };

  return (
    <div className={`min-h-screen flex flex-col bg-[#f8fafc] text-[#1e293b] ${
      isHighContrast ? 'high-contrast' : ''
    } ${
      fontScale === 'large' ? 'font-large' : fontScale === 'xlarge' ? 'font-xlarge' : 'font-normal'
    }`}>
      <GovHeader 
        onOpenDemoLogin={() => setDemoLoginOpen(true)}
        publicTab={publicTab}
        setPublicTab={setPublicTab}
      />
      <GovNavigation 
        activeTab={publicTab}
        setActiveTab={setPublicTab}
      />
      <MainContent 
        publicTab={publicTab}
        setPublicTab={setPublicTab}
        onOpenDemoLogin={() => setDemoLoginOpen(true)}
      />
      <GovFooter />
      <ToastContainer />

      {/* Official S3WaaS Demo Credentials Modal */}
      {demoLoginOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-2xs" role="dialog">
          <div className="bg-white border border-slate-300 max-w-2xl w-full shadow-2xl rounded-xs overflow-hidden">
            <div className="bg-[#002642] text-white p-4 flex justify-between items-center border-b-2 border-[#f37021]">
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm">BHUMISETU - OFFICIAL DEMO PERSONA DIRECTORY</span>
              </div>
              <button
                onClick={() => setDemoLoginOpen(false)}
                className="px-2.5 py-1 bg-white/10 hover:bg-white/20 text-white font-bold text-xs rounded-xs"
              >
                ✕ Close
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <p className="text-slate-600">
                Select an official role below to simulate the respective administrative or citizen persona with tailored statutory access permissions.
              </p>

              <div className="space-y-2.5 max-h-96 overflow-y-auto">
                {DEMO_USERS.map((user) => (
                  <div
                    key={user.id}
                    className={`p-3.5 border rounded-xs flex justify-between items-center transition-colors ${
                      currentUser.id === user.id 
                        ? 'border-[#0b3866] bg-amber-50/70' 
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <div>
                      <div className="font-bold text-sm text-[#002642]">
                        {user.name} <span className="text-xs font-normal text-slate-500">({user.nameHi})</span>
                      </div>
                      <div className="font-semibold text-slate-700 text-xs mt-0.5">
                        {user.designation} • <span className="text-[#f37021] font-bold">{user.role}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Jurisdiction: {user.jurisdiction.join(', ')}
                      </div>
                    </div>

                    <button
                      onClick={() => handleSelectUser(user)}
                      className={`px-3.5 py-1.5 font-bold text-xs rounded-xs transition-colors ${
                        currentUser.id === user.id
                          ? 'bg-[#138808] text-white'
                          : 'bg-[#0b3866] hover:bg-[#082c52] text-white'
                      }`}
                    >
                      {currentUser.id === user.id ? 'Active Persona' : 'Select Persona'}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-3 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setDemoLoginOpen(false)}
                className="px-4 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold text-xs rounded-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
