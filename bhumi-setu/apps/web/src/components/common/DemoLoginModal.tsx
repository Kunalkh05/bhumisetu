import React from 'react';
import { useApp } from '../../context/AppContext';
import { DEMO_USERS } from '../../data/mockData';
import { ShieldCheck, User, X, Key, CheckCircle, Smartphone, ExternalLink, Info } from 'lucide-react';

export const DemoLoginModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  const { currentUser, setCurrentUser, setPortalMode, language, addToast } = useApp();

  if (!isOpen) return null;

  const handleSelectUser = (user: typeof DEMO_USERS[0]) => {
    setCurrentUser(user);
    if (user.isCitizen) {
      setPortalMode('CITIZEN');
    } else {
      setPortalMode('OFFICER');
    }
    onClose();
    addToast({
      type: 'success',
      message: `Signed in as ${user.name} (${user.designation})`,
      messageHi: `${user.nameHi} के रूप में सफलतापूर्वक लॉगिन किया गया।`,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in" role="dialog" aria-modal="true" aria-labelledby="demo-login-title">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-5 bg-gradient-to-r from-blue-900 to-indigo-950 text-white flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-800/80 border border-blue-600 text-amber-400">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h2 id="demo-login-title" className="text-lg font-bold">
                {language === 'en' ? 'BHUMISETU Temporary Demo Logins' : 'भूमिसेतु अस्थायी डेमो लॉगिन'}
              </h2>
              <p className="text-xs text-blue-200">
                {language === 'en' ? 'Pre-configured credentials for administrative testing & citizen simulation' : 'प्रशासनिक परीक्षण एवं नागरिक सिमुलेशन हेतु पूर्व-कॉन्फ़िगर क्रेडेंशियल्स'}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4">
          <div className="p-3 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded-xl text-xs text-blue-900 dark:text-blue-200 flex items-start gap-2.5">
            <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold mb-0.5">
                {language === 'en' ? 'Role-Based Access Control (RBAC) System:' : 'भूमिका आधारित अभिगम नियंत्रण (RBAC) प्रणाली:'}
              </p>
              <p className="text-slate-700 dark:text-slate-300">
                {language === 'en' 
                  ? 'Each government persona holds distinct statutory powers under RFCTLARR Act 2013. Select any persona to test workflows like Stage Transitions, OCR Document Corrections, or Citizen OTP Access.'
                  : 'प्रत्येक सरकारी पद के पास भूमि अधिग्रहण अधिनियम 2013 के अंतर्गत पृथक अधिकार हैं। किसी भी पद को चुनकर कार्यप्रवाह का परीक्षण करें।'}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {DEMO_USERS.map((user) => {
              const isSelected = currentUser.id === user.id;
              return (
                <div
                  key={user.id}
                  className={`p-4 rounded-xl border transition-all relative flex flex-col justify-between ${
                    isSelected
                      ? 'border-blue-600 bg-blue-50/50 dark:bg-blue-950/40 ring-2 ring-blue-500/20'
                      : 'border-slate-200 dark:border-slate-800 hover:border-blue-400 dark:hover:border-blue-700 bg-slate-50/60 dark:bg-slate-800/40'
                  }`}
                >
                  {isSelected && (
                    <span className="absolute top-3 right-3 flex items-center gap-1 text-[11px] font-bold text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/60 px-2 py-0.5 rounded-full">
                      <CheckCircle className="w-3 h-3" />
                      {language === 'en' ? 'Active' : 'सक्रिय'}
                    </span>
                  )}

                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`p-1.5 rounded-lg ${user.isCitizen ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'}`}>
                        {user.isCitizen ? <Smartphone className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
                      </div>
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                        user.role === 'DISTRICT_COLLECTOR' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-200' :
                        user.role === 'LAO' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200' :
                        user.role === 'SURVEY_OFFICER' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200' :
                        'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200'
                      }`}>
                        {user.role.replace('_', ' ')}
                      </span>
                    </div>

                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {language === 'en' ? user.name : user.nameHi}
                    </h3>
                    <p className="text-xs text-slate-600 dark:text-slate-400 font-medium">
                      {language === 'en' ? user.designation : user.designationHi}
                    </p>

                    <div className="mt-2.5 pt-2 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-400 space-y-1">
                      {user.email && (
                        <div className="truncate"><strong className="text-slate-700 dark:text-slate-300">Email:</strong> {user.email}</div>
                      )}
                      {user.mobile && (
                        <div><strong className="text-slate-700 dark:text-slate-300">Mobile:</strong> {user.mobile}</div>
                      )}
                      {user.caseReference && (
                        <div><strong className="text-slate-700 dark:text-slate-300">Case Ref:</strong> <span className="font-mono text-emerald-700 dark:text-emerald-400">{user.caseReference}</span></div>
                      )}
                      <div><strong className="text-slate-700 dark:text-slate-300">Jurisdiction:</strong> {user.jurisdiction.join(', ')}</div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleSelectUser(user)}
                    className={`mt-4 w-full py-2 px-3 rounded-lg font-bold text-xs transition-colors flex items-center justify-center gap-1.5 ${
                      isSelected
                        ? 'bg-blue-700 text-white hover:bg-blue-800'
                        : 'bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-800 dark:text-slate-200 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300'
                    }`}
                  >
                    <span>{isSelected ? (language === 'en' ? 'Currently Logged In' : 'वर्तमान में सक्रिय') : (language === 'en' ? 'Sign In as This User' : 'इस उपयोगकर्ता से लॉगिन करें')}</span>
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-bold transition-colors"
          >
            {language === 'en' ? 'Close Guide' : 'बंद करें'}
          </button>
        </div>
      </div>
    </div>
  );
};
